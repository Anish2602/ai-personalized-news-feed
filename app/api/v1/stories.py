from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.v1.deps import StoryServiceDep
from app.schemas.common import CursorPage
from app.schemas.story import StoryArticleRef, StoryDetail, StoryRead

router = APIRouter(prefix="/stories", tags=["stories"])


@router.get("", response_model=CursorPage[StoryRead])
async def list_stories(
    service: StoryServiceDep,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = Query(default=None),
) -> CursorPage[StoryRead]:
    rows, next_cursor = await service.list_stories(limit=limit, cursor=cursor)
    return CursorPage[StoryRead](
        items=[StoryRead.model_validate(r) for r in rows], next_cursor=next_cursor
    )


@router.get("/{story_id}", response_model=StoryDetail)
async def get_story(story_id: UUID, service: StoryServiceDep) -> StoryDetail:
    story = await service.get_story(story_id)
    return StoryDetail(
        id=story.id,
        canonical_title=story.canonical_title,
        summary=story.summary,
        key_points=story.key_points,
        topics=story.topics,
        created_at=story.created_at,
        updated_at=story.updated_at,
        article_count=len(story.articles),
        sources=service.sources_for(story),
        articles=[StoryArticleRef.model_validate(a) for a in story.articles],
    )
