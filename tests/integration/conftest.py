"""Integration-test fixtures backed by a real PostgreSQL database.

Set ``TEST_DATABASE_URL`` to point at a throwaway database. If it is not
reachable, the integration tests are skipped rather than failed so the unit
suite still runs anywhere.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db_session
from app.main import create_app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://newsfeed:newsfeed@localhost:5432/newsfeed_test",
)
TEST_QDRANT_URL = os.environ.get("TEST_QDRANT_URL", "http://localhost:6333")


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Test database unavailable ({exc})", allow_module_level=True)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Each test runs inside a transaction that is rolled back afterwards."""
    conn = await test_engine.connect()
    trans = await conn.begin()
    factory = async_sessionmaker(bind=conn, expire_on_commit=False, autoflush=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await conn.close()


@pytest.fixture
def fake_redis():
    import fakeredis.aioredis

    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest_asyncio.fixture
async def qdrant_store():
    """A throwaway Qdrant collection (skips the test if Qdrant is unreachable)."""
    from uuid import uuid4

    from qdrant_client import AsyncQdrantClient

    from app.vector.collections import CollectionSpec
    from app.vector.search import QdrantVectorStore

    client = AsyncQdrantClient(url=TEST_QDRANT_URL, check_compatibility=False, timeout=5)
    spec = CollectionSpec(name=f"test_{uuid4().hex}", vector_size=3)
    store = QdrantVectorStore(client, spec)
    try:
        await store.ensure_collection()
    except Exception as exc:  # noqa: BLE001
        await client.close()
        pytest.skip(f"Qdrant unavailable ({exc})")
    try:
        yield store
    finally:
        try:
            await client.delete_collection(spec.name)
        finally:
            await client.close()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncClient:
    from app.api.v1.deps import get_queue_processing, get_queue_profile_rebuild

    app = create_app()

    async def _override_session():
        # No commit: the outer fixture transaction is rolled back for isolation.
        yield db_session

    app.dependency_overrides[get_db_session] = _override_session
    # No Celery broker in tests — background dispatch is a no-op unless a test
    # overrides these with a spy.
    app.dependency_overrides[get_queue_processing] = lambda: lambda _a: None
    app.dependency_overrides[get_queue_profile_rebuild] = lambda: lambda _u: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
