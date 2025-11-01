"""Additional RouterNode tests: fallbacks and context edges."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import patch

import pytest

from tests.unit.orchestration.test_utils import (
    MockChatOpenAI,
    MockLLMResponse,
    patch_openai_in_module,
)
from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state


@contextmanager
def router_context(
    llm_cls: type[MockChatOpenAI] = MockChatOpenAI,
) -> Iterator[RouterNode]:
    """Create router with injected ChatOpenAI patch."""
    container = AppServiceContainer()
    with patch("tripsage.orchestration.routing.ChatOpenAI", llm_cls):
        yield RouterNode(container)


@pytest.mark.asyncio
@patch_openai_in_module("tripsage.orchestration.routing")
async def test_classification_missing_fields_fallback() -> None:
    """Fallback classification when LLM omits required routing fields."""

    class _LLM(MockChatOpenAI):
        """LLM stub that returns empty JSON."""

        async def ainvoke(self, *_: Any, **__: Any) -> Any:
            return MockLLMResponse("{}")

    with router_context(_LLM) as router:
        classify_intent = cast(Any, router)._classify_intent
        _unused_state = create_initial_state("u", "help")
        out = await classify_intent("x", {}, "user-1")
        assert out["agent"] in {"general_agent", "error_recovery"}


def test_activity_search_only_context() -> None:
    """Context builder should flag activity-only presence as activities."""
    with router_context() as router:
        st: TravelPlanningState = create_initial_state("u", "")
        st["activity_searches"].append({"id": 1})
        ctx = router._build_conversation_context(st)  # type: ignore[reportPrivateUsage]
        assert ctx["previous_searches"] == "activities"
