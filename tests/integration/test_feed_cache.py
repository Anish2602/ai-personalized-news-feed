from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.cache.feed_cache import FeedCache
from app.db.models.article import Article
from app.db.models.story import Story
from app.db.models.user import User
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.story_repository import StoryRepository
from app.services.feed_service import FeedService
from app.services.recommendation_service import RecommendationService
from tests._fakes import FakeVectorStore

pytestmark = pytest.mark.asyncio


async def _seed(db_session, n=3) -> User:
    user = User(email=f"{uuid.uuid4().hex}@e.com", name="U")
    db_session.add(user)
    await db_session.flush()
    for _ in range(n):
        s = Story(canonical_title="s", summary="x", topics=["AI"])
        db_session.add(s)
        await db_session.flush()
        db_session.add(
            Article(
                title="t", url=f"https://e.com/{uuid.uuid4().hex}", source="src",
                story_id=s.id, published_at=datetime.now(tz=UTC).replace(microsecond=0),
            )
        )
    await db_session.flush()
    return user


def _service(db_session, cache) -> FeedService:
    rec = RecommendationService(
        StoryRepository(db_session),
        InteractionRepository(db_session),
        ProfileRepository(db_session),
        FakeVectorStore(),
    )
    return FeedService(rec, cache, StoryRepository(db_session))


async def test_second_request_is_a_cache_hit(db_session, fake_redis):
    user = await _seed(db_session)
    cache = FeedCache(fake_redis, ttl_seconds=300)
    svc = _service(db_session, cache)

    first = await svc.get_page(user.id, limit=10, cursor=None)
    second = await svc.get_page(user.id, limit=10, cursor=None)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert [i.story_id for i in first.items] == [i.story_id for i in second.items]


async def test_ttl_is_applied(db_session, fake_redis):
    user = await _seed(db_session, n=1)
    cache = FeedCache(fake_redis, ttl_seconds=123)
    await _service(db_session, cache).get_page(user.id, limit=10, cursor=None)

    ttl = await fake_redis.ttl(FeedCache.key(user.id))
    assert 0 < ttl <= 123


async def test_invalidate_forces_regeneration(db_session, fake_redis):
    user = await _seed(db_session)
    cache = FeedCache(fake_redis, ttl_seconds=300)
    svc = _service(db_session, cache)

    await svc.get_page(user.id, limit=10, cursor=None)
    await cache.invalidate(user.id)
    after = await svc.get_page(user.id, limit=10, cursor=None)
    assert after.cache_hit is False


async def test_high_signal_interaction_invalidates_via_service(db_session, fake_redis):
    from app.db.models.interaction import InteractionType
    from app.repositories.article_repository import ArticleRepository
    from app.repositories.user_repository import UserRepository
    from app.schemas.interaction import InteractionCreate
    from app.services.interaction_service import InteractionService

    user = await _seed(db_session)
    cache = FeedCache(fake_redis, ttl_seconds=300)
    await _service(db_session, cache).get_page(user.id, limit=10, cursor=None)
    assert await fake_redis.exists(FeedCache.key(user.id))

    article = (await db_session.execute(select(Article))).scalars().first()
    interactions = InteractionService(
        InteractionRepository(db_session),
        UserRepository(db_session),
        ArticleRepository(db_session),
        feed_cache=cache,
    )
    await interactions.record(
        InteractionCreate(
            user_id=user.id, article_id=article.id, interaction_type=InteractionType.LIKE
        )
    )
    assert not await fake_redis.exists(FeedCache.key(user.id))
