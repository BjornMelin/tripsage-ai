"""
Test basic functionality of Phase 2 migrated agent nodes.

This test module verifies that all Phase 2 agent nodes can be instantiated
and their basic methods work properly.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from tripsage.orchestration.nodes.accommodation_agent import AccommodationAgentNode
from tripsage.orchestration.nodes.budget_agent import BudgetAgentNode
from tripsage.orchestration.nodes.destination_research_agent import DestinationResearchAgentNode
from tripsage.orchestration.nodes.itinerary_agent import ItineraryAgentNode
from tripsage.orchestration.state import TravelPlanningState


@pytest.fixture
def mock_state():
    """Create a mock travel planning state for testing."""
    return TravelPlanningState(
        messages=[{"role": "user", "content": "Test message", "timestamp": "2024-01-01T00:00:00Z"}],
        user_preferences={},
        flight_searches=[],
        accommodation_searches=[],
        budget_analyses=[],
        destination_research=[],
        itineraries=[],
        destination_info={},
    )


class TestAccommodationAgentNode:
    """Test AccommodationAgentNode functionality."""

    def test_initialization(self):
        """Test that AccommodationAgentNode can be initialized."""
        agent = AccommodationAgentNode()
        assert agent.node_name == "accommodation_agent"
        assert agent.llm is not None

    @pytest.mark.asyncio
    async def test_extract_accommodation_parameters(self, mock_state, monkeypatch):
        """Test parameter extraction for accommodation searches."""
        agent = AccommodationAgentNode()
        
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = '{"location": "Paris", "check_in_date": "2024-03-15", "guests": 2}'
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        monkeypatch.setattr(agent, "llm", mock_llm)
        
        params = await agent._extract_accommodation_parameters("Find hotels in Paris", mock_state)
        
        assert params is not None
        assert params["location"] == "Paris"
        assert params["check_in_date"] == "2024-03-15"
        assert params["guests"] == 2

    @pytest.mark.asyncio
    async def test_handle_general_inquiry(self, mock_state, monkeypatch):
        """Test handling of general accommodation inquiries."""
        agent = AccommodationAgentNode()
        
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = "I'd be happy to help you find accommodations!"
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        monkeypatch.setattr(agent, "llm", mock_llm)
        
        response = await agent._handle_general_accommodation_inquiry("Tell me about hotels", mock_state)
        
        assert response["role"] == "assistant"
        assert "accommodations" in response["content"]


class TestBudgetAgentNode:
    """Test BudgetAgentNode functionality."""

    def test_initialization(self):
        """Test that BudgetAgentNode can be initialized."""
        agent = BudgetAgentNode()
        assert agent.node_name == "budget_agent"
        assert agent.llm is not None

    @pytest.mark.asyncio
    async def test_optimize_budget(self, mock_state):
        """Test budget optimization functionality."""
        agent = BudgetAgentNode()
        
        params = {
            "total_budget": 5000,
            "trip_length": 10,
            "travelers": 2,
            "destination": "Paris"
        }
        
        result = await agent._optimize_budget(params, mock_state)
        
        assert result["total_budget"] == 5000
        assert result["trip_length"] == 10
        assert result["travelers"] == 2
        assert "allocations" in result
        assert "daily_budget" in result
        assert "percentages" in result

    @pytest.mark.asyncio
    async def test_track_expenses(self, mock_state):
        """Test expense tracking functionality."""
        agent = BudgetAgentNode()
        
        params = {
            "expenses": [
                {"category": "food", "amount": 50},
                {"category": "transportation", "amount": 30}
            ]
        }
        
        result = await agent._track_expenses(params, mock_state)
        
        assert result["expenses_count"] == 2
        assert result["total_spent"] == 80
        assert result["categories"]["food"] == 50
        assert result["categories"]["transportation"] == 30


class TestDestinationResearchAgentNode:
    """Test DestinationResearchAgentNode functionality."""

    def test_initialization(self):
        """Test that DestinationResearchAgentNode can be initialized."""
        agent = DestinationResearchAgentNode()
        assert agent.node_name == "destination_research_agent"
        assert agent.llm is not None

    @pytest.mark.asyncio
    async def test_extract_research_parameters(self, mock_state, monkeypatch):
        """Test parameter extraction for destination research."""
        agent = DestinationResearchAgentNode()
        
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = '{"destination": "Tokyo", "research_type": "attractions"}'
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        monkeypatch.setattr(agent, "llm", mock_llm)
        
        params = await agent._extract_research_parameters("Tell me about Tokyo attractions", mock_state)
        
        assert params is not None
        assert params["destination"] == "Tokyo"
        assert params["research_type"] == "attractions"

    @pytest.mark.asyncio
    async def test_research_overview(self):
        """Test overview research functionality."""
        agent = DestinationResearchAgentNode()
        
        result = await agent._research_overview("Paris")
        
        assert "overview_data" in result
        assert "sources" in result


class TestItineraryAgentNode:
    """Test ItineraryAgentNode functionality."""

    def test_initialization(self):
        """Test that ItineraryAgentNode can be initialized."""
        agent = ItineraryAgentNode()
        assert agent.node_name == "itinerary_agent"
        assert agent.llm is not None

    @pytest.mark.asyncio
    async def test_create_itinerary(self, mock_state):
        """Test itinerary creation functionality."""
        agent = ItineraryAgentNode()
        
        params = {
            "destination": "Paris",
            "start_date": "2024-03-15",
            "end_date": "2024-03-20",
            "interests": ["museums", "food"],
            "pace": "moderate"
        }
        
        result = await agent._create_itinerary(params, mock_state)
        
        assert "itinerary_id" in result
        assert result["destination"] == "Paris"
        assert result["duration"] == 6  # 5 nights, 6 days
        assert "daily_schedule" in result
        assert "total_activities" in result

    @pytest.mark.asyncio
    async def test_generate_daily_schedule(self):
        """Test daily schedule generation."""
        agent = ItineraryAgentNode()
        
        schedule = await agent._generate_daily_schedule(
            "Paris", 3, "2024-03-15", [], [], ["museums"], "moderate", 100
        )
        
        assert len(schedule) == 3  # 3 days
        assert all("day" in day for day in schedule)
        assert all("date" in day for day in schedule)
        assert all("activities" in day for day in schedule)

    def test_calculate_estimated_cost(self):
        """Test cost calculation functionality."""
        agent = ItineraryAgentNode()
        
        daily_schedule = [
            {
                "activities": [
                    {"estimated_cost": 20},
                    {"estimated_cost": 30}
                ]
            },
            {
                "activities": [
                    {"estimated_cost": 25}
                ]
            }
        ]
        
        result = agent._calculate_estimated_cost(daily_schedule, 50)
        
        assert result["total_estimated_cost"] == 75
        assert result["average_daily_cost"] == 37.5
        assert len(result["daily_costs"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])