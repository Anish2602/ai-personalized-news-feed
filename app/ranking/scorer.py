"""Transparent linear ranking function (no ML model).

    final = w_sem·semantic + w_fresh·freshness + w_pop·popularity
          + w_src·source_quality + w_div·diversity + w_topic·topic_affinity

Every feature is normalized to [0, 1] before weighting, so the weights are the
only knobs and they are all in config. ``score`` returns the total and the
per-feature contribution so the feed can explain itself (`?debug=true`).
"""

from __future__ import annotations

from pydantic import BaseModel


class RankFeatures(BaseModel):
    semantic: float = 0.0
    freshness: float = 0.0
    popularity: float = 0.0
    source_quality: float = 0.0
    diversity: float = 0.0
    # Overlap between a story's topics and the user's declared interests
    # (UserInterest.weight, signed) — the only personalization signal a
    # brand-new user has before they've liked/saved anything.
    topic_affinity: float = 0.0


class RankResult(BaseModel):
    score: float
    features: RankFeatures
    contributions: dict[str, float]


def score(features: RankFeatures, weights: dict[str, float]) -> RankResult:
    contributions = {
        name: round(weights.get(name, 0.0) * value, 6)
        for name, value in features.model_dump().items()
    }
    return RankResult(
        score=round(sum(contributions.values()), 6),
        features=features,
        contributions=contributions,
    )


def normalize_counts(values: dict[object, float]) -> dict[object, float]:
    """Min-max normalize to [0, 1]; all-equal (incl. empty) → all 0."""
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi - lo < 1e-9:
        return dict.fromkeys(values, 0.0)
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}
