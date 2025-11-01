"""Tests for RouterNode classification and context handling."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import patch

import pytest

from tests.unit.orchestration.test_utils import MockChatOpenAI, MockLLMResponse
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState


@contextmanager
def router_context(
    llm_cls: type[MockChatOpenAI] = MockChatOpenAI,
) -> Iterator[RouterNode]:
    """Yield a router node with patched ChatOpenAI implementation."""
    container = AppServiceContainer()
    with patch("tripsage.orchestration.routing.ChatOpenAI", llm_cls):
        yield RouterNode(container)


@pytest.mark.asyncio
async def test_classify_intent_json_and_fallback(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Router should parse JSON or fall back with safe default when parse fails."""
    responses = iter(
        [
            '{"agent": "flight_agent", "confidence": 0.9, "reasoning": "flight"}',
            "not-json",
        ]
    )

    class _Factory(MockChatOpenAI):
        """Factory that yields predetermined responses per instantiation."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._response_iter = responses

        async def ainvoke(self, *_: Any, **__: Any) -> MockLLMResponse:
            """Return the next configured response regardless of prompt."""
            return MockLLMResponse(next(self._response_iter, "null"))

    with router_context(_Factory) as router:
        classify_intent = cast(Any, router)._classify_intent
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

        fallback = await classify_intent("what is travel?", {}, user_id)
        assert fallback["agent"] in {"general_agent", "error_recovery"}


def test_build_conversation_context_variants(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """_build_conversation_context should reflect available state slices."""
    with router_context() as router:
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
    responses = iter(
        [
            '{"agent": "invalid_agent", "confidence": 0.9, "reasoning": "-"}',
            '{"agent": "flight_agent", "confidence": 1.5, "reasoning": "-"}',
        ]
    )

    class _Factory(MockChatOpenAI):
        """Factory returning predetermined invalid classifications."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self._response_iter = responses

        async def ainvoke(self, *_: Any, **__: Any) -> MockLLMResponse:
            return MockLLMResponse(next(self._response_iter, "null"))

    with router_context(_Factory) as router:
        classify_intent = cast(Any, router)._classify_intent
        state = state_factory()
        user_id = str(state["user_id"])

        fb1 = await classify_intent("x", {}, user_id)
        assert fb1["agent"] == "general_agent"

        fb2 = await classify_intent("x", {}, user_id)
        assert fb2["agent"] == "general_agent"
