"""Centralised, environment-driven application configuration.

All tunables live here so that nothing (credentials, model names, thresholds,
scoring weights) is hardcoded in business logic. Import the singleton via
``get_settings()`` which is cached for the process lifetime.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "AI Personalized News Feed"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Security ---
    secret_key: str = "change-me-in-production"
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # --- PostgreSQL ---
    database_url: str = "postgresql+psycopg://newsfeed:newsfeed@localhost:5432/newsfeed"
    db_pool_size: int = 10
    db_max_overflow: int = 5
    db_echo: bool = False

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Qdrant ---
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "articles"
    qdrant_vector_size: int = 384

    # --- Embeddings ---
    embedding_provider: str = "sentence_transformer"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    embedding_max_chars: int = 2000

    # --- LLM ---
    llm_provider: str = "openai"
    llm_enabled: bool = False
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 30
    llm_max_retries: int = 3
    llm_temperature: float = 0.2
    llm_max_tokens: int = 700
    llm_output_max_attempts: int = 2

    # --- News ingestion ---
    news_rss_feeds: list[str] = Field(default_factory=list)
    news_api_enabled: bool = False
    news_api_key: str | None = None
    ingest_max_articles_per_feed: int = 50
    ingest_http_timeout_seconds: float = 15.0
    ingest_interval_minutes: int = 30

    # --- Deduplication ---
    semantic_duplicate_threshold: float = 0.90
    dedup_top_k: int = 10

    # --- Topic taxonomy ---
    topic_taxonomy: list[str] = Field(
        default_factory=lambda: [
            "Artificial Intelligence",
            "Software Engineering",
            "Cloud",
            "Cybersecurity",
            "Startups",
            "Business",
            "Finance",
            "Science",
            "Technology",
            "Politics",
            "World",
            "Sports",
            "Entertainment",
        ]
    )

    # --- Interaction weights ---
    interaction_weight_view: float = 1.0
    interaction_weight_click: float = 2.0
    interaction_weight_like: float = 3.0
    interaction_weight_save: float = 4.0
    interaction_weight_share: float = 4.0
    interaction_weight_skip: float = -1.0
    interaction_weight_dislike: float = -4.0

    # --- User profile ---
    profile_max_interactions: int = 200

    # --- Ranking weights (must sum to 1.0 — see test_ranking_weights_sum_to_one) ---
    rank_weight_semantic: float = 0.50
    rank_weight_freshness: float = 0.15
    rank_weight_popularity: float = 0.10
    rank_weight_source_quality: float = 0.10
    rank_weight_diversity: float = 0.05
    rank_weight_topic_affinity: float = 0.10
    freshness_decay_hours: float = 24.0
    feed_default_limit: int = 20
    feed_max_limit: int = 50
    feed_candidate_pool: int = 200
    feed_exclude_consumed: bool = True

    # Per-source trust score in [0, 1]; sources not listed get the default.
    source_quality: dict[str, float] = Field(default_factory=dict)
    source_quality_default: float = 0.5

    # --- Feed cache + diversity ---
    feed_cache_ttl_seconds: int = 300
    feed_diversity_max_streak: int = 2
    feed_cache_invalidate_types: list[str] = Field(
        default_factory=lambda: ["LIKE", "DISLIKE", "SAVE", "SHARE", "SKIP"]
    )

    # --- Celery task policy ---
    task_max_retries: int = 3
    task_retry_backoff_seconds: int = 10

    # --- Observability ---
    worker_metrics_port: int = 9100

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    @field_validator("qdrant_api_key", "llm_api_key", "news_api_key", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        # An unset env var is often written as `KEY=` -> treat "" as absent.
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def interaction_weights(self) -> dict[str, float]:
        """Map of InteractionType name -> weight, sourced entirely from config."""
        return {
            "VIEW": self.interaction_weight_view,
            "CLICK": self.interaction_weight_click,
            "LIKE": self.interaction_weight_like,
            "SAVE": self.interaction_weight_save,
            "SHARE": self.interaction_weight_share,
            "SKIP": self.interaction_weight_skip,
            "DISLIKE": self.interaction_weight_dislike,
        }

    @property
    def ranking_weights(self) -> dict[str, float]:
        return {
            "semantic": self.rank_weight_semantic,
            "freshness": self.rank_weight_freshness,
            "popularity": self.rank_weight_popularity,
            "source_quality": self.rank_weight_source_quality,
            "diversity": self.rank_weight_diversity,
            "topic_affinity": self.rank_weight_topic_affinity,
        }

    @property
    def sync_database_url(self) -> str:
        """Sync SQLAlchemy URL for Alembic. psycopg3 supports sync + async."""
        return self.database_url

    @property
    def cors_allows_wildcard(self) -> bool:
        return "*" in self.cors_allow_origins

    def production_issues(self) -> list[str]:
        """Blocking misconfigurations for a production deployment (checked at
        startup). Non-production environments ignore these."""
        if not self.is_production:
            return []
        issues: list[str] = []
        if self.secret_key == "change-me-in-production" or len(self.secret_key) < 16:
            issues.append("SECRET_KEY is unset/default/too short")
        if self.debug:
            issues.append("DEBUG must be false in production")
        if self.cors_allows_wildcard:
            issues.append("CORS_ALLOW_ORIGINS must not be '*' in production")
        if self.llm_enabled and not self.llm_api_key:
            issues.append("LLM_ENABLED is true but LLM_API_KEY is missing")
        return issues


@lru_cache
def get_settings() -> Settings:
    return Settings()
