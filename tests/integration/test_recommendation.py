from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.db.models.article import Article
from app.db.models.interaction import Interaction, InteractionType
from app.db.models.profile import UserProfile
from app.db.models.story import Story
from app.db.models.user import User
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.story_repository import StoryRepository
from app.services.recommendation_service import RecommendationService
from tests._fakes import FakeVectorStore

pytestmark = pytest.mark.asyncio


async def _user(db_session, *, profile_vec=None) -> User:
    u = User(email=f"{uuid.uuid4().hex}@e.com", name="U")
    db_session.add(u)
    await db_session.flush()
    if profile_vec is not None:
        db_session.add(
            UserProfile(
                user_id=u.id, embedding=profile_vec, interaction_count=5, embedding_model="m"
            )
        )
        await db_session.flush()
    return u


async def _story(db_session, *, vector, topics, source="src", hours_old=1) -> Story:
    story = Story(canonical_title="s", summary="x", topics=topics)
    db_session.add(story)
    await db_session.flush()
    art = Article(
        title="t",
        url=f"https://e.com/{uuid.uuid4().hex}",
        source=source,
        story_id=story.id,
        published_at=datetime.now(tz=UTC).replace(microsecond=0),
    )
    db_session.add(art)
    await db_session.flush()
    return story, art


def _svc(db_session, store):
    return RecommendationService(
        StoryRepository(db_session),
        InteractionRepository(db_session),
        ProfileRepository(db_session),
        store,
    )


async def test_relevant_story_ranks_above_irrelevant(db_session):
    user = await _user(db_session, profile_vec=[1.0, 0.0, 0.0])
    store = FakeVectorStore()

    relevant, r_art = await _story(db_session, vector=[1.0, 0.0, 0.0], topics=["AI"])
    other, o_art = await _story(db_session, vector=[0.0, 1.0, 0.0], topics=["Sports"])
    store.seed(r_art.id, [1.0, 0.0, 0.0], story_id=relevant.id)
    store.seed(o_art.id, [0.0, 1.0, 0.0], story_id=other.id)

    result = await _svc(db_session, store).generate_feed(user.id, limit=10)

    assert result.cold_start is False
    ids = [r.story.id for r in result.items]
    assert ids[0] == relevant.id
    assert result.items[0].semantic_similarity > result.items[1].semantic_similarity


async def test_disliked_story_is_excluded(db_session):
    user = await _user(db_session, profile_vec=[1.0, 0.0, 0.0])
    store = FakeVectorStore()
    s1, a1 = await _story(db_session, vector=[1.0, 0.0, 0.0], topics=["AI"])
    s2, a2 = await _story(db_session, vector=[0.9, 0.1, 0.0], topics=["AI"])
    store.seed(a1.id, [1.0, 0.0, 0.0], story_id=s1.id)
    store.seed(a2.id, [1.0, 0.0, 0.0], story_id=s2.id)

    db_session.add(
        Interaction(user_id=user.id, article_id=a1.id, interaction_type=InteractionType.DISLIKE)
    )
    await db_session.flush()

    result = await _svc(db_session, store).generate_feed(user.id, limit=10)
    assert [r.story.id for r in result.items] == [s2.id]


async def test_consumed_story_is_excluded(db_session):
    user = await _user(db_session, profile_vec=[1.0, 0.0, 0.0])
    store = FakeVectorStore()
    s1, a1 = await _story(db_session, vector=[1.0, 0.0, 0.0], topics=["AI"])
    store.seed(a1.id, [1.0, 0.0, 0.0], story_id=s1.id)
    db_session.add(
        Interaction(user_id=user.id, article_id=a1.id, interaction_type=InteractionType.CLICK)
    )
    await db_session.flush()

    result = await _svc(db_session, store).generate_feed(user.id, limit=10)
    assert result.items == []


async def test_cold_start_uses_recent_stories(db_session):
    user = await _user(db_session)  # no profile
    store = FakeVectorStore()
    await _story(db_session, vector=[1.0, 0.0, 0.0], topics=["AI"])
    await _story(db_session, vector=[0.0, 1.0, 0.0], topics=["Cloud"])

    result = await _svc(db_session, store).generate_feed(user.id, limit=10)
    assert result.cold_start is True
    assert len(result.items) == 2
    assert all(r.semantic_similarity == 0.0 for r in result.items)
