"""Build a user interest vector from weighted article embeddings.

Pure and deterministic — the I/O (loading interactions, fetching vectors,
persisting) lives in ``ProfileService``.

    profile = normalize( Σ wᵢ · vᵢ  /  Σ |wᵢ| )

Negative weights (SKIP, DISLIKE) push the profile *away* from that content.
Returns ``None`` when there is no usable signal (no vectors, or the weighted
sum is the zero vector).
"""

from __future__ import annotations

import math
from collections.abc import Iterable

Vector = list[float]

_EPSILON = 1e-9


def weighted_profile(items: Iterable[tuple[Vector, float]]) -> Vector | None:
    items = [(v, w) for v, w in items if v and abs(w) > _EPSILON]
    if not items:
        return None

    dim = len(items[0][0])
    if any(len(v) != dim for v, _ in items):
        raise ValueError("all embeddings must have the same dimension")

    acc = [0.0] * dim
    total_abs = 0.0
    for vec, weight in items:
        for i, value in enumerate(vec):
            acc[i] += value * weight
        total_abs += abs(weight)

    if total_abs < _EPSILON:
        return None
    acc = [x / total_abs for x in acc]
    return _normalize(acc)


def _normalize(vec: Vector) -> Vector | None:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < _EPSILON:
        return None
    return [x / norm for x in vec]


def aggregate_weights_by_article(
    interactions: Iterable[tuple[str, float]],
) -> dict[str, float]:
    """Sum the signed weights of every interaction on the same article."""
    out: dict[str, float] = {}
    for article_id, weight in interactions:
        out[article_id] = out.get(article_id, 0.0) + weight
    return out
