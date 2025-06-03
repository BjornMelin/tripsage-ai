"""
Integration tests for orchestration nodes.

This module tests the integration between different orchestration nodes
and the centralized tool registry.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.error_recovery import ErrorRecoveryNode
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import (
    ErrorInfo,
    HandoffContext,
    create_initial_state,
)


class TestNodesIntegration:
    """Test integration between orchestration nodes."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        return Mock(spec=ServiceRegistry)

    @pytest.fixture
    def sample_state(self):
        """Create a sample travel planning state."""
        return create_initial_state("test_user", "Find me flights to NYC")

    @pytest.mark.asyncio
    async def test_flight_agent_tool_registry_integration(self, mock_service_registry):
        """Test that FlightAgentNode properly integrates with tool registry."""
        with patch(
            "tripsage.orchestration.nodes.flight_agent.get_tool_registry"
        ) as mock_registry:
            # Setup mock tool registry
            mock_tool_registry = Mock()
            mock_tool_registry.get_tools_for_agent.return_value = []
            mock_tool_registry.get_langchain_tools_for_agent.return_value = []
            mock_registry.return_value = mock_tool_registry

            # Create flight agent node
            flight_agent = FlightAgentNode(mock_service_registry)

            # Verify tool registry integration
            assert flight_agent.tool_registry == mock_tool_registry
            mock_tool_registry.get_tools_for_agent.assert_called_with(
                agent_type="flight_agent",
                capabilities=[
                    "flight_search",
                    "geocoding",
                    "weather",
                    "web_search",
                    "memory",
                ],
            )

    @pytest.mark.asyncio
    async def test_router_node_classification(self, mock_service_registry):
        """Test router node intent classification."""
        with patch("tripsage.orchestration.routing.ChatOpenAI") as mock_llm_class:
            # Setup mock LLM
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = (
                '{"agent": "flight_agent", "confidence": 0.9, '
                '"reasoning": "User wants flights"}'
            )
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            # Create router node
            router = RouterNode(mock_service_registry)

            # Create test state
            state = create_initial_state("test_user", "Find me flights to NYC")

            # Process the state
            result = await router.process(state)

            # Verify routing decision
            assert result["current_agent"] == "flight_agent"
            assert "handoff_context" in result
            assert result["handoff_context"]["routing_confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_error_recovery_retry_strategy(self, mock_service_registry):
        """Test error recovery node retry strategy."""
        # Create error recovery node
        error_recovery = ErrorRecoveryNode(mock_service_registry)

        # Create state with error
        state = create_initial_state("test_user", "Test message")
        error_info = ErrorInfo(
            error_count=2,
            last_error="Test error",
            retry_attempts={"flight_agent": 1},
            error_history=[],
        )
        state["error_info"] = error_info.model_dump()
        state["current_agent"] = "flight_agent"

        # Process error recovery
        result = await error_recovery.process(state)

        # Verify retry logic
        assert len(result["messages"]) > len(state["messages"])
        assert result["current_agent"] == "router"
        assert "handoff_context" in result

        # Check that retry attempt was recorded
        updated_error_info = ErrorInfo.model_validate(result["error_info"])
        assert updated_error_info.retry_attempts["flight_agent"] == 2

    @pytest.mark.asyncio
    async def test_error_recovery_escalation(self, mock_service_registry):
        """Test error recovery escalation to human support."""
        # Create error recovery node
        error_recovery = ErrorRecoveryNode(mock_service_registry)

        # Create state with high error count
        state = create_initial_state("test_user", "Test message")
        error_info = ErrorInfo(
            error_count=6,  # Above escalation threshold
            last_error="Persistent error",
            retry_attempts={"flight_agent": 3},
            error_history=[],
        )
        state["error_info"] = error_info.model_dump()
        state["current_agent"] = "flight_agent"

        # Process error recovery
        result = await error_recovery.process(state)

        # Verify escalation logic
        escalation_message = result["messages"][-1]
        assert escalation_message["escalation"] is True
        assert "human" in escalation_message["content"].lower()
        assert "handoff_context" in result
        assert (
            result["handoff_context"]["escalation"]["reason"]
            == "Multiple error recovery attempts failed"
        )

    @pytest.mark.asyncio
    async def test_flight_agent_parameter_extraction(self, mock_service_registry):
        """Test flight agent parameter extraction from user message."""
        with (
            patch("tripsage.orchestration.nodes.flight_agent.get_tool_registry"),
            patch(
                "tripsage.orchestration.nodes.flight_agent.ChatOpenAI"
            ) as mock_llm_class,
        ):
            # Setup mock LLM for parameter extraction
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = (
                '{"origin": "NYC", "destination": "LAX", '
                '"departure_date": "2024-03-15"}'
            )
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            # Create flight agent
            flight_agent = FlightAgentNode(mock_service_registry)

            # Create test state
            state = create_initial_state(
                "test_user", "Find flights from NYC to LAX on March 15th"
            )

            # Extract parameters
            params = await flight_agent._extract_flight_parameters(
                "Find flights from NYC to LAX on March 15th", state
            )

            # Verify parameter extraction
            assert params["origin"] == "NYC"
            assert params["destination"] == "LAX"
            assert params["departure_date"] == "2024-03-15"

    @pytest.mark.asyncio
    async def test_flight_agent_search_execution(self, mock_service_registry):
        """Test flight agent search execution with tool registry."""
        with patch(
            "tripsage.orchestration.nodes.flight_agent.get_tool_registry"
        ) as mock_registry:
            # Setup mock tool registry
            mock_tool_registry = Mock()
            mock_search_tool = Mock()
            mock_search_tool.execute = AsyncMock(
                return_value={
                    "flights": [
                        {"airline": "Delta", "price": "$300", "departure_time": "08:00"}
                    ]
                }
            )
            mock_tool_registry.get_tool.return_value = mock_search_tool
            mock_tool_registry.get_tools_for_agent.return_value = []
            mock_tool_registry.get_langchain_tools_for_agent.return_value = []
            mock_registry.return_value = mock_tool_registry

            # Create flight agent
            flight_agent = FlightAgentNode(mock_service_registry)

            # Execute search
            search_params = {"origin": "NYC", "destination": "LAX"}
            result = await flight_agent._search_flights(search_params)

            # Verify search execution
            assert "flights" in result
            assert len(result["flights"]) == 1
            assert result["flights"][0]["airline"] == "Delta"
            mock_search_tool.execute.assert_called_once_with(**search_params)

    @pytest.mark.asyncio
    async def test_nodes_state_consistency(self, mock_service_registry):
        """Test that nodes maintain state consistency."""
        with (
            patch("tripsage.orchestration.routing.ChatOpenAI") as mock_llm_class,
            patch("tripsage.orchestration.nodes.flight_agent.get_tool_registry"),
        ):
            # Setup mocks
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = (
                '{"agent": "flight_agent", "confidence": 0.9, '
                '"reasoning": "Flight request"}'
            )
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_llm_class.return_value = mock_llm

            # Create nodes
            router = RouterNode(mock_service_registry)

            # Create initial state
            initial_state = create_initial_state("test_user", "Find flights to NYC")

            # Process through router
            routed_state = await router.process(initial_state)

            # Verify state structure is maintained
            assert routed_state["user_id"] == initial_state["user_id"]
            assert routed_state["session_id"] == initial_state["session_id"]
            assert len(routed_state["messages"]) == len(initial_state["messages"])
            assert "current_agent" in routed_state
            assert "handoff_context" in routed_state

    @pytest.mark.asyncio
    async def test_handoff_context_flow(self, mock_service_registry):
        """Test handoff context flows correctly between nodes."""
        # Create error recovery node
        error_recovery = ErrorRecoveryNode(mock_service_registry)

        # Create state with handoff context
        state = create_initial_state("test_user", "Test message")
        handoff_context = HandoffContext(
            from_agent="flight_agent",
            to_agent="error_recovery",
            routing_confidence=0.7,
            routing_reasoning="Error occurred",
            timestamp="2024-01-01T00:00:00Z",
            message_analyzed="Test message",
        )
        state["handoff_context"] = handoff_context.model_dump()
        state["current_agent"] = "flight_agent"
        state["error_info"] = ErrorInfo().model_dump()

        # Process through error recovery
        result = await error_recovery.process(state)

        # Verify new handoff context is created
        assert "handoff_context" in result
        new_handoff = HandoffContext.model_validate(result["handoff_context"])
        assert new_handoff.from_agent == "error_recovery"
        assert new_handoff.to_agent == "router"

    @pytest.mark.asyncio
    async def test_memory_integration_flow(self, mock_service_registry):
        """Test memory integration across nodes."""
        with patch(
            "tripsage.orchestration.nodes.flight_agent.get_tool_registry"
        ) as mock_registry:
            # Setup mock memory tool
            mock_tool_registry = Mock()
            mock_memory_tool = Mock()
            mock_memory_tool.execute = AsyncMock(return_value={"status": "saved"})
            mock_tool_registry.get_tool.return_value = mock_memory_tool
            mock_tool_registry.get_tools_for_agent.return_value = [mock_memory_tool]
            mock_tool_registry.get_langchain_tools_for_agent.return_value = []
            mock_registry.return_value = mock_tool_registry

            # Create flight agent
            flight_agent = FlightAgentNode(mock_service_registry)

            # Verify memory tools are available
            tools = flight_agent.available_tools
            assert mock_memory_tool in tools

            # Test memory tool capability
            result = await mock_memory_tool.execute(
                content="User prefers economy class"
            )
            assert result["status"] == "saved"
