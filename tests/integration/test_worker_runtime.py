"""The sync↔async bridge that Celery tasks use.

These are plain sync tests: ``run_with_session`` calls ``asyncio.run`` internally,
exactly as a synchronous Celery task does, so it must not run inside a loop.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import create_engine, delete, select

from app.core.config import Settings
from app.db.models import Base
from app.db.models.user import User
from app.workers import runtime

_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://newsfeed:newsfeed@localhost:5432/newsfeed_test",
)


@pytest.fixture
def sync_engine():
    engine = create_engine(_URL)
    try:
        with engine.begin() as conn:
            Base.metadata.create_all(conn)
    except Exception as exc:  # noqa: BLE001
        engine.dispose()
        pytest.skip(f"Test database unavailable ({exc})")
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def _point_runtime_at_test_db(monkeypatch):
    monkeypatch.setattr(runtime, "get_settings", lambda: Settings(database_url=_URL))


def test_run_with_session_commits_on_success_and_rolls_back_on_error(sync_engine):
    committed = f"{uuid.uuid4().hex}@rt.com"
    rolled_back = f"{uuid.uuid4().hex}@rt.com"

    async def _good(session):
        session.add(User(email=committed, name="RT"))
        return "ok"

    async def _bad(session):
        session.add(User(email=rolled_back, name="RT"))
        await session.flush()
        raise RuntimeError("boom")

    assert runtime.run_with_session(_good) == "ok"
    with pytest.raises(RuntimeError):
        runtime.run_with_session(_bad)

    with sync_engine.begin() as conn:
        present = set(
            conn.execute(
                select(User.email).where(User.email.in_([committed, rolled_back]))
            ).scalars()
        )
        assert present == {committed}
        conn.execute(delete(User).where(User.email == committed))
