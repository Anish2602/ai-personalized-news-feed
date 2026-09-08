from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.db.models.article import Article
from app.db.models.processing import ProcessingJob
from app.ingestion.base import NewsSource, RawArticle
from app.repositories.article_repository import ArticleRepository
from app.repositories.processing_repository import ProcessingRepository
from app.services.ingestion_service import IngestionService

pytestmark = pytest.mark.asyncio


class FakeSource(NewsSource):
    def __init__(self, name: str, items: list[RawArticle]) -> None:
        self.name = name
        self._items = items

    async def fetch(self) -> list[RawArticle]:
        return self._items


def _item(url: str, *, title: str = "Title") -> RawArticle:
    return RawArticle(
        title=title,
        url=url,
        description="<p>body</p>",
        source="Fake Feed",
        published_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


async def _service(db_session, spy):
    return IngestionService(
        ArticleRepository(db_session), ProcessingRepository(db_session), queue_processing=spy
    )


async def test_ingest_persists_new_and_queues_processing(db_session):
    queued: list = []
    service = await _service(db_session, queued.append)

    source = FakeSource(
        "fake",
        [
            _item("https://ex.com/a"),
            _item("https://ex.com/b"),
            _item("https://ex.com/a"),  # in-batch duplicate
            RawArticle(title=None, url="https://ex.com/c", source="Fake Feed"),  # invalid
            RawArticle(title="x", url="ftp://ex.com/d", source="Fake Feed"),  # bad scheme
        ],
    )
    [report] = await service.ingest_sources([source])

    assert report.fetched == 5
    assert report.inserted == 2
    assert report.duplicates == 1
    assert report.invalid == 2

    count = await db_session.scalar(select(func.count()).select_from(Article))
    assert count == 2
    jobs = await db_session.scalar(select(func.count()).select_from(ProcessingJob))
    assert jobs == 2
    assert len(queued) == 2
    assert all(isinstance(x, uuid.UUID) for x in queued)


async def test_ingestion_is_idempotent(db_session):
    service = await _service(db_session, lambda _a: None)
    source = FakeSource("fake", [_item("https://ex.com/dup1"), _item("https://ex.com/dup2")])

    first = (await service.ingest_sources([source]))[0]
    second = (await service.ingest_sources([source]))[0]

    assert first.inserted == 2
    assert second.inserted == 0
    assert second.duplicates == 2
    total = await db_session.scalar(select(func.count()).select_from(Article))
    assert total == 2


async def test_failing_source_is_isolated(db_session):
    class Boom(NewsSource):
        name = "boom"

        async def fetch(self):
            raise RuntimeError("feed down")

    service = await _service(db_session, lambda _a: None)
    reports = await service.ingest_sources([Boom(), FakeSource("ok", [_item("https://ex.com/ok")])])
    assert reports[0].error == "feed down"
    assert reports[0].inserted == 0
    assert reports[1].inserted == 1
