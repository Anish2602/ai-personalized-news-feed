"""Celery application singleton + beat schedule."""

from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()


@setup_logging.connect
def _configure(**_kwargs: object) -> None:
    configure_logging(settings.log_level, json_output=not settings.debug)


celery_app = Celery(
    "ai_news_feed",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.ingestion_tasks",
        "app.workers.processing_tasks",
        "app.workers.feed_tasks",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=settings.task_retry_backoff_seconds,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "ingest-news-periodically": {
            "task": "app.workers.ingestion_tasks.ingest_news",
            "schedule": float(settings.ingest_interval_minutes * 60),
        }
    },
)
