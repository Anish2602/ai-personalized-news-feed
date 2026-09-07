from __future__ import annotations

import json

import pytest

from app.ai.classifier import Classifier
from app.core.exceptions import UpstreamError
from tests._fakes import FakeLLMProvider

pytestmark = pytest.mark.asyncio

TAXONOMY = [
    "Artificial Intelligence",
    "Cloud",
    "Cybersecurity",
    "Finance",
    "Technology",
]


async def test_uses_llm_topics_when_valid():
    llm = FakeLLMProvider(json.dumps({"topics": ["Cloud", "Artificial Intelligence"]}))
    c = Classifier(llm, TAXONOMY)
    assert await c.classify(title="t", text="b") == ["Cloud", "Artificial Intelligence"]


async def test_drops_topics_outside_taxonomy():
    llm = FakeLLMProvider(json.dumps({"topics": ["Cloud", "Astrology", "Cooking"]}))
    c = Classifier(llm, TAXONOMY)
    assert await c.classify(title="t", text="b") == ["Cloud"]


async def test_falls_back_when_llm_returns_junk():
    llm = FakeLLMProvider("totally not json")
    c = Classifier(llm, TAXONOMY)
    topics = await c.classify(title="New AI model released", text="a neural network and llm")
    assert "Artificial Intelligence" in topics


async def test_falls_back_when_llm_raises():
    llm = FakeLLMProvider(error=UpstreamError("timeout"))
    c = Classifier(llm, TAXONOMY)
    topics = await c.classify(title="AWS outage", text="kubernetes on aws cloud went down")
    assert "Cloud" in topics


async def test_keyword_fallback_without_llm():
    c = Classifier(None, TAXONOMY)
    topics = await c.classify(
        title="Ransomware breach at bank", text="a malware exploit hit the stock market"
    )
    assert set(topics) & {"Cybersecurity", "Finance"}


async def test_fallback_default_when_no_keywords_match():
    c = Classifier(None, TAXONOMY)
    topics = await c.classify(title="zzz", text="qqq")
    assert topics == ["Technology"]


async def test_respects_max_topics():
    llm = FakeLLMProvider(json.dumps({"topics": TAXONOMY}))
    c = Classifier(llm, TAXONOMY, max_topics=2)
    assert len(await c.classify(title="t", text="b")) == 2
