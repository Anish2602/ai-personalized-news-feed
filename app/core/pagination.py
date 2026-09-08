"""Opaque cursor-based (keyset) pagination.

The cursor is an internal detail the client must not parse: it is a URL-safe
base64 of a compact JSON payload. Decoding is total — any malformed or tampered
value raises :class:`ValidationError` so the API can answer 422 rather than 500.

Keyset (not offset) pagination keeps page cost constant as the dataset grows and
is stable under concurrent inserts.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any

from app.core.exceptions import ValidationError


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        payload = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Malformed pagination cursor.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Malformed pagination cursor.")
    return payload


def encode_offset_cursor(offset: int) -> str:
    """Cursor for slicing a materialized, cached list (e.g. the feed snapshot)."""
    return encode_cursor({"o": offset})


def decode_offset_cursor(cursor: str) -> int:
    payload = decode_cursor(cursor)
    offset = payload.get("o")
    if not isinstance(offset, int) or offset < 0:
        raise ValidationError("Malformed pagination cursor.")
    return offset


def encode_keyset_cursor(created_at: datetime, id_: Any) -> str:
    """Cursor for a ``(created_at DESC, id DESC)`` ordering."""
    return encode_cursor({"ts": created_at.isoformat(), "id": str(id_)})


def decode_keyset_cursor(cursor: str) -> tuple[datetime, str]:
    payload = decode_cursor(cursor)
    try:
        return datetime.fromisoformat(payload["ts"]), str(payload["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValidationError("Malformed pagination cursor.") from exc
