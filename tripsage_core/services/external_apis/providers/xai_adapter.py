"""xAI adapter using OpenAI-compatible client if available."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from os import getenv
from typing import Any

from .interfaces import ChatCompletionAdapter
from .token_budget import count_tokens as _count_tokens


class XAIAdapter(ChatCompletionAdapter):
    """Adapter for xAI via OpenAI-compatible SDK endpoints."""

    def __init__(self, api_key: str, *, base_url: str | None = None) -> None:
        """Create a new xAI adapter using OpenAI-compatible SDK.

        Args:
            api_key: xAI API key.
            base_url: Optional base URL if different from default.
        """
        from openai import OpenAI  # lazy import

        resolved_base = base_url or getenv("XAI_API_BASE") or "https://api.x.ai/v1"
        self._client = OpenAI(api_key=api_key, base_url=resolved_base)  # type: ignore[call-arg]

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        model: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Perform a chat completion and return assistant content."""
        from typing import cast

        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if headers:
            kwargs["extra_headers"] = headers

        resp = cast(Any, self._client).chat.completions.create(**kwargs)
        return str(resp.choices[0].message.content or "")

    def count_tokens(self, texts: Iterable[str], model_hint: str | None = None) -> int:
        """Count tokens using provider-default encoding."""
        return _count_tokens(texts, model_hint)
