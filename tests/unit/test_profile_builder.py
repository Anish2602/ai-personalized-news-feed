from __future__ import annotations

import math

import pytest

from app.ai.profile_builder import aggregate_weights_by_article, weighted_profile


def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def test_weighted_average_then_normalized():
    # two vectors, weights 3 and 1 -> result leans toward the first, unit length
    out = weighted_profile([([1.0, 0.0, 0.0], 3.0), ([0.0, 1.0, 0.0], 1.0)])
    assert out == pytest.approx(_unit([3.0, 1.0, 0.0]))
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0)


def test_negative_weight_pushes_away():
    out = weighted_profile([([1.0, 0.0], 4.0), ([1.0, 0.0], -4.0), ([0.0, 1.0], 1.0)])
    # the +x and -x contributions cancel; only +y remains
    assert out == pytest.approx([0.0, 1.0])


def test_empty_returns_none():
    assert weighted_profile([]) is None
    assert weighted_profile([([1.0, 0.0], 0.0)]) is None


def test_cancelling_to_zero_returns_none():
    assert weighted_profile([([1.0, 0.0], 2.0), ([-1.0, 0.0], 2.0)]) is None


def test_dimension_mismatch_raises():
    with pytest.raises(ValueError):
        weighted_profile([([1.0, 0.0], 1.0), ([1.0], 1.0)])


def test_aggregate_weights_by_article_sums_signed():
    agg = aggregate_weights_by_article([("a", 1.0), ("a", 3.0), ("b", -4.0), ("a", -1.0)])
    assert agg == {"a": 3.0, "b": -4.0}
