"""
End-to-end integration tests for the TripSage travel planning flow.

These tests simulate complete user journeys through the travel planning process,
including destination research, flight search, accommodation booking, and
itinerary creation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import OpenAI
from openai.types.beta.thread import Thread

from tripsage.agents.planning import TravelPlanningAgent
from tripsage.agents.travel import TravelAgent
from tripsage.utils.session_memory import SessionMemory


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = MagicMock(spec=OpenAI)
    client.beta = MagicMock()
    client.beta.threads = MagicMock()
    client.beta.threads.runs = MagicMock()
    client.beta.assistants = MagicMock()
    
    # Mock thread creation
    mock_thread = MagicMock(spec=Thread)
    mock_thread.id = "test-thread-123"
    client.beta.threads.create.return_value = mock_thread
    
    return client


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager for testing."""
    manager = AsyncMock()
    manager.invoke = AsyncMock()
    manager.initialize = AsyncMock()
    available_mcps = ["weather", "flights", "hotels"]
    manager.get_available_mcps = MagicMock(return_value=available_mcps)
    return manager


@pytest.fixture
def test_session_memory():
    """Create a test session memory instance."""
    return SessionMemory(session_id="test-session-123")


@pytest.fixture
def travel_agent(mock_openai_client, mock_mcp_manager, test_session_memory):
    """Create a travel agent instance for testing."""
    agent = TravelAgent(
        openai=mock_openai_client,
        mcp_manager=mock_mcp_manager,
        session_memory=test_session_memory,
    )
    agent.assistant_id = "test-assistant-123"
    return agent


@pytest.fixture
def planning_agent(mock_openai_client, mock_mcp_manager, test_session_memory):
    """Create a planning agent instance for testing."""
    agent = TravelPlanningAgent(
        openai=mock_openai_client,
        mcp_manager=mock_mcp_manager,
        session_memory=test_session_memory,
    )
    agent.assistant_id = "test-planning-assistant-123"
    return agent


class TestEndToEndTravelPlanningFlow:
    """Test complete travel planning workflows."""
    
    @pytest.mark.asyncio
    async def test_simple_trip_planning_flow(self, travel_agent, mock_mcp_manager):
        """Test a simple trip planning flow from search to itinerary."""
        # Mock MCP responses
        mock_mcp_manager.invoke.side_effect = self._mock_mcp_responses
        
        # Mock OpenAI responses
        stream = self._mock_run_stream()
        travel_agent.openai.beta.threads.runs.create_and_stream.return_value = stream
        
        # Simulate user request
        user_request = "I want to plan a 5-day trip to Paris next month"
        
        # Start the planning process
        await travel_agent.process_request(user_request)
        
        # Verify MCP calls were made
        assert mock_mcp_manager.invoke.called
        
        # Verify appropriate MCPs were invoked
        call_args_list = mock_mcp_manager.invoke.call_args_list
        mcp_names = [call[0][0] for call in call_args_list]
        
        assert "weather" in mcp_names
        assert "flights" in mcp_names
        assert "hotels" in mcp_names
        
        # Verify session memory was updated
        trip_data = travel_agent.session_memory.get("current_trip")
        assert trip_data is not None
        assert trip_data["destination"] == "Paris"
        assert trip_data["duration"] == "5 days"
    
    @pytest.mark.asyncio
    async def test_multi_destination_planning(self, planning_agent, mock_mcp_manager):
        """Test planning for a multi-destination trip."""
        # Mock MCP responses
        mock_mcp_manager.invoke.side_effect = self._mock_multi_destination_responses
        
        # Mock OpenAI responses  
        stream = self._mock_run_stream()
        planning_agent.openai.beta.threads.runs.create_and_stream.return_value = stream
        
        # Simulate complex request
        user_request = (
            "Plan a 2-week European trip visiting Paris, Rome, and Barcelona. "
            "I want to spend 4 days in each city with travel days between them."
        )
        
        # Start planning process
        await planning_agent.process_request(user_request)
        
        # Verify multiple destination searches
        call_args_list = mock_mcp_manager.invoke.call_args_list
        
        # Check for weather queries for each city
        weather_calls = [
            call for call in call_args_list 
            if call[0][0] == "weather"
        ]
        assert len(weather_calls) >= 3  # One for each city
        
        # Check for flight searches between cities
        flight_calls = [
            call for call in call_args_list
            if call[0][0] == "flights"
        ]
        assert len(flight_calls) >= 3  # One for each segment
        
        # Verify itinerary structure
        itinerary = planning_agent.session_memory.get("itinerary")
        assert itinerary is not None
        assert len(itinerary["segments"]) == 4  # 3 city stays + 3 travel segments
    
    @pytest.mark.asyncio
    async def test_budget_constrained_planning(self, planning_agent, mock_mcp_manager):
        """Test planning with strict budget constraints."""
        # Mock MCP responses with budget options
        mock_mcp_manager.invoke.side_effect = self._mock_budget_responses
        
        # Mock OpenAI responses
        stream = self._mock_run_stream()
        planning_agent.openai.beta.threads.runs.create_and_stream.return_value = stream
        
        # Simulate budget-conscious request
        user_request = (
            "I need to plan a 3-day trip to New York with a total budget of $500 "
            "including flights and hotel. Find the cheapest options."
        )
        
        # Start planning process
        await planning_agent.process_request(user_request)
        
        # Verify budget-specific queries
        flight_calls = [
            call for call in mock_mcp_manager.invoke.call_args_list
            if call[0][0] == "flights" and call[0][1] == "search_budget_flights"
        ]
        assert len(flight_calls) > 0
        
        # Verify budget tracking
        budget_tracker = planning_agent.session_memory.get("budget_tracker")
        assert budget_tracker is not None
        assert budget_tracker["total_budget"] == 500
        assert budget_tracker["remaining_budget"] >= 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, travel_agent, mock_mcp_manager):
        """Test error recovery during the planning process."""
        # Mock MCP responses with failures
        mock_mcp_manager.invoke.side_effect = self._mock_error_responses
        
        # Mock OpenAI responses
        stream = self._mock_run_stream()
        travel_agent.openai.beta.threads.runs.create_and_stream.return_value = stream
        
        # Simulate request
        user_request = "Plan a trip to Tokyo next week"
        
        # Start planning process
        await travel_agent.process_request(user_request)
        
        # Verify error handling and retry logic
        call_count = mock_mcp_manager.invoke.call_count
        assert call_count > 3  # Multiple retries expected
        
        # Verify fallback behavior
        error_log = travel_agent.session_memory.get("errors")
        assert error_log is not None
        assert len(error_log) > 0
        
        # Verify alternative suggestions were generated
        alternatives = travel_agent.session_memory.get("alternative_suggestions")
        assert alternatives is not None
    
    @pytest.mark.asyncio
    async def test_preference_based_planning(self, planning_agent, mock_mcp_manager):
        """Test planning with specific user preferences."""
        # Mock MCP responses with preference filtering
        mock_mcp_manager.invoke.side_effect = self._mock_preference_responses
        
        # Mock OpenAI responses
        stream = self._mock_run_stream()
        planning_agent.openai.beta.threads.runs.create_and_stream.return_value = stream
        
        # Simulate preference-based request
        user_request = (
            "Plan a romantic getaway to Santorini. I prefer boutique hotels with "
            "sea views and want to avoid touristy areas. Include wine tasting."
        )
        
        # Start planning process
        await planning_agent.process_request(user_request)
        
        # Verify preference-based filtering
        hotel_calls = [
            call for call in mock_mcp_manager.invoke.call_args_list
            if call[0][0] == "hotels"
        ]
        
        # Check that preferences were passed to hotel search
        for call in hotel_calls:
            params = call[0][2]
            assert "preferences" in params
            assert "boutique" in params["preferences"]
            assert "sea_view" in params["preferences"]
        
        # Verify activities include wine tasting
        activities = planning_agent.session_memory.get("activities")
        assert activities is not None
        wine_activities = [a for a in activities if "wine" in a["name"].lower()]
        assert len(wine_activities) > 0
    
    # Helper methods for mocking responses
    def _mock_mcp_responses(self, mcp_name, method, params):
        """Mock standard MCP responses."""
        if mcp_name == "weather" and method == "get_forecast":
            return {
                "forecast": [
                    {"date": "2024-02-01", "temp": 15, "condition": "Sunny"},
                    {"date": "2024-02-02", "temp": 16, "condition": "Partly Cloudy"},
                ]
            }
        elif mcp_name == "flights" and method == "search":
            return {
                "flights": [
                    {
                        "id": "FL123",
                        "price": 450,
                        "departure": "2024-02-01T10:00:00",
                        "arrival": "2024-02-01T13:00:00",
                    }
                ]
            }
        elif mcp_name == "hotels" and method == "search":
            return {
                "hotels": [
                    {
                        "id": "HTL456",
                        "name": "Hotel Paris",
                        "price_per_night": 120,
                        "rating": 4.5,
                    }
                ]
            }
        return {}
    
    def _mock_multi_destination_responses(self, mcp_name, method, params):
        """Mock responses for multi-destination trips."""
        city = params.get("city", "")
        
        if mcp_name == "weather":
            return {
                "forecast": [
                    {"date": "2024-02-01", "temp": 15, "condition": "Sunny"},
                ]
            }
        elif mcp_name == "flights":
            return {
                "flights": [
                    {
                        "id": f"FL-{city[:3]}",
                        "price": 350 + (len(city) * 10),
                        "departure": "2024-02-01T10:00:00",
                        "arrival": "2024-02-01T13:00:00",
                    }
                ]
            }
        return {}
    
    def _mock_budget_responses(self, mcp_name, method, params):
        """Mock responses for budget-constrained searches."""
        if mcp_name == "flights" and method == "search_budget_flights":
            return {
                "flights": [
                    {
                        "id": "BUDGET-FL",
                        "price": 150,
                        "departure": "2024-02-01T06:00:00",
                        "arrival": "2024-02-01T09:00:00",
                    }
                ]
            }
        elif mcp_name == "hotels" and method == "search":
            max_price = params.get("max_price", 100)
            return {
                "hotels": [
                    {
                        "id": "BUDGET-HTL",
                        "name": "Budget Inn",
                        "price_per_night": max(50, max_price - 20),
                        "rating": 3.5,
                    }
                ]
            }
        return {}
    
    def _mock_error_responses(self, mcp_name, method, params):
        """Mock error responses for testing recovery."""
        # Simulate intermittent failures
        if hasattr(self, "_error_count"):
            self._error_count += 1
        else:
            self._error_count = 1
        
        if self._error_count < 3:
            raise Exception(f"Service {mcp_name} temporarily unavailable")
        
        # Return success after retries
        return self._mock_mcp_responses(mcp_name, method, params)
    
    def _mock_preference_responses(self, mcp_name, method, params):
        """Mock responses filtered by preferences."""
        if mcp_name == "hotels" and method == "search":
            preferences = params.get("preferences", [])
            hotels = []
            
            if "boutique" in preferences and "sea_view" in preferences:
                hotels.append({
                    "id": "BOUTIQUE-1",
                    "name": "Sunset Boutique Hotel",
                    "price_per_night": 250,
                    "rating": 4.8,
                    "amenities": ["sea_view", "infinity_pool", "spa"],
                })
            
            return {"hotels": hotels}
        
        elif mcp_name == "activities" and method == "search":
            return {
                "activities": [
                    {
                        "id": "WINE-1",
                        "name": "Santorini Wine Tasting Tour",
                        "price": 85,
                        "duration": "4 hours",
                    }
                ]
            }
        
        return {}
    
    def _mock_run_stream(self):
        """Mock OpenAI run stream for testing."""
        # Simulate streaming responses
        events = [
            {"event": "thread.run.created", "data": {"id": "run-123"}},
            {"event": "thread.run.in_progress", "data": {"id": "run-123"}},
            {
                "event": "thread.run.completed",
                "data": {"id": "run-123", "status": "completed"}
            },
        ]
        
        for event in events:
            yield event


@pytest.mark.asyncio
async def test_full_travel_planning_integration():
    """Test the complete travel planning integration with all components."""
    # This test would use real components with mocked external services
    # It's marked for integration testing in CI/CD pipelines
    
    # Initialize real components
    from tripsage.mcp_abstraction.manager import mcp_manager
    
    # Mock only external services
    maps_patch = "tripsage.clients.maps.google_maps_mcp_client.GoogleMapsMCPClient"
    weather_patch = "tripsage.clients.weather.weather_mcp_client.WeatherMCPClient"
    
    with patch(maps_patch) as mock_maps:
        with patch(weather_patch) as mock_weather:
            # Configure mocks
            mock_maps.return_value.invoke_method = AsyncMock()
            mock_weather.return_value.invoke_method = AsyncMock()
            
            # Initialize MCP manager
            await mcp_manager.initialize()
            
            # Create session memory
            session_memory = SessionMemory(session_id="integration-test")
            
            # Create OpenAI client (mocked)
            mock_openai = MagicMock(spec=OpenAI)
            
            # Create travel agent
            agent = TravelAgent(
                openai=mock_openai,
                mcp_manager=mcp_manager,
                session_memory=session_memory,
            )
            
            # Test request
            result = await agent.process_request("Plan a trip to London")
            
            # Verify integration
            assert result is not None
            
            # Cleanup
            await mcp_manager.shutdown()