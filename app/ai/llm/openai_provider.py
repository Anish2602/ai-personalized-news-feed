from __future__ import annotations

import time
from typing import TYPE_CHECKING

from app.ai.llm.base import LLMMessage, LLMProvider
from app.core.config import get_settings
from app.core.exceptions import UpstreamError
from app.core.logging import get_logger
from app.core.metrics import llm_latency_seconds, llm_requests_total

if TYPE_CHECKING:
    from openai import AsyncOpenAI

logger = get_logger(__name__)
_PROVIDER_LABEL = "openai"


class OpenAIProvider(LLMProvider):
    """Works with the OpenAI API or any OpenAI-compatible endpoint
    (``LLM_BASE_URL``). Nothing here is OpenAI-specific beyond the wire format."""

    def __init__(self, *, model: str | None = None) -> None:
        settings = get_settings()
        self._model = model or settings.llm_model
        self._temperature = settings.llm_temperature
        self._max_tokens = settings.llm_max_tokens
        self._timeout = settings.llm_timeout_seconds
        self._max_retries = settings.llm_max_retries
        self._api_key = settings.llm_api_key
        self._base_url = settings.llm_base_url
        self._client: AsyncOpenAI | None = None

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._client

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        from openai import APIError, APIStatusError

        kwargs: dict = {
            "model": self._model,
            "messages": [m.model_dump() for m in messages],
            "temperature": self._temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self._max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.perf_counter()
        try:
            response = await self._get_client().chat.completions.create(**kwargs)
        except APIStatusError as exc:
            llm_requests_total.labels(_PROVIDER_LABEL, "complete", "error").inc()
            if exc.status_code and 400 <= exc.status_code < 500 and exc.status_code != 429:
                raise UpstreamError(f"LLM rejected the request ({exc.status_code}).") from exc
            raise UpstreamError(f"LLM error ({exc.status_code}).") from exc
        except APIError as exc:
            llm_requests_total.labels(_PROVIDER_LABEL, "complete", "error").inc()
            raise UpstreamError(f"LLM transport error: {exc}") from exc
        finally:
            llm_latency_seconds.labels(_PROVIDER_LABEL, "complete").observe(
                time.perf_counter() - start
            )

        llm_requests_total.labels(_PROVIDER_LABEL, "complete", "ok").inc()
        content = response.choices[0].message.content or ""
        return content.strip()
