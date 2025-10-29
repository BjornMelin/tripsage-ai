"""RouterNode fallback tests that simulate classification exceptions."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from tests.unit.orchestration.test_utils import MockChatOpenAI
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.routing import RouterNode


def _make_router() -> RouterNode:
    """Create router with a mock classifier."""
    container = AppServiceContainer()
    with patch("tripsage.orchestration.routing.ChatOpenAI", MockChatOpenAI):
        return RouterNode(container)


@pytest.mark.asyncio
async def test_classify_with_exception_fallback() -> None:
    """When classification raises, router returns safe fallback dict."""
    router = _make_router()

    async def _raise(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise RuntimeError("classifier down")

    # Patch private classify to raise so fallback path is reached
    router._classify_intent = _raise  # type: ignore[assignment, reportPrivateUsage]
    out = await router._classify_with_fallback("hi", {})  # type: ignore[reportPrivateUsage]
    assert out["agent"] in {"general_agent", "error_recovery"}
    assert 0.0 <= out.get("confidence", 0.0) <= 1.0
