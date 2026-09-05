"""Celery application singleton.

Phase 1: only the app object + config wiring exists so the ``worker`` container
and ``docker compose`` are valid. Task modules and the beat schedule are added
in Phase 3.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, json_output=not settings.debug)

celery_app = Celery(
    "ai_news_feed",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
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
    timezone="UTC",
    enable_utc=True,
)

# Phase 3+: celery_app.autodiscover_tasks(["app.workers"])
