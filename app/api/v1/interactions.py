from __future__ import annotations

from fastapi import APIRouter, status

from app.api.v1.deps import InteractionServiceDep
from app.schemas.interaction import InteractionCreate, InteractionRead

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionRead, status_code=status.HTTP_201_CREATED)
async def create_interaction(
    payload: InteractionCreate, service: InteractionServiceDep
) -> InteractionRead:
    interaction = await service.record(payload)
    return InteractionRead.model_validate(interaction)
