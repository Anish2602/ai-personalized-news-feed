from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.models.interaction import InteractionType
from app.schemas.common import ORMModel


class InteractionCreate(BaseModel):
    user_id: UUID
    article_id: UUID
    interaction_type: InteractionType


class InteractionRead(ORMModel):
    id: UUID
    user_id: UUID
    article_id: UUID
    interaction_type: InteractionType
    created_at: datetime
