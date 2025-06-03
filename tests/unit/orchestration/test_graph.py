"""
Comprehensive tests for the TripSage LangGraph orchestrator.

This module tests the main orchestration graph that coordinates all specialized
travel planning agents using LangGraph.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.state import create_initial_state


class TestTripSageOrchestrator:
    """Test the main orchestration graph."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        return Mock(spec=ServiceRegistry)

    @pytest.fixture
    def orchestrator(self, mock_service_registry):
        """Create an orchestrator instance for testing."""
        with (
            patch("tripsage.orchestration.graph.get_memory_bridge"),
            patch("tripsage.orchestration.graph.get_handoff_coordinator"),
            patch("tripsage.orchestration.graph.get_default_config"),
        ):
            return TripSageOrchestrator(service_registry=mock_service_registry)

    def test_orchestrator_initialization(self, orchestrator, mock_service_registry):
        """Test that the orchestrator initializes correctly."""
        assert orchestrator.service_registry == mock_service_registry
        assert orchestrator.graph is not None
        assert orchestrator.compiled_graph is None
        assert not orchestrator._initialized

    @pytest.mark.asyncio
    async def test_async_initialization(self, orchestrator):
        """Test async initialization of the orchestrator."""
        with patch.object(orchestrator, "checkpointer"):
            await orchestrator.initialize()

            assert orchestrator._initialized is True
            assert orchestrator.compiled_graph is not None

    def test_graph_has_required_nodes(self, orchestrator):
        """Test that the graph contains all required nodes."""
        graph = orchestrator.graph

        # Check that all expected nodes are present
        expected_nodes = {
            "router",
            "flight_agent",
            "accommodation_agent",
            "budget_agent",
            "destination_research_agent",
            "itinerary_agent",
            "general_agent",
            "memory_update",
            "error_recovery",
        }

        # Get actual nodes from the graph
        actual_nodes = set(graph.nodes.keys())
        assert expected_nodes.issubset(actual_nodes)

    def test_route_to_agent_with_valid_agent(self, orchestrator):
        """Test routing to a valid agent."""
        state = {
            "current_agent": "flight_agent",
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._route_to_agent(state)
        assert result == "flight_agent"

    def test_route_to_agent_with_error_count(self, orchestrator):
        """Test routing to error recovery when error count is high."""
        state = {
            "current_agent": "invalid_agent",
            "error_count": 5,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._route_to_agent(state)
        assert result == "error_recovery"

    def test_route_to_agent_fallback(self, orchestrator):
        """Test fallback routing to general agent."""
        state = {
            "current_agent": "invalid_agent",
            "error_count": 0,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._route_to_agent(state)
        assert result == "general_agent"

    def test_determine_next_step_with_errors(self, orchestrator):
        """Test next step determination when errors are present."""
        state = {
            "error_count": 2,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._determine_next_step(state)
        assert result == "error"

    def test_determine_next_step_with_handoff(self, orchestrator):
        """Test next step determination with agent handoff."""
        state = {
            "current_agent": "flight_agent",
            "error_count": 0,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        # Mock handoff coordinator to return a handoff
        mock_handoff_result = ("accommodation_agent", Mock())
        mock_handoff_result[1].model_dump = Mock(return_value={"test": "data"})
        orchestrator.handoff_coordinator.determine_next_agent = Mock(
            return_value=mock_handoff_result
        )

        result = orchestrator._determine_next_step(state)
        assert result == "continue"
        assert state["next_agent"] == "accommodation_agent"

    def test_determine_next_step_with_memory_update(self, orchestrator):
        """Test next step determination that requires memory update."""
        state = {
            "current_agent": "flight_agent",
            "error_count": 0,
            "user_preferences": {"budget": 1000},
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        # Mock handoff coordinator to return no handoff
        orchestrator.handoff_coordinator.determine_next_agent = Mock(return_value=None)

        result = orchestrator._determine_next_step(state)
        assert result == "memory"

    def test_determine_next_step_end_conversation(self, orchestrator):
        """Test next step determination that ends conversation."""
        state = {
            "current_agent": "flight_agent",
            "error_count": 0,
            "messages": [{"role": "assistant", "content": "How can I help?"}],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        # Mock handoff coordinator to return no handoff
        orchestrator.handoff_coordinator.determine_next_agent = Mock(return_value=None)

        result = orchestrator._determine_next_step(state)
        assert result == "end"

    def test_handle_recovery_retry(self, orchestrator):
        """Test recovery handling with retry."""
        state = {
            "error_count": 2,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._handle_recovery(state)
        assert result == "retry"

    def test_handle_recovery_end(self, orchestrator):
        """Test recovery handling that ends conversation."""
        state = {
            "error_count": 5,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._handle_recovery(state)
        assert result == "end"

    @pytest.mark.asyncio
    async def test_process_message_success(self, orchestrator):
        """Test successful message processing."""
        with (
            patch.object(orchestrator, "initialize", new_callable=AsyncMock),
            patch.object(orchestrator, "memory_bridge") as mock_memory_bridge,
            patch.object(orchestrator, "compiled_graph") as mock_graph,
        ):
            # Setup mocks
            mock_memory_bridge.hydrate_state = AsyncMock(
                return_value={
                    "messages": [{"role": "user", "content": "Find me flights"}],
                    "user_id": "test_user",
                    "session_id": "test_session",
                }
            )
            mock_memory_bridge.extract_and_persist_insights = AsyncMock(return_value={})

            mock_graph.ainvoke = AsyncMock(
                return_value={
                    "messages": [
                        {"role": "user", "content": "Find me flights"},
                        {
                            "role": "assistant",
                            "content": "I found some flights for you",
                        },
                    ],
                    "current_agent": "flight_agent",
                    "user_id": "test_user",
                    "session_id": "test_session",
                }
            )

            result = await orchestrator.process_message(
                "test_user", "Find me flights", "test_session"
            )

            assert result["response"] == "I found some flights for you"
            assert result["session_id"] == "test_session"
            assert result["agent_used"] == "flight_agent"

    @pytest.mark.asyncio
    async def test_process_message_error(self, orchestrator):
        """Test message processing with error."""
        with (
            patch.object(orchestrator, "initialize", new_callable=AsyncMock),
            patch.object(orchestrator, "memory_bridge") as mock_memory_bridge,
        ):
            # Setup error condition
            mock_memory_bridge.hydrate_state = AsyncMock(
                side_effect=Exception("Database error")
            )

            result = await orchestrator.process_message("test_user", "Find me flights")

            assert "error" in result
            assert "apologize" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_get_session_state_success(self, orchestrator):
        """Test successful session state retrieval."""
        with patch.object(orchestrator, "compiled_graph") as mock_graph:
            mock_state = Mock()
            mock_state.values = {"test": "state"}
            mock_graph.get_state = Mock(return_value=mock_state)

            result = await orchestrator.get_session_state("test_session")
            assert result == {"test": "state"}

    @pytest.mark.asyncio
    async def test_get_session_state_error(self, orchestrator):
        """Test session state retrieval with error."""
        with patch.object(orchestrator, "compiled_graph") as mock_graph:
            mock_graph.get_state = Mock(side_effect=Exception("State error"))

            result = await orchestrator.get_session_state("test_session")
            assert result is None


class TestStateCreation:
    """Test state creation and management."""

    def test_create_initial_state(self):
        """Test creation of initial travel planning state."""
        state = create_initial_state("test_user", "Hello")

        assert state["user_id"] == "test_user"
        assert len(state["messages"]) == 1
        assert state["messages"][0]["content"] == "Hello"
        assert state["messages"][0]["role"] == "user"
        assert state["session_id"].startswith("session_test_user_")
        assert state["is_active"] is True
        assert state["flight_searches"] == []
        assert state["accommodation_searches"] == []
        assert state["activity_searches"] == []

    def test_create_initial_state_with_session_id(self):
        """Test creation of initial state with existing session ID."""
        session_id = "existing_session"
        state = create_initial_state("test_user", "Hello", session_id)

        assert state["session_id"] == session_id
        assert state["user_id"] == "test_user"
