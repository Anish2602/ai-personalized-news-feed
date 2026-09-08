from __future__ import annotations

from app.core.config import Settings

_PROD = {
    "environment": "production",
    "debug": False,
    "secret_key": "a-sufficiently-long-secret-value",
    "cors_allow_origins": ["https://app.example.com"],
}


def test_development_has_no_production_issues():
    assert Settings(environment="development", secret_key="short").production_issues() == []


def test_healthy_production_config_passes():
    assert Settings(**_PROD).production_issues() == []


def test_default_secret_key_is_flagged():
    issues = Settings(**{**_PROD, "secret_key": "change-me-in-production"}).production_issues()
    assert any("SECRET_KEY" in i for i in issues)


def test_debug_true_is_flagged():
    issues = Settings(**{**_PROD, "debug": True}).production_issues()
    assert any("DEBUG" in i for i in issues)


def test_wildcard_cors_is_flagged():
    issues = Settings(**{**_PROD, "cors_allow_origins": ["*"]}).production_issues()
    assert any("CORS" in i for i in issues)


def test_llm_enabled_without_key_is_flagged():
    issues = Settings(**{**_PROD, "llm_enabled": True, "llm_api_key": None}).production_issues()
    assert any("LLM_API_KEY" in i for i in issues)
