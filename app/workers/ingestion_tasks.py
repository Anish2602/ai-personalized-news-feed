from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import worker_failures_total
from app.ingestion.rss import RSSNewsSource
from app.repositories.article_repository import ArticleRepository
from app.repositories.processing_repository import ProcessingRepository
from app.services.ingestion_service import IngestionService
from app.workers.celery_app import celery_app
from app.workers.runtime import run_with_session

logger = get_logger(__name__)


def _enqueue_processing(article_id: UUID) -> None:
    # Imported here to avoid a circular import at module load.
    from app.workers.processing_tasks import process_article

    process_article.delay(str(article_id))


@celery_app.task(
    name="app.workers.ingestion_tasks.ingest_news",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def ingest_news(self, feeds: list[str] | None = None) -> dict[str, object]:
    """Fetch every configured RSS feed and persist new articles. Idempotent."""
    settings = get_settings()
    feed_urls = feeds or settings.news_rss_feeds
    logger.info("ingest_news_start", feeds=len(feed_urls))

    try:
        async def _op(session):
            service = IngestionService(
                ArticleRepository(session),
                ProcessingRepository(session),
                queue_processing=_enqueue_processing,
            )
            sources = [RSSNewsSource(url) for url in feed_urls]
            reports = await service.ingest_sources(sources)
            return [r.model_dump() for r in reports]

        reports = run_with_session(_op)
    except Exception as exc:
        worker_failures_total.labels(task="ingest_news").inc()
        logger.exception("ingest_news_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=self.default_retry_delay) from exc

    total_inserted = sum(r["inserted"] for r in reports)
    logger.info("ingest_news_done", inserted=total_inserted, sources=len(reports))
    return {"inserted": total_inserted, "reports": reports}
