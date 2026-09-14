from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class InteractionType(enum.StrEnum):
    VIEW = "VIEW"
    CLICK = "CLICK"
    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    SAVE = "SAVE"
    SKIP = "SKIP"
    SHARE = "SHARE"


class Interaction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interactions"
    __table_args__ = (
        Index("ix_interactions_user_created", "user_id", "created_at"),
        Index("ix_interactions_article_type", "article_id", "interaction_type"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType, name="interaction_type"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
