from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.exceptions import ValidationError
from app.core.pagination import (
    decode_cursor,
    decode_keyset_cursor,
    encode_cursor,
    encode_keyset_cursor,
)


def test_cursor_roundtrip():
    payload = {"ts": "2026-01-01T00:00:00+00:00", "id": "abc"}
    assert decode_cursor(encode_cursor(payload)) == payload


def test_cursor_is_opaque_base64_without_padding_issues():
    token = encode_cursor({"a": 1})
    assert "{" not in token and " " not in token


def test_keyset_cursor_roundtrip():
    ts = datetime(2026, 6, 1, 12, 30, tzinfo=UTC)
    token = encode_keyset_cursor(ts, "id-1")
    decoded_ts, decoded_id = decode_keyset_cursor(token)
    assert decoded_ts == ts
    assert decoded_id == "id-1"


@pytest.mark.parametrize("bad", ["", "!!!", "not-base64", "YWJj", "eyJ4IjoxfQ"])
def test_malformed_cursor_raises_validation_error(bad):
    with pytest.raises(ValidationError):
        decode_keyset_cursor(bad)
