from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)


class UserRead(ORMModel):
    id: UUID
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime


class InterestAssignItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    weight: float = Field(default=1.0, ge=-10.0, le=10.0)


class InterestAssignRequest(BaseModel):
    items: list[InterestAssignItem] = Field(min_length=1, max_length=50)


class UserInterestRead(BaseModel):
    name: str
    weight: float
    created_at: datetime
