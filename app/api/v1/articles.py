from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.deps import ArticleServiceDep
from app.schemas.article import ArticleDetail, ArticleRead
from app.schemas.common import CursorPage

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("", response_model=CursorPage[ArticleRead])
async def list_articles(
    service: ArticleServiceDep,
    limit: int = Query(default=20, ge=1, le=50),
    source: str | None = Query(default=None),
    status: str | None = Query(default=None, description="PENDING|PROCESSING|COMPLETED|FAILED"),
    cursor: str | None = Query(default=None, description="Opaque cursor from a prior response"),
) -> CursorPage[ArticleRead]:
    rows, next_cursor = await service.list_articles(
        limit=limit, source=source, status=status, cursor=cursor
    )
    return CursorPage[ArticleRead](
        items=[ArticleRead.model_validate(r) for r in rows], next_cursor=next_cursor
    )


@router.get("/{article_id}", response_model=ArticleDetail)
async def get_article(article_id: UUID, service: ArticleServiceDep) -> ArticleDetail:
    return ArticleDetail.model_validate(await service.get_article(article_id))
