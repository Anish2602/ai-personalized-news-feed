from __future__ import annotations

from app.core.config import Settings


def test_settings_load_from_env(settings):
    assert settings.app_name
    assert settings.environment == "development"
    assert settings.news_rss_feeds == ["https://example.com/rss"]


def test_interaction_weights_are_config_driven():
    s = Settings(interaction_weight_like=9.0)
    assert s.interaction_weights["LIKE"] == 9.0
    assert set(s.interaction_weights) == {
        "VIEW",
        "CLICK",
        "LIKE",
        "SAVE",
        "SHARE",
        "SKIP",
        "DISLIKE",
    }


def test_ranking_weights_roughly_sum_to_one():
    s = Settings()
    assert abs(sum(s.ranking_weights.values()) - 1.0) < 1e-6


def test_no_secrets_hardcoded_in_defaults():
    s = Settings()
    assert s.llm_api_key is None
    assert s.qdrant_api_key is None
