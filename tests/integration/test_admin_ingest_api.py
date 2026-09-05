from __future__ import annotations

import pytest

from app.api.v1.deps import get_queue_processing
from app.ingestion.base import RawArticle

pytestmark = pytest.mark.asyncio

CANNED = [
    RawArticle(title="One", url="https://ex.com/1", source="Canned"),
    RawArticle(title="Two", url="https://ex.com/2", source="Canned"),
]


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    async def _fetch(self):  # noqa: ANN001
        return list(CANNED)

    monkeypatch.setattr("app.ingestion.rss.RSSNewsSource.fetch", _fetch)


async def test_sync_ingest_returns_report(client):
    calls: list = []
    client._transport.app.dependency_overrides[get_queue_processing] = lambda: calls.append

    resp = await client.post(
        "/api/v1/admin/ingest",
        json={"run_sync": True, "feeds": ["https://ex.com/feed.xml"]},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "completed"
    assert body["reports"][0]["inserted"] == 2
    assert body["reports"][0]["source"] == "ex.com"
    assert len(calls) == 2


async def test_sync_ingest_is_idempotent(client):
    client._transport.app.dependency_overrides[get_queue_processing] = lambda: (lambda _a: None)
    payload = {"run_sync": True, "feeds": ["https://ex.com/feed.xml"]}

    first = (await client.post("/api/v1/admin/ingest", json=payload)).json()
    second = (await client.post("/api/v1/admin/ingest", json=payload)).json()
    assert first["reports"][0]["inserted"] == 2
    assert second["reports"][0]["inserted"] == 0
    assert second["reports"][0]["duplicates"] == 2


async def test_async_ingest_enqueues_task(client, monkeypatch):
    monkeypatch.setattr("app.workers.dispatch.enqueue_ingest", lambda feeds=None: "task-abc")
    resp = await client.post("/api/v1/admin/ingest", json={"feeds": ["https://ex.com/f.xml"]})
    assert resp.status_code == 202
    assert resp.json() == {"status": "queued", "task_id": "task-abc"}
