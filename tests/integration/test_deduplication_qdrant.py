from __future__ import annotations

import uuid

import pytest

from app.db.models.article import Article
from app.repositories.article_repository import ArticleRepository
from app.repositories.story_repository import StoryRepository
from app.services.deduplication_service import DeduplicationService
from tests._fakes import FakeEmbeddingProvider

pytestmark = pytest.mark.asyncio

# Deterministic vectors: "same story" texts collapse to one direction.
EMB = FakeEmbeddingProvider(
    mapping={
        "rate decision": [1.0, 0.0, 0.0],
        "rate decision (wire copy)": [0.99, 0.01, 0.0],
        "sports result": [0.0, 1.0, 0.0],
    }
)


async def _article(db_session, title: str) -> Article:
    art = Article(title=title, url=f"https://ex.com/{uuid.uuid4().hex}", source="s")
    db_session.add(art)
    await db_session.flush()
    return art


def _service(db_session, store) -> DeduplicationService:
    return DeduplicationService(
        ArticleRepository(db_session), StoryRepository(db_session), store, EMB,
        threshold=0.9, top_k=5,
    )


async def test_first_article_starts_a_story(db_session, qdrant_store):
    art = await _article(db_session, "A")
    result = await _service(db_session, qdrant_store).deduplicate(art, text="rate decision")

    assert result.is_duplicate is False
    await db_session.flush()
    await db_session.refresh(art)
    assert art.story_id == result.story_id
    assert art.embedding_reference == str(art.id)


async def test_near_duplicate_joins_same_story(db_session, qdrant_store):
    svc = _service(db_session, qdrant_store)
    a = await _article(db_session, "A")
    r1 = await svc.deduplicate(a, text="rate decision")

    b = await _article(db_session, "B")
    r2 = await svc.deduplicate(b, text="rate decision (wire copy)")

    assert r2.is_duplicate is True
    assert r2.story_id == r1.story_id
    assert r2.similarity is not None and r2.similarity >= 0.9


async def test_unrelated_article_gets_its_own_story(db_session, qdrant_store):
    svc = _service(db_session, qdrant_store)
    a = await _article(db_session, "A")
    r1 = await svc.deduplicate(a, text="rate decision")

    c = await _article(db_session, "C")
    r3 = await svc.deduplicate(c, text="sports result")

    assert r3.is_duplicate is False
    assert r3.story_id != r1.story_id
