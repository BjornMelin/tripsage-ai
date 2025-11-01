"""MemoryUpdateNode tests: search/interaction insights and memory update path."""

from __future__ import annotations

from typing import Any, cast

import pytest

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.memory_update import MemoryUpdateNode
from tripsage.orchestration.state import create_initial_state


def _make_node() -> MemoryUpdateNode:
    """Create a MemoryUpdateNode with an empty service container."""
    return MemoryUpdateNode(AppServiceContainer())


def test_extract_search_and_interaction_insights() -> None:
    """_extract_search_insights captures routes/locations/types; interaction counts."""
    node = _make_node()
    st = create_initial_state("u1", "")
    st["flight_searches"] = [
        {"parameters": {"origin": "NYC", "destination": "LAX"}},
        {"parameters": {"origin": "NYC", "destination": "LAX"}},
    ]
    st["accommodation_searches"] = [
        {"parameters": {"location": "Paris"}},
    ]
    st["activity_searches"] = [
        {"parameters": {"type": "museum"}},
    ]
    st["agent_history"] = ["router", "flight_agent", "flight_agent"]

    search_insights = node._extract_search_insights(st)  # type: ignore[reportPrivateUsage]
    interaction_insights = node._extract_interaction_insights(st)  # type: ignore[reportPrivateUsage]

    assert any("Searched flight route: NYC-LAX" in s for s in search_insights)
    assert any("Searched accommodation in: Paris" in s for s in search_insights)
    assert any("Interested in activity type: museum" in s for s in search_insights)
    assert any("Frequently used flight_agent" in s for s in interaction_insights)


@pytest.mark.asyncio
async def test_process_invokes_memory_tool() -> None:
    """process() should call memory tool when insights exist and not crash."""
    node = _make_node()

    class _Tool:
        def __init__(self) -> None:
            self.called: bool = False

        async def ainvoke(self, *_: Any, **__: Any) -> dict[str, Any]:
            """Record invocation and return success payload."""
            self.called = True
            return {"ok": True}

    node.memory_tool = cast(Any, _Tool())

    st = create_initial_state("u1", "")
    st["flight_searches"] = [{"parameters": {"origin": "NYC", "destination": "LAX"}}]
    out = await node.process(st)
    assert out is st
    assert cast(_Tool, node.memory_tool).called  # type: ignore[union-attr]
