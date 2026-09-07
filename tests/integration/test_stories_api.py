from __future__ import annotations

import uuid

import pytest

from app.db.models.article import Article
from app.db.models.story import Story

pytestmark = pytest.mark.asyncio


async def _story(db_session, *, n_articles=2, **kw) -> Story:
    story = Story(
        canonical_title=kw.get("title", "Big event"),
        summary=kw.get("summary", "It happened."),
        key_points=kw.get("key_points", ["a", "b"]),
        topics=kw.get("topics", ["Technology"]),
    )
    db_session.add(story)
    await db_session.flush()
    for i in range(n_articles):
        db_session.add(
            Article(
                title=f"coverage {i}",
                url=f"https://ex.com/{uuid.uuid4().hex}",
                source=f"src{i}",
                story_id=story.id,
            )
        )
    await db_session.flush()
    return story


async def test_get_story_detail(client, db_session):
    story = await _story(db_session, n_articles=3)
    resp = await client.get(f"/api/v1/stories/{story.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "It happened."
    assert body["key_points"] == ["a", "b"]
    assert body["topics"] == ["Technology"]
    assert body["article_count"] == 3
    assert body["sources"] == ["src0", "src1", "src2"]
    assert len(body["articles"]) == 3


async def test_get_missing_story_404(client):
    resp = await client.get(f"/api/v1/stories/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_list_stories_paginates(client, db_session):
    for _ in range(5):
        await _story(db_session, n_articles=1)

    seen = []
    cursor = None
    for _ in range(10):
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = (await client.get("/api/v1/stories", params=params)).json()
        seen += [s["id"] for s in body["items"]]
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 5
