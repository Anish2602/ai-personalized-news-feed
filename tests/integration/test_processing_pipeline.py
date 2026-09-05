from __future__ import annotations

import uuid

import pytest

from app.db.models.article import Article, ArticleProcessingStatus
from app.db.models.processing import ProcessingJobStatus
from app.repositories.processing_repository import ProcessingRepository
from app.workers.processing_tasks import _record_failure, _run_pipeline

pytestmark = pytest.mark.asyncio


async def _article_with_job(db_session) -> Article:
    article = Article(title="T", url=f"https://ex.com/{uuid.uuid4().hex}", source="s")
    db_session.add(article)
    await db_session.flush()
    await ProcessingRepository(db_session).create_job(article.id)
    return article


async def test_pipeline_advances_state_to_completed(db_session):
    article = await _article_with_job(db_session)

    result = await _run_pipeline(db_session, article.id)
    assert result["status"] == "completed"

    await db_session.flush()
    await db_session.refresh(article)
    assert article.processing_status == ArticleProcessingStatus.COMPLETED
    job = await ProcessingRepository(db_session).get_latest_job(article.id)
    assert job.status == ProcessingJobStatus.COMPLETED
    assert job.started_at is not None and job.completed_at is not None


async def test_pipeline_is_idempotent(db_session):
    article = await _article_with_job(db_session)
    await _run_pipeline(db_session, article.id)
    again = await _run_pipeline(db_session, article.id)
    assert again["status"] == "already_completed"


async def test_record_failure_permanent_marks_failed(db_session):
    article = await _article_with_job(db_session)
    await _record_failure(db_session, article.id, "boom", retry=False)

    job = await ProcessingRepository(db_session).get_latest_job(article.id)
    assert job.status == ProcessingJobStatus.FAILED
    assert job.error == "boom"
    await db_session.flush()
    await db_session.refresh(article)
    assert article.processing_status == ArticleProcessingStatus.FAILED


async def test_record_failure_retry_keeps_job_pending_and_counts(db_session):
    article = await _article_with_job(db_session)
    await _record_failure(db_session, article.id, "transient", retry=True)

    job = await ProcessingRepository(db_session).get_latest_job(article.id)
    assert job.status == ProcessingJobStatus.PENDING
    assert job.retry_count == 1
