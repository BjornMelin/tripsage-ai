"""Comprehensive tests for LangGraph orchestration system.

Tests the modern LangGraph-based agent orchestration with proper state management,
node implementations, and tool integration following latest best practices.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.graph import TripSageOrchestrator
from tripsage.orchestration.nodes.accommodation_agent import AccommodationAgentNode
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.routing import RouterNode
from tripsage.orchestration.state import (
    DestinationInfo,
    ErrorInfo,
    HandoffContext,
    TravelDates,
    UserPreferences,
    create_initial_state,
)

# Import test utilities for mocking
from .test_utils import (
    patch_openai_in_module,
)


class TestTravelPlanningState:
    """Test enhanced state management system."""

    def test_create_initial_state_basic(self):
        """Test creating basic initial state."""
        state = create_initial_state("user_123", "I want to plan a trip")

        assert state["user_id"] == "user_123"
        assert len(state["messages"]) == 1
        assert state["messages"][0]["content"] == "I want to plan a trip"
        assert state["messages"][0]["role"] == "user"
        assert state["session_id"].startswith("session_user_123_")
        assert state["is_active"] is True
        assert state["error_info"]["error_count"] == 0

    def test_create_initial_state_with_session(self):
        """Test creating state with existing session ID."""
        session_id = "existing_session_123"
        state = create_initial_state("user_456", "Hello", session_id)

        assert state["session_id"] == session_id
        assert state["user_id"] == "user_456"

    def test_user_preferences_model(self):
        """Test UserPreferences Pydantic model."""
        preferences = UserPreferences(
            budget_total=2000.0,
            budget_currency="EUR",
            seat_class="business",
            accommodation_type="hotel",
            travel_style="luxury",
        )

        assert preferences.budget_total == 2000.0
        assert preferences.budget_currency == "EUR"
        assert preferences.seat_class == "business"

    def test_travel_dates_model(self):
        """Test TravelDates Pydantic model."""
        dates = TravelDates(
            departure_date="2024-06-15",
            return_date="2024-06-22",
            flexible_dates=True,
            date_range_days=3,
        )

        assert dates.departure_date == "2024-06-15"
        assert dates.return_date == "2024-06-22"
        assert dates.flexible_dates is True
        assert dates.date_range_days == 3

    def test_destination_info_model(self):
        """Test DestinationInfo Pydantic model."""
        destination = DestinationInfo(
            origin="New York",
            destination="Paris",
            intermediate_stops=["London"],
            trip_type="round_trip",
            purpose="leisure",
        )

        assert destination.origin == "New York"
        assert destination.destination == "Paris"
        assert "London" in destination.intermediate_stops
        assert destination.trip_type == "round_trip"
        assert destination.purpose == "leisure"

    def test_error_info_model(self):
        """Test ErrorInfo Pydantic model."""
        error_info = ErrorInfo(
            error_count=2,
            last_error="API timeout",
            retry_attempts={"flight_agent": 1, "accommodation_agent": 1},
            error_history=[
                {"error": "Connection error", "timestamp": "2024-01-01T00:00:00Z"},
                {"error": "API timeout", "timestamp": "2024-01-01T00:01:00Z"},
            ],
        )

        assert error_info.error_count == 2
        assert error_info.last_error == "API timeout"
        assert error_info.retry_attempts["flight_agent"] == 1
        assert len(error_info.error_history) == 2
        assert error_info.error_history[0]["error"] == "Connection error"

    def test_handoff_context_model(self):
        """Test HandoffContext Pydantic model."""
        handoff = HandoffContext(
            from_agent="router",
            to_agent="flight_agent",
            routing_confidence=0.9,
            routing_reasoning="User mentioned flights",
            timestamp="2024-01-01T12:00:00Z",
            message_analyzed="Find me flights",
        )

        assert handoff.from_agent == "router"
        assert handoff.routing_confidence == 0.9


class TestTripSageOrchestrator:
    """Test the main LangGraph orchestrator."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create a comprehensive mock service registry."""
        registry = Mock(spec=ServiceRegistry)
        registry.flight_service = Mock()
        registry.accommodation_service = Mock()
        registry.memory_service = Mock()
        registry.auth_service = Mock()
        registry.user_service = Mock()
        return registry

    @pytest.fixture
    def orchestrator(self, mock_service_registry):
        """Create orchestrator with mocked dependencies."""
        with (
            patch("tripsage.orchestration.graph.get_memory_bridge"),
            patch("tripsage.orchestration.graph.get_handoff_coordinator"),
            patch("tripsage.orchestration.graph.get_default_config"),
        ):
            return TripSageOrchestrator(service_registry=mock_service_registry)

    def test_orchestrator_initialization(self, orchestrator, mock_service_registry):
        """Test orchestrator initializes correctly."""
        assert orchestrator.service_registry == mock_service_registry
        assert orchestrator.graph is not None
        assert orchestrator.compiled_graph is None
        assert not orchestrator._initialized

    @pytest.mark.asyncio
    async def test_async_initialization(self, orchestrator):
        """Test async initialization of orchestrator."""
        with patch.object(orchestrator, "checkpointer"):
            await orchestrator.initialize()

            assert orchestrator._initialized is True
            assert orchestrator.compiled_graph is not None

    def test_graph_structure(self, orchestrator):
        """Test that graph contains required nodes."""
        graph = orchestrator.graph

        # Check all expected nodes are present
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

        actual_nodes = set(graph.nodes.keys())
        assert expected_nodes.issubset(actual_nodes)

    def test_routing_logic(self, orchestrator):
        """Test agent routing logic."""
        # Test valid agent routing
        state = {
            "current_agent": "flight_agent",
            "error_count": 0,
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._route_to_agent(state)
        assert result == "flight_agent"

    def test_error_recovery_routing(self, orchestrator):
        """Test routing to error recovery."""
        state = {
            "current_agent": "invalid_agent",
            "error_info": {"error_count": 5},
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._route_to_agent(state)
        assert result == "error_recovery"

    def test_next_step_determination(self, orchestrator):
        """Test determining next steps after agent completion."""
        # Test error case
        state_with_errors = {
            "error_info": {"error_count": 2},
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._determine_next_step(state_with_errors)
        assert result == "error"

    def test_recovery_handling(self, orchestrator):
        """Test error recovery handling."""
        # Test retry case
        state_retry = {
            "error_info": {"error_count": 2},
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._handle_recovery(state_retry)
        assert result == "retry"

        # Test end case
        state_end = {
            "error_info": {"error_count": 5},
            "messages": [],
            "user_id": "test_user",
            "session_id": "test_session",
        }

        result = orchestrator._handle_recovery(state_end)
        assert result == "end"

    @pytest.mark.asyncio
    async def test_message_processing_success(self, orchestrator):
        """Test successful message processing."""
        with (
            patch.object(orchestrator, "initialize", new_callable=AsyncMock),
            patch.object(orchestrator, "memory_bridge") as mock_memory,
            patch.object(orchestrator, "compiled_graph") as mock_graph,
        ):
            # Setup mocks
            mock_memory.hydrate_state = AsyncMock(
                return_value={
                    "messages": [{"role": "user", "content": "Find flights"}],
                    "user_id": "test_user",
                    "session_id": "test_session",
                }
            )
            mock_memory.extract_and_persist_insights = AsyncMock(return_value={})

            mock_graph.ainvoke = AsyncMock(
                return_value={
                    "messages": [
                        {"role": "user", "content": "Find flights"},
                        {"role": "assistant", "content": "I found flights for you"},
                    ],
                    "current_agent": "flight_agent",
                    "user_id": "test_user",
                    "session_id": "test_session",
                }
            )

            result = await orchestrator.process_message(
                "test_user", "Find flights", "test_session"
            )

            assert result["response"] == "I found flights for you"
            assert result["session_id"] == "test_session"
            assert result["agent_used"] == "flight_agent"

    @pytest.mark.asyncio
    async def test_message_processing_error(self, orchestrator):
        """Test message processing with error."""
        with (
            patch.object(orchestrator, "initialize", new_callable=AsyncMock),
            patch.object(orchestrator, "memory_bridge") as mock_memory,
        ):
            mock_memory.hydrate_state = AsyncMock(
                side_effect=Exception("Database error")
            )

            result = await orchestrator.process_message("test_user", "Find flights")

            assert "error" in result
            assert "apologize" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_session_state_management(self, orchestrator):
        """Test session state retrieval."""
        with patch.object(orchestrator, "compiled_graph") as mock_graph:
            mock_state = Mock()
            mock_state.values = {"test": "state", "messages": []}
            mock_graph.get_state = Mock(return_value=mock_state)

            result = await orchestrator.get_session_state("test_session")
            assert result == {"test": "state", "messages": []}


class TestAgentNodes:
    """Test individual agent node implementations."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry for nodes."""
        registry = Mock(spec=ServiceRegistry)
        registry.flight_service = Mock()
        registry.accommodation_service = Mock()
        registry.memory_service = Mock()
        return registry

    @pytest.fixture
    def mock_tool_registry(self):
        """Create mock tool registry."""
        registry = Mock()
        registry.get_tools_for_agent = Mock(return_value=[])
        registry.get_langchain_tools_for_agent = Mock(return_value=[])
        return registry

    def test_flight_agent_initialization(self, mock_service_registry):
        """Test flight agent node initialization."""
        with (
            patch("tripsage.orchestration.nodes.flight_agent.get_tool_registry"),
            patch_openai_in_module("tripsage.orchestration.nodes.flight_agent"),
        ):
            node = FlightAgentNode(mock_service_registry)

            assert node.name == "flight_agent"
            assert node.service_registry == mock_service_registry
            assert hasattr(node, "available_tools")

    def test_accommodation_agent_initialization(self, mock_service_registry):
        """Test accommodation agent node initialization."""
        with patch_openai_in_module("tripsage.orchestration.nodes.accommodation_agent"):
            node = AccommodationAgentNode(mock_service_registry)

            assert node.name == "accommodation_agent"
            assert node.service_registry == mock_service_registry

    @pytest.mark.asyncio
    async def test_router_node_processing(self, mock_service_registry):
        """Test router node message processing."""
        with patch_openai_in_module("tripsage.orchestration.routing"):
            router = RouterNode(mock_service_registry)
            state = create_initial_state("test_user", "Find me flights to NYC")

            result = await router.process(state)

            assert result["current_agent"] == "flight_agent"
            assert "handoff_context" in result


class TestStateIntegration:
    """Test state integration across the orchestration system."""

    def test_state_serialization(self):
        """Test that state models serialize correctly."""
        preferences = UserPreferences(budget_total=1500.0, seat_class="economy")
        dates = TravelDates(departure_date="2024-06-01", return_date="2024-06-05")

        # Test serialization to dict
        pref_dict = preferences.model_dump()
        dates_dict = dates.model_dump()

        assert pref_dict["budget_total"] == 1500.0
        assert dates_dict["departure_date"] == "2024-06-01"
        assert dates_dict["return_date"] == "2024-06-05"

        # Test deserialization from dict
        restored_prefs = UserPreferences.model_validate(pref_dict)
        restored_dates = TravelDates.model_validate(dates_dict)

        assert restored_prefs.budget_total == 1500.0
        assert restored_dates.departure_date == "2024-06-01"

    def test_state_workflow_integration(self):
        """Test complete state workflow."""
        # Create initial state
        state = create_initial_state("user_789", "Plan a family vacation")

        # Add user preferences
        preferences = UserPreferences(
            budget_total=3000.0, accommodation_type="hotel", travel_style="comfort"
        )
        state["user_preferences"] = preferences.model_dump()

        # Add travel dates
        dates = TravelDates(
            departure_date="2024-07-15", return_date="2024-07-29", flexible_dates=False
        )
        state["travel_dates"] = dates.model_dump()

        # Add destination info
        destination = DestinationInfo(
            origin="Chicago",
            destination="Orlando",
            trip_type="round_trip",
            purpose="family",
        )
        state["destination_info"] = destination.model_dump()

        # Verify state integrity
        assert state["user_preferences"]["budget_total"] == 3000.0
        assert state["travel_dates"]["departure_date"] == "2024-07-15"
        assert state["destination_info"]["destination"] == "Orlando"
        assert state["destination_info"]["trip_type"] == "round_trip"
        assert state["user_id"] == "user_789"

    def test_error_handling_state(self):
        """Test error handling state management."""
        error_info = ErrorInfo(
            error_count=3,
            last_error="Network timeout",
            retry_attempts={"flight_agent": 2, "accommodation_agent": 1},
            error_history=[
                {"error": "Connection error", "timestamp": "2024-01-01T00:00:00Z"},
                {"error": "API timeout", "timestamp": "2024-01-01T00:01:00Z"},
                {"error": "Network timeout", "timestamp": "2024-01-01T00:02:00Z"},
            ],
        )

        state = create_initial_state("user_error", "Test message")
        state["error_info"] = error_info.model_dump()

        # Verify error state is properly managed
        restored_error = ErrorInfo.model_validate(state["error_info"])
        assert restored_error.error_count == 3
        assert len(restored_error.error_history) == 3
        assert restored_error.retry_attempts["flight_agent"] == 2

    def test_handoff_context_workflow(self):
        """Test handoff context in state workflow."""
        handoff = HandoffContext(
            from_agent="router",
            to_agent="flight_agent",
            routing_confidence=0.95,
            routing_reasoning="Strong flight intent detected",
            timestamp="2024-01-01T10:00:00Z",
            message_analyzed="I need flights from NYC to LAX",
        )

        state = create_initial_state("user_handoff", "Flight booking request")
        state["handoff_context"] = handoff.model_dump()

        # Verify handoff context preservation
        restored_handoff = HandoffContext.model_validate(state["handoff_context"])
        assert restored_handoff.from_agent == "router"
        assert restored_handoff.to_agent == "flight_agent"
        assert restored_handoff.routing_confidence == 0.95
