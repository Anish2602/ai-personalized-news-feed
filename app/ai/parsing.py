"""Best-effort JSON recovery from LLM output.

Models wrap JSON in prose or ```json fences even when asked not to. This pulls
the first balanced ``{...}`` object out and parses it; returns ``None`` if there
is nothing usable.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json_object(raw: str) -> dict[str, Any] | None:
    if not raw or not raw.strip():
        return None

    candidates: list[str] = []
    fenced = _FENCE_RE.search(raw)
    if fenced:
        candidates.append(fenced.group(1))
    candidates.append(raw)

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(raw[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed
    return None
