from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ArticleProcessingStatus(enum.StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Article(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "articles"

    story_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Point into Qdrant (the vector store owns the actual embedding).
    embedding_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    topics: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    processing_status: Mapped[ArticleProcessingStatus] = mapped_column(
        Enum(ArticleProcessingStatus, name="article_processing_status"),
        default=ArticleProcessingStatus.PENDING,
        server_default=ArticleProcessingStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    story: Mapped[Story | None] = relationship(back_populates="articles")  # noqa: F821
