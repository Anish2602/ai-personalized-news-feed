"""Per-article AI processing pipeline task.

Phase 3 wires the task lifecycle — idempotency, state transitions, exponential
backoff, failure accounting. The pipeline body (clean → embed → semantic dedup →
classify → summarize) is filled in Phases 4–5; today it is a no-op that just
advances the job/article state so the machinery is testable end to end.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError, UpstreamError
from app.core.logging import bind_context, clear_context, get_logger
from app.core.metrics import articles_processed_total, worker_failures_total
from app.db.models.processing import ProcessingJobStatus
from app.repositories.processing_repository import ProcessingRepository
from app.workers.celery_app import celery_app
from app.workers.runtime import run_with_session

logger = get_logger(__name__)

# Errors worth retrying (transient dependency failures). Everything else is
# treated as permanent and fails the job immediately.
RETRYABLE_ERRORS: tuple[type[Exception], ...] = (
    UpstreamError,
    ServiceUnavailableError,
    ConnectionError,
    TimeoutError,
)

_settings = get_settings()


def _backoff_seconds(attempt: int) -> int:
    return _settings.task_retry_backoff_seconds * (2**attempt)


async def _run_pipeline(session: AsyncSession, article_id: UUID) -> dict[str, str]:
    repo = ProcessingRepository(session)
    job = await repo.get_latest_job(article_id)
    if job is None:
        job = await repo.create_job(article_id)
    if job.status == ProcessingJobStatus.COMPLETED:
        return {"status": "already_completed", "article_id": str(article_id)}

    await repo.mark_processing(job)

    # --- Phase 4/5: pipeline steps land here ---
    #   text = clean(article)
    #   vector = await embed(text)
    #   story = await deduplicate(article, vector)
    #   topics = await classify(text)
    #   summary = await summarize(text)
    logger.info("process_article_pipeline", article_id=str(article_id), pipeline="noop")

    await repo.mark_completed(job)
    return {"status": "completed", "article_id": str(article_id)}


async def _record_failure(
    session: AsyncSession, article_id: UUID, error: str, *, retry: bool
) -> None:
    repo = ProcessingRepository(session)
    job = await repo.get_latest_job(article_id)
    if job is not None:
        await repo.mark_failed(job, error, retry=retry)


@celery_app.task(
    name="app.workers.processing_tasks.process_article",
    bind=True,
    max_retries=_settings.task_max_retries,
    acks_late=True,
)
def process_article(self, article_id: str) -> dict[str, str]:
    bind_context(task_id=self.request.id, article_id=article_id)
    aid = UUID(article_id)
    try:
        outcome = run_with_session(lambda s: _run_pipeline(s, aid))
        articles_processed_total.labels(result=outcome["status"]).inc()
        return outcome
    except RETRYABLE_ERRORS as exc:
        msg = str(exc)
        will_retry = self.request.retries < self.max_retries
        worker_failures_total.labels(task="process_article").inc()
        run_with_session(lambda s: _record_failure(s, aid, msg, retry=will_retry))
        logger.warning(
            "process_article_retry", error=msg, attempt=self.request.retries + 1
        )
        raise self.retry(exc=exc, countdown=_backoff_seconds(self.request.retries)) from exc
    except Exception as exc:  # permanent failure
        msg = str(exc)
        worker_failures_total.labels(task="process_article").inc()
        articles_processed_total.labels(result="failed").inc()
        run_with_session(lambda s: _record_failure(s, aid, msg, retry=False))
        logger.exception("process_article_failed", error=msg)
        raise
    finally:
        clear_context()
