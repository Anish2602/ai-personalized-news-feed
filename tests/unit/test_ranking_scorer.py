from __future__ import annotations

import pytest

from app.ranking.scorer import RankFeatures, normalize_counts, score

WEIGHTS = {
    "semantic": 0.55,
    "freshness": 0.20,
    "popularity": 0.10,
    "source_quality": 0.10,
    "diversity": 0.05,
}


def test_score_is_weighted_sum_with_contributions():
    feats = RankFeatures(
        semantic=1.0, freshness=0.5, popularity=0.0, source_quality=1.0, diversity=0.0
    )
    result = score(feats, WEIGHTS)
    assert result.score == pytest.approx(0.55 + 0.10 + 0.10)
    assert result.contributions["semantic"] == pytest.approx(0.55)
    assert result.contributions["freshness"] == pytest.approx(0.10)


def test_all_zero_features_score_zero():
    assert score(RankFeatures(), WEIGHTS).score == 0.0


def test_semantic_dominates_ordering():
    a = score(RankFeatures(semantic=0.9, freshness=0.1), WEIGHTS).score
    b = score(RankFeatures(semantic=0.2, freshness=1.0), WEIGHTS).score
    assert a > b


def test_normalize_counts_minmax():
    assert normalize_counts({"a": 0.0, "b": 5.0, "c": 10.0}) == {"a": 0.0, "b": 0.5, "c": 1.0}


def test_normalize_counts_all_equal_is_zero():
    assert normalize_counts({"a": 3.0, "b": 3.0}) == {"a": 0.0, "b": 0.0}
    assert normalize_counts({}) == {}
