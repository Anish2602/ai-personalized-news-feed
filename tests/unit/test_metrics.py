from __future__ import annotations

from prometheus_client import REGISTRY

from app.core.metrics import start_worker_metrics_server

REQUIRED = {
    "articles_ingested_total",
    "articles_processed_total",
    "duplicate_articles_total",
    "embedding_requests_total",
    "embedding_latency_seconds",
    "llm_requests_total",
    "llm_latency_seconds",
    "feed_requests_total",
    "feed_generation_latency_seconds",
    "feed_cache_hits_total",
    "feed_cache_misses_total",
    "worker_failures_total",
    "http_requests_total",
    "celery_tasks_total",
}


def test_all_spec_metrics_are_registered():
    names = {metric.name for metric in REGISTRY.collect()}
    # counters register under their base name (without the _total suffix)
    missing = {m.removesuffix("_total") for m in REQUIRED} - names
    assert not missing, missing


def test_worker_metrics_server_survives_port_clash(monkeypatch):
    def _raise(_port):
        raise OSError("address in use")

    monkeypatch.setattr("prometheus_client.start_http_server", _raise)
    start_worker_metrics_server(9999)  # must not raise
