from __future__ import annotations

from dataclasses import dataclass, field

from app.ranking.diversity import interleave_by_topic, topic_rarity_scores


@dataclass
class C:
    id: str
    topics: list[str] = field(default_factory=list)


def test_rarity_higher_for_less_common_primary_topic():
    cands = [C("1", ["AI"]), C("2", ["AI"]), C("3", ["AI"]), C("4", ["Cloud"])]
    scores = topic_rarity_scores(cands)
    assert scores["4"] > scores["1"]
    assert scores["1"] == scores["2"] == scores["3"]
    assert all(0.0 <= v <= 1.0 for v in scores.values())


def test_rarity_deterministic():
    cands = [C("1", ["AI"]), C("2", ["Cloud"])]
    assert topic_rarity_scores(cands) == topic_rarity_scores(cands)


def test_rarity_empty():
    assert topic_rarity_scores([]) == {}


def test_interleave_breaks_long_streaks():
    ranked = [C(str(i), ["AI"]) for i in range(4)] + [C("x", ["Cloud"]), C("y", ["Business"])]
    out = interleave_by_topic(ranked, max_streak=2)

    primaries = [c.topics[0] for c in out]
    # no 3 in a row
    assert not any(
        primaries[i] == primaries[i + 1] == primaries[i + 2]
        for i in range(len(primaries) - 2)
    )
    # same members, nothing lost
    assert {c.id for c in out} == {c.id for c in ranked}


def test_interleave_noop_when_already_diverse():
    ranked = [C("1", ["AI"]), C("2", ["Cloud"]), C("3", ["AI"]), C("4", ["Business"])]
    assert [c.id for c in interleave_by_topic(ranked, max_streak=2)] == ["1", "2", "3", "4"]
