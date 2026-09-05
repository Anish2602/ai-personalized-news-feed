"""Thin helpers that turn a domain event into an enqueued Celery task.

Keeping these here (not in the services) means the service layer never imports
Celery and stays unit-testable with a plain callable.
"""

from __future__ import annotations

from uuid import UUID


def enqueue_process_article(article_id: UUID) -> None:
    from app.workers.processing_tasks import process_article

    process_article.delay(str(article_id))


def enqueue_ingest(feeds: list[str] | None = None) -> str:
    from app.workers.ingestion_tasks import ingest_news

    return ingest_news.delay(feeds).id
