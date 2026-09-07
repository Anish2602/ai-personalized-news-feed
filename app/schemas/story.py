from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class StoryArticleRef(ORMModel):
    id: UUID
    title: str
    url: str
    source: str
    published_at: datetime | None


class StoryRead(ORMModel):
    id: UUID
    canonical_title: str
    summary: str | None
    key_points: list[str]
    topics: list[str]
    created_at: datetime
    updated_at: datetime


class StoryDetail(StoryRead):
    article_count: int
    sources: list[str]
    articles: list[StoryArticleRef]
