from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    interests: Mapped[list[UserInterest]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Interest(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "interests"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    users: Mapped[list[UserInterest]] = relationship(
        back_populates="interest", cascade="all, delete-orphan"
    )


class UserInterest(Base):
    __tablename__ = "user_interests"

    # Composite primary key == the required composite uniqueness constraint on
    # (user_id, interest_id).
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    interest_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interests.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="interests")
    interest: Mapped[Interest] = relationship(back_populates="users")
