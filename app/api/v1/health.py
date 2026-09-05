"""Liveness / readiness / metrics endpoints.

- ``GET /health``  — liveness: process is up. No dependency checks.
- ``GET /ready``   — readiness: PostgreSQL, Redis and Qdrant are reachable.
- ``GET /metrics`` — Prometheus exposition format.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_session_factory

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


async def _check_postgres() -> bool:
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - report, don't crash readiness
        logger.warning("healthcheck_failed", component="postgres", error=str(exc))
        return False


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(get_settings().redis_url)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        logger.warning("healthcheck_failed", component="redis", error=str(exc))
        return False


async def _check_qdrant() -> bool:
    try:
        from qdrant_client import AsyncQdrantClient

        settings = get_settings()
        client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            check_compatibility=False,
        )
        try:
            await client.get_collections()
            return True
        finally:
            await client.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("healthcheck_failed", component="qdrant", error=str(exc))
        return False


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready(response: Response) -> dict[str, Any]:
    pg, redis_ok, qdrant_ok = await asyncio.gather(
        _check_postgres(), _check_redis(), _check_qdrant()
    )
    components = {"postgres": pg, "redis": redis_ok, "qdrant": qdrant_ok}
    all_ok = all(components.values())
    if not all_ok:
        response.status_code = 503
    return {
        "status": "ready" if all_ok else "degraded",
        "components": {k: "up" if v else "down" for k, v in components.items()},
    }


@router.get("/metrics", summary="Prometheus metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
