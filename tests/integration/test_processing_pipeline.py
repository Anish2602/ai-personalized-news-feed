from __future__ import annotations

import contextlib
import uuid

import pytest

from app.core.exceptions import LLMOutputError, UpstreamError
from app.db.models.article import Article, ArticleProcessingStatus
from app.db.models.processing import ProcessingJobStatus
from app.db.models.story import Story
from app.repositories.processing_repository import ProcessingRepository
from app.workers import processing_tasks
from app.workers.processing_tasks import _record_failure, _run_pipeline
from tests._fakes import FakeEmbeddingProvider, FakeLLMProvider, FakeVectorStore

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _stub_ai(monkeypatch):
    store = FakeVectorStore()

    @contextlib.asynccontextmanager
    async def _vs():
        yield store

    monkeypatch.setattr(processing_tasks, "vector_store", _vs)
    monkeypatch.setattr(processing_tasks, "get_embedding_provider", FakeEmbeddingProvider)
    # LLM disabled by default -> extractive summary + keyword classification.
    monkeypatch.setattr(processing_tasks, "get_llm_provider", lambda: None)


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
    assert article.story_id is not None
    assert article.embedding_reference == str(article.id)
    assert result["story_id"] == str(article.story_id)
    job = await ProcessingRepository(db_session).get_latest_job(article.id)
    assert job.status == ProcessingJobStatus.COMPLETED
    assert job.started_at is not None and job.completed_at is not None

    # enrichment ran (fallback path): article classified, story summarized
    assert article.topics  # non-empty
    story = await db_session.get(Story, article.story_id)
    assert story.summary
    assert set(article.topics).issubset(set(story.topics))


async def test_malformed_llm_output_fails_the_job(db_session, monkeypatch):
    # 1 call for the classifier + up to 2 for the summarizer, all unparseable.
    monkeypatch.setattr(
        processing_tasks,
        "get_llm_provider",
        lambda: FakeLLMProvider(["nonsense", "still nonsense", "nope"]),
    )
    article = await _article_with_job(db_session)

    with pytest.raises(LLMOutputError):
        await _run_pipeline(db_session, article.id)


async def test_missing_article_is_retryable_not_permanent(db_session):
    """A Celery worker can pick up process_article before the transaction that
    inserted the article commits (dual-write race between DB + broker). That
    must surface as a retryable UpstreamError, not a permanent failure or a
    raw FK-violation crash — see app/workers/processing_tasks.py."""
    with pytest.raises(UpstreamError):
        await _run_pipeline(db_session, uuid.uuid4())


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
