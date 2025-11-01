"""OpenRouter adapter using OpenAI-compatible SDK with attribution headers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from tripsage_core.services.external_apis.providers.interfaces import (
    ChatCompletionAdapter,
)
from tripsage_core.services.external_apis.providers.token_budget import (
    count_tokens as _count_tokens,
)


class OpenRouterAdapter(ChatCompletionAdapter):
    """Adapter for OpenRouter via OpenAI SDK base_url."""

    def __init__(self, api_key: str) -> None:
        """Create a new OpenRouter adapter.

        Args:
            api_key: OpenRouter API key.
        """
        self._api_key = api_key
        from openai import OpenAI  # lazy import

        self._client = OpenAI(
            api_key=self._api_key, base_url="https://openrouter.ai/api/v1"
        )  # type: ignore[call-arg]

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
