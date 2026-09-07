from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from app.ranking.freshness import freshness_score

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def test_zero_age_is_one():
    assert freshness_score(NOW, now=NOW, decay_hours=24) == 1.0


def test_one_decay_period_is_one_over_e():
    got = freshness_score(NOW - timedelta(hours=24), now=NOW, decay_hours=24)
    assert math.isclose(got, math.exp(-1), rel_tol=1e-9)


def test_monotonic_decreasing_with_age():
    ages = [0, 6, 12, 24, 48, 96]
    scores = [freshness_score(NOW - timedelta(hours=h), now=NOW, decay_hours=24) for h in ages]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 < s <= 1.0 for s in scores)


def test_none_published_uses_default():
    assert freshness_score(None, now=NOW, decay_hours=24) == 0.5
    assert freshness_score(None, now=NOW, decay_hours=24, default=0.1) == 0.1


def test_future_timestamp_clamped_to_one():
    assert freshness_score(NOW + timedelta(hours=5), now=NOW, decay_hours=24) == 1.0


def test_naive_datetime_treated_as_utc():
    naive = datetime(2026, 9, 7, 12, 0)
    assert freshness_score(naive, now=NOW, decay_hours=24) == 1.0
