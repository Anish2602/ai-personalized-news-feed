from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response schemas populated directly from SQLAlchemy rows."""

    model_config = ConfigDict(from_attributes=True)


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
