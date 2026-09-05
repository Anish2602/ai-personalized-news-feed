"""Qdrant client lifecycle.

``vector_store()`` yields a ready ``QdrantVectorStore`` backed by a fresh client
and closes it afterwards. A per-scope client (rather than a module singleton)
keeps things correct when Celery tasks each run in their own event loop.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.vector.search import QdrantVectorStore


def new_qdrant_client() -> AsyncQdrantClient:
    settings = get_settings()
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        check_compatibility=False,
        timeout=10,
    )


@asynccontextmanager
async def vector_store() -> AsyncIterator[QdrantVectorStore]:
    client = new_qdrant_client()
    try:
        yield QdrantVectorStore(client)
    finally:
        await client.close()
