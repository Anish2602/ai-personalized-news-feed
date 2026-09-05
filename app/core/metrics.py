"""Prometheus metric definitions.

Centralised so both the API process and Celery workers register the same
collectors against the default registry.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# --- Ingestion / processing ---
articles_ingested_total = Counter(
    "articles_ingested_total", "Articles persisted by ingestion", ["source"]
)
articles_processed_total = Counter(
    "articles_processed_total", "Articles that finished the processing pipeline", ["result"]
)
duplicate_articles_total = Counter(
    "duplicate_articles_total", "Articles attached to an existing story as duplicates", ["stage"]
)
worker_failures_total = Counter(
    "worker_failures_total", "Celery task failures", ["task"]
)

# --- Embeddings ---
embedding_requests_total = Counter(
    "embedding_requests_total", "Embedding provider calls", ["provider"]
)
embedding_latency_seconds = Histogram(
    "embedding_latency_seconds", "Embedding call latency", ["provider"]
)

# --- LLM ---
llm_requests_total = Counter(
    "llm_requests_total", "LLM provider calls", ["provider", "operation", "result"]
)
llm_latency_seconds = Histogram(
    "llm_latency_seconds", "LLM call latency", ["provider", "operation"]
)

# --- Feed ---
feed_requests_total = Counter("feed_requests_total", "Feed endpoint requests")
feed_generation_latency_seconds = Histogram(
    "feed_generation_latency_seconds", "Time to build a feed page (cache miss path)"
)
feed_cache_hits_total = Counter("feed_cache_hits_total", "Feed cache hits")
feed_cache_misses_total = Counter("feed_cache_misses_total", "Feed cache misses")

# --- HTTP ---
http_requests_total = Counter(
    "http_requests_total", "HTTP requests", ["method", "path", "status"]
)
http_request_latency_seconds = Histogram(
    "http_request_latency_seconds", "HTTP request latency", ["method", "path"]
)
