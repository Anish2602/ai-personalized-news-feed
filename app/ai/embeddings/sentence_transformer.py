from __future__ import annotations

import asyncio
import threading
import time
from typing import TYPE_CHECKING

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import embedding_latency_seconds, embedding_requests_total

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = get_logger(__name__)

_PROVIDER_LABEL = "sentence_transformer"


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local, offline embeddings. The model is loaded lazily on first use and
    shared for the process lifetime; ``encode`` runs in a worker thread so it
    never blocks the event loop."""

    def __init__(self, model_name: str | None = None, *, batch_size: int | None = None) -> None:
        settings = get_settings()
        self._model_name = model_name or settings.embedding_model
        self._batch_size = batch_size or settings.embedding_batch_size
        self._model: SentenceTransformer | None = None
        self._lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return int(self._get_model().get_sentence_embedding_dimension())

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    logger.info("embedding_model_loading", model=self._model_name)
                    self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        start = time.perf_counter()
        vectors = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        embedding_latency_seconds.labels(provider=_PROVIDER_LABEL).observe(
            time.perf_counter() - start
        )
        embedding_requests_total.labels(provider=_PROVIDER_LABEL).inc()
        return [v.tolist() for v in vectors]

    async def embed_text(self, text: str) -> list[float]:
        (vector,) = await self.embed_documents([text])
        return vector

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._encode, texts)
