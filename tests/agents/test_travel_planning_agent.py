"""
Tests for the TravelPlanningAgent.

These tests verify that the main orchestrator agent properly initializes,
registers tools, and can execute successful handoffs to specialized agents.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents import RunContext, RunResult
from src.agents.travel_planning_agent import TravelPlanningAgent


@pytest.fixture
def mock_runner():
    """Mock for the OpenAI Agents SDK Runner."""
    mock = MagicMock()
    mock.run = AsyncMock()
    return mock


@pytest.fixture
def mock_flight_agent():
    """Mock for the FlightAgent."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value={"content": "Flight search completed", "status": "success"}
    )
    return mock


@pytest.fixture
def mock_accommodation_agent():
    """Mock for the AccommodationAgent."""
    mock = MagicMock()
    mock.run = AsyncMock(
        return_value={"content": "Accommodation search completed", "status": "success"}
    )
    return mock


class TestTravelPlanningAgent:
    """Tests for the main TravelPlanningAgent orchestrator."""

    @patch("src.agents.travel_planning_agent.FlightAgent")
    @patch("src.agents.travel_planning_agent.AccommodationAgent")
    @patch("src.agents.travel_planning_agent.DestinationResearchAgent")
    @patch("src.agents.travel_planning_agent.BudgetAgent")
    @patch("src.agents.travel_planning_agent.ItineraryAgent")
    def test_agent_initialization(
        self,
        mock_itinerary_agent_cls,
        mock_budget_agent_cls,
        mock_destination_agent_cls,
        mock_accommodation_agent_cls,
        mock_flight_agent_cls,
    ):
        """Test that the agent initializes with proper configuration."""
        # Setup mocks
        mock_flight_agent_cls.return_value = MagicMock()
        mock_accommodation_agent_cls.return_value = MagicMock()
        mock_destination_agent_cls.return_value = MagicMock()
        mock_budget_agent_cls.return_value = MagicMock()
        mock_itinerary_agent_cls.return_value = MagicMock()

        # Create agent
        agent = TravelPlanningAgent(name="Test Travel Planner")

        # Verify specialized agents were initialized
        mock_flight_agent_cls.assert_called_once()
        mock_accommodation_agent_cls.assert_called_once()
        mock_destination_agent_cls.assert_called_once()
        mock_budget_agent_cls.assert_called_once()
        mock_itinerary_agent_cls.assert_called_once()

        # Verify agent has expected configuration
        assert agent.name == "Test Travel Planner"
        assert "travel planning" in agent.instructions.lower()
        assert agent.model == "gpt-4"  # Default model
        assert agent.temperature == 0.2  # Default temperature

    @patch("src.agents.base_agent.Runner")
    @patch("src.agents.travel_planning_agent.FlightAgent")
    async def test_agent_run(self, mock_flight_agent_cls, mock_runner_cls, mock_runner):
        """Test that the agent can execute a run with the OpenAI SDK Runner."""
        # Setup mocks
        mock_runner_cls.return_value = mock_runner
        mock_flight_agent = MagicMock()
        mock_flight_agent_cls.return_value = mock_flight_agent

        # Mock runner response
        mock_result = MagicMock(spec=RunResult)
        mock_result.output = "I've planned your trip to Paris"
        mock_result.tool_calls = []
        mock_result.handoffs = {}
        mock_runner.run.return_value = mock_result

        # Create agent
        agent = TravelPlanningAgent()

        # Execute run
        result = await agent.run("Plan a trip to Paris for 5 days")

        # Verify runner was called with correct parameters
        mock_runner.run.assert_called_once()
        args = mock_runner.run.call_args
        assert args[1]["input"] == "Plan a trip to Paris for 5 days"
        assert isinstance(args[1]["context"], RunContext)

        # Verify result
        assert result["content"] == "I've planned your trip to Paris"
        assert result["status"] == "success"
        assert "tool_calls" in result
        assert "handoffs" in result

    @patch("src.agents.base_agent.Runner")
    @patch("src.agents.travel_planning_agent.FlightAgent")
    async def test_agent_handoff(
        self, mock_flight_agent_cls, mock_runner_cls, mock_runner, mock_flight_agent
    ):
        """Test that the agent can execute a handoff to a specialized agent."""
        # Setup mocks
        mock_runner_cls.return_value = mock_runner
        mock_flight_agent_cls.return_value = mock_flight_agent

        # Mock runner response with handoff
        mock_result = MagicMock(spec=RunResult)
        mock_result.output = "I'll search for flights to London"
        mock_result.tool_calls = []
        mock_result.handoffs = {"flight_agent": "Find flights from New York to London"}
        mock_runner.run.return_value = mock_result

        # Create agent
        agent = TravelPlanningAgent()

        # Execute run
        result = await agent.run("Find flights from New York to London")

        # Verify handoff was processed
        mock_flight_agent.run.assert_called_once_with(
            "Find flights from New York to London", context={}
        )

        # Verify result includes handoff information
        assert result["content"] == "I'll search for flights to London"
        assert result["status"] == "success"
        assert "handoffs" in result
        assert "flight_agent" in result["handoffs"]

    @patch("src.agents.travel_planning_agent.WebSearchTool")
    def test_websearch_tool_registration(self, mock_websearch_tool_cls):
        """Test that the WebSearchTool is properly configured and registered."""
        # Setup mock
        mock_websearch_tool = MagicMock()
        mock_websearch_tool_cls.return_value = mock_websearch_tool

        # Create agent
        TravelPlanningAgent()

        # Verify WebSearchTool was created with travel-specific configuration
        mock_websearch_tool_cls.assert_called_once()
        kwargs = mock_websearch_tool_cls.call_args[1]

        # Verify travel-related allowed domains were configured
        allowed_domains = kwargs.get("allowed_domains", [])
        assert any("tripadvisor" in domain for domain in allowed_domains)
        assert any("booking" in domain for domain in allowed_domains)
        assert any("expedia" in domain for domain in allowed_domains)
