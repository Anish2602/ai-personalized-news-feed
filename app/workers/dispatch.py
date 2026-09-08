"""Thin helpers that turn a domain event into an enqueued Celery task.

Keeping these here (not in the services) means the service layer never imports
Celery and stays unit-testable with a plain callable. Each helper forwards the
current ``request_id`` as a task header so worker logs correlate with the API
request that triggered them.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.logging import get_context


def _headers() -> dict[str, Any]:
    request_id = get_context().get("request_id")
    return {"request_id": request_id} if request_id else {}


def enqueue_process_article(article_id: UUID) -> None:
    from app.workers.processing_tasks import process_article

    process_article.apply_async(args=[str(article_id)], headers=_headers())


def enqueue_ingest(feeds: list[str] | None = None) -> str:
    from app.workers.ingestion_tasks import ingest_news

    return ingest_news.apply_async(args=[feeds], headers=_headers()).id


def enqueue_profile_rebuild(user_id: UUID) -> None:
    from app.workers.feed_tasks import rebuild_user_profile

    rebuild_user_profile.apply_async(args=[str(user_id)], headers=_headers())
