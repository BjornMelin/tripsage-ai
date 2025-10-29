"""Additional RouterNode tests: fallbacks and context edges."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

import pytest

from tests.unit.orchestration.test_utils import MockChatOpenAI, patch_openai_in_module
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state


def _make_router() -> RouterNode:
    """Create router with MockChatOpenAI classifier."""
    container = AppServiceContainer()
    with patch("tripsage.orchestration.routing.ChatOpenAI", MockChatOpenAI):
        return RouterNode(container)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.routing")
async def test_classification_missing_fields_fallback() -> None:
    """Fallback classification when LLM omits required routing fields."""
    router = _make_router()

    class _LLM:
        """LLM stub."""

        async def ainvoke(self, *_: Any, **__: Any) -> Any:
            """Return empty JSON string."""
            return "{}"  # Missing keys

    router.classifier = cast(Any, _LLM())
    _unused_state = create_initial_state("u", "help")
    out = await router._classify_intent("x", {})  # type: ignore[reportPrivateUsage]
    assert out["agent"] in {"general_agent", "error_recovery"}


def test_activity_search_only_context() -> None:
    """Context builder should flag activity-only presence as activities."""
    router = _make_router()
    st: TravelPlanningState = create_initial_state("u", "")
    st["activity_searches"].append({"id": 1})
    ctx = router._build_conversation_context(st)  # type: ignore[reportPrivateUsage]
    assert ctx["previous_searches"] == "activities"
