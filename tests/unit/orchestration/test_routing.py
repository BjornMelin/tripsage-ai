"""Tests for RouterNode classification and context handling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import patch

import pytest

from tests.unit.orchestration.test_utils import MockChatOpenAI
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState


def _make_router() -> RouterNode:
    """Make router node."""
    container = AppServiceContainer()
    with patch("tripsage.orchestration.routing.ChatOpenAI", MockChatOpenAI):
        return RouterNode(container)


@pytest.mark.asyncio
async def test_classify_intent_json_and_fallback(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Router should parse JSON or fall back with safe default when parse fails."""
    router = _make_router()
    classify_intent = cast(Any, router)._classify_intent
    # Mock returns agent=flight_agent JSON
    cast(Any, router.classifier).set_default_response(  # type: ignore[attr-defined] # pylint: disable=no-member
        '{"agent": "flight_agent", "confidence": 0.9, "reasoning": "flight"}'
    )
    state = state_factory(
        extra={"messages": [{"role": "user", "content": "find flights"}]}
    )
    user_id = str(state["user_id"])
    classification = await classify_intent(
        "find flights",
        router._build_conversation_context(state),  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
        user_id,
    )
    assert classification["agent"] == "flight_agent"

    # Now use a classifier that returns invalid JSON to trigger fallback
    class _BadLLM:
        """Bad LLM stub."""

        async def ainvoke(self, *_: Any, **__: Any):
            """Invoke bad LLM."""
            return "not-json"

    router.classifier = _BadLLM()  # type: ignore[assignment]
    fallback = await classify_intent("what is travel?", {}, user_id)
    assert fallback["agent"] in {"general_agent", "error_recovery"}


def test_build_conversation_context_variants(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """_build_conversation_context should reflect available state slices."""
    router = _make_router()
    st = state_factory(
        extra={
            "flight_searches": [{"id": 1}],
            "user_preferences": {"items": ["window seat"]},
            "destination_info": {"recent_destinations": ["Paris"]},
            "agent_history": ["router", "flight_agent"],
        }
    )
    ctx = router._build_conversation_context(st)  # type: ignore[reportPrivateUsage]  # pylint: disable=protected-access
    assert ctx["previous_searches"] == "flights"
    assert "user_preferences" in ctx
    assert "current_trip_context" in ctx
    assert ctx["recent_agents"] == ["router", "flight_agent"]


@pytest.mark.asyncio
async def test_invalid_agent_and_confidence_bounds(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Router should fallback on invalid agent or bad confidence values."""
    router = _make_router()
    classify_intent = cast(Any, router)._classify_intent
    state = state_factory()
    user_id = str(state["user_id"])

    class _BadAgentLLM:
        """Bad agent LLM stub."""

        async def ainvoke(self, *_: Any, **__: Any):
            """Return invalid agent in serialized JSON."""
            return '{"agent": "invalid_agent", "confidence": 0.9, "reasoning": "-"}'

    router.classifier = _BadAgentLLM()  # type: ignore[assignment]
    fb1 = await classify_intent("x", {}, user_id)
    assert fb1["agent"] == "general_agent"

    class _BadConfLLM:
        """Bad confidence LLM stub."""

        async def ainvoke(self, *_: Any, **__: Any):
            """Return out-of-bounds confidence to trigger fallback."""
            return '{"agent": "flight_agent", "confidence": 1.5, "reasoning": "-"}'

    router.classifier = _BadConfLLM()  # type: ignore[assignment]
    fb2 = await classify_intent("x", {}, user_id)
    assert fb2["agent"] == "general_agent"
