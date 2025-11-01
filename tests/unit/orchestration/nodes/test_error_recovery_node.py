"""ErrorRecoveryNode tests: retry and fallback flows."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.error_recovery import ErrorRecoveryNode
from tripsage.orchestration.state import TravelPlanningState


async def _run(
    node: ErrorRecoveryNode, state: TravelPlanningState
) -> TravelPlanningState:
    """Run node with typed state and return updated state."""
    return await node.process(state)


@pytest.mark.asyncio
async def test_retry_then_fallback(
    state_factory: Callable[..., TravelPlanningState],
) -> None:
    """Error recovery should retry first and then fall back after threshold."""
    services = AppServiceContainer()
    node = ErrorRecoveryNode(services)
    # First: error_count below retry threshold triggers retry path
    st = state_factory(current_agent="flight_agent", error_count=1)
    st = await _run(node, st)
    assert st["current_agent"] == "router"
    # After retries exceed threshold, fallback path sets current_agent to a fallback
    st = state_factory(current_agent="flight_agent", error_count=node.max_retries + 1)
    st = await _run(node, st)
    assert st["current_agent"] in {"general_agent", "router", "budget_agent"}
