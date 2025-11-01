"""Anthropic Messages API adapter via official SDK."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

from tripsage_core.services.external_apis.providers.interfaces import (
    ChatCompletionAdapter,
)
from tripsage_core.services.external_apis.providers.token_budget import (
    count_tokens as _count_tokens,
)


class AnthropicAdapter(ChatCompletionAdapter):
    """Thin adapter over Anthropic's Python SDK."""

    def __init__(self, api_key: str) -> None:
        """Create a new Anthropic adapter.

        Args:
            api_key: Anthropic API key.
        """
        from anthropic import Anthropic  # type: ignore[reportMissingImports]

        self._client = Anthropic(api_key=api_key)

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        model: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        headers: dict[str, str] | None = None,  # unused in Anthropic
    ) -> str:
        """Perform a messages.create call and return text content."""
        # Anthropic expects roles 'user'/'assistant'; system can be prepended if present
        ant_msgs: list[dict[str, str]] = []
        system_prefix: str | None = None
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_prefix = (system_prefix or "") + str(content)
                continue
            ant_msgs.append({"role": str(role), "content": str(content)})
        if system_prefix:
            # Prepend system as a user message prefix for simplicity
            if ant_msgs:
                ant_msgs[0]["content"] = f"{system_prefix}\n\n{ant_msgs[0]['content']}"
            else:
                ant_msgs.append({"role": "user", "content": system_prefix})

        # Anthropic requires max_tokens as a mandatory keyword argument
        max_tokens_value = int(max_tokens) if max_tokens is not None else 1024

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": ant_msgs,
            "max_tokens": max_tokens_value,
        }
        if temperature is not None:
            kwargs["temperature"] = float(temperature)

        msg = cast(Any, self._client).messages.create(**kwargs)
        chunks: list[str] = []
        for c in getattr(msg, "content", []) or []:
            text = getattr(c, "text", None)
            if isinstance(text, str):
                chunks.append(text)
        return "".join(chunks)

    def count_tokens(self, texts: Iterable[str], model_hint: str | None = None) -> int:
        """Count tokens using provider-default encoding."""
        return _count_tokens(texts, model_hint)
