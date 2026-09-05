"""Lightweight test doubles for the AI layer (no model downloads, no network)."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID, uuid4

from app.ai.embeddings.base import EmbeddingProvider
from app.vector.search import VectorMatch


class FakeEmbeddingProvider(EmbeddingProvider):
    """Maps text → a fixed unit vector via a small lookup, default orthogonal-ish."""

    def __init__(self, mapping: dict[str, list[float]] | None = None, dim: int = 3) -> None:
        self._mapping = mapping or {}
        self._dim = dim
        self.calls: list[str] = []

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return "fake"

    def _vec(self, text: str) -> list[float]:
        if text in self._mapping:
            v = self._mapping[text]
        else:
            # deterministic pseudo-vector from the hash, then L2-normalize
            h = abs(hash(text))
            v = [((h >> (i * 8)) & 0xFF) + 1 for i in range(self._dim)]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    async def embed_text(self, text: str) -> list[float]:
        self.calls.append(text)
        return self._vec(text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(t) for t in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.points: dict[str, tuple[list[float], dict[str, Any]]] = {}
        self.forced_matches: list[VectorMatch] | None = None

    async def ensure_collection(self) -> None:  # noqa: D102
        return None

    async def upsert(self, point_id: str, vector: list[float], payload: dict[str, Any]) -> None:
        self.points[point_id] = (vector, payload)

    async def search(
        self, vector: list[float], *, limit: int, exclude_id: str | None = None
    ) -> list[VectorMatch]:
        if self.forced_matches is not None:
            return [m for m in self.forced_matches if m.id != exclude_id][:limit]
        scored = [
            VectorMatch(id=pid, score=_cosine(vector, vec), payload=payload)
            for pid, (vec, payload) in self.points.items()
            if pid != exclude_id
        ]
        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:limit]

    async def delete(self, point_id: str) -> None:
        self.points.pop(point_id, None)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def match(
    *, article_id: UUID | None = None, story_id: UUID | None = None, score: float
) -> VectorMatch:
    aid = article_id or uuid4()
    payload: dict[str, Any] = {"article_id": str(aid)}
    if story_id is not None:
        payload["story_id"] = str(story_id)
    return VectorMatch(id=str(aid), score=score, payload=payload)
