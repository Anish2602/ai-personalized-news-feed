from __future__ import annotations

import uuid

import pytest

from app.db.models.article import Article
from app.db.models.interaction import Interaction, InteractionType
from app.db.models.user import User
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.profile_service import ProfileService
from tests._fakes import FakeVectorStore

pytestmark = pytest.mark.asyncio


async def _user(db_session) -> User:
    u = User(email=f"{uuid.uuid4().hex}@e.com", name="U")
    db_session.add(u)
    await db_session.flush()
    return u


async def _article(db_session) -> Article:
    a = Article(title="t", url=f"https://e.com/{uuid.uuid4().hex}", source="s")
    db_session.add(a)
    await db_session.flush()
    return a


def _svc(db_session, store):
    return ProfileService(InteractionRepository(db_session), ProfileRepository(db_session), store)


async def test_rebuild_builds_vector_from_weighted_interactions(db_session):
    user = await _user(db_session)
    liked, disliked = await _article(db_session), await _article(db_session)

    store = FakeVectorStore()
    store.seed(liked.id, [1.0, 0.0, 0.0])
    store.seed(disliked.id, [1.0, 0.0, 0.0])

    db_session.add_all(
        [
            Interaction(
                user_id=user.id, article_id=liked.id, interaction_type=InteractionType.LIKE
            ),
            Interaction(
                user_id=user.id, article_id=disliked.id, interaction_type=InteractionType.DISLIKE
            ),
        ]
    )
    await db_session.flush()

    result = await _svc(db_session, store).rebuild(user.id)

    assert result.has_vector is True
    assert result.interaction_count == 2
    profile = await ProfileRepository(db_session).get(user.id)
    assert profile.embedding is not None
    assert profile.embedding_model  # recorded for invalidation


async def test_rebuild_with_no_interactions_stores_null_vector(db_session):
    user = await _user(db_session)
    result = await _svc(db_session, FakeVectorStore()).rebuild(user.id)

    assert result.has_vector is False
    profile = await ProfileRepository(db_session).get(user.id)
    assert profile is not None
    assert profile.embedding is None


async def test_rebuild_is_idempotent(db_session):
    user = await _user(db_session)
    art = await _article(db_session)
    store = FakeVectorStore()
    store.points[str(art.id)] = ([0.0, 1.0, 0.0], {})
    db_session.add(
        Interaction(user_id=user.id, article_id=art.id, interaction_type=InteractionType.SAVE)
    )
    await db_session.flush()

    first = await _svc(db_session, store).rebuild(user.id)
    second = await _svc(db_session, store).rebuild(user.id)
    p1 = (await ProfileRepository(db_session).get(user.id)).embedding
    assert first.model_dump() == second.model_dump()
    assert p1 == pytest.approx([0.0, 1.0, 0.0])
