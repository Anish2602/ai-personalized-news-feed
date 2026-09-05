from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db.models.article import ArticleProcessingStatus
from app.schemas.common import ORMModel


class ArticleRead(ORMModel):
    id: UUID
    story_id: UUID | None
    title: str
    description: str | None
    url: str
    source: str
    published_at: datetime | None
    processing_status: ArticleProcessingStatus
    created_at: datetime


class ArticleDetail(ArticleRead):
    content: str | None
    embedding_reference: str | None
