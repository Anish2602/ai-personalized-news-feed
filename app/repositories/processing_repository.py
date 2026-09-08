from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.db.models.article import Article, ArticleProcessingStatus
from app.db.models.processing import ProcessingJob, ProcessingJobStatus
from app.repositories.base import BaseRepository


def _now() -> datetime:
    return datetime.now(tz=UTC)


class ProcessingRepository(BaseRepository):
    async def create_job(self, article_id: UUID) -> ProcessingJob:
        job = ProcessingJob(article_id=article_id, status=ProcessingJobStatus.PENDING)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_latest_job(self, article_id: UUID) -> ProcessingJob | None:
        result = await self.session.execute(
            select(ProcessingJob)
            .where(ProcessingJob.article_id == article_id)
            .order_by(ProcessingJob.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_processing(self, job: ProcessingJob) -> None:
        job.status = ProcessingJobStatus.PROCESSING
        job.started_at = _now()
        job.error = None
        await self._set_article_status(job.article_id, ArticleProcessingStatus.PROCESSING)

    async def mark_completed(self, job: ProcessingJob) -> None:
        job.status = ProcessingJobStatus.COMPLETED
        job.completed_at = _now()
        job.error = None
        await self._set_article_status(job.article_id, ArticleProcessingStatus.COMPLETED)

    async def mark_failed(self, job: ProcessingJob, error: str, *, retry: bool) -> None:
        job.error = error[:2000]
        if retry:
            job.retry_count += 1
            job.status = ProcessingJobStatus.PENDING
        else:
            job.status = ProcessingJobStatus.FAILED
            job.completed_at = _now()
            await self._set_article_status(job.article_id, ArticleProcessingStatus.FAILED)

    async def _set_article_status(self, article_id: UUID, status: ArticleProcessingStatus) -> None:
        article = await self.session.get(Article, article_id)
        if article is not None:
            article.processing_status = status
