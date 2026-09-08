from __future__ import annotations

from types import SimpleNamespace

from app.core.logging import clear_context, get_context
from app.workers import celery_app as ca


def _task(name="app.workers.x.do", request_id=None):
    req = SimpleNamespace(get=lambda k, d=None: {"request_id": request_id}.get(k, d))
    return SimpleNamespace(name=name, request=req)


def test_prerun_binds_task_context_including_request_id():
    clear_context()
    ca._bind_task_context(task_id="tid-1", task=_task(request_id="req-9"))
    ctx = get_context()
    assert ctx["task_id"] == "tid-1"
    assert ctx["task_name"] == "app.workers.x.do"
    assert ctx["request_id"] == "req-9"
    clear_context()


def test_postrun_records_metric_and_clears_context():
    from prometheus_client import REGISTRY

    task = _task(name="app.workers.x.done")
    ca._bind_task_context(task_id="tid-2", task=task)
    before = (
        REGISTRY.get_sample_value(
            "celery_tasks_total", {"task": "app.workers.x.done", "state": "SUCCESS"}
        )
        or 0.0
    )

    ca._record_task(task_id="tid-2", task=task, state="SUCCESS")

    after = REGISTRY.get_sample_value(
        "celery_tasks_total", {"task": "app.workers.x.done", "state": "SUCCESS"}
    )
    assert after == before + 1
    assert get_context() == {}


def test_dispatch_forwards_request_id_header(monkeypatch):
    from app.core.logging import bind_context
    from app.workers import dispatch

    clear_context()
    bind_context(request_id="abc-123")
    assert dispatch._headers() == {"request_id": "abc-123"}
    clear_context()
    assert dispatch._headers() == {}
