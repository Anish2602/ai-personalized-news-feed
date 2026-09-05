from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_liveness(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_requests_total" in resp.text


@pytest.mark.asyncio
async def test_ready_reports_components(client):
    # No infra running in unit CI -> readiness is degraded but well-formed.
    resp = await client.get("/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert set(body["components"]) == {"postgres", "redis", "qdrant"}


@pytest.mark.asyncio
async def test_request_id_header_roundtrips(client):
    resp = await client.get("/health", headers={"X-Request-Id": "abc-123"})
    assert resp.headers["X-Request-Id"] == "abc-123"
