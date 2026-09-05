from __future__ import annotations

from app.ingestion.base import RawArticle
from app.ingestion.normalizer import normalize


def _raw(**kw) -> RawArticle:
    base = {"title": "Hello", "url": "https://example.com/x", "source": "src"}
    return RawArticle(**{**base, **kw})


def test_strips_html_and_collapses_whitespace():
    out = normalize(_raw(description="<p>Big   <b>news</b>\n\ntoday</p>"))
    assert out is not None
    assert out.description == "Big news today"


def test_unescapes_entities():
    out = normalize(_raw(title="AT&amp;T raises prices"))
    assert out is not None and out.title == "AT&T raises prices"


def test_drops_record_without_title():
    assert normalize(_raw(title="   ")) is None


def test_drops_record_without_valid_url():
    assert normalize(_raw(url="javascript:alert(1)")) is None
    assert normalize(_raw(url="not-a-url")) is None
    assert normalize(_raw(url=None)) is None


def test_clamps_long_title():
    out = normalize(_raw(title="A" * 900))
    assert out is not None and len(out.title) == 500


def test_empty_description_becomes_none():
    out = normalize(_raw(description="<p></p>"))
    assert out is not None and out.description is None
