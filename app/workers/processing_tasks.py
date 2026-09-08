"""Per-article AI processing pipeline task.

Lifecycle (idempotency, state transitions, exponential backoff, failure
accounting) plus the Phase 4 body: clean → embed → semantic dedup into a story.
Topic classification and summarization are added in Phase 5.
"""

from __future__ import annotations

from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.classifier import Classifier
from app.ai.embeddings import build_embedding_text, get_embedding_provider
from app.ai.llm import get_llm_provider
from app.ai.summarizer import Summarizer
from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError, UpstreamError
from app.core.logging import bind_context, get_logger
from app.core.metrics import articles_processed_total, worker_failures_total
from app.db.models.processing import ProcessingJobStatus
from app.repositories.article_repository import ArticleRepository
from app.repositories.processing_repository import ProcessingRepository
from app.repositories.story_repository import StoryRepository
from app.services.deduplication_service import DeduplicationService
from app.services.enrichment_service import EnrichmentService
from app.vector.client import vector_store
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
    httpx.HTTPError,
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

    articles = ArticleRepository(session)
    article = await articles.get(article_id)
    if article is None:
        raise LookupError(f"article {article_id} not found")  # permanent

    await repo.mark_processing(job)

    text = build_embedding_text(
        title=article.title, description=article.description, content=article.content
    )

    stories = StoryRepository(session)
    try:
        async with vector_store() as store:
            dedup = DeduplicationService(
                articles, stories, store, get_embedding_provider()
            )
            dedup_result = await dedup.deduplicate(article, text=text)
    except (httpx.HTTPError, ConnectionError, TimeoutError, OSError) as exc:
        raise UpstreamError(f"embedding/vector failure: {exc}") from exc

    settings = get_settings()
    llm = get_llm_provider()
    enrichment = EnrichmentService(
        articles,
        stories,
        Summarizer(llm),
        Classifier(llm, settings.topic_taxonomy),
        settings.topic_taxonomy,
    )
    enrich_result = await enrichment.enrich(
        article, text=text, story_id=dedup_result.story_id
    )

    await repo.mark_completed(job)
    logger.info(
        "process_article_pipeline",
        article_id=str(article_id),
        story_id=str(dedup_result.story_id),
        duplicate=dedup_result.is_duplicate,
        topics=enrich_result.article_topics,
        summarized=enrich_result.summarized,
    )
    return {
        "status": "completed",
        "article_id": str(article_id),
        "story_id": str(dedup_result.story_id),
        "duplicate": str(dedup_result.is_duplicate),
    }


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
    bind_context(article_id=article_id)  # task_id/request_id bound by celery signal
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
