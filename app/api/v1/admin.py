from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.v1.deps import IngestionServiceDep, SessionDep
from app.core.logging import get_logger
from app.ingestion.rss import RSSNewsSource
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.ingestion_service import SourceReport
from app.services.profile_service import ProfileResult, ProfileService
from app.vector.client import vector_store

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


class IngestRequest(BaseModel):
    feeds: list[str] | None = None
    run_sync: bool = False


class IngestQueued(BaseModel):
    status: str = "queued"
    task_id: str


class IngestResult(BaseModel):
    status: str = "completed"
    reports: list[SourceReport]


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestQueued | IngestResult,
)
async def trigger_ingest(payload: IngestRequest, service: IngestionServiceDep):
    """Kick off ingestion. Async by default (202 + task id); ``run_sync=true``
    runs it in-process and returns the per-source report (handy for demos)."""
    from app.core.config import get_settings

    feeds = payload.feeds or get_settings().news_rss_feeds

    if payload.run_sync:
        sources = [RSSNewsSource(url) for url in feeds]
        reports = await service.ingest_sources(sources)
        return IngestResult(reports=reports)

    from app.workers.dispatch import enqueue_ingest

    task_id = enqueue_ingest(feeds)
    logger.info("ingest_triggered", task_id=task_id, feeds=len(feeds))
    return IngestQueued(task_id=task_id)


@router.post("/profile/{user_id}/rebuild", response_model=ProfileResult)
async def rebuild_profile(user_id: UUID, session: SessionDep) -> ProfileResult:
    """Synchronously rebuild a user's interest vector (normally a Celery task)."""
    async with vector_store() as store:
        service = ProfileService(InteractionRepository(session), ProfileRepository(session), store)
        return await service.rebuild(user_id)
