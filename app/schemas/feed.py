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
    # The story's most-recently-published member article. Interactions are
    # recorded per article (POST /interactions needs an article_id), and
    # clients need a real link to send a reader to, so the feed exposes one
    # representative article per story rather than making the client fetch
    # GET /stories/{id} just to find one to react to / read.
    primary_article_id: UUID
    primary_article_url: str
    # Populated only when ?debug=true
    features: RankFeatures | None = None
    contributions: dict[str, float] | None = None


class FeedResponse(BaseModel):
    items: list[FeedItem]
    next_cursor: str | None = None
    cold_start: bool
