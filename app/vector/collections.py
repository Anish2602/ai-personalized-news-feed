"""Qdrant collection schema for article embeddings."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    vector_size: int
    distance: str = "Cosine"  # embeddings are L2-normalized -> cosine == dot


def articles_collection() -> CollectionSpec:
    settings = get_settings()
    return CollectionSpec(
        name=settings.qdrant_collection,
        vector_size=settings.qdrant_vector_size,
    )
