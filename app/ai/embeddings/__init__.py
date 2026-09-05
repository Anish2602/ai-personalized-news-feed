"""Embedding provider selection.

``get_embedding_provider()`` returns a process-wide singleton chosen by
``EMBEDDING_PROVIDER``. Add new providers here — nothing else imports concrete
provider classes.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import get_settings


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    name = get_settings().embedding_provider.lower()
    if name in ("sentence_transformer", "sentence-transformers", "st"):
        from app.ai.embeddings.sentence_transformer import (
            SentenceTransformerEmbeddingProvider,
        )

        return SentenceTransformerEmbeddingProvider()
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {name!r}")


def build_embedding_text(*, title: str, description: str | None, content: str | None) -> str:
    """Compact representation of an article for embedding/dedup."""
    parts = [title.strip()]
    if description:
        parts.append(description.strip())
    elif content:
        parts.append(content.strip())
    text = "\n\n".join(p for p in parts if p)
    return text[: get_settings().embedding_max_chars]


__all__ = ["EmbeddingProvider", "get_embedding_provider", "build_embedding_text"]
