"""Structured story summarization.

Produces ``{summary, key_points[], topics[]}`` validated by Pydantic. Malformed
LLM output is recovered where possible, re-prompted up to
``LLM_OUTPUT_MAX_ATTEMPTS`` times, then raises :class:`LLMOutputError`. When no
LLM is configured it degrades to a deterministic extractive summary.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.ai.llm.base import LLMMessage, LLMProvider
from app.ai.parsing import extract_json_object
from app.core.config import get_settings
from app.core.exceptions import LLMOutputError
from app.core.logging import get_logger

logger = get_logger(__name__)

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_SYSTEM = (
    "You summarize news articles. Reply with ONLY a JSON object of the form "
    '{{"summary": string, "key_points": string[], "topics": string[]}}. '
    "summary: 2-3 neutral sentences. key_points: 3-5 short bullet strings. "
    "topics: 1-4 labels chosen from this list: {taxonomy}."
)


class SummaryResult(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    key_points: list[str] = Field(default_factory=list, max_length=10)
    topics: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("key_points", "topics", mode="before")
    @classmethod
    def _to_list(cls, v: object) -> object:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


class Summarizer:
    def __init__(self, llm: LLMProvider | None, *, max_attempts: int | None = None) -> None:
        self.llm = llm
        self.max_attempts = max_attempts or get_settings().llm_output_max_attempts

    async def summarize(
        self, *, title: str, text: str, taxonomy: list[str]
    ) -> SummaryResult:
        if self.llm is None:
            return self._extractive(title, text)

        system = _SYSTEM.format(taxonomy=", ".join(taxonomy))
        user = f"Title: {title}\n\nArticle:\n{text}"
        messages = [
            LLMMessage(role="system", content=system),
            LLMMessage(role="user", content=user),
        ]

        last_error = "no attempts made"
        for attempt in range(1, self.max_attempts + 1):
            raw = await self.llm.complete(messages, json_mode=True)
            payload = extract_json_object(raw)
            if payload is None:
                last_error = "response was not JSON"
            else:
                payload.setdefault("summary", "")
                try:
                    result = SummaryResult.model_validate(payload)
                    if result.summary.strip():
                        result.topics = [t for t in result.topics if t in taxonomy]
                        return result
                    last_error = "empty summary"
                except ValidationError as exc:
                    last_error = f"schema mismatch: {exc.error_count()} errors"
            logger.warning("summarizer_retry", attempt=attempt, reason=last_error)
            messages.append(
                LLMMessage(
                    role="user",
                    content="That was not valid. Reply with ONLY the JSON object, nothing else.",
                )
            )

        raise LLMOutputError(f"summarizer failed after {self.max_attempts} attempts: {last_error}")

    @staticmethod
    def _extractive(title: str, text: str) -> SummaryResult:
        sentences = [s.strip() for s in _SENTENCE_RE.split(text.strip()) if s.strip()]
        summary = " ".join(sentences[:3]) if sentences else title
        return SummaryResult(summary=summary[:4000], key_points=sentences[:3], topics=[])
