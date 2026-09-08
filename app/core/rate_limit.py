"""Redis fixed-window rate limiting.

Per-caller (``X-User-Id`` if present, else client IP), counted in
``RATE_LIMIT_WINDOW_SECONDS`` buckets. Health/metrics/docs are never limited.
**Fails open** — if Redis is unavailable the request is allowed rather than
dropped.
"""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.cache.redis import get_redis
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_EXEMPT_PREFIXES = ("/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json")


def _client_id(request: Request) -> str:
    user = request.headers.get("X-User-Id")
    if user:
        return f"user:{user}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:  # noqa: ANN001
        super().__init__(app)
        self._limit = settings.rate_limit_requests
        self._window = settings.rate_limit_window_seconds

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        if request.url.path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        window = int(time.time()) // self._window
        key = f"ratelimit:{_client_id(request)}:{window}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, self._window)
        except Exception as exc:  # noqa: BLE001 - fail open
            logger.warning("rate_limit_backend_unavailable", error=str(exc))
            return await call_next(request)

        if count > self._limit:
            retry_after = self._window - (int(time.time()) % self._window)
            logger.info("rate_limited", client=_client_id(request), count=count)
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests."}},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self._limit - count))
        return response
