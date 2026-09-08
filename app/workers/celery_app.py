"""Celery application singleton, beat schedule, and observability signals."""

from __future__ import annotations

import contextlib
import time
from typing import Any

from celery import Celery
from celery.signals import (
    setup_logging,
    task_failure,
    task_postrun,
    task_prerun,
    worker_process_init,
    worker_ready,
)

from app.core.config import get_settings
from app.core.logging import bind_context, clear_context, configure_logging, get_logger
from app.core.metrics import (
    celery_task_latency_seconds,
    celery_tasks_total,
    start_worker_metrics_server,
)

settings = get_settings()
logger = get_logger(__name__)

_task_started_at: dict[str, float] = {}
_metrics_started = False


@setup_logging.connect
def _configure(**_kwargs: object) -> None:
    configure_logging(settings.log_level, json_output=not settings.debug)


def _start_metrics(**_kwargs: object) -> None:
    """Bind the metrics HTTP server once per process. Connected to both
    ``worker_process_init`` (prefork children) and ``worker_ready`` (solo pool /
    main process) so it works regardless of the pool."""
    global _metrics_started
    if _metrics_started or not settings.worker_metrics_port:
        return
    _metrics_started = True
    start_worker_metrics_server(settings.worker_metrics_port)


worker_process_init.connect(_start_metrics)
worker_ready.connect(_start_metrics)


@task_prerun.connect
def _bind_task_context(task_id: str, task: Any, **_kwargs: object) -> None:
    clear_context()
    request_id = None
    with contextlib.suppress(Exception):
        request_id = task.request.get("request_id")
    bind_context(task_id=task_id, task_name=task.name, request_id=request_id)
    _task_started_at[task_id] = time.perf_counter()


@task_postrun.connect
def _record_task(task_id: str, task: Any, state: str, **_kwargs: object) -> None:
    started = _task_started_at.pop(task_id, None)
    if started is not None:
        celery_task_latency_seconds.labels(task=task.name).observe(
            time.perf_counter() - started
        )
    celery_tasks_total.labels(task=task.name, state=str(state)).inc()
    clear_context()


@task_failure.connect
def _log_task_failure(
    task_id: str, exception: BaseException, sender: Any, **_kwargs: object
) -> None:
    logger.error(
        "celery_task_failure",
        task_name=getattr(sender, "name", "?"),
        error=str(exception),
    )


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
