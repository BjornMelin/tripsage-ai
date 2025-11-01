"""Minimal provider interfaces for LLM adapters.

These Protocols define the narrow surface used by orchestrators/services to
avoid depending on specific SDKs. Adapters are small, typed, and easy to swap.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol


class ChatCompletionAdapter(Protocol):
    """Protocol for chat completion providers.

    Implementations should be thin wrappers over official SDKs.
    """

    def complete(
        self,
        messages: Sequence[dict[str, str]],
        model: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:  # pragma: no cover - Protocol stub
        """Return the assistant content for a chat completion."""
        raise NotImplementedError

    def count_tokens(
        self, texts: Iterable[str], model_hint: str | None = None
    ) -> int:  # pragma: no cover - Protocol stub
        """Return a coarse token count for budgeting/limits."""
        raise NotImplementedError
