from __future__ import annotations

from app.workers import processing_tasks


def test_backoff_is_exponential(monkeypatch):
    monkeypatch.setattr(processing_tasks._settings, "task_retry_backoff_seconds", 10)
    assert processing_tasks._backoff_seconds(0) == 10
    assert processing_tasks._backoff_seconds(1) == 20
    assert processing_tasks._backoff_seconds(2) == 40
    assert processing_tasks._backoff_seconds(3) == 80
