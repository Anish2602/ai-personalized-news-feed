from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.api.v1.deps import get_feed_service
from app.cache.feed_cache import FeedCache
from app.db.models.article import Article
from app.db.models.profile import UserProfile
from app.db.models.story import Story
from app.db.models.user import User
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.story_repository import StoryRepository
from app.services.feed_service import FeedService
from app.services.recommendation_service import RecommendationService
from tests._fakes import FakeVectorStore

pytestmark = pytest.mark.asyncio


@pytest.fixture
def store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture(autouse=True)
def _override_feed(client, db_session, store, fake_redis):
    def _factory():
        recommender = RecommendationService(
            StoryRepository(db_session),
            InteractionRepository(db_session),
            ProfileRepository(db_session),
            store,
        )
        cache = FeedCache(fake_redis, ttl_seconds=300)
        return FeedService(recommender, cache, StoryRepository(db_session))

    client._transport.app.dependency_overrides[get_feed_service] = _factory


async def _user(db_session) -> User:
    u = User(email=f"{uuid.uuid4().hex}@e.com", name="U")
    db_session.add(u)
    await db_session.flush()
    return u


async def _story(db_session, *, topics) -> tuple[Story, Article]:
    s = Story(canonical_title="Big story", summary="sum", topics=topics)
    db_session.add(s)
    await db_session.flush()
    a = Article(
        title="t", url=f"https://e.com/{uuid.uuid4().hex}", source="Ars Technica",
        story_id=s.id, published_at=datetime.now(tz=UTC).replace(microsecond=0),
    )
    db_session.add(a)
    await db_session.flush()
    return s, a


async def test_feed_requires_user_header(client):
    resp = await client.get("/api/v1/feed")
    assert resp.status_code == 401


async def test_bad_user_header_is_401(client):
    resp = await client.get("/api/v1/feed", headers={"X-User-Id": "not-a-uuid"})
    assert resp.status_code == 401


async def test_cold_start_feed_returns_recent_stories(client, db_session):
    user = await _user(db_session)
    await _story(db_session, topics=["AI"])
    await _story(db_session, topics=["Cloud"])

    resp = await client.get("/api/v1/feed", headers={"X-User-Id": str(user.id)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["cold_start"] is True
    assert len(body["items"]) == 2
    assert body["items"][0]["features"] is None  # debug off


async def test_feed_debug_includes_feature_breakdown(client, db_session, store):
    user = await _user(db_session)
    s, a = await _story(db_session, topics=["AI"])
    db_session.add(
        UserProfile(
            user_id=user.id, embedding=[1.0, 0.0, 0.0], interaction_count=3, embedding_model="m"
        )
    )
    store.seed(a.id, [1.0, 0.0, 0.0], story_id=s.id)
    await db_session.flush()

    resp = await client.get(
        "/api/v1/feed", params={"debug": True}, headers={"X-User-Id": str(user.id)}
    )
    item = resp.json()["items"][0]
    assert item["features"]["semantic"] > 0
    assert set(item["contributions"]) == {
        "semantic", "freshness", "popularity", "source_quality", "diversity"
    }


async def test_feed_paginates_over_a_stable_snapshot(client, db_session):
    user = await _user(db_session)
    for _ in range(5):
        await _story(db_session, topics=["AI"])

    headers = {"X-User-Id": str(user.id)}
    seen: list[str] = []
    cursor = None
    for _ in range(10):
        params = {"limit": 2}
        if cursor:
            params["cursor"] = cursor
        body = (await client.get("/api/v1/feed", params=params, headers=headers)).json()
        seen += [i["story_id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 5


async def test_bad_cursor_is_422(client, db_session):
    user = await _user(db_session)
    await _story(db_session, topics=["AI"])
    resp = await client.get(
        "/api/v1/feed", params={"cursor": "@@@"}, headers={"X-User-Id": str(user.id)}
    )
    assert resp.status_code == 422
