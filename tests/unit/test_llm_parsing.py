from __future__ import annotations

import pytest

from app.ai.parsing import extract_json_object


@pytest.mark.parametrize(
    "raw",
    [
        '{"a": 1}',
        '```json\n{"a": 1}\n```',
        'Sure! Here is the JSON:\n{"a": 1}\nHope that helps.',
        '```\n{"a": 1}\n```',
    ],
)
def test_recovers_object(raw):
    assert extract_json_object(raw) == {"a": 1}


@pytest.mark.parametrize("raw", ["", "   ", "not json at all", "[1, 2, 3]", "null"])
def test_returns_none_when_unusable(raw):
    assert extract_json_object(raw) is None


def test_prefers_first_valid_candidate():
    raw = 'prefix {"summary": "s", "key_points": ["a"]} suffix'
    assert extract_json_object(raw) == {"summary": "s", "key_points": ["a"]}
