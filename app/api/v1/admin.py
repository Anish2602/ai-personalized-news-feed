from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.api.v1.deps import IngestionServiceDep
from app.core.logging import get_logger
from app.ingestion.rss import RSSNewsSource
from app.services.ingestion_service import SourceReport

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
