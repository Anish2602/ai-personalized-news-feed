"""Normalize + validate raw articles. Returns ``None`` for records that cannot
be salvaged so the ingestion service can drop them and count them."""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

from app.ingestion.base import RawArticle

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

_TITLE_MAX = 500
_DESC_MAX = 4000
_CONTENT_MAX = 50_000


def _clean_text(value: str | None, *, limit: int) -> str | None:
    if not value:
        return None
    text = html.unescape(_TAG_RE.sub(" ", value))
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        return None
    return text[:limit]


def _valid_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return url.strip()[:2048]


def normalize(raw: RawArticle) -> RawArticle | None:
    url = _valid_url(raw.url)
    title = _clean_text(raw.title, limit=_TITLE_MAX)
    if url is None or title is None:
        return None

    return RawArticle(
        title=title,
        url=url,
        description=_clean_text(raw.description, limit=_DESC_MAX),
        content=_clean_text(raw.content, limit=_CONTENT_MAX),
        source=raw.source.strip()[:200] or "unknown",
        published_at=raw.published_at,
    )
