"""News-source abstraction.

A ``NewsSource`` knows how to pull a batch of ``RawArticle`` records from one
external origin (an RSS feed, a news API, …). It performs no persistence and no
deduplication — that is the ingestion service's job.
"""

from __future__ import annotations

import abc
from datetime import datetime

from pydantic import BaseModel


class RawArticle(BaseModel):
    """A single article as reported by a source, before normalization."""

    title: str | None = None
    url: str | None = None
    description: str | None = None
    content: str | None = None
    source: str
    published_at: datetime | None = None


class NewsSource(abc.ABC):
    #: stable, human-readable identifier stored on ``Article.source``
    name: str

    @abc.abstractmethod
    async def fetch(self) -> list[RawArticle]:
        """Return the current batch. Must not raise for individual bad entries —
        skip them; may raise if the whole source is unreachable."""
        raise NotImplementedError
