"""LLM provider selection.

``get_llm_provider()`` returns ``None`` when the LLM is disabled or unconfigured
so callers transparently fall back (keyword classification, extractive summary).
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.llm.base import LLMMessage, LLMProvider
from app.core.config import get_settings


@lru_cache
def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if not settings.llm_enabled or not settings.llm_api_key:
        return None
    name = settings.llm_provider.lower()
    if name in ("openai", "openai-compatible", "oai"):
        from app.ai.llm.openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"Unknown LLM_PROVIDER: {name!r}")


__all__ = ["LLMMessage", "LLMProvider", "get_llm_provider"]
