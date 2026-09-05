from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.deduplication_service import DeduplicationService
from tests._fakes import FakeEmbeddingProvider, FakeVectorStore, match

pytestmark = pytest.mark.asyncio


class FakeArticleRepo:
    def __init__(self, articles=None):
        self.articles = {a.id: a for a in (articles or [])}
        self.embedding_refs: dict = {}

    async def get(self, article_id):
        return self.articles.get(article_id)

    async def assign_story(self, article_id, story_id):
        art = self.articles.get(article_id)
        if art is not None:
            art.story_id = story_id

    async def set_embedding_reference(self, article_id, reference):
        self.embedding_refs[article_id] = reference


class FakeStoryRepo:
    def __init__(self):
        self.created: list = []

    async def create(self, *, canonical_title, summary=None):
        story = SimpleNamespace(id=uuid4(), canonical_title=canonical_title, summary=summary)
        self.created.append(story)
        return story


def _article(**kw):
    base = {
        "id": uuid4(),
        "title": "Fed holds rates",
        "description": "d",
        "content": "c",
        "source": "src",
        "story_id": None,
        "published_at": None,
    }
    return SimpleNamespace(**{**base, **kw})


def _service(*, articles=None, vectors=None, threshold=0.9):
    art_repo = FakeArticleRepo(articles)
    story_repo = FakeStoryRepo()
    vs = vectors or FakeVectorStore()
    svc = DeduplicationService(
        art_repo, story_repo, vs, FakeEmbeddingProvider(), threshold=threshold, top_k=5
    )
    return svc, art_repo, story_repo, vs


async def test_empty_index_creates_new_story():
    article = _article()
    svc, art_repo, story_repo, vs = _service(articles=[article])

    result = await svc.deduplicate(article, text="hello world")

    assert result.is_duplicate is False
    assert len(story_repo.created) == 1
    assert article.story_id == result.story_id
    assert str(article.id) in vs.points  # vector persisted for future matches
    assert art_repo.embedding_refs[article.id] == str(article.id)


async def test_similar_article_attaches_to_existing_story():
    existing_story = uuid4()
    neighbour = _article(story_id=existing_story)
    article = _article()
    vs = FakeVectorStore()
    vs.forced_matches = [match(article_id=neighbour.id, story_id=existing_story, score=0.97)]

    svc, _art, story_repo, _vs = _service(articles=[neighbour, article], vectors=vs)
    result = await svc.deduplicate(article, text="dup")

    assert result.is_duplicate is True
    assert result.story_id == existing_story
    assert result.similarity == pytest.approx(0.97)
    assert story_repo.created == []  # reused, not created


async def test_below_threshold_creates_new_story():
    article = _article()
    vs = FakeVectorStore()
    vs.forced_matches = [match(score=0.80)]
    svc, _a, story_repo, _v = _service(articles=[article], vectors=vs, threshold=0.9)

    result = await svc.deduplicate(article, text="unrelated")
    assert result.is_duplicate is False
    assert len(story_repo.created) == 1


async def test_threshold_is_inclusive():
    article = _article()
    neighbour = _article(story_id=uuid4())
    vs = FakeVectorStore()
    vs.forced_matches = [match(article_id=neighbour.id, story_id=neighbour.story_id, score=0.90)]
    svc, *_ = _service(articles=[neighbour, article], vectors=vs, threshold=0.90)

    result = await svc.deduplicate(article, text="x")
    assert result.is_duplicate is True


async def test_match_neighbour_without_story_backfills_both():
    neighbour = _article(story_id=None)
    article = _article()
    vs = FakeVectorStore()
    vs.forced_matches = [match(article_id=neighbour.id, score=0.95)]  # no story_id in payload

    svc, art_repo, story_repo, _vs = _service(articles=[neighbour, article], vectors=vs)
    result = await svc.deduplicate(article, text="x")

    assert result.is_duplicate is True
    assert len(story_repo.created) == 1
    assert neighbour.story_id == result.story_id
    assert article.story_id == result.story_id
