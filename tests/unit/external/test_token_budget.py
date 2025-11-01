"""Smoke test for token budgeting utility."""

from tripsage_core.services.external_apis.providers.token_budget import count_tokens


def test_count_tokens_basic() -> None:
    """Ensure counting returns a positive integer."""
    texts = ["hello", "world"]
    total = count_tokens(texts, model_hint="gpt-4o-mini")
    assert isinstance(total, int)
    assert total > 0
