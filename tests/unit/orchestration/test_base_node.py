"""Tests for BaseAgentNode helper methods."""

from __future__ import annotations

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState


class _Node(BaseAgentNode):
    """Test subclass of BaseAgentNode."""

    def _initialize_tools(self) -> None:
        """Initialize tools."""
        return

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Return state unchanged for test subclass."""
        return state


def test_create_response_message_and_services() -> None:
    """_create_response_message and service getters should work as expected."""
    container = AppServiceContainer()
    node = _Node("test_node", container)
    msg = node._create_response_message("ok", {"k": 1})  # type: ignore[reportPrivateUsage]
    assert msg["role"] == "assistant"
    assert msg["content"] == "ok"
    assert msg["agent"] == "test_node"
    assert msg["k"] == 1

    # Optional missing service returns None
    assert node.get_optional_service("unknown") is None
