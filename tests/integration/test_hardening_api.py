"""Rate limiting, security headers and CORS wiring on the real app."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.session import get_db_session

pytestmark = pytest.mark.asyncio


def _app_with_settings(monkeypatch, db_session, **overrides):
    settings = Settings(secret_key="test-secret-value-long", **overrides)
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    from app.main import create_app

    app = create_app()

    async def _session():
        yield db_session

    app.dependency_overrides[get_db_session] = _session
    return app


async def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_security_headers_present(monkeypatch, db_session):
    app = _app_with_settings(monkeypatch, db_session, rate_limit_enabled=False)
    async with await _client(app) as ac:
        resp = await ac.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


async def test_rate_limit_returns_429_after_the_limit(monkeypatch, db_session, fake_redis):
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: fake_redis)
    app = _app_with_settings(
        monkeypatch,
        db_session,
        rate_limit_enabled=True,
        rate_limit_requests=3,
        rate_limit_window_seconds=60,
    )
    async with await _client(app) as ac:
        codes = [(await ac.get("/api/v1/articles")).status_code for _ in range(5)]
    assert codes.count(200) == 3
    assert codes[-1] == 429
    async with await _client(app) as ac:
        resp = await ac.get("/api/v1/articles")
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"
    assert "Retry-After" in resp.headers


async def test_health_is_exempt_from_rate_limiting(monkeypatch, db_session, fake_redis):
    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: fake_redis)
    app = _app_with_settings(
        monkeypatch, db_session, rate_limit_enabled=True, rate_limit_requests=1
    )
    async with await _client(app) as ac:
        codes = [(await ac.get("/health")).status_code for _ in range(5)]
    assert codes == [200] * 5


async def test_rate_limiter_fails_open_when_redis_down(monkeypatch, db_session):
    class _Broken:
        async def incr(self, *_a):
            raise ConnectionError("no redis")

    monkeypatch.setattr("app.core.rate_limit.get_redis", lambda: _Broken())
    app = _app_with_settings(
        monkeypatch, db_session, rate_limit_enabled=True, rate_limit_requests=1
    )
    async with await _client(app) as ac:
        codes = [(await ac.get("/api/v1/articles")).status_code for _ in range(4)]
    assert codes == [200] * 4
