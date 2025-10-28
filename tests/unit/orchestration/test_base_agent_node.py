"""Unit tests for :mod:`tripsage.orchestration.nodes.base`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState


class TestAgentNode(BaseAgentNode):
    """Concrete implementation of BaseAgentNode for testing."""

    def _initialize_tools(self) -> None:
        """Initialize tools for testing."""

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process state for testing."""
        return state


@pytest.fixture()
def mock_service_registry() -> ServiceRegistry:
    """Create a mock service registry for testing."""
    return MagicMock(spec=ServiceRegistry)


@pytest.fixture()
def test_agent_node(mock_service_registry: ServiceRegistry) -> TestAgentNode:
    """Create a TestAgentNode instance for testing."""
    return TestAgentNode("test_node", mock_service_registry)


@pytest.fixture()
def sample_state() -> TravelPlanningState:
    """Create a sample travel planning state for testing."""
    return {
        "messages": [],
        "user_id": "test_user",
        "session_id": "test_session",
        "user_preferences": None,
        "travel_dates": None,
        "destination_info": None,
        "flight_searches": [],
        "accommodation_searches": [],
        "activity_searches": [],
        "budget_analyses": [],
        "destination_research": [],
        "itineraries": [],
        "booking_progress": None,
        "current_agent": None,
        "agent_history": [],
        "handoff_context": None,
        "error_info": {},
        "active_tool_calls": [],
        "completed_tool_calls": [],
        "conversation_summary": None,
        "extracted_entities": {},
        "user_intent": None,
        "confidence_score": None,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z",
        "last_activity": "2023-01-01T00:00:00Z",
        "is_active": True,
    }


def test_base_agent_node_initialization(
    test_agent_node: TestAgentNode, mock_service_registry: ServiceRegistry
) -> None:
    """BaseAgentNode initializes with correct attributes."""
    assert test_agent_node.node_name == "test_node"
    assert test_agent_node.service_registry == mock_service_registry
    assert test_agent_node.config == {}
    assert test_agent_node.name == "test_node"


def test_base_agent_node_initialization_with_config(
    mock_service_registry: ServiceRegistry,
) -> None:
    """BaseAgentNode accepts custom config."""
    config = {"test_key": "test_value"}
    node = TestAgentNode("test_node", mock_service_registry, config=config)

    assert node.config == config


@pytest.mark.asyncio
async def test_call_success(
    test_agent_node: TestAgentNode, sample_state: TravelPlanningState
) -> None:
    """__call__ method executes successfully and updates state."""
    initial_history = sample_state["agent_history"].copy()
    initial_updated_at = sample_state["updated_at"]

    result = await test_agent_node(sample_state)

    assert result["agent_history"] == [*initial_history, "test_node"]
    assert (
        result["updated_at"] != initial_updated_at
    )  # update_state_timestamp updates this


@pytest.mark.asyncio
async def test_call_with_error(
    test_agent_node: TestAgentNode, sample_state: TravelPlanningState
) -> None:
    """__call__ method handles errors gracefully."""
    # Mock process to raise an exception
    test_agent_node.process = AsyncMock(side_effect=Exception("Test error"))

    result = await test_agent_node(sample_state)

    # Check error info was updated
    assert result["error_info"]["error_count"] == 1
    assert result["error_info"]["last_error"] == "Test error"
    assert result["error_info"]["retry_attempts"]["test_node"] == 1

    # Check error message was added
    assert len(result["messages"]) == 1
    message = result["messages"][0]
    assert message["role"] == "assistant"
    assert "encountered an issue" in message["content"]
    assert message["agent"] == "test_node"
    assert message["error"] is True


def test_handle_error(
    test_agent_node: TestAgentNode, sample_state: TravelPlanningState
) -> None:
    """_handle_error updates state with error information."""
    error = Exception("Test error")

    result = test_agent_node._handle_error(sample_state, error)  # type: ignore[reportPrivateUsage]

    assert result["error_info"]["error_count"] == 1
    assert result["error_info"]["last_error"] == "Test error"
    assert result["error_info"]["retry_attempts"]["test_node"] == 1
    assert len(result["messages"]) == 1


def test_extract_user_intent(test_agent_node: TestAgentNode) -> None:
    """_extract_user_intent returns basic intent information."""
    message = "I want to go to Paris"

    result = test_agent_node._extract_user_intent(message)  # type: ignore[reportPrivateUsage]

    assert result["message"] == message
    assert result["node"] == "test_node"
    assert "timestamp" in result


def test_create_response_message(test_agent_node: TestAgentNode) -> None:
    """_create_response_message creates properly formatted message."""
    content = "This is a test response"

    result = test_agent_node._create_response_message(content)  # type: ignore[reportPrivateUsage]

    assert result["role"] == "assistant"
    assert result["content"] == content
    assert result["agent"] == "test_node"
    assert "timestamp" in result


def test_create_response_message_with_additional_data(
    test_agent_node: TestAgentNode,
) -> None:
    """_create_response_message includes additional data."""
    content = "Response"
    additional_data = {"extra": "data", "number": 42}

    result = test_agent_node._create_response_message(content, additional_data)  # type: ignore[reportPrivateUsage]

    assert result["extra"] == "data"
    assert result["number"] == 42


def test_get_service(
    test_agent_node: TestAgentNode, mock_service_registry: ServiceRegistry
) -> None:
    """get_service delegates to service registry."""
    mock_service = MagicMock()
    mock_service_registry.get_required_service = MagicMock(return_value=mock_service)

    result = test_agent_node.get_service("test_service")  # type: ignore[reportUnknownVariableType]

    mock_service_registry.get_required_service.assert_called_once_with("test_service")
    assert result == mock_service


def test_get_optional_service(
    test_agent_node: TestAgentNode, mock_service_registry: ServiceRegistry
) -> None:
    """get_optional_service delegates to service registry."""
    mock_service = MagicMock()
    mock_service_registry.get_optional_service = MagicMock(return_value=mock_service)

    result = test_agent_node.get_optional_service("test_service")

    mock_service_registry.get_optional_service.assert_called_once_with("test_service")
    assert result == mock_service
