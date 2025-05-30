"""
Tests for the FlightAgent specialized agent.

These tests verify that the FlightAgent correctly initializes,
registers the appropriate tools, and can execute flight-specific
operations with the flight search and booking components.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.agents.flight import FlightAgent


@pytest.fixture
def mock_flights_client():
    """Mock for the flights MCP client."""
    mock = MagicMock()
    mock.search_flights = AsyncMock(
        return_value={"flights": [{"id": "flight123", "price": 350.0}]}
    )
    return mock


@pytest.fixture
def mock_flight_search():
    """Mock for the TripSageFlightSearch component."""
    mock = MagicMock()
    mock.search_flights = AsyncMock(
        return_value={
            "flights": [
                {
                    "id": "flight123",
                    "origin": "LAX",
                    "destination": "JFK",
                    "departure_time": "2023-06-15T08:00:00",
                    "airline": "United",
                    "price": 350.0,
                }
            ],
            "count": 1,
        }
    )
    mock.search_multi_city = AsyncMock(
        return_value={
            "flights": [
                {
                    "id": "multiCity123",
                    "segments": [
                        {"origin": "LAX", "destination": "JFK"},
                        {"origin": "JFK", "destination": "MIA"},
                    ],
                    "price": 500.0,
                }
            ],
            "count": 1,
        }
    )
    mock.get_price_history = AsyncMock(
        return_value={
            "route": "LAX-JFK",
            "average_price": 320.0,
            "current_price": 350.0,
            "trend": "increasing",
        }
    )
    return mock


@pytest.fixture
def mock_flight_booking():
    """Mock for the TripSageFlightBooking component."""
    mock = MagicMock()
    mock.book_flight = AsyncMock(
        return_value={
            "booking_id": "booking123",
            "status": "confirmed",
            "passengers": [{"name": "John Doe"}],
            "flight": {"id": "flight123"},
        }
    )
    mock.get_booking_status = AsyncMock(
        return_value={"booking_id": "booking123", "status": "confirmed"}
    )
    mock.cancel_booking = AsyncMock(
        return_value={
            "booking_id": "booking123",
            "status": "cancelled",
            "refund_amount": 300.0,
        }
    )
    return mock


@pytest.fixture
def mock_memory_client():
    """Mock for the memory MCP client."""
    mock = MagicMock()
    mock.create_entities = AsyncMock(return_value={"success": True})
    mock.create_relations = AsyncMock(return_value={"success": True})
    return mock


class TestFlightAgent:
    """Tests for the FlightAgent specialized agent."""

    def test_agent_initialization(self):
        """Test that the agent initializes with proper configuration."""
        with (
            patch(
                "src.agents.flight_agent.TripSageFlightSearch"
            ) as mock_flight_search_cls,
            patch(
                "src.agents.flight_agent.TripSageFlightBooking"
            ) as mock_flight_booking_cls,
            patch("src.agents.flight_agent._register_mcp_client_tools"),
        ):
            # Setup mocks
            mock_flight_search_cls.return_value = MagicMock()
            mock_flight_booking_cls.return_value = MagicMock()

            # Create agent
            agent = FlightAgent(name="Test Flight Agent")

            # Verify agent has expected configuration
            assert agent.name == "Test Flight Agent"
            assert "flight search and booking" in agent.instructions.lower()
            assert agent.model == "gpt-4"  # Default model
            assert agent.temperature == 0.2  # Default temperature
            assert agent.metadata["agent_type"] == "flight_specialist"

            # Verify components were initialized
            mock_flight_search_cls.assert_called_once()
            mock_flight_booking_cls.assert_called_once()

            # Verify tools were registered (this is an approximation)
            assert hasattr(agent, "search_flights")
            assert hasattr(agent, "enhanced_flight_search")
            assert hasattr(agent, "search_multi_city_flights")
            assert hasattr(agent, "get_flight_price_history")
            assert hasattr(agent, "book_flight")

    @patch("src.agents.flight_agent.TripSageFlightSearch")
    @patch("src.agents.flight_agent.TripSageFlightBooking")
    async def test_search_flights(
        self, mock_flight_booking_cls, mock_flight_search_cls, mock_flight_search
    ):
        """Test the search_flights tool."""
        # Setup mocks
        mock_flight_search_cls.return_value = mock_flight_search
        mock_flight_booking_cls.return_value = MagicMock()

        # Create agent
        agent = FlightAgent()

        # Execute search_flights
        result = await agent.search_flights(
            {
                "origin": "LAX",
                "destination": "JFK",
                "departure_date": "2023-06-15",
                "adults": 1,
            }
        )

        # Verify flight search was called with correct parameters
        mock_flight_search.search_flights.assert_called_once()
        call_args = mock_flight_search.search_flights.call_args[0][0]
        assert call_args["origin"] == "LAX"
        assert call_args["destination"] == "JFK"
        assert call_args["departure_date"] == "2023-06-15"
        assert call_args["adults"] == 1

        # Verify result
        assert "flights" in result
        assert len(result["flights"]) == 1
        assert result["flights"][0]["id"] == "flight123"
        assert result["flights"][0]["price"] == 350.0

    @patch("src.agents.flight_agent.TripSageFlightSearch")
    @patch("src.agents.flight_agent.TripSageFlightBooking")
    async def test_search_multi_city_flights(
        self, mock_flight_booking_cls, mock_flight_search_cls, mock_flight_search
    ):
        """Test the search_multi_city_flights tool."""
        # Setup mocks
        mock_flight_search_cls.return_value = mock_flight_search
        mock_flight_booking_cls.return_value = MagicMock()

        # Create agent
        agent = FlightAgent()

        # Execute search_multi_city_flights
        result = await agent.search_multi_city_flights(
            {
                "segments": [
                    {
                        "origin": "LAX",
                        "destination": "JFK",
                        "date": "2023-06-15",
                    },
                    {
                        "origin": "JFK",
                        "destination": "MIA",
                        "date": "2023-06-20",
                    },
                ],
                "adults": 1,
            }
        )

        # Verify multi-city search was called
        mock_flight_search.search_multi_city.assert_called_once()

        # Verify result
        assert "flights" in result
        assert len(result["flights"]) == 1
        assert result["flights"][0]["id"] == "multiCity123"
        assert result["flights"][0]["price"] == 500.0

    @patch("src.agents.flight_agent.TripSageFlightSearch")
    @patch("src.agents.flight_agent.TripSageFlightBooking")
    async def test_get_flight_price_history(
        self, mock_flight_booking_cls, mock_flight_search_cls, mock_flight_search
    ):
        """Test the get_flight_price_history tool."""
        # Setup mocks
        mock_flight_search_cls.return_value = mock_flight_search
        mock_flight_booking_cls.return_value = MagicMock()

        # Create agent
        agent = FlightAgent()

        # Execute get_flight_price_history
        result = await agent.get_flight_price_history(
            {
                "origin": "LAX",
                "destination": "JFK",
                "cabin_class": "economy",
                "days_back": 90,
            }
        )

        # Verify price history was called
        mock_flight_search.get_price_history.assert_called_once()

        # Verify result
        assert result["route"] == "LAX-JFK"
        assert result["average_price"] == 320.0
        assert result["current_price"] == 350.0
        assert result["trend"] == "increasing"

    @patch("src.agents.flight_agent.TripSageFlightSearch")
    @patch("src.agents.flight_agent.TripSageFlightBooking")
    async def test_book_flight(
        self, mock_flight_search_cls, mock_flight_booking_cls, mock_flight_booking
    ):
        """Test the book_flight tool."""
        # Setup mocks
        mock_flight_search_cls.return_value = MagicMock()
        mock_flight_booking_cls.return_value = mock_flight_booking

        # Create agent
        agent = FlightAgent()

        # Execute book_flight
        result = await agent.book_flight(
            {
                "flight_id": "flight123",
                "passengers": [
                    {
                        "first_name": "John",
                        "last_name": "Doe",
                        "dob": "1980-01-01",
                        "email": "john@example.com",
                    }
                ],
                "payment": {"type": "credit_card", "number": "1234xxxxxxxxxxxx"},
            }
        )

        # Verify booking was called
        mock_flight_booking.book_flight.assert_called_once()

        # Verify result
        assert result["booking_id"] == "booking123"
        assert result["status"] == "confirmed"
        assert result["flight"]["id"] == "flight123"

    @patch("src.agents.flight_agent.TripSageFlightSearch")
    @patch("src.agents.flight_agent.TripSageFlightBooking")
    @patch("src.agents.flight_agent.get_memory_client")
    async def test_store_flight_details(
        self,
        mock_get_memory_client,
        mock_flight_booking_cls,
        mock_flight_search_cls,
        mock_memory_client,
    ):
        """Test the store_flight_details tool."""
        # Setup mocks
        mock_flight_search_cls.return_value = MagicMock()
        mock_flight_booking_cls.return_value = MagicMock()
        mock_get_memory_client.return_value = mock_memory_client

        # Create agent
        agent = FlightAgent()

        # Execute store_flight_details
        result = await agent.store_flight_details(
            {
                "flight_id": "flight123",
                "trip_id": "trip456",
                "user_id": "user789",
                "notes": "Business trip",
            }
        )

        # Verify memory client methods were called
        mock_memory_client.create_entities.assert_called_once()
        mock_memory_client.create_relations.assert_called_once()

        # Verify result
        assert result["success"] is True
        assert "Flight details stored" in result["message"]
        assert result["flight_id"] == "flight123"

    @patch("src.agents.flight_agent.FlightAgent")
    def test_create_flight_agent(self, mock_flight_agent_cls):
        """Test the create_flight_agent factory function."""
        # Setup mock
        mock_agent = MagicMock()
        mock_flight_agent_cls.return_value = mock_agent

        # Call factory function
        agent = create_flight_agent()

        # Verify agent was created and returned
        mock_flight_agent_cls.assert_called_once()
        assert agent == mock_agent

    @patch("src.agents.flight_agent.FlightAgent")
    @patch("src.agents.flight_agent.handoff")
    def test_create_flight_agent_handoff(self, mock_handoff, mock_flight_agent_cls):
        """Test the create_flight_agent_handoff factory function."""
        # Setup mocks
        mock_agent = MagicMock()
        mock_flight_agent_cls.return_value = mock_agent
        mock_handoff.return_value = "handoff_function"

        # Call factory function
        handoff_fn = create_flight_agent_handoff()

        # Verify handoff was created and returned
        mock_flight_agent_cls.assert_called_once()
        mock_handoff.assert_called_once()
        assert mock_handoff.call_args[1]["agent"] == mock_agent
        assert handoff_fn == "handoff_function"

        # Test the on_handoff function
        on_handoff_fn = mock_handoff.call_args[1]["on_handoff"]
        ctx = MagicMock(spec=RunContextWrapper)
        ctx.session_data = {}
        on_handoff_fn(ctx, "Test input")
        assert ctx.session_data["source_agent"] == "TravelPlanningAgent"
