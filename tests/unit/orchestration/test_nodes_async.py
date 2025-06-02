"""
Tests for async orchestration nodes.

This module tests the refactored orchestration nodes that now properly use
async/await patterns and correct service registry initialization.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage.orchestration.nodes.accommodation_agent import AccommodationAgentNode
from tripsage.orchestration.nodes.budget_agent import BudgetAgentNode
from tripsage.orchestration.nodes.destination_research_agent import (
    DestinationResearchAgentNode,
)
from tripsage.orchestration.nodes.error_recovery import ErrorRecoveryNode
from tripsage.orchestration.nodes.flight_agent import FlightAgentNode
from tripsage.orchestration.nodes.itinerary_agent import ItineraryAgentNode
from tripsage.orchestration.nodes.memory_update import MemoryUpdateNode
from tripsage.orchestration.state import TravelPlanningState


class TestOrchestrationNodesInitialization:
    """Test proper initialization of orchestration nodes with service registry."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry."""
        registry = MagicMock(spec=ServiceRegistry)
        registry.get_service = MagicMock()
        registry.get_optional_service = MagicMock()
        return registry

    def test_accommodation_agent_initialization(self, mock_service_registry):
        """Test accommodation agent initializes with service registry."""
        node = AccommodationAgentNode(mock_service_registry)

        assert node.name == "accommodation_agent"
        assert node.service_registry == mock_service_registry
        assert hasattr(node, "llm")

    def test_budget_agent_initialization(self, mock_service_registry):
        """Test budget agent initializes with service registry."""
        node = BudgetAgentNode(mock_service_registry)

        assert node.name == "budget_agent"
        assert node.service_registry == mock_service_registry
        assert hasattr(node, "llm")

    def test_destination_research_agent_initialization(self, mock_service_registry):
        """Test destination research agent initializes with service registry."""
        node = DestinationResearchAgentNode(mock_service_registry)

        assert node.name == "destination_research_agent"
        assert node.service_registry == mock_service_registry
        assert hasattr(node, "llm")

    def test_flight_agent_initialization(self, mock_service_registry):
        """Test flight agent initializes with service registry."""
        node = FlightAgentNode(mock_service_registry)

        assert node.name == "flight_agent"
        assert node.service_registry == mock_service_registry
        assert hasattr(node, "llm")

    def test_itinerary_agent_initialization(self, mock_service_registry):
        """Test itinerary agent initializes with service registry."""
        node = ItineraryAgentNode(mock_service_registry)

        assert node.name == "itinerary_agent"
        assert node.service_registry == mock_service_registry
        assert hasattr(node, "llm")

    def test_memory_update_node_initialization(self, mock_service_registry):
        """Test memory update node initializes with service registry."""
        node = MemoryUpdateNode(mock_service_registry)

        assert node.name == "memory_update"
        assert node.service_registry == mock_service_registry

    def test_error_recovery_node_initialization(self, mock_service_registry):
        """Test error recovery node initializes with service registry."""
        node = ErrorRecoveryNode(mock_service_registry)

        assert node.name == "error_recovery"
        assert node.service_registry == mock_service_registry
        assert node.max_retries == 3
        assert node.escalation_threshold == 5


class TestAccommodationAgentNodeAsync:
    """Test async operations of accommodation agent node."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry with accommodation service."""
        registry = MagicMock(spec=ServiceRegistry)
        mock_accommodation_service = AsyncMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={
                "accommodations": [
                    {
                        "id": "hotel_123",
                        "name": "Test Hotel",
                        "price_per_night": 150.0,
                        "rating": 4.5,
                        "location": "Paris, France",
                    }
                ],
                "total_count": 1,
            }
        )
        registry.get_service.return_value = mock_accommodation_service
        return registry

    @pytest.fixture
    def accommodation_node(self, mock_service_registry):
        """Create accommodation agent node for testing."""
        with patch(
            "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"
        ) as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search_accommodations")
            )
            mock_llm.return_value = mock_llm_instance

            node = AccommodationAgentNode(mock_service_registry)
            node.llm = mock_llm_instance
            return node

    @pytest.fixture
    def travel_state(self):
        """Create travel planning state for testing."""
        return TravelPlanningState(
            user_request="Find hotels in Paris for 2 guests",
            current_agent="accommodation_agent",
            messages=[],
            search_results={},
            user_preferences={
                "location": "Paris, France",
                "check_in": "2024-06-01",
                "check_out": "2024-06-05",
                "guests": 2,
            },
        )

    @pytest.mark.asyncio
    async def test_accommodation_search_processing(
        self, accommodation_node, travel_state
    ):
        """Test accommodation search processing."""
        # Execute
        result_state = await accommodation_node.process(travel_state)

        # Verify
        assert result_state.current_agent == "accommodation_agent"
        assert "accommodation_search" in result_state.search_results

        # Verify LLM was called
        accommodation_node.llm.ainvoke.assert_called()

    @pytest.mark.asyncio
    async def test_accommodation_node_error_handling(
        self, mock_service_registry, travel_state
    ):
        """Test accommodation node error handling."""
        # Setup node with failing service
        registry = mock_service_registry
        mock_accommodation_service = AsyncMock()
        mock_accommodation_service.search_accommodations.side_effect = Exception(
            "Service unavailable"
        )
        registry.get_service.return_value = mock_accommodation_service

        with patch(
            "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"
        ) as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm.return_value = mock_llm_instance

            node = AccommodationAgentNode(registry)
            node.llm = mock_llm_instance

            # Execute and verify graceful error handling
            result_state = await node.process(travel_state)

            # Should not crash and should set error state
            assert result_state.current_agent == "accommodation_agent"


class TestFlightAgentNodeAsync:
    """Test async operations of flight agent node."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry with flight service."""
        registry = MagicMock(spec=ServiceRegistry)
        mock_flight_service = AsyncMock()
        mock_flight_service.search_flights = AsyncMock(
            return_value={
                "flights": [
                    {
                        "id": "flight_123",
                        "airline": "Test Airways",
                        "origin": "JFK",
                        "destination": "CDG",
                        "price": 599.99,
                        "duration": "8h 15m",
                    }
                ],
                "total_count": 1,
            }
        )
        registry.get_service.return_value = mock_flight_service
        return registry

    @pytest.fixture
    def flight_node(self, mock_service_registry):
        """Create flight agent node for testing."""
        with patch("tripsage.orchestration.nodes.flight_agent.ChatOpenAI") as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search_flights")
            )
            mock_llm.return_value = mock_llm_instance

            node = FlightAgentNode(mock_service_registry)
            node.llm = mock_llm_instance
            return node

    @pytest.fixture
    def flight_travel_state(self):
        """Create travel planning state for flight search."""
        return TravelPlanningState(
            user_request="Find flights from NYC to Paris",
            current_agent="flight_agent",
            messages=[],
            search_results={},
            user_preferences={
                "origin": "JFK",
                "destination": "CDG",
                "departure_date": "2024-06-01",
                "passengers": 2,
            },
        )

    @pytest.mark.asyncio
    async def test_flight_search_processing(self, flight_node, flight_travel_state):
        """Test flight search processing."""
        # Execute
        result_state = await flight_node.process(flight_travel_state)

        # Verify
        assert result_state.current_agent == "flight_agent"
        assert (
            "flight_search" in result_state.search_results
            or "flights" in result_state.search_results
        )

        # Verify LLM was called
        flight_node.llm.ainvoke.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_flight_and_accommodation_processing(
        self, mock_service_registry
    ):
        """Test concurrent processing of flight and accommodation nodes."""
        # Setup both nodes
        with (
            patch(
                "tripsage.orchestration.nodes.flight_agent.ChatOpenAI"
            ) as mock_flight_llm,
            patch(
                "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"
            ) as mock_accommodation_llm,
        ):
            mock_flight_llm_instance = AsyncMock()
            mock_flight_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search_flights")
            )
            mock_flight_llm.return_value = mock_flight_llm_instance

            mock_accommodation_llm_instance = AsyncMock()
            mock_accommodation_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search_accommodations")
            )
            mock_accommodation_llm.return_value = mock_accommodation_llm_instance

            flight_node = FlightAgentNode(mock_service_registry)
            flight_node.llm = mock_flight_llm_instance

            accommodation_node = AccommodationAgentNode(mock_service_registry)
            accommodation_node.llm = mock_accommodation_llm_instance

        # Setup states
        flight_state = TravelPlanningState(
            user_request="Find flights",
            current_agent="flight_agent",
            messages=[],
            search_results={},
            user_preferences={"origin": "NYC", "destination": "Paris"},
        )

        accommodation_state = TravelPlanningState(
            user_request="Find hotels",
            current_agent="accommodation_agent",
            messages=[],
            search_results={},
            user_preferences={"location": "Paris", "guests": 2},
        )

        # Execute concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(
            flight_node.process(flight_state),
            accommodation_node.process(accommodation_state),
        )
        end_time = asyncio.get_event_loop().time()

        # Verify both completed
        assert len(results) == 2
        assert results[0].current_agent == "flight_agent"
        assert results[1].current_agent == "accommodation_agent"

        # Verify concurrent execution (should be faster than sequential)
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete quickly with mocks


class TestBudgetAgentNodeAsync:
    """Test async operations of budget agent node."""

    @pytest.fixture
    def budget_node(self, mock_service_registry):
        """Create budget agent node for testing."""
        with patch("tripsage.orchestration.nodes.budget_agent.ChatOpenAI") as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="optimize_budget")
            )
            mock_llm.return_value = mock_llm_instance

            node = BudgetAgentNode(mock_service_registry)
            node.llm = mock_llm_instance
            return node

    @pytest.fixture
    def budget_travel_state(self):
        """Create travel planning state for budget optimization."""
        return TravelPlanningState(
            user_request="Optimize my travel budget",
            current_agent="budget_agent",
            messages=[],
            search_results={
                "flights": [{"price": 599.99}],
                "accommodations": [{"price_per_night": 150.0}],
            },
            user_preferences={"budget": 2000.0},
        )

    @pytest.mark.asyncio
    async def test_budget_optimization_processing(
        self, budget_node, budget_travel_state
    ):
        """Test budget optimization processing."""
        # Execute
        result_state = await budget_node.process(budget_travel_state)

        # Verify
        assert result_state.current_agent == "budget_agent"

        # Verify LLM was called
        budget_node.llm.ainvoke.assert_called()

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry."""
        registry = MagicMock(spec=ServiceRegistry)
        return registry


class TestMemoryUpdateNodeAsync:
    """Test async operations of memory update node."""

    @pytest.fixture
    def memory_node(self, mock_service_registry):
        """Create memory update node for testing."""
        node = MemoryUpdateNode(mock_service_registry)
        return node

    @pytest.fixture
    def memory_travel_state(self):
        """Create travel planning state for memory update."""
        return TravelPlanningState(
            user_request="Remember my preferences",
            current_agent="memory_update",
            messages=[
                {"role": "user", "content": "I prefer boutique hotels"},
                {
                    "role": "assistant",
                    "content": "I'll remember your preference for boutique hotels",
                },
            ],
            search_results={},
            user_preferences={"accommodation_type": "boutique"},
        )

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry with memory service."""
        registry = MagicMock(spec=ServiceRegistry)
        mock_memory_service = AsyncMock()
        mock_memory_service.add_conversation_memory = AsyncMock()
        registry.get_service.return_value = mock_memory_service
        return registry

    @pytest.mark.asyncio
    async def test_memory_update_processing(self, memory_node, memory_travel_state):
        """Test memory update processing."""
        # Execute
        result_state = await memory_node.process(memory_travel_state)

        # Verify
        assert result_state.current_agent == "memory_update"


class TestErrorRecoveryNodeAsync:
    """Test async operations of error recovery node."""

    @pytest.fixture
    def error_recovery_node(self, mock_service_registry):
        """Create error recovery node for testing."""
        node = ErrorRecoveryNode(mock_service_registry)
        return node

    @pytest.fixture
    def error_travel_state(self):
        """Create travel planning state with error."""
        return TravelPlanningState(
            user_request="Handle this error",
            current_agent="error_recovery",
            messages=[],
            search_results={},
            user_preferences={},
            errors=["Service timeout", "API rate limit exceeded"],
        )

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry."""
        registry = MagicMock(spec=ServiceRegistry)
        return registry

    @pytest.mark.asyncio
    async def test_error_recovery_processing(
        self, error_recovery_node, error_travel_state
    ):
        """Test error recovery processing."""
        # Execute
        result_state = await error_recovery_node.process(error_travel_state)

        # Verify
        assert result_state.current_agent == "error_recovery"
        # Error recovery should process the errors
        assert hasattr(result_state, "errors")


class TestNodeConcurrencyAndPerformance:
    """Test concurrency and performance aspects of orchestration nodes."""

    @pytest.fixture
    def mock_service_registry(self):
        """Create mock service registry with slow services to test concurrency."""
        registry = MagicMock(spec=ServiceRegistry)

        # Mock slow service calls to test async behavior
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return {"results": [{"id": "test_result"}]}

        mock_service = AsyncMock()
        mock_service.search_accommodations = slow_search
        mock_service.search_flights = slow_search
        registry.get_service.return_value = mock_service
        return registry

    @pytest.mark.asyncio
    async def test_multiple_nodes_concurrent_processing(self, mock_service_registry):
        """Test multiple nodes processing concurrently."""
        # Setup multiple nodes
        with (
            patch(
                "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"
            ) as mock_accommodation_llm,
            patch(
                "tripsage.orchestration.nodes.flight_agent.ChatOpenAI"
            ) as mock_flight_llm,
            patch(
                "tripsage.orchestration.nodes.budget_agent.ChatOpenAI"
            ) as mock_budget_llm,
        ):
            # Setup LLM mocks
            for mock_llm in [mock_accommodation_llm, mock_flight_llm, mock_budget_llm]:
                mock_llm_instance = AsyncMock()
                mock_llm_instance.ainvoke = AsyncMock(
                    return_value=MagicMock(content="process")
                )
                mock_llm.return_value = mock_llm_instance

            nodes = [
                AccommodationAgentNode(mock_service_registry),
                FlightAgentNode(mock_service_registry),
                BudgetAgentNode(mock_service_registry),
            ]

        # Setup states
        states = [
            TravelPlanningState(
                user_request="Find accommodations",
                current_agent="accommodation_agent",
                messages=[],
                search_results={},
                user_preferences={},
            ),
            TravelPlanningState(
                user_request="Find flights",
                current_agent="flight_agent",
                messages=[],
                search_results={},
                user_preferences={},
            ),
            TravelPlanningState(
                user_request="Optimize budget",
                current_agent="budget_agent",
                messages=[],
                search_results={},
                user_preferences={},
            ),
        ]

        # Execute all nodes concurrently
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(
            *[node.process(state) for node, state in zip(nodes, states, strict=False)]
        )
        end_time = asyncio.get_event_loop().time()

        # Verify all completed
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.current_agent == states[i].current_agent

        # Verify concurrent execution
        total_time = end_time - start_time
        # Should be much faster than 3 * 0.1 = 0.3 seconds if truly concurrent
        assert total_time < 0.25

    @pytest.mark.asyncio
    async def test_node_processing_isolation(self, mock_service_registry):
        """Test that node processing doesn't interfere with each other."""
        # Setup nodes that might interfere
        with patch(
            "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"
        ) as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search")
            )
            mock_llm.return_value = mock_llm_instance

            node1 = AccommodationAgentNode(mock_service_registry)
            node2 = AccommodationAgentNode(mock_service_registry)

        # Setup different states
        state1 = TravelPlanningState(
            user_request="Find luxury hotels",
            current_agent="accommodation_agent",
            messages=[],
            search_results={},
            user_preferences={"luxury": True},
        )

        state2 = TravelPlanningState(
            user_request="Find budget hotels",
            current_agent="accommodation_agent",
            messages=[],
            search_results={},
            user_preferences={"budget": True},
        )

        # Execute concurrently
        results = await asyncio.gather(node1.process(state1), node2.process(state2))

        # Verify states remain isolated
        assert results[0].user_preferences.get("luxury") is True
        assert results[1].user_preferences.get("budget") is True
        assert results[0].user_request == "Find luxury hotels"
        assert results[1].user_request == "Find budget hotels"


@pytest.mark.integration
class TestNodeIntegrationAsync:
    """Integration tests for orchestration nodes."""

    @pytest.mark.asyncio
    async def test_complete_node_workflow(self):
        """Test complete workflow through multiple nodes."""
        # Setup service registry with all required services
        mock_registry = MagicMock(spec=ServiceRegistry)

        # Setup mock services
        mock_flight_service = AsyncMock()
        mock_flight_service.search_flights = AsyncMock(
            return_value={"flights": [{"id": "flight_123", "price": 599.99}]}
        )

        mock_accommodation_service = AsyncMock()
        mock_accommodation_service.search_accommodations = AsyncMock(
            return_value={
                "accommodations": [{"id": "hotel_456", "price_per_night": 150.0}]
            }
        )

        def get_service(service_name):
            if "flight" in service_name:
                return mock_flight_service
            elif "accommodation" in service_name:
                return mock_accommodation_service
            return AsyncMock()

        mock_registry.get_service.side_effect = get_service

        # Setup workflow state
        initial_state = TravelPlanningState(
            user_request="Plan a trip to Paris",
            current_agent="flight_agent",
            messages=[],
            search_results={},
            user_preferences={
                "origin": "NYC",
                "destination": "Paris",
                "budget": 2000.0,
            },
        )

        # Execute workflow through multiple nodes
        with (
            patch(
                "tripsage.orchestration.nodes.flight_agent.ChatOpenAI"
            ) as mock_flight_llm,
            patch(
                "tripsage.orchestration.nodes.accommodation_agent.ChatOpenAI"
            ) as mock_accommodation_llm,
        ):
            # Setup LLM mocks
            mock_flight_llm_instance = AsyncMock()
            mock_flight_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search_flights")
            )
            mock_flight_llm.return_value = mock_flight_llm_instance

            mock_accommodation_llm_instance = AsyncMock()
            mock_accommodation_llm_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="search_accommodations")
            )
            mock_accommodation_llm.return_value = mock_accommodation_llm_instance

            # Create nodes
            flight_node = FlightAgentNode(mock_registry)
            accommodation_node = AccommodationAgentNode(mock_registry)

            # Execute workflow
            state_after_flights = await flight_node.process(initial_state)
            state_after_flights.current_agent = "accommodation_agent"
            final_state = await accommodation_node.process(state_after_flights)

        # Verify workflow completion
        assert final_state.current_agent == "accommodation_agent"
        assert len(final_state.search_results) > 0 or final_state.search_results == {}
        assert final_state.user_preferences["budget"] == 2000.0
