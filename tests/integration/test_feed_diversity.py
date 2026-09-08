from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

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


async def test_feed_does_not_stack_one_topic(db_session, fake_redis):
    user = User(email=f"{uuid.uuid4().hex}@e.com", name="U")
    db_session.add(user)
    await db_session.flush()

    # 6 AI stories (freshest) then 2 Cloud — naive ranking would be AI×6, Cloud×2
    now = datetime.now(tz=UTC).replace(microsecond=0)
    for i in range(6):
        topic, age = "AI", i
        s = Story(canonical_title=f"ai {i}", summary="x", topics=[topic])
        db_session.add(s)
        await db_session.flush()
        db_session.add(
            Article(
                title="t",
                url=f"https://e.com/{uuid.uuid4().hex}",
                source="s",
                story_id=s.id,
                published_at=now - timedelta(hours=age),
            )
        )
    for i in range(2):
        s = Story(canonical_title=f"cloud {i}", summary="x", topics=["Cloud"])
        db_session.add(s)
        await db_session.flush()
        db_session.add(
            Article(
                title="t",
                url=f"https://e.com/{uuid.uuid4().hex}",
                source="s",
                story_id=s.id,
                published_at=now - timedelta(hours=10 + i),
            )
        )
    await db_session.flush()

    rec = RecommendationService(
        StoryRepository(db_session),
        InteractionRepository(db_session),
        ProfileRepository(db_session),
        FakeVectorStore(),
    )
    svc = FeedService(rec, FeedCache(fake_redis, ttl_seconds=300), StoryRepository(db_session))
    page = await svc.get_page(user.id, limit=20, cursor=None)

    primaries = [i.topics[0] for i in page.items]
    assert len(primaries) == 8
    # FEED_DIVERSITY_MAX_STREAK defaults to 2 -> never 3 identical in a row
    assert not any(
        primaries[i] == primaries[i + 1] == primaries[i + 2] for i in range(len(primaries) - 2)
    )
