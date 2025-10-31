"""Token budgeting utilities using tiktoken.

Provides minimal helpers to count tokens for prompt budgeting and guardrails.
"""

from __future__ import annotations

from collections.abc import Iterable


def count_tokens(texts: Iterable[str], model_hint: str | None = None) -> int:
    """Return the total token count for a collection of texts.

    Args:
        texts: Sequence of strings to tokenize.
        model_hint: Optional model id to select encoding (best-effort).

    Returns:
        Sum of token counts across all strings.
    """
    import tiktoken

    enc = None
    if model_hint:
        try:
            enc = tiktoken.encoding_for_model(model_hint)
        except KeyError:
            enc = None
    if enc is None:
        enc = tiktoken.get_encoding("cl100k_base")

    total = 0
    for s in texts:
        total += len(enc.encode(s))
    return total
