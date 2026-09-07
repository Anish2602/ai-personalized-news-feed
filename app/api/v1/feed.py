from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import RecommendationServiceDep
from app.core.metrics import feed_generation_latency_seconds, feed_requests_total
from app.core.security import get_current_user_id
from app.schemas.feed import FeedItem, FeedResponse
from app.services.recommendation_service import RankedStory

router = APIRouter(tags=["feed"])


def _to_item(ranked: RankedStory, *, debug: bool) -> FeedItem:
    story = ranked.story
    published = [a.published_at for a in story.articles if a.published_at]
    return FeedItem(
        story_id=story.id,
        canonical_title=story.canonical_title,
        summary=story.summary,
        topics=story.topics,
        sources=sorted({a.source for a in story.articles}),
        article_count=len(story.articles),
        published_at=max(published) if published else story.created_at,
        score=ranked.rank.score,
        features=ranked.rank.features if debug else None,
        contributions=ranked.rank.contributions if debug else None,
    )


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    service: RecommendationServiceDep,
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(default=20, ge=1, le=50),
    debug: bool = Query(default=False, description="include per-feature score breakdown"),
) -> FeedResponse:
    feed_requests_total.inc()
    started = time.perf_counter()
    result = await service.generate_feed(user_id, limit=limit)
    feed_generation_latency_seconds.observe(time.perf_counter() - started)

    return FeedResponse(
        items=[_to_item(r, debug=debug) for r in result.items],
        next_cursor=None,  # Phase 7
        cold_start=result.cold_start,
    )
