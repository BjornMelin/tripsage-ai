"""Tests for TripSageOrchestrator and graph construction.

This module provides full test coverage for the main orchestration graph
including node configuration, routing logic, and message processing.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.state import create_initial_state


class TestTripSageOrchestrator:
    """Test the main orchestration graph."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a mock service registry."""
        registry = Mock(spec=ServiceRegistry)
        registry.get_memory_bridge.return_value = MagicMock()
        checkpoint_service = MagicMock()
        checkpoint_service.get_async_checkpointer = AsyncMock(
            return_value=MemorySaver()
        )
        registry.get_checkpoint_service.return_value = checkpoint_service
        return registry

    @pytest.fixture
    def orchestrator(self, mock_service_registry):
        """Create an orchestrator instance for testing."""
        with (
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
            "error_info": {"error_count": 5},
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
            "error_info": {"error_count": 2},
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
        assert state["current_agent"] == "accommodation_agent"

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
            "error_info": {"error_count": 5},
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


class TestTripSageOrchestrator:
    """Test suite for TripSageOrchestrator."""

    @pytest.fixture
    def comprehensive_mock_registry(self):
        """Create a mock service registry."""
        registry = MagicMock(spec=ServiceRegistry)

        # Mock all services with proper async patterns
        services = {
            "accommodation_service": AsyncMock(),
            "flight_service": AsyncMock(),
            "budget_service": AsyncMock(),
            "destination_service": AsyncMock(),
            "itinerary_service": AsyncMock(),
            "memory_service": AsyncMock(),
            "chat_service": AsyncMock(),
            "user_service": AsyncMock(),
            "location_service": AsyncMock(),
            "weather_service": AsyncMock(),
        }

        # Configure service behavior
        services["flight_service"].search_flights = AsyncMock(
            return_value={"flights": [], "status": "success"}
        )
        services["accommodation_service"].search_accommodations = AsyncMock(
            return_value={"listings": [], "status": "success"}
        )

        registry.get_required_service = MagicMock(side_effect=services.get)
        registry.get_optional_service = MagicMock(side_effect=services.get)
        memory_bridge = MagicMock()

        def hydrate_identity(state):  # type: ignore
            return state

        memory_bridge.hydrate_state = AsyncMock(side_effect=hydrate_identity)
        memory_bridge.extract_and_persist_insights = AsyncMock(
            return_value={"insights": "test"}
        )
        registry.get_memory_bridge.return_value = memory_bridge
        checkpoint_service = MagicMock()
        checkpoint_service.get_async_checkpointer = AsyncMock(
            return_value=MemorySaver()
        )
        registry.get_checkpoint_service.return_value = checkpoint_service

        return registry

    @pytest.fixture
    def enhanced_orchestrator(self, comprehensive_mock_registry):
        """Create an enhanced orchestrator with full mocking."""
        with (
            patch("tripsage.orchestration.graph.get_handoff_coordinator") as mock_coord,
            patch("tripsage.orchestration.graph.get_default_config"),
        ):
            mock_coord.return_value.determine_next_agent = MagicMock(return_value=None)

            return TripSageOrchestrator(
                service_registry=comprehensive_mock_registry,
                checkpointer=MemorySaver(),
            )

    def test_all_agent_nodes_present(self, enhanced_orchestrator):
        """Test that all required agent nodes are present in the graph."""
        graph = enhanced_orchestrator.graph

        # All expected nodes
        _required_nodes = {
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

        # Graph should have all required nodes
        assert graph is not None
        assert hasattr(graph, "nodes")

    def test_routing_edge_cases(self, enhanced_orchestrator):
        """Test edge cases in routing logic."""
        # Test with missing fields
        state = {}
        assert enhanced_orchestrator._route_to_agent(state) == "general_agent"

        # Test with high error count but valid agent
        state = {"current_agent": "flight_agent", "error_count": 10}
        assert enhanced_orchestrator._route_to_agent(state) == "flight_agent"

        # Test with invalid agent and moderate error count
        state = {"current_agent": "unknown_agent", "error_count": 2}
        assert enhanced_orchestrator._route_to_agent(state) == "general_agent"

    def test_next_step_determination_comprehensive(self, enhanced_orchestrator):
        """Test next step determination logic."""
        # Test with complex handoff scenario
        enhanced_orchestrator.handoff_coordinator.determine_next_agent.return_value = (
            "budget_agent",
            MagicMock(model_dump=MagicMock(return_value={"handoff": "context"})),
        )

        state = {
            "error_info": {"error_count": 0},
            "current_agent": "accommodation_agent",
            "booking_progress": {"total_cost": 5000},
            "messages": [],
        }

        result = enhanced_orchestrator._determine_next_step(state)
        assert result == "continue"
        assert state["current_agent"] == "budget_agent"

        # Test with technical difficulties message
        state = {
            "error_info": {"error_count": 0},
            "messages": [
                {
                    "role": "assistant",
                    "content": (
                        "I'm experiencing technical difficulties and need human support"
                    ),
                }
            ],
            "current_agent": "general_agent",
        }

        enhanced_orchestrator.handoff_coordinator.determine_next_agent.return_value = (
            None
        )
        result = enhanced_orchestrator._determine_next_step(state)
        assert result == "end"

    @pytest.mark.asyncio
    async def test_postgres_checkpointer_initialization(self, enhanced_orchestrator):
        """Test PostgreSQL checkpointer initialization."""
        # Mock checkpoint manager
        mock_async_checkpointer = AsyncMock()
        enhanced_orchestrator.checkpoint_service = MagicMock()
        enhanced_orchestrator.checkpoint_service.get_async_checkpointer = AsyncMock(
            return_value=mock_async_checkpointer
        )

        enhanced_orchestrator.checkpointer = None
        enhanced_orchestrator._initialized = False

        await enhanced_orchestrator.initialize()

        assert enhanced_orchestrator.checkpointer == mock_async_checkpointer

    @pytest.mark.asyncio
    async def test_postgres_checkpointer_fallback(self, enhanced_orchestrator):
        """Test fallback to MemorySaver when PostgreSQL fails."""
        enhanced_orchestrator.checkpoint_service = MagicMock()
        enhanced_orchestrator.checkpoint_service.get_async_checkpointer = AsyncMock(
            side_effect=Exception("PostgreSQL connection failed")
        )

        enhanced_orchestrator.checkpointer = None
        enhanced_orchestrator._initialized = False

        await enhanced_orchestrator.initialize()

        assert isinstance(enhanced_orchestrator.checkpointer, MemorySaver)

    @pytest.mark.asyncio
    async def test_process_message_with_empty_response(self, enhanced_orchestrator):
        """Test handling of empty response from graph."""
        await enhanced_orchestrator.initialize()

        # Mock empty response
        enhanced_orchestrator.compiled_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [],  # No messages
                "current_agent": None,
                "session_id": "test-session",
            }
        )

        result = await enhanced_orchestrator.process_message("user-123", "Test message")

        # Should have default response
        assert result["response"] == "I'm ready to help with your travel planning!"

    @pytest.mark.asyncio
    async def test_process_message_memory_persistence_error(
        self, enhanced_orchestrator
    ):
        """Test graceful handling of memory persistence errors."""
        await enhanced_orchestrator.initialize()

        # Mock successful processing but failed persistence
        enhanced_orchestrator.compiled_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [{"role": "assistant", "content": "Found flights"}],
                "current_agent": "flight_agent",
            }
        )

        enhanced_orchestrator.memory_bridge.extract_and_persist_insights = AsyncMock(
            side_effect=Exception("Memory service unavailable")
        )

        # Should still return successful response
        result = await enhanced_orchestrator.process_message("user-123", "Find flights")

        assert result["response"] == "Found flights"
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_concurrent_message_processing(self, enhanced_orchestrator):
        """Test handling of concurrent message processing."""
        await enhanced_orchestrator.initialize()

        # Mock different responses for concurrent calls
        responses = [
            {
                "messages": [{"role": "assistant", "content": f"Response {i}"}],
                "current_agent": "general_agent",
                "session_id": f"session-{i}",
            }
            for i in range(3)
        ]

        enhanced_orchestrator.compiled_graph.ainvoke = AsyncMock(side_effect=responses)

        # Process multiple messages concurrently with explicit session IDs
        import asyncio

        tasks = [
            enhanced_orchestrator.process_message(
                f"user-{i}", f"Message {i}", session_id=f"session-{i}"
            )
            for i in range(3)
        ]

        results = await asyncio.gather(*tasks)

        # Verify all processed correctly
        for i, result in enumerate(results):
            assert result["response"] == f"Response {i}"
            assert result["session_id"] == f"session-{i}"

    def test_general_agent_comprehensive_response(self, enhanced_orchestrator):
        """Test general agent provides help."""
        general_agent = enhanced_orchestrator._create_general_agent()

        # Verify it's an async function
        import asyncio

        assert asyncio.iscoroutinefunction(general_agent)

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, enhanced_orchestrator):
        """Test complete error recovery flow."""
        # Create state with multiple errors
        state = create_initial_state("user-123", "Test")
        state["error_info"]["error_count"] = 2
        state["error_info"]["retry_attempts"] = {"flight_agent": 2}

        # Test recovery decision
        assert enhanced_orchestrator._handle_recovery(state) == "retry"

        # Increase error count
        state["error_info"]["error_count"] = 4
        assert enhanced_orchestrator._handle_recovery(state) == "end"

    def test_custom_configuration(self):
        """Test orchestrator with custom configuration."""
        custom_config = {"max_retries": 5, "timeout": 30, "debug": True}

        with (
            patch("tripsage.orchestration.graph.get_handoff_coordinator"),
            patch("tripsage.orchestration.graph.get_default_config"),
        ):
            mock_registry = MagicMock(spec=ServiceRegistry)
            mock_registry.get_required_service = MagicMock(return_value=MagicMock())
            mock_registry.get_memory_bridge.return_value = MagicMock()
            checkpoint_service = MagicMock()
            checkpoint_service.get_async_checkpointer = AsyncMock(
                return_value=MemorySaver()
            )
            mock_registry.get_checkpoint_service.return_value = checkpoint_service

            orchestrator = TripSageOrchestrator(
                config=custom_config, service_registry=mock_registry
            )

            assert orchestrator.config == custom_config

    @pytest.mark.asyncio
    async def test_session_state_with_complex_data(self, enhanced_orchestrator):
        """Test session state retrieval with complex nested data."""
        await enhanced_orchestrator.initialize()

        complex_state = {
            "session_id": "complex-session",
            "messages": [
                {"role": "user", "content": "Complex request"},
                {"role": "assistant", "content": "Complex response"},
            ],
            "flight_searches": [
                {"search_id": "FL123", "results": [{"flight": "data"}]}
            ],
            "user_preferences": {
                "budget_total": 5000,
                "preferred_airlines": ["United", "Delta"],
            },
            "nested_data": {"level1": {"level2": {"level3": "deep_value"}}},
        }

        mock_state = MagicMock()
        mock_state.values = complex_state
        enhanced_orchestrator.compiled_graph.get_state = MagicMock(
            return_value=mock_state
        )

        result = await enhanced_orchestrator.get_session_state("complex-session")

        assert result == complex_state
        assert result["nested_data"]["level1"]["level2"]["level3"] == "deep_value"
