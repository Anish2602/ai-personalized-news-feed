"""Ingestion orchestration: fetch → normalize → URL-dedup → persist → queue AI.

Stage 1 of the two-stage deduplication strategy is here (cheap URL-level dedup).
Stage 2 (semantic) runs in the processing pipeline (Phase 4) so we never embed
an article we already have.

Idempotent: re-running against the same feed inserts nothing new.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import UUID

from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.metrics import articles_ingested_total, duplicate_articles_total
from app.ingestion.base import NewsSource
from app.ingestion.normalizer import normalize
from app.repositories.article_repository import ArticleRepository
from app.repositories.processing_repository import ProcessingRepository

logger = get_logger(__name__)

# Called with a new article id so the caller can enqueue AI processing. The
# service stays ignorant of Celery; workers inject ``process_article.delay``.
QueueProcessing = Callable[[UUID], None]


class SourceReport(BaseModel):
    source: str
    fetched: int = 0
    inserted: int = 0
    duplicates: int = 0
    invalid: int = 0
    error: str | None = None


class IngestionService:
    def __init__(
        self,
        articles: ArticleRepository,
        processing: ProcessingRepository,
        queue_processing: QueueProcessing | None = None,
    ) -> None:
        self.articles = articles
        self.processing = processing
        self._queue_processing = queue_processing or (lambda _aid: None)

    async def ingest_source(self, source: NewsSource) -> SourceReport:
        report = SourceReport(source=source.name)
        try:
            raws = await source.fetch()
        except Exception as exc:  # noqa: BLE001 - one bad source must not abort the run
            logger.warning("ingest_source_failed", source=source.name, error=str(exc))
            report.error = str(exc)
            return report

        report.fetched = len(raws)
        seen_in_batch: set[str] = set()
        for raw in raws:
            norm = normalize(raw)
            if norm is None:
                report.invalid += 1
                continue
            assert norm.url and norm.title
            if norm.url in seen_in_batch:
                report.duplicates += 1
                continue
            seen_in_batch.add(norm.url)

            if await self.articles.get_by_url(norm.url) is not None:
                report.duplicates += 1
                duplicate_articles_total.labels(stage="url").inc()
                continue

            article = await self.articles.create(
                title=norm.title,
                url=norm.url,
                source=norm.source,
                description=norm.description,
                content=norm.content,
                published_at=norm.published_at,
            )
            await self.processing.create_job(article.id)
            self._queue_processing(article.id)
            report.inserted += 1
            articles_ingested_total.labels(source=norm.source).inc()

        logger.info(
            "ingest_source_done",
            source=source.name,
            inserted=report.inserted,
            duplicates=report.duplicates,
            invalid=report.invalid,
        )
        return report

    async def ingest_sources(self, sources: Iterable[NewsSource]) -> list[SourceReport]:
        return [await self.ingest_source(s) for s in sources]
