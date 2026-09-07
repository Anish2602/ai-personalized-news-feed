"""Thin async wrapper over a Qdrant collection: ensure / upsert / search / delete."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient, models

from app.core.logging import get_logger
from app.vector.collections import CollectionSpec, articles_collection

logger = get_logger(__name__)


class VectorMatch(BaseModel):
    id: str
    score: float
    payload: dict[str, Any]


class VectorStoreProtocol(Protocol):
    async def ensure_collection(self) -> None: ...
    async def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None: ...
    async def search(
        self, vector: list[float], *, limit: int, exclude_id: str | None = None
    ) -> list[VectorMatch]: ...
    async def retrieve_vectors(self, ids: list[str]) -> dict[str, list[float]]: ...
    async def delete(self, point_id: str) -> None: ...


class QdrantVectorStore:
    def __init__(self, client: AsyncQdrantClient, spec: CollectionSpec | None = None) -> None:
        self._client = client
        self._spec = spec or articles_collection()
        self._ensured = False

    async def ensure_collection(self) -> None:
        if self._ensured:
            return
        if not await self._client.collection_exists(self._spec.name):
            await self._client.create_collection(
                collection_name=self._spec.name,
                vectors_config=models.VectorParams(
                    size=self._spec.vector_size,
                    distance=models.Distance[self._spec.distance.upper()],
                ),
            )
            logger.info("qdrant_collection_created", collection=self._spec.name)
        self._ensured = True

    async def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        await self.ensure_collection()
        await self._client.upsert(
            collection_name=self._spec.name,
            points=[models.PointStruct(id=point_id, vector=vector, payload=payload)],
            wait=True,
        )

    async def search(
        self, vector: list[float], *, limit: int, exclude_id: str | None = None
    ) -> list[VectorMatch]:
        await self.ensure_collection()
        query_filter = None
        if exclude_id is not None:
            query_filter = models.Filter(
                must_not=[models.HasIdCondition(has_id=[exclude_id])]
            )
        result = await self._client.query_points(
            collection_name=self._spec.name,
            query=vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )
        return [
            VectorMatch(id=str(p.id), score=float(p.score), payload=p.payload or {})
            for p in result.points
        ]

    async def retrieve_vectors(self, ids: list[str]) -> dict[str, list[float]]:
        if not ids:
            return {}
        await self.ensure_collection()
        records = await self._client.retrieve(
            collection_name=self._spec.name,
            ids=ids,
            with_vectors=True,
            with_payload=False,
        )
        return {str(r.id): list(r.vector) for r in records if r.vector is not None}

    async def delete(self, point_id: str) -> None:
        await self._client.delete(
            collection_name=self._spec.name,
            points_selector=models.PointIdsList(points=[point_id]),
            wait=True,
        )
