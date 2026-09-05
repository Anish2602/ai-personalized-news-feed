from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.db.models.article import Article
from app.db.models.interaction import Interaction

pytestmark = pytest.mark.asyncio


async def _make_user(client) -> str:
    return (
        await client.post(
            "/api/v1/users", json={"email": f"{uuid.uuid4().hex}@example.com", "name": "U"}
        )
    ).json()["id"]


async def _make_article(db_session) -> Article:
    article = Article(title="T", url=f"https://example.com/{uuid.uuid4().hex}", source="seed")
    db_session.add(article)
    await db_session.flush()
    return article


async def test_record_interaction_persists(client, db_session):
    user_id = await _make_user(client)
    article = await _make_article(db_session)

    resp = await client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "article_id": str(article.id), "interaction_type": "LIKE"},
    )
    assert resp.status_code == 201
    assert resp.json()["interaction_type"] == "LIKE"

    count = await db_session.scalar(
        select(func.count())
        .select_from(Interaction)
        .where(Interaction.user_id == uuid.UUID(user_id))
    )
    assert count == 1


async def test_unknown_user_is_404(client, db_session):
    article = await _make_article(db_session)
    resp = await client.post(
        "/api/v1/interactions",
        json={
            "user_id": str(uuid.uuid4()),
            "article_id": str(article.id),
            "interaction_type": "VIEW",
        },
    )
    assert resp.status_code == 404


async def test_unknown_article_is_404(client):
    user_id = await _make_user(client)
    resp = await client.post(
        "/api/v1/interactions",
        json={
            "user_id": user_id,
            "article_id": str(uuid.uuid4()),
            "interaction_type": "VIEW",
        },
    )
    assert resp.status_code == 404


async def test_invalid_interaction_type_is_422(client, db_session):
    user_id = await _make_user(client)
    article = await _make_article(db_session)
    resp = await client.post(
        "/api/v1/interactions",
        json={"user_id": user_id, "article_id": str(article.id), "interaction_type": "NOPE"},
    )
    assert resp.status_code == 422
