"""Personalized ranking.

    load profile → candidate stories (Qdrant search by profile vector) → drop
    consumed/disliked → per-story ranking features → transparent linear score →
    sort → topic-diversity interleave.

Returns the *full* ranked list; slicing into pages and caching is the
``FeedService``'s job. Cold start (no profile) → semantic term is 0 and the feed
falls back to freshness + popularity + source quality.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.interaction import InteractionType
from app.db.models.story import Story
from app.ranking.diversity import interleave_by_topic, topic_rarity_scores
from app.ranking.freshness import freshness_score
from app.ranking.scorer import RankFeatures, RankResult, normalize_counts, score
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.story_repository import StoryRepository
from app.vector.search import VectorStoreProtocol

logger = get_logger(__name__)

_POPULARITY_TYPES = (
    InteractionType.VIEW,
    InteractionType.LIKE,
    InteractionType.SAVE,
    InteractionType.SHARE,
)


@dataclass
class RankedStory:
    story: Story
    rank: RankResult
    semantic_similarity: float


@dataclass
class FeedResult:
    items: list[RankedStory]
    cold_start: bool


class RecommendationService:
    def __init__(
        self,
        stories: StoryRepository,
        interactions: InteractionRepository,
        profiles: ProfileRepository,
        vectors: VectorStoreProtocol,
    ) -> None:
        self.stories = stories
        self.interactions = interactions
        self.profiles = profiles
        self.vectors = vectors
        self._settings = get_settings()

    async def rank_stories(self, user_id: UUID) -> FeedResult:
        settings = self._settings
        profile = await self.profiles.get(user_id)

        semantic_by_story: dict[UUID, float] = {}
        cold_start = not (profile and profile.embedding)

        if not cold_start:
            matches = await self.vectors.search(
                profile.embedding, limit=settings.feed_candidate_pool
            )
            for m in matches:
                raw_sid = m.payload.get("story_id")
                if not raw_sid:
                    continue
                sid = UUID(raw_sid)
                semantic_by_story[sid] = max(semantic_by_story.get(sid, 0.0), m.score)
            candidates = await self.stories.get_many_with_articles(list(semantic_by_story))
        else:
            candidates = await self.stories.recent_with_articles(limit=settings.feed_candidate_pool)

        if not candidates:
            return FeedResult(items=[], cold_start=cold_start)

        candidate_ids = [s.id for s in candidates]
        signals = await self.interactions.user_story_signals(user_id, candidate_ids)
        candidates = [s for s in candidates if not self._excluded(signals.get(s.id, set()))]
        if not candidates:
            return FeedResult(items=[], cold_start=cold_start)

        engagement = await self.interactions.story_engagement([s.id for s in candidates])
        popularity = normalize_counts(
            {s.id: self._popularity_raw(engagement.get(s.id, {})) for s in candidates}
        )
        rarity = topic_rarity_scores(candidates)
        weights = settings.ranking_weights
        now = datetime.now(tz=UTC)

        ranked: list[RankedStory] = []
        for s in candidates:
            features = RankFeatures(
                semantic=0.0 if cold_start else semantic_by_story.get(s.id, 0.0),
                freshness=freshness_score(
                    self._published_at(s),
                    now=now,
                    decay_hours=settings.freshness_decay_hours,
                ),
                popularity=popularity.get(s.id, 0.0),
                source_quality=self._source_quality(s),
                diversity=rarity.get(s.id, 0.0),
            )
            ranked.append(
                RankedStory(
                    story=s,
                    rank=score(features, weights),
                    semantic_similarity=features.semantic,
                )
            )

        ranked.sort(key=lambda r: r.rank.score, reverse=True)
        ordered = interleave_by_topic(
            ranked,
            max_streak=settings.feed_diversity_max_streak,
            topic_of=lambda r: r.story.topics,
        )
        logger.info(
            "feed_ranked",
            user_id=str(user_id),
            candidates=len(candidates),
            ranked=len(ordered),
            cold_start=cold_start,
        )
        return FeedResult(items=ordered, cold_start=cold_start)

    def _excluded(self, signals: set[InteractionType]) -> bool:
        if InteractionType.DISLIKE in signals:
            return True
        consumed = {InteractionType.CLICK, InteractionType.VIEW} & signals
        return self._settings.feed_exclude_consumed and bool(consumed)

    def _popularity_raw(self, counts: dict[InteractionType, int]) -> float:
        w = self._settings.interaction_weights
        return sum(abs(w[t.value]) * counts.get(t, 0) for t in _POPULARITY_TYPES)

    @staticmethod
    def _published_at(story: Story) -> datetime | None:
        stamps = [a.published_at for a in story.articles if a.published_at]
        return max(stamps) if stamps else story.created_at

    def _source_quality(self, story: Story) -> float:
        table = self._settings.source_quality
        default = self._settings.source_quality_default
        sources = {a.source for a in story.articles}
        if not sources:
            return default
        return sum(table.get(src, default) for src in sources) / len(sources)
