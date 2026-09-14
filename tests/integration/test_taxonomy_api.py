from __future__ import annotations

import pytest

from app.core.config import get_settings

pytestmark = pytest.mark.asyncio


async def test_taxonomy_returns_configured_topics(client):
    resp = await client.get("/api/v1/taxonomy")
    assert resp.status_code == 200
    body = resp.json()
    assert body["topics"] == get_settings().topic_taxonomy
    assert "Sports" in body["topics"]
