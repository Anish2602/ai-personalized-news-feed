from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.core.pagination import decode_offset_cursor, encode_offset_cursor


def test_offset_cursor_roundtrip():
    for offset in (0, 1, 20, 999):
        assert decode_offset_cursor(encode_offset_cursor(offset)) == offset


def test_offset_cursor_is_opaque():
    token = encode_offset_cursor(40)
    assert token.isascii() and "{" not in token and "40" not in token


@pytest.mark.parametrize("bad", ["", "@@@", "not-base64", "eyJvIjotMX0="])  # last = {"o":-1}
def test_bad_offset_cursor_raises(bad):
    with pytest.raises(ValidationError):
        decode_offset_cursor(bad)
