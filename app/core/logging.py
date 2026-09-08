"""Structured JSON logging via structlog, bridged with the stdlib logging module.

Emits one JSON object per log line with a stable schema. A ``contextvars``-backed
binder lets request/task middleware attach ``request_id``, ``user_id``,
``article_id`` and ``task_id`` that then appear on every downstream log line.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_CONFIGURED = False

_SHARED_PROCESSORS: list[Any] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    renderer: Any = (
        structlog.processors.JSONRenderer()
        if json_output
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=_SHARED_PROCESSORS,
        )
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Attach key/values to the current context (request or task scope)."""
    structlog.contextvars.bind_contextvars(**{k: v for k, v in kwargs.items() if v is not None})


def get_context() -> dict[str, Any]:
    """Snapshot of the currently-bound context vars (e.g. to propagate the
    ``request_id`` from an API request onto an enqueued Celery task)."""
    return dict(structlog.contextvars.get_contextvars())


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
