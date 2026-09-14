from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


class TaxonomyResponse(BaseModel):
    topics: list[str]


@router.get("", response_model=TaxonomyResponse)
async def get_taxonomy() -> TaxonomyResponse:
    """The fixed set of topic labels articles/stories are classified into
    (`TOPIC_TAXONOMY`). Only interests whose name matches one of these can
    ever affect ranking — clients use this to offer valid suggestions rather
    than free text that can never match anything."""
    return TaxonomyResponse(topics=get_settings().topic_taxonomy)
