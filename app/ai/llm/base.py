from __future__ import annotations

import abc
from typing import Literal

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMProvider(abc.ABC):
    """Minimal chat-completion interface. Concrete providers translate transport
    failures into :class:`app.core.exceptions.UpstreamError` (retryable); they do
    NOT interpret the response body — malformed *content* is the caller's problem
    (see the summarizer/classifier recovery logic)."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str: ...

    @abc.abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str: ...
