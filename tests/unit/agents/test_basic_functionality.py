"""
Basic functionality tests for LangGraph orchestrator.

These tests verify that the core Phase 1 implementation is working correctly.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.orchestration.config import LangGraphConfig
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import TravelPlanningState, create_initial_state


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    with patch("tripsage.config.app_settings.settings") as mock_settings:
        mock_settings.agent.model_name = "gpt-4"
        mock_settings.agent.temperature = 0.7
        mock_settings.agent.max_tokens = 4096
        mock_settings.openai_api_key.get_secret_value.return_value = "test-api-key"
        mock_settings.database.supabase_url = None

        config = LangGraphConfig.from_app_settings()
        yield config


@pytest.fixture
def sample_state():
    """Sample travel planning state for testing."""
    state = create_initial_state(
        user_id="test-user-123",
        message="I need help finding flights from NYC to Paris",
        session_id="test-session-456",
    )
    state["user_preferences"] = {"budget": "moderate", "class": "economy"}
    state["context"] = {"query_type": "flight_search"}
    return state


class TestTripSageOrchestrator:
    """Test the main orchestrator functionality."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, mock_config):
        """Test that orchestrator initializes correctly."""
        orchestrator = TripSageOrchestrator(mock_config)

        # Check that the graph is built
        assert orchestrator.graph is not None

        # Check that router is in the graph
        assert "router" in orchestrator.graph.nodes

    @pytest.mark.asyncio
    async def test_router_classification(self, mock_config, sample_state):
        """Test that router correctly classifies user intent."""
        with patch("tripsage.orchestration.routing.get_openai_client") as mock_client:
            # Mock OpenAI response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = """
            {
                "agent": "flight_agent",
                "confidence": 0.95,
                "reasoning": "User is asking about flights from NYC to Paris"
            }
            """

            mock_openai = Mock()
            mock_openai.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_openai

            router = RouterNode()
            result = await router.process(sample_state)

            # Check that routing was successful
            assert result["current_agent"] == "flight_agent"
            assert "router" in result["agent_history"]

    @pytest.mark.asyncio
    async def test_flight_agent_processing(self, mock_config, sample_state):
        """Test that flight agent processes requests correctly."""
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_manager:
            # Mock MCP manager response
            mock_manager_instance = Mock()
            mock_manager_instance.invoke = AsyncMock(
                return_value={
                    "flights": [
                        {
                            "airline": "Air France",
                            "departure": "2024-02-01T10:00:00Z",
                            "arrival": "2024-02-01T22:00:00Z",
                            "price": 650,
                        }
                    ]
                }
            )
            mock_manager.return_value = mock_manager_instance

            # Update state for flight agent
            flight_state = sample_state.copy()
            flight_state["current_agent"] = "flight_agent"

            flight_agent = FlightAgentNode()
            result = await flight_agent.process(flight_state)

            # Check that flight search was executed
            assert "flight_searches" in result
            assert len(result["flight_searches"]) > 0

    @pytest.mark.asyncio
    async def test_phase1_placeholder_agents(self, mock_config, sample_state):
        """Test that Phase 1 placeholder agents work correctly."""
        orchestrator = TripSageOrchestrator(mock_config)

        # Test accommodation agent placeholder
        accommodation_state = sample_state.copy()
        accommodation_state["current_agent"] = "accommodation_agent"

        result = await orchestrator._accommodation_agent(accommodation_state)

        # Check placeholder response
        assert len(result["messages"]) > len(sample_state["messages"])
        new_message = result["messages"][-1]
        assert "accommodation_agent" in new_message["content"]
        assert "Phase 1 implementation" in new_message["content"]

    @pytest.mark.asyncio
    async def test_error_recovery_node(self, mock_config, sample_state):
        """Test error recovery functionality."""
        from tripsage.orchestration.nodes.error_recovery import ErrorRecoveryNode

        # Create error state
        error_state = sample_state.copy()
        error_state["error_count"] = 1
        error_state["last_error"] = "Test error message"

        error_recovery = ErrorRecoveryNode()
        result = await error_recovery.process(error_state)

        # Check that error was handled
        assert "messages" in result
        assert len(result["messages"]) > len(error_state["messages"])

    @pytest.mark.asyncio
    async def test_memory_update_node(self, mock_config, sample_state):
        """Test memory update functionality."""
        from tripsage.orchestration.nodes.memory_update import MemoryUpdateNode

        # Add some data to extract insights from
        memory_state = sample_state.copy()
        memory_state["budget_constraints"] = {"max_budget": 1000}
        memory_state["destination_info"] = {"name": "Paris", "preferences": ["museums"]}

        with patch.object(
            MemoryUpdateNode, "_update_knowledge_graph"
        ) as mock_kg_update:
            with patch.object(
                MemoryUpdateNode, "_update_session_data"
            ) as mock_session_update:
                mock_kg_update.return_value = None
                mock_session_update.return_value = None

                memory_node = MemoryUpdateNode()
                await memory_node.process(memory_state)

                # Check that insights were extracted
                mock_kg_update.assert_called_once()
                mock_session_update.assert_called_once()

    def test_state_schema_validation(self):
        """Test that state schema validation works correctly."""
        # Valid state
        valid_state = TravelPlanningState(
            user_id="test-123",
            session_id="session-456",
            messages=[],
            current_agent="router",
            agent_history=[],
        )

        assert valid_state["user_id"] == "test-123"
        assert valid_state["session_id"] == "session-456"
        assert valid_state["current_agent"] == "router"

    @pytest.mark.asyncio
    async def test_graph_routing_logic(self, mock_config, sample_state):
        """Test the graph routing logic."""
        orchestrator = TripSageOrchestrator(mock_config)

        # Test different routing scenarios
        test_cases = [
            (
                "router",
                [
                    "flight_agent",
                    "accommodation_agent",
                    "budget_agent",
                    "itinerary_agent",
                ],
            ),
            ("flight_agent", ["memory_update", "END"]),
            ("accommodation_agent", ["memory_update", "END"]),
            ("memory_update", ["END"]),
        ]

        for current_agent, expected_next in test_cases:
            test_state = sample_state.copy()
            test_state["current_agent"] = current_agent

            next_node = orchestrator._determine_next_node(test_state)
            assert next_node in expected_next, (
                f"Expected {next_node} to be in {expected_next} "
                f"for agent {current_agent}"
            )


class TestErrorHandling:
    """Test error handling in the orchestrator."""

    @pytest.mark.asyncio
    async def test_mcp_connection_error(self, mock_config, sample_state):
        """Test handling of MCP connection errors."""
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_manager:
            # Mock MCP connection error
            mock_manager_instance = Mock()
            mock_manager_instance.invoke = AsyncMock(
                side_effect=Exception("MCP connection failed")
            )
            mock_manager.return_value = mock_manager_instance

            flight_agent = FlightAgentNode()
            result = await flight_agent.process(sample_state)

            # Check that error was handled gracefully
            assert "error_count" in result
            assert result["error_count"] > 0

    @pytest.mark.asyncio
    async def test_invalid_state_handling(self, mock_config):
        """Test handling of invalid state."""
        orchestrator = TripSageOrchestrator(mock_config)

        # Create invalid state (missing required fields)
        invalid_state = {"user_id": "test"}  # Missing required fields

        # Should handle gracefully or raise appropriate error
        try:
            result = await orchestrator._router(invalid_state)
            # If it doesn't raise an error, it should at least not crash
            assert isinstance(result, dict)
        except (KeyError, ValueError, TypeError):
            # Expected behavior for invalid state
            pass


@pytest.mark.integration
class TestLangGraphIntegration:
    """Integration tests for LangGraph components."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, mock_config, sample_state):
        """Test a complete conversation flow through the graph."""
        with patch("tripsage.orchestration.routing.get_openai_client") as mock_client:
            with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_manager:
                # Mock OpenAI router response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.choices[0].message.content = """
                {
                    "agent": "flight_agent",
                    "confidence": 0.95,
                    "reasoning": "User wants flight information"
                }
                """

                mock_openai = Mock()
                mock_openai.chat.completions.create = AsyncMock(
                    return_value=mock_response
                )
                mock_client.return_value = mock_openai

                # Mock MCP manager
                mock_manager_instance = Mock()
                mock_manager_instance.invoke = AsyncMock(return_value={"flights": []})
                mock_manager.return_value = mock_manager_instance

                orchestrator = TripSageOrchestrator(mock_config)

                # Process through router -> flight_agent -> memory_update
                router_result = await orchestrator._router(sample_state)
                assert router_result["current_agent"] == "flight_agent"

                flight_result = await orchestrator._flight_agent(router_result)
                assert "flight_searches" in flight_result

                memory_result = await orchestrator._memory_update(flight_result)
                assert memory_result is not None

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, mock_config, sample_state):
        """Test error recovery flow in the graph."""
        with patch("tripsage.mcp_abstraction.manager.MCPManager") as mock_manager:
            # Mock MCP error
            mock_manager_instance = Mock()
            mock_manager_instance.invoke = AsyncMock(
                side_effect=Exception("Service error")
            )
            mock_manager.return_value = mock_manager_instance

            orchestrator = TripSageOrchestrator(mock_config)

            # Process flight agent with error
            flight_state = sample_state.copy()
            flight_state["current_agent"] = "flight_agent"

            result = await orchestrator._flight_agent(flight_state)

            # Should have incremented error count
            assert result.get("error_count", 0) > 0

            # Test error recovery
            recovery_result = await orchestrator._error_recovery(result)
            assert recovery_result is not None
