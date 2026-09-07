from __future__ import annotations

import json

import pytest

from app.ai.summarizer import Summarizer
from app.core.exceptions import LLMOutputError
from tests._fakes import FakeLLMProvider

pytestmark = pytest.mark.asyncio

TAXONOMY = ["Artificial Intelligence", "Cloud", "Business"]


def _good(**over):
    base = {
        "summary": "A neutral two sentence summary. It states the facts.",
        "key_points": ["point one", "point two", "point three"],
        "topics": ["Artificial Intelligence", "NotInTaxonomy"],
    }
    return json.dumps({**base, **over})


async def test_parses_valid_output_and_filters_topics():
    s = Summarizer(FakeLLMProvider(_good()))
    result = await s.summarize(title="T", text="body", taxonomy=TAXONOMY)
    assert result.summary.startswith("A neutral")
    assert result.key_points == ["point one", "point two", "point three"]
    assert result.topics == ["Artificial Intelligence"]  # unknown label dropped


async def test_recovers_from_fenced_json():
    s = Summarizer(FakeLLMProvider(f"```json\n{_good()}\n```"))
    result = await s.summarize(title="T", text="b", taxonomy=TAXONOMY)
    assert result.summary


async def test_reprompts_then_succeeds():
    llm = FakeLLMProvider(["not json", _good()])
    s = Summarizer(llm, max_attempts=2)
    result = await s.summarize(title="T", text="b", taxonomy=TAXONOMY)
    assert result.summary
    assert len(llm.calls) == 2


async def test_raises_after_exhausting_attempts():
    llm = FakeLLMProvider(["garbage", '{"key_points": []}'])  # 2nd has empty summary
    s = Summarizer(llm, max_attempts=2)
    with pytest.raises(LLMOutputError):
        await s.summarize(title="T", text="b", taxonomy=TAXONOMY)


async def test_fallback_when_no_llm_is_extractive():
    s = Summarizer(None)
    text = "First sentence here. Second sentence follows. Third one too. Fourth ignored."
    result = await s.summarize(title="T", text=text, taxonomy=TAXONOMY)
    assert result.summary == "First sentence here. Second sentence follows. Third one too."
    assert result.topics == []
