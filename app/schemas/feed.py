from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.ranking.scorer import RankFeatures


class FeedItem(BaseModel):
    story_id: UUID
    canonical_title: str
    summary: str | None
    topics: list[str]
    sources: list[str]
    article_count: int
    published_at: datetime | None
    score: float
    # Populated only when ?debug=true
    features: RankFeatures | None = None
    contributions: dict[str, float] | None = None


class FeedResponse(BaseModel):
    items: list[FeedItem]
    next_cursor: str | None = None
    cold_start: bool
