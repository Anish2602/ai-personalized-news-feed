from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import FeedServiceDep
from app.core.metrics import feed_requests_total
from app.core.security import get_current_user_id
from app.schemas.feed import FeedResponse

router = APIRouter(tags=["feed"])


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    service: FeedServiceDep,
    user_id: UUID = Depends(get_current_user_id),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None, description="opaque cursor from a prior response"),
    debug: bool = Query(default=False, description="include per-feature score breakdown"),
) -> FeedResponse:
    feed_requests_total.inc()
    page = await service.get_page(user_id, limit=limit, cursor=cursor, debug=debug)
    return FeedResponse(items=page.items, next_cursor=page.next_cursor, cold_start=page.cold_start)
