"""Tests for BaseAgentNode.

This module provides full test coverage for the base agent node functionality
including error handling, logging, state management, and tool initialization.
Tests use actual domain models with proper mocking and async patterns.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from tripsage.app_state import AppServiceContainer
from tripsage.orchestration.nodes.base import BaseAgentNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state
from tests.unit.orchestration.test_utils import create_mock_services


class TestableAgentNode(BaseAgentNode):
    """Concrete implementation of BaseAgentNode for testing."""

    def __init__(
        self,
        services: AppServiceContainer,
        process_func=None,
        initialize_func=None,
        config: dict[str, Any] | None = None,
    ):
        """Initialize with optional custom functions."""
        self.process_func = process_func
        self.initialize_func = initialize_func
        super().__init__("test_agent", services, config)

    def _initialize_tools(self) -> None:
        """Initialize tools for testing."""
        if self.initialize_func:
            self.initialize_func()
        else:
            # Default initialization
            self.test_tool = MagicMock()

    async def process(self, state: TravelPlanningState) -> TravelPlanningState:
        """Process state for testing."""
        if self.process_func:
            return await self.process_func(state)
        else:
            # Default implementation
            state["messages"].append(
                {
                    "role": "assistant",
                    "content": "Test response",
                    "agent": self.node_name,
                }
            )
            return state


class TestBaseAgentNode:
    """Test suite for BaseAgentNode."""

    @pytest.fixture
    def mock_services(self):
        """Create a mock service container."""
        services = create_mock_services(
            {
                "memory_service": MagicMock(),
            }
        )
        services.get_required_service = MagicMock(
            side_effect=lambda name, **_: getattr(services, name)
        )
        services.get_optional_service = MagicMock(
            side_effect=lambda name, **_: getattr(services, name, None)
        )
        return services

    @pytest.fixture
    def sample_state(self):
        """Create a sample travel planning state."""
        return create_initial_state("user-123", "Help me plan a trip to Tokyo")

    @pytest.fixture
    def test_node(self, mock_services):
        """Create a testable agent node."""
        return TestableAgentNode(mock_services)

    def test_node_initialization(self, mock_services):
        """Test basic node initialization."""
        config = {"test_config": "value"}
        node = TestableAgentNode(mock_services, config=config)

        assert node.node_name == "test_agent"
        assert node.name == "test_agent"  # Property alias
        assert node.services == mock_services
        assert node.config == config
        assert hasattr(node, "logger")
        assert hasattr(node, "test_tool")

    def test_custom_tool_initialization(self, mock_services):
        """Test custom tool initialization."""
        initialized = False

        def custom_init():
            nonlocal initialized
            initialized = True

        _node = TestableAgentNode(mock_services, initialize_func=custom_init)

        assert initialized is True

    @pytest.mark.asyncio
    async def test_successful_processing(self, test_node, sample_state):
        """Test successful state processing."""
        # Process the state
        result = await test_node(sample_state)

        # Verify state updates
        assert len(result["messages"]) == 2  # Original + response
        assert result["messages"][-1]["role"] == "assistant"
        assert result["messages"][-1]["content"] == "Test response"
        assert result["messages"][-1]["agent"] == "test_agent"

        # Verify agent history
        assert "test_agent" in result["agent_history"]

        # Verify timestamp update
        assert result["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_custom_processing(self, mock_services, sample_state):
        """Test node with custom processing function."""

        async def custom_process(state):
            state["custom_field"] = "custom_value"
            state["messages"].append(
                {
                    "role": "assistant",
                    "content": "Custom response",
                    "agent": "test_agent",
                }
            )
            return state

        node = TestableAgentNode(mock_services, process_func=custom_process)
        result = await node(sample_state)

        assert result["custom_field"] == "custom_value"
        assert result["messages"][-1]["content"] == "Custom response"

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_services, sample_state):
        """Test error handling during processing."""

        async def failing_process(state):
            raise ValueError("Processing failed")

        node = TestableAgentNode(mock_services, process_func=failing_process)

        # Process should handle error gracefully
        result = await node(sample_state)

        # Verify error tracking in error_info structure
        assert result["error_info"]["error_count"] == 1
        assert result["error_info"]["last_error"] == "Processing failed"
        assert "test_agent" in result["error_info"]["retry_attempts"]
        assert result["error_info"]["retry_attempts"]["test_agent"] == 1

        # Verify error message added
        error_msg = result["messages"][-1]
        assert error_msg["role"] == "assistant"
        assert "encountered an issue" in error_msg["content"]
        assert error_msg["error"] is True
        assert error_msg["agent"] == "test_agent"

    @pytest.mark.asyncio
    async def test_multiple_errors_increment_count(
        self, mock_services, sample_state
    ):
        """Test that multiple errors increment the error count correctly."""

        async def failing_process(state):
            raise RuntimeError("Another error")

        node = TestableAgentNode(mock_services, process_func=failing_process)

        # First error
        result1 = await node(sample_state)
        assert result1["error_info"]["error_count"] == 1

        # Second error
        result2 = await node(result1)
        assert result2["error_info"]["error_count"] == 2
        assert result2["error_info"]["retry_attempts"]["test_agent"] == 2

    def test_extract_user_intent_default(self, test_node):
        """Test default user intent extraction."""
        message = "I want to book a flight"
        intent = test_node._extract_user_intent(message)

        assert intent["message"] == message
        assert intent["node"] == "test_agent"
        assert "timestamp" in intent

    def test_create_response_message(self, test_node):
        """Test response message creation."""
        content = "Here are your flight options"
        additional_data = {"flight_count": 5, "search_id": "abc123"}

        message = test_node._create_response_message(content, additional_data)

        assert message["role"] == "assistant"
        assert message["content"] == content
        assert message["agent"] == "test_agent"
        assert message["flight_count"] == 5
        assert message["search_id"] == "abc123"
        assert "timestamp" in message

    def test_create_response_message_without_additional_data(self, test_node):
        """Test response message creation without additional data."""
        content = "Simple response"
        message = test_node._create_response_message(content)

        assert message["role"] == "assistant"
        assert message["content"] == content
        assert message["agent"] == "test_agent"
        assert "timestamp" in message

    def test_get_service_required(self, test_node, mock_service_registry):
        """Test getting a required service."""
        mock_service = MagicMock()
        mock_service_registry.get_required_service.return_value = mock_service

        service = test_node.get_service("test_service")

        assert service == mock_service
        mock_service_registry.get_required_service.assert_called_once_with(
            "test_service"
        )

    def test_get_service_optional(self, test_node, mock_service_registry):
        """Test getting an optional service."""
        mock_service = MagicMock()
        mock_service_registry.get_optional_service.return_value = mock_service

        service = test_node.get_optional_service("optional_service")

        assert service == mock_service
        mock_service_registry.get_optional_service.assert_called_once_with(
            "optional_service"
        )

    def test_get_service_optional_none(self, test_node, mock_service_registry):
        """Test getting an optional service that doesn't exist."""
        mock_service_registry.get_optional_service.return_value = None

        service = test_node.get_optional_service("nonexistent_service")

        assert service is None

    @pytest.mark.asyncio
    async def test_logging_during_execution(self, test_node, sample_state, caplog):
        """Test that proper logging occurs during execution."""
        # Process the state
        await test_node(sample_state)

        # Check log messages
        assert "Executing test_agent node" in caplog.text
        assert "Successfully completed test_agent node execution" in caplog.text

    @pytest.mark.asyncio
    async def test_error_logging(self, mock_service_registry, sample_state, caplog):
        """Test error logging during failed processing."""

        async def failing_process(state):
            raise Exception("Test error")

        node = TestableAgentNode(mock_service_registry, process_func=failing_process)

        await node(sample_state)

        assert "Error in test_agent node: Test error" in caplog.text

    @pytest.mark.asyncio
    async def test_state_timestamp_update(self, test_node, sample_state):
        """Test that state timestamp is properly updated."""
        original_timestamp = sample_state.get("updated_at")

        # Small delay to ensure timestamp difference
        import asyncio

        await asyncio.sleep(0.01)

        result = await test_node(sample_state)

        # Timestamp should be updated
        assert result["updated_at"] != original_timestamp
        assert datetime.fromisoformat(result["updated_at"]) > datetime.fromisoformat(
            original_timestamp
        )

    @pytest.mark.asyncio
    async def test_inheritance_pattern(self, mock_service_registry):
        """Test that the inheritance pattern works correctly."""

        class CustomAgentNode(BaseAgentNode):
            def _initialize_tools(self):
                self.custom_tool = "initialized"

            async def process(self, state):
                state["custom_processed"] = True
                return state

        node = CustomAgentNode("custom_agent", mock_service_registry)

        assert node.node_name == "custom_agent"
        assert hasattr(node, "custom_tool")
        assert node.custom_tool == "initialized"

        state = create_initial_state("user-123", "Test message")
        result = await node(state)

        assert result["custom_processed"] is True
        assert "custom_agent" in result["agent_history"]
