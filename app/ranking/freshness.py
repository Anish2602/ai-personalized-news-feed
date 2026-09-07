"""Exponential recency decay.

    freshness = exp(-age_hours / decay_hours)

age 0h → 1.0 · age == decay_hours → ~0.368 · older → →0. This is a smooth score,
not a sort key — a slightly older but highly relevant story can still rank above
a fresh irrelevant one.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime


def freshness_score(
    published_at: datetime | None,
    *,
    now: datetime | None = None,
    decay_hours: float,
    default: float = 0.5,
) -> float:
    if published_at is None:
        return default
    now = now or datetime.now(tz=UTC)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
    if decay_hours <= 0:
        return 1.0 if age_hours == 0 else 0.0
    return math.exp(-age_hours / decay_hours)
