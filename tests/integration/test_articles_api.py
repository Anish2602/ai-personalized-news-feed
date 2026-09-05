from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.db.models.article import Article

pytestmark = pytest.mark.asyncio


async def _seed(db_session, n: int) -> list[Article]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [
        Article(
            title=f"Article {i}",
            url=f"https://example.com/a/{i}",
            source="seed" if i % 2 == 0 else "other",
            description=f"desc {i}",
            published_at=base + timedelta(hours=i),
        )
        for i in range(n)
    ]
    db_session.add_all(rows)
    await db_session.flush()
    return rows


async def test_get_article_and_404(client, db_session):
    [row] = await _seed(db_session, 1)
    resp = await client.get(f"/api/v1/articles/{row.id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Article 0"

    missing = await client.get(f"/api/v1/articles/{uuid.uuid4()}")
    assert missing.status_code == 404


async def test_list_pagination_walks_all_rows_without_overlap(client, db_session):
    await _seed(db_session, 25)

    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        params = {"limit": 10}
        if cursor:
            params["cursor"] = cursor
        body = (await client.get("/api/v1/articles", params=params)).json()
        seen.extend(item["id"] for item in body["items"])
        cursor = body["next_cursor"]
        pages += 1
        if cursor is None:
            break
        assert pages < 10  # guard against an infinite loop

    assert len(seen) == 25
    assert len(set(seen)) == 25  # no duplicates across pages


async def test_list_filters_by_source(client, db_session):
    await _seed(db_session, 10)
    body = (await client.get("/api/v1/articles", params={"source": "seed", "limit": 50})).json()
    assert body["items"]
    assert all(item["source"] == "seed" for item in body["items"])


async def test_bad_cursor_is_422(client, db_session):
    resp = await client.get("/api/v1/articles", params={"cursor": "!!!not-base64!!!"})
    assert resp.status_code == 422
