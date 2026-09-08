from __future__ import annotations

import pytest

from app.core.logging import bind_context, clear_context, get_context


@pytest.fixture(autouse=True)
def _clean():
    clear_context()
    yield
    clear_context()


def test_bind_and_get_context():
    bind_context(request_id="r1", user_id="u1")
    assert get_context() == {"request_id": "r1", "user_id": "u1"}


def test_none_values_are_dropped():
    bind_context(request_id="r1", user_id=None, article_id=None)
    assert get_context() == {"request_id": "r1"}


def test_clear_context():
    bind_context(task_id="t1")
    clear_context()
    assert get_context() == {}
