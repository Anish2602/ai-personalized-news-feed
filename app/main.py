"""FastAPI application factory + ASGI entrypoint.

Wiring only — no business logic. Schema management is Alembic's job, so there is
deliberately no ``create_all`` on startup.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import bind_context, clear_context, configure_logging, get_logger
from app.core.metrics import http_request_latency_seconds, http_requests_total
from app.db.session import dispose_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=not settings.debug)
    logger.info("app_startup", environment=settings.environment, app=settings.app_name)
    yield
    await dispose_engine()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=not settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        clear_context()
        bind_context(request_id=request_id)
        start = time.perf_counter()
        route = request.scope.get("route")
        path_label = getattr(route, "path", request.url.path)
        try:
            response = await call_next(request)
        finally:
            elapsed = time.perf_counter() - start
            http_request_latency_seconds.labels(request.method, path_label).observe(elapsed)
        http_requests_total.labels(request.method, path_label, response.status_code).inc()
        response.headers["X-Request-Id"] = request_id
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(elapsed * 1000, 2),
        )
        clear_context()
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
