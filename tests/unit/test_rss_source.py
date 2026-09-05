from __future__ import annotations

import pytest

from app.ingestion.rss import RSSNewsSource

RSS_XML = b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Example Tech</title>
  <item>
    <title>GPU prices fall</title>
    <link>https://example.com/gpu</link>
    <description>&lt;p&gt;Good news for builders&lt;/p&gt;</description>
    <pubDate>Wed, 01 Jan 2026 12:00:00 GMT</pubDate>
  </item>
  <item>
    <title>No link here</title>
    <description>should still map, url invalid downstream</description>
  </item>
</channel></rss>
"""


class _StubRSS(RSSNewsSource):
    async def _download(self) -> bytes:
        return RSS_XML


@pytest.mark.asyncio
async def test_fetch_maps_entries():
    src = _StubRSS("https://example.com/feed.xml")
    items = await src.fetch()
    assert len(items) == 2

    first = items[0]
    assert first.title == "GPU prices fall"
    assert first.url == "https://example.com/gpu"
    assert first.source == "Example Tech"
    assert first.published_at is not None
    assert first.published_at.year == 2026


@pytest.mark.asyncio
async def test_fetch_respects_max_articles():
    src = _StubRSS("https://example.com/feed.xml", max_articles=1)
    assert len(await src.fetch()) == 1


@pytest.mark.asyncio
async def test_unparseable_feed_raises():
    class _Broken(RSSNewsSource):
        async def _download(self) -> bytes:
            return b"totally not xml <<<"

    with pytest.raises(ValueError):
        await _Broken("https://example.com/broken").fetch()
