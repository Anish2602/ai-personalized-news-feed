from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Story(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A canonical news event. Duplicate articles are grouped under one story."""

    __tablename__ = "stories"

    canonical_title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    topics: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    articles: Mapped[list[Article]] = relationship(  # noqa: F821
        back_populates="story", cascade="all, delete-orphan"
    )
