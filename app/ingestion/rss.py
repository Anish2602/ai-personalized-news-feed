"""RSS/Atom news source. Fetches the feed over HTTP and maps entries to
``RawArticle``. Never scrapes the target site."""

from __future__ import annotations

from datetime import UTC, datetime
from time import mktime
from urllib.parse import urlparse

import feedparser
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.base import NewsSource, RawArticle

logger = get_logger(__name__)


class RSSNewsSource(NewsSource):
    def __init__(
        self,
        feed_url: str,
        *,
        max_articles: int | None = None,
        timeout: float | None = None,
    ) -> None:
        settings = get_settings()
        self.feed_url = feed_url
        self.max_articles = max_articles or settings.ingest_max_articles_per_feed
        self.timeout = timeout or settings.ingest_http_timeout_seconds
        self.name = urlparse(feed_url).netloc or feed_url

    async def _download(self) -> bytes:
        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=True, headers={"User-Agent": "ai-news-feed/0.1"}
        ) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()
            return resp.content

    async def fetch(self) -> list[RawArticle]:
        body = await self._download()
        parsed = feedparser.parse(body)
        # feedparser sets .bozo on malformed feeds but still yields usable entries.
        if parsed.bozo and not parsed.entries:
            raise ValueError(f"Unparseable feed: {self.feed_url} ({parsed.bozo_exception})")

        feed_title = getattr(parsed.feed, "title", None) or self.name
        out: list[RawArticle] = []
        for entry in parsed.entries[: self.max_articles]:
            raw = self._map_entry(entry, feed_title)
            if raw is not None:
                out.append(raw)
        logger.info("rss_fetched", feed=self.name, entries=len(parsed.entries), mapped=len(out))
        return out

    @staticmethod
    def _map_entry(entry: feedparser.FeedParserDict, feed_title: str) -> RawArticle | None:
        try:
            content = None
            if getattr(entry, "content", None):
                content = entry.content[0].get("value")
            published = None
            for key in ("published_parsed", "updated_parsed"):
                struct = entry.get(key)
                if struct:
                    published = datetime.fromtimestamp(mktime(struct), tz=UTC)
                    break
            return RawArticle(
                title=entry.get("title"),
                url=entry.get("link"),
                description=entry.get("summary"),
                content=content,
                source=feed_title,
                published_at=published,
            )
        except Exception as exc:  # noqa: BLE001 - one bad entry must not kill the batch
            logger.warning("rss_entry_skipped", error=str(exc))
            return None
