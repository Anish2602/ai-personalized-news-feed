"""Cache-aware, paginated feed.

    request → Redis snapshot?
      hit  → slice page by offset cursor
      miss → RecommendationService.rank_stories → store snapshot → slice

Pagination is a stable offset into one cached snapshot, so every page of a walk
is consistent even as new stories arrive. Invalidation (on profile-changing
interactions, or a profile rebuild) just deletes the snapshot key.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel

from app.cache.feed_cache import CachedFeed, CachedFeedItem, FeedCache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import feed_cache_hits_total, feed_cache_misses_total
from app.core.pagination import decode_offset_cursor, encode_offset_cursor
from app.db.models.story import Story
from app.repositories.story_repository import StoryRepository
from app.schemas.feed import FeedItem
from app.services.recommendation_service import RecommendationService

logger = get_logger(__name__)


class FeedPage(BaseModel):
    items: list[FeedItem]
    next_cursor: str | None
    cold_start: bool
    cache_hit: bool


class FeedService:
    def __init__(
        self,
        recommender: RecommendationService,
        cache: FeedCache,
        stories: StoryRepository,
    ) -> None:
        self.recommender = recommender
        self.cache = cache
        self.stories = stories
        self._settings = get_settings()

    async def get_page(
        self, user_id: UUID, *, limit: int, cursor: str | None, debug: bool = False
    ) -> FeedPage:
        limit = max(1, min(limit, self._settings.feed_max_limit))
        offset = decode_offset_cursor(cursor) if cursor else 0

        snapshot = await self.cache.get(user_id)
        cache_hit = snapshot is not None
        if snapshot is None:
            snapshot = await self._build_snapshot(user_id)
            await self.cache.set(user_id, snapshot)
        (feed_cache_hits_total if cache_hit else feed_cache_misses_total).inc()

        window = snapshot.items[offset : offset + limit]
        stories = {
            s.id: s for s in await self.stories.get_many_with_articles([w.story_id for w in window])
        }
        items = [
            self._to_item(w, stories[w.story_id], debug=debug)
            for w in window
            if w.story_id in stories
        ]
        has_more = offset + limit < len(snapshot.items)
        return FeedPage(
            items=items,
            next_cursor=encode_offset_cursor(offset + limit) if has_more else None,
            cold_start=snapshot.cold_start,
            cache_hit=cache_hit,
        )

    async def _build_snapshot(self, user_id: UUID) -> CachedFeed:
        result = await self.recommender.rank_stories(user_id)
        return CachedFeed(
            generated_at=datetime.now(tz=UTC),
            cold_start=result.cold_start,
            items=[
                CachedFeedItem(
                    story_id=r.story.id,
                    primary_article_id=self._primary_article(r.story).id,
                    score=r.rank.score,
                    features=r.rank.features,
                    contributions=r.rank.contributions,
                )
                for r in result.items
            ],
        )

    @staticmethod
    def _primary_article(story: Story):
        """The story's freshest member article — used as the one clients
        record interactions (like/dislike/save/...) against."""
        return max(story.articles, key=lambda a: a.published_at or a.created_at)

    @staticmethod
    def _to_item(cached: CachedFeedItem, story: Story, *, debug: bool) -> FeedItem:
        published = [a.published_at for a in story.articles if a.published_at]
        return FeedItem(
            story_id=story.id,
            canonical_title=story.canonical_title,
            summary=story.summary,
            topics=story.topics,
            sources=sorted({a.source for a in story.articles}),
            article_count=len(story.articles),
            published_at=max(published) if published else story.created_at,
            score=cached.score,
            primary_article_id=cached.primary_article_id,
            features=cached.features if debug else None,
            contributions=cached.contributions if debug else None,
        )
