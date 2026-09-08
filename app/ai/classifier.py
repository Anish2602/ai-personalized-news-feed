"""Topic classification against a configurable taxonomy.

Prefers the LLM; on any LLM failure (transport or malformed) it falls back to a
transparent keyword matcher so an article is never left uncategorized.
"""

from __future__ import annotations

import re

from app.ai.llm.base import LLMMessage, LLMProvider
from app.ai.parsing import extract_json_object
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimal keyword hints for the offline fallback. Not exhaustive — the LLM path
# is the real classifier; this just keeps categorization non-empty.
_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Artificial Intelligence": ("ai", "machine learning", "llm", "neural", "openai", "model"),
    "Software Engineering": ("python", "javascript", "code", "compiler", "framework", "api"),
    "Cloud": ("aws", "azure", "gcp", "kubernetes", "serverless", "cloud"),
    "Cybersecurity": ("vulnerability", "breach", "malware", "exploit", "ransomware", "phishing"),
    "Startups": ("startup", "seed round", "series a", "founder", "y combinator"),
    "Business": ("acquisition", "merger", "revenue", "earnings", "layoffs"),
    "Finance": ("stock", "market", "inflation", "interest rate", "bond", "crypto"),
    "Science": ("research", "study", "physics", "biology", "climate", "space"),
    "Technology": ("gadget", "device", "chip", "processor", "hardware", "smartphone"),
    "Politics": ("senate", "congress", "election", "policy", "regulation", "president"),
    "World": ("ukraine", "china", "europe", "united nations", "treaty"),
    "Sports": ("nba", "nfl", "soccer", "olympics", "championship", "tournament"),
    "Entertainment": ("movie", "film", "netflix", "music", "album", "streaming series"),
}

_SYSTEM = (
    "You classify a news article into topics. Reply with ONLY a JSON object "
    '{{"topics": string[]}} where each topic is EXACTLY one of: {taxonomy}. '
    "Choose 1-3 topics, most specific first."
)


class Classifier:
    def __init__(
        self,
        llm: LLMProvider | None,
        taxonomy: list[str] | None = None,
        *,
        max_topics: int = 3,
    ) -> None:
        self.llm = llm
        self.taxonomy = taxonomy or get_settings().topic_taxonomy
        self.max_topics = max_topics

    async def classify(self, *, title: str, text: str) -> list[str]:
        if self.llm is not None:
            try:
                topics = await self._classify_llm(title, text)
                if topics:
                    return topics
                logger.warning("classifier_llm_empty_fallback")
            except AppError as exc:
                logger.warning("classifier_llm_failed_fallback", error=str(exc))
        return self._keyword_fallback(title, text)

    async def _classify_llm(self, title: str, text: str) -> list[str]:
        messages = [
            LLMMessage(role="system", content=_SYSTEM.format(taxonomy=", ".join(self.taxonomy))),
            LLMMessage(role="user", content=f"Title: {title}\n\n{text}"),
        ]
        raw = await self.llm.complete(messages, json_mode=True, temperature=0.0)
        payload = extract_json_object(raw) or {}
        raw_topics = payload.get("topics", [])
        if isinstance(raw_topics, str):
            raw_topics = [raw_topics]
        valid = [t for t in raw_topics if t in self.taxonomy]
        return _dedupe(valid)[: self.max_topics]

    def _keyword_fallback(self, title: str, text: str) -> list[str]:
        haystack = f"{title}\n{text}".lower()
        scored = [
            (topic, sum(_matches(kw, haystack) for kw in kws))
            for topic, kws in _KEYWORDS.items()
            if topic in self.taxonomy
        ]
        hits = sorted((s for s in scored if s[1] > 0), key=lambda s: s[1], reverse=True)
        if hits:
            return [t for t, _ in hits[: self.max_topics]]
        return ["Technology"] if "Technology" in self.taxonomy else self.taxonomy[:1]


def _matches(keyword: str, haystack: str) -> bool:
    """Whole-word (or phrase) match so short keywords like "ai" don't fire on
    "certain" / "email"."""
    return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", haystack) is not None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
