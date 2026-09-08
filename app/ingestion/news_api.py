"""NewsAPI-style HTTP source.

Kept as a thin, disabled-by-default implementation to demonstrate that the
``NewsSource`` abstraction is genuinely pluggable. Enable with
``NEWS_API_ENABLED=true`` and ``NEWS_API_KEY=...``.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import get_settings
from app.core.exceptions import UpstreamError
from app.ingestion.base import NewsSource, RawArticle

_ENDPOINT = "https://newsapi.org/v2/top-headlines"


class NewsAPISource(NewsSource):
    name = "newsapi.org"

    def __init__(self, *, query: str | None = None, page_size: int | None = None) -> None:
        settings = get_settings()
        if not settings.news_api_enabled or not settings.news_api_key:
            raise UpstreamError("NewsAPI source is not configured.")
        self._api_key = settings.news_api_key
        self._query = query
        self._page_size = page_size or settings.ingest_max_articles_per_feed
        self._timeout = settings.ingest_http_timeout_seconds

    async def fetch(self) -> list[RawArticle]:
        params = {"pageSize": self._page_size, "language": "en"}
        if self._query:
            params["q"] = self._query
        else:
            params["category"] = "technology"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(_ENDPOINT, params=params, headers={"X-Api-Key": self._api_key})
        if resp.status_code != 200:
            raise UpstreamError(f"NewsAPI returned {resp.status_code}")

        out: list[RawArticle] = []
        for item in resp.json().get("articles", []):
            published = item.get("publishedAt")
            out.append(
                RawArticle(
                    title=item.get("title"),
                    url=item.get("url"),
                    description=item.get("description"),
                    content=item.get("content"),
                    source=(item.get("source") or {}).get("name") or self.name,
                    published_at=datetime.fromisoformat(published.replace("Z", "+00:00"))
                    if published
                    else None,
                )
            )
        return out
