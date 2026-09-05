from __future__ import annotations

import pytest

from app.ai.embeddings import build_embedding_text, get_embedding_provider
from app.ai.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider


class _FakeModel:
    def __init__(self, dim: int = 4) -> None:
        self._dim = dim
        self.encode_calls = 0

    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

    def encode(self, texts, **kwargs):
        import numpy as np

        self.encode_calls += 1
        return np.array([[float(len(t))] * self._dim for t in texts])


@pytest.mark.asyncio
async def test_embed_documents_shape_and_metric():
    provider = SentenceTransformerEmbeddingProvider("stub-model")
    provider._model = _FakeModel(dim=4)

    vecs = await provider.embed_documents(["ab", "cdef"])
    assert [len(v) for v in vecs] == [4, 4]
    assert vecs[0] == [2.0, 2.0, 2.0, 2.0]


@pytest.mark.asyncio
async def test_embed_text_unwraps_single_vector():
    provider = SentenceTransformerEmbeddingProvider("stub-model")
    provider._model = _FakeModel(dim=3)
    v = await provider.embed_text("xyz")
    assert v == [3.0, 3.0, 3.0]


@pytest.mark.asyncio
async def test_empty_input_short_circuits():
    provider = SentenceTransformerEmbeddingProvider("stub-model")
    model = _FakeModel()
    provider._model = model
    assert await provider.embed_documents([]) == []
    assert model.encode_calls == 0


def test_model_name_is_configurable_not_hardcoded():
    assert SentenceTransformerEmbeddingProvider("my/model").model_name == "my/model"


def test_unknown_provider_raises(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setattr(
        "app.ai.embeddings.get_settings", lambda: Settings(embedding_provider="bogus")
    )
    get_embedding_provider.cache_clear()
    with pytest.raises(ValueError):
        get_embedding_provider()
    get_embedding_provider.cache_clear()


def test_build_embedding_text_prefers_description_and_truncates():
    text = build_embedding_text(title="T", description="desc here", content="should be ignored")
    assert "desc here" in text
    assert "ignored" not in text

    long = build_embedding_text(title="T", description="x" * 9000, content=None)
    assert len(long) <= 2000 + 10
