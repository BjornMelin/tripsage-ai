"""Simple token budgeting utilities using tiktoken when available.

Falls back to a coarse heuristic if model encoding is unknown.
"""

from __future__ import annotations

from collections.abc import Iterable


def count_tokens(texts: Iterable[str], model_hint: str | None = None) -> int:
    """Count tokens for an iterable of texts.

    Uses ``tiktoken`` when available; otherwise, a 4-chars-per-token heuristic.

    Args:
        texts: Iterable of strings to count.
        model_hint: Optional encoding hint (e.g., OpenAI model name).

    Returns:
        Total token count as an integer.
    """
    total = 0
    try:
        import tiktoken  # type: ignore
    except ImportError:
        # Fallback heuristic: ~4 chars/token
        for t in texts:
            total += max(1, len(t or "") // 4)
        return total

    enc = tiktoken.get_encoding("cl100k_base")
    for t in texts:
        total += len(enc.encode(t or ""))
    return total


# Minimal per-model limits (extendable). Values are conservative defaults.
MODEL_LIMITS: dict[str, int] = {
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4.1": 128_000,
    "gpt-5": 200_000,
    "gpt-5-mini": 200_000,
    # Anthropic
    "claude-3.5-sonnet": 200_000,
    "claude-3.5-haiku": 200_000,
}
