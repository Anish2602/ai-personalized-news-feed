from __future__ import annotations

import json
import uuid

import pytest

from app.ai.classifier import Classifier
from app.ai.summarizer import Summarizer
from app.db.models.article import Article
from app.db.models.story import Story
from app.repositories.article_repository import ArticleRepository
from app.repositories.story_repository import StoryRepository
from app.services.enrichment_service import EnrichmentService
from tests._fakes import FakeLLMProvider

pytestmark = pytest.mark.asyncio

TAXONOMY = ["Artificial Intelligence", "Cloud", "Business", "Technology"]

LLM_JSON = json.dumps(
    {
        "summary": "The company shipped a new model. Analysts reacted positively.",
        "key_points": ["new model", "positive reaction"],
        "topics": ["Artificial Intelligence", "Business"],
    }
)


async def _story_with_article(db_session, *, topics=None) -> tuple[Story, Article]:
    story = Story(canonical_title="Seed", topics=topics or [])
    db_session.add(story)
    await db_session.flush()
    art = Article(
        title="OpenAI ships model",
        url=f"https://ex.com/{uuid.uuid4().hex}",
        source="Wire",
        description="a new llm and neural network",
        story_id=story.id,
    )
    db_session.add(art)
    await db_session.flush()
    return story, art


def _service(db_session, llm) -> EnrichmentService:
    return EnrichmentService(
        ArticleRepository(db_session),
        StoryRepository(db_session),
        Summarizer(llm),
        Classifier(llm, TAXONOMY),
        TAXONOMY,
    )


async def test_first_article_summarizes_and_classifies(db_session):
    story, art = await _story_with_article(db_session)
    llm = FakeLLMProvider([json.dumps({"topics": ["Artificial Intelligence"]}), LLM_JSON])

    result = await _service(db_session, llm).enrich(art, text="body", story_id=story.id)

    assert result.summarized is True
    await db_session.flush()
    await db_session.refresh(story)
    await db_session.refresh(art)
    assert story.summary.startswith("The company shipped")
    assert story.key_points == ["new model", "positive reaction"]
    assert "Artificial Intelligence" in story.topics
    assert art.topics == ["Artificial Intelligence"]


async def test_duplicate_article_merges_topics_without_resummarizing(db_session):
    story, _first = await _story_with_article(db_session)
    story.summary = "already summarized"
    story.topics = ["Cloud"]
    await db_session.flush()

    dup = Article(
        title="AWS re:Invent",
        url=f"https://ex.com/{uuid.uuid4().hex}",
        source="Wire2",
        description="kubernetes on aws cloud",
        story_id=story.id,
    )
    db_session.add(dup)
    await db_session.flush()

    # No summary response provided -> if it tried to summarize, FakeLLM would raise.
    llm = FakeLLMProvider([json.dumps({"topics": ["Cloud", "Technology"]})])
    result = await _service(db_session, llm).enrich(dup, text="body", story_id=story.id)

    assert result.summarized is False
    await db_session.flush()
    await db_session.refresh(story)
    assert story.summary == "already summarized"
    assert set(story.topics) == {"Cloud", "Technology"}


async def test_no_llm_uses_fallbacks(db_session):
    story, art = await _story_with_article(db_session)
    result = await _service(db_session, None).enrich(
        art, text="a neural network llm story about ai", story_id=story.id
    )
    assert result.summarized is True
    await db_session.flush()
    await db_session.refresh(story)
    assert story.summary  # extractive, non-empty
    assert art.topics  # keyword fallback, non-empty
