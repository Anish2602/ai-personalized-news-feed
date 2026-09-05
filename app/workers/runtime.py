"""Bridge between synchronous Celery tasks and the async service/repository layer.

Each task run gets a fresh async engine (``NullPool``) and one session/transaction
that is committed on success and rolled back on error. A new engine per run avoids
the "attached to a different event loop" problem that a module-level async engine
would hit across successive ``asyncio.run`` calls.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

T = TypeVar("T")


def run_with_session(operation: Callable[[AsyncSession], Awaitable[T]]) -> T:
    async def _runner() -> T:
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        try:
            async with factory() as session:
                try:
                    result = await operation(session)
                    await session.commit()
                    return result
                except Exception:
                    await session.rollback()
                    raise
        finally:
            await engine.dispose()

    return asyncio.run(_runner())
