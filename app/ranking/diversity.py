"""Topic diversity.

Two pieces, both deterministic:

* ``topic_rarity_scores`` — a per-candidate feature in [0, 1]: candidates whose
  primary topic is rare in the pool score higher. Feeds the ``diversity`` term
  of the ranking function.
* ``interleave_by_topic`` — a stable re-ordering that avoids showing several
  same-topic items back to back (used by the feed in Phase 7).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar


class HasTopics(Protocol):
    id: object
    topics: Sequence[str]


T = TypeVar("T")


def _primary_topic(topics: Sequence[str]) -> str:
    return topics[0] if topics else "_none"


def topic_rarity_scores(candidates: Sequence[HasTopics]) -> dict[object, float]:
    if not candidates:
        return {}
    counts = Counter(_primary_topic(c.topics) for c in candidates)
    total = len(candidates)
    # rarity = 1 - (share of the pool with this primary topic); rescaled to [0,1]
    return {
        c.id: 1.0 - (counts[_primary_topic(c.topics)] - 1) / max(total - 1, 1) for c in candidates
    }


def interleave_by_topic(
    ranked: Sequence[T],
    *,
    max_streak: int = 2,
    topic_of: Callable[[T], Sequence[str]] = lambda x: x.topics,  # type: ignore[attr-defined]
) -> list[T]:
    """Reorder a ranked list so no primary topic appears more than ``max_streak``
    times consecutively, disturbing the original order as little as possible."""
    remaining = list(ranked)
    out: list[T] = []
    streak_topic: str | None = None
    streak = 0

    while remaining:
        pick_idx = 0
        if streak >= max_streak:
            for i, cand in enumerate(remaining):
                if _primary_topic(topic_of(cand)) != streak_topic:
                    pick_idx = i
                    break
        cand = remaining.pop(pick_idx)
        topic = _primary_topic(topic_of(cand))
        if topic == streak_topic:
            streak += 1
        else:
            streak_topic, streak = topic, 1
        out.append(cand)
    return out
