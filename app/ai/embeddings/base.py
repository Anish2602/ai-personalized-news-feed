from __future__ import annotations

import abc


class EmbeddingProvider(abc.ABC):
    """Turns text into dense vectors. Implementations must be safe to reuse as a
    process-wide singleton and to call from multiple event loops (do blocking
    model work in a worker thread)."""

    @property
    @abc.abstractmethod
    def dimension(self) -> int:
        """Vector length — must equal ``QDRANT_VECTOR_SIZE``."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...

    @abc.abstractmethod
    async def embed_text(self, text: str) -> list[float]: ...

    @abc.abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
