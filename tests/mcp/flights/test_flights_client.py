"""
Tests for the Flights MCP client.

This module contains tests for the Flights MCP client implementation
that interfaces with the flights-mcp server.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.mcp.flights.client import FlightService, FlightsMCPClient, MCPError
from src.mcp.flights.models import (
    AirportSearchResponse,
    FlightPriceResponse,
    FlightSearchResponse,
    OfferDetailsResponse,
    PriceTrackingResponse,
)


@pytest.fixture
def mock_settings():
    """Mock the settings."""
    with patch("src.mcp.flights.client.settings") as mock:
        mock.flights_mcp.endpoint = "http://test-endpoint"
        mock.flights_mcp.api_key.get_secret_value.return_value = "test-api-key"
        yield mock


@pytest.fixture
def client(mock_settings):
    """Create a test client instance."""
    return FlightsMCPClient(
        endpoint="http://test-endpoint",
        api_key="test-api-key",
        use_cache=False,
    )


@pytest.fixture
def mock_flight_search_response():
    """Create a mock response for search_flights."""
    return {
        "offers": [
            {
                "id": "off_123456",
                "total_amount": 499.99,
                "total_currency": "USD",
                "base_amount": 450.00,
                "tax_amount": 49.99,
                "passenger_count": 1,
                "slices": [
                    {
                        "origin": {
                            "iata_code": "JFK",
                            "name": "John F. Kennedy International Airport",
                            "city": "New York",
                            "country": "United States",
                        },
                        "destination": {
                            "iata_code": "LAX",
                            "name": "Los Angeles International Airport",
                            "city": "Los Angeles",
                            "country": "United States",
                        },
                        "departure_time": "2025-06-15T08:30:00",
                        "arrival_time": "2025-06-15T11:45:00",
                        "duration_minutes": 375,
                        "segments": [
                            {
                                "origin": "JFK",
                                "destination": "LAX",
                                "departure_time": "2025-06-15T08:30:00",
                                "arrival_time": "2025-06-15T11:45:00",
                                "duration_minutes": 375,
                                "carrier": "AA",
                                "flight_number": "123",
                                "aircraft": "Boeing 787-9",
                            }
                        ],
                    }
                ],
            }
        ],
        "offer_count": 1,
        "currency": "USD",
        "search_id": "srch_123456",
        "cheapest_price": 499.99,
    }


@pytest.fixture
def mock_multi_city_search_response():
    """Create a mock response for search_multi_city."""
    return {
        "offers": [
            {
                "id": "off_234567",
                "total_amount": 799.99,
                "total_currency": "USD",
                "base_amount": 700.00,
                "tax_amount": 99.99,
                "passenger_count": 1,
                "slices": [
                    {
                        "origin": {"iata_code": "JFK"},
                        "destination": {"iata_code": "LAX"},
                        "departure_time": "2025-06-15T08:30:00",
                        "arrival_time": "2025-06-15T11:45:00",
                        "duration_minutes": 375,
                        "segments": [
                            {
                                "origin": "JFK",
                                "destination": "LAX",
                                "duration_minutes": 375,
                            }
                        ],
                    },
                    {
                        "origin": {"iata_code": "LAX"},
                        "destination": {"iata_code": "SFO"},
                        "departure_time": "2025-06-20T10:15:00",
                        "arrival_time": "2025-06-20T11:45:00",
                        "duration_minutes": 90,
                        "segments": [
                            {
                                "origin": "LAX",
                                "destination": "SFO",
                                "duration_minutes": 90,
                            }
                        ],
                    },
                ],
            }
        ],
        "offer_count": 1,
        "currency": "USD",
        "search_id": "srch_234567",
        "cheapest_price": 799.99,
    }


@pytest.fixture
def mock_airport_search_response():
    """Create a mock response for get_airports."""
    return {
        "airports": [
            {
                "iata_code": "JFK",
                "name": "John F. Kennedy International Airport",
                "city": "New York",
                "country": "United States",
                "latitude": 40.6413,
                "longitude": -73.7781,
                "timezone": "America/New_York",
            },
            {
                "iata_code": "LGA",
                "name": "LaGuardia Airport",
                "city": "New York",
                "country": "United States",
                "latitude": 40.7769,
                "longitude": -73.8740,
                "timezone": "America/New_York",
            },
        ],
        "count": 2,
    }


@pytest.fixture
def mock_offer_details_response():
    """Create a mock response for get_offer_details."""
    return {
        "offer_id": "off_123456",
        "total_amount": 499.99,
        "currency": "USD",
        "slices": [
            {
                "origin": {"iata_code": "JFK"},
                "destination": {"iata_code": "LAX"},
                "segments": [
                    {"origin": "JFK", "destination": "LAX", "duration_minutes": 375}
                ],
            }
        ],
        "passengers": {"adults": 1, "children": 0, "infants": 0},
        "fare_details": {
            "conditions": "Non-refundable, Changes allowed with fee",
            "baggage_allowance": "1 checked bag included",
        },
    }


@pytest.fixture
def mock_flight_price_response():
    """Create a mock response for get_flight_prices."""
    return {
        "origin": "JFK",
        "destination": "LAX",
        "departure_date": "2025-06-15",
        "return_date": None,
        "current_price": 499.99,
        "currency": "USD",
        "prices": [520.00, 510.00, 505.00, 499.99],
        "dates": ["2025-05-01", "2025-05-08", "2025-05-15", "2025-05-22"],
        "trend": "falling",
    }


@pytest.fixture
def mock_price_tracking_response():
    """Create a mock response for track_prices."""
    return {
        "tracking_id": "track_123456",
        "origin": "JFK",
        "destination": "LAX",
        "departure_date": "2025-06-15",
        "return_date": None,
        "email": "test@example.com",
        "frequency": "daily",
        "current_price": 499.99,
        "currency": "USD",
        "threshold_price": 450.00,
    }


class TestFlightsMCPClient:
    """Tests for the FlightsMCPClient class."""

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_search_flights(
        self, mock_call_tool, client, mock_flight_search_response
    ):
        """Test searching for flights."""
        mock_call_tool.return_value = mock_flight_search_response

        # Test with valid parameters
        result = await client.search_flights(
            origin="JFK",
            destination="LAX",
            departure_date="2025-06-15",
            adults=1,
            cabin_class="economy",
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "search_flights"

        # Verify parameters are validated
        params = call_args[1]
        assert params["origin"] == "JFK"
        assert params["destination"] == "LAX"
        assert params["departure_date"] == "2025-06-15"
        assert params["adults"] == 1

        # Verify result parsing
        assert isinstance(result, FlightSearchResponse)
        assert result.offer_count == 1
        assert len(result.offers) == 1
        assert result.offers[0].id == "off_123456"
        assert result.offers[0].total_amount == 499.99
        assert result.cheapest_price == 499.99

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_search_flights_validation_error(self, mock_call_tool, client):
        """Test validation error handling for search_flights."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError",
            exc_info={"destination": ["Airport code must be 3 characters (IATA code)"]},
        )

        # Test with invalid airport code
        with pytest.raises(MCPError) as exc_info:
            await client.search_flights(
                origin="JFK", destination="INVALID", departure_date="2025-06-15"
            )

        assert "Invalid parameters" in str(exc_info.value)

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_search_flights_api_error(self, mock_call_tool, client):
        """Test API error handling for search_flights."""
        # Simulate API error
        mock_call_tool.side_effect = Exception("API rate limit exceeded")

        # Test with rate limit error
        with pytest.raises(MCPError) as exc_info:
            await client.search_flights(
                origin="JFK", destination="LAX", departure_date="2025-06-15"
            )

        # Check correct error message and status code
        assert "rate limit" in str(exc_info.value).lower()

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_search_multi_city(
        self, mock_call_tool, client, mock_multi_city_search_response
    ):
        """Test searching for multi-city flights."""
        mock_call_tool.return_value = mock_multi_city_search_response

        # Test with valid parameters
        segments = [
            {"origin": "JFK", "destination": "LAX", "departure_date": "2025-06-15"},
            {"origin": "LAX", "destination": "SFO", "departure_date": "2025-06-20"},
        ]

        result = await client.search_multi_city(
            segments=segments, adults=1, cabin_class="economy"
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "search_multi_city"

        # Verify parameters are validated
        params = call_args[1]
        assert "segments" in params
        assert len(params["segments"]) == 2
        assert params["segments"][0]["origin"] == "JFK"
        assert params["segments"][1]["destination"] == "SFO"

        # Verify result parsing
        assert isinstance(result, FlightSearchResponse)
        assert result.offer_count == 1
        assert len(result.offers) == 1
        assert result.offers[0].id == "off_234567"
        assert result.offers[0].total_amount == 799.99
        assert len(result.offers[0].slices) == 2

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_search_multi_city_validation_error(self, mock_call_tool, client):
        """Test validation error handling for search_multi_city."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError",
            exc_info={
                "segments": ["At least two segments are required for multi-city search"]
            },
        )

        # Test with only one segment
        segments = [
            {"origin": "JFK", "destination": "LAX", "departure_date": "2025-06-15"}
        ]

        with pytest.raises(MCPError) as exc_info:
            await client.search_multi_city(segments=segments)

        assert "Invalid parameters" in str(exc_info.value)
        assert "multi-city search" in str(exc_info.value)

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_get_airports(
        self, mock_call_tool, client, mock_airport_search_response
    ):
        """Test getting airport information."""
        mock_call_tool.return_value = mock_airport_search_response

        # Test with valid search term
        result = await client.get_airports(search_term="New York")

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "get_airports"

        # Verify parameters are validated
        params = call_args[1]
        assert params["search_term"] == "New York"

        # Verify result parsing
        assert isinstance(result, AirportSearchResponse)
        assert result.count == 2
        assert len(result.airports) == 2
        assert result.airports[0].iata_code == "JFK"
        assert result.airports[0].city == "New York"
        assert result.airports[1].iata_code == "LGA"

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_get_airports_validation_error(self, mock_call_tool, client):
        """Test validation error handling for get_airports."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError",
            exc_info={"code": ["Airport code must be 3 characters (IATA code)"]},
        )

        # Test with invalid code
        with pytest.raises(MCPError) as exc_info:
            await client.get_airports(code="INVALID")

        assert "Invalid parameters" in str(exc_info.value)
        assert "airport search" in str(exc_info.value)

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_get_offer_details(
        self, mock_call_tool, client, mock_offer_details_response
    ):
        """Test getting offer details."""
        mock_call_tool.return_value = mock_offer_details_response

        # Test with valid offer ID
        result = await client.get_offer_details(offer_id="off_123456")

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "get_offer_details"

        # Verify parameters are validated
        params = call_args[1]
        assert params["offer_id"] == "off_123456"

        # Verify result parsing
        assert isinstance(result, OfferDetailsResponse)
        assert result.offer_id == "off_123456"
        assert result.total_amount == 499.99
        assert result.currency == "USD"
        assert len(result.slices) == 1
        assert "adults" in result.passengers
        assert "conditions" in result.fare_details

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_get_flight_prices(
        self, mock_call_tool, client, mock_flight_price_response
    ):
        """Test getting flight price history."""
        mock_call_tool.return_value = mock_flight_price_response

        # Test with valid parameters
        result = await client.get_flight_prices(
            origin="JFK", destination="LAX", departure_date="2025-06-15"
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "get_flight_prices"

        # Verify parameters are validated
        params = call_args[1]
        assert params["origin"] == "JFK"
        assert params["destination"] == "LAX"
        assert params["departure_date"] == "2025-06-15"

        # Verify result parsing
        assert isinstance(result, FlightPriceResponse)
        assert result.origin == "JFK"
        assert result.destination == "LAX"
        assert result.current_price == 499.99
        assert len(result.prices) == 4
        assert len(result.dates) == 4
        assert result.trend == "falling"

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_track_prices(
        self, mock_call_tool, client, mock_price_tracking_response
    ):
        """Test tracking flight prices."""
        mock_call_tool.return_value = mock_price_tracking_response

        # Test with valid parameters
        result = await client.track_prices(
            origin="JFK",
            destination="LAX",
            departure_date="2025-06-15",
            notification_email="test@example.com",
            price_threshold=450.00,
            frequency="daily",
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "track_prices"

        # Verify parameters are validated
        params = call_args[1]
        assert params["origin"] == "JFK"
        assert params["destination"] == "LAX"
        assert params["departure_date"] == "2025-06-15"
        assert params["email"] == "test@example.com"
        assert params["threshold_percentage"] == 450.00
        assert params["frequency"] == "daily"

        # Verify result parsing
        assert isinstance(result, PriceTrackingResponse)
        assert result.tracking_id == "track_123456"
        assert result.origin == "JFK"
        assert result.destination == "LAX"
        assert result.email == "test@example.com"
        assert result.threshold_price == 450.00
        assert result.frequency == "daily"

    @patch("src.mcp.flights.client.FastMCPClient.call_tool")
    async def test_track_prices_validation_error(self, mock_call_tool, client):
        """Test validation error handling for track_prices."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError", exc_info={"email": ["Invalid email format"]}
        )

        # Test with invalid email
        with pytest.raises(MCPError) as exc_info:
            await client.track_prices(
                origin="JFK",
                destination="LAX",
                departure_date="2025-06-15",
                notification_email="invalid-email",
            )

        assert "Invalid parameters" in str(exc_info.value)
        assert "price tracking" in str(exc_info.value)

    async def test_create_order(self, client):
        """Test creating a flight booking order (unsupported operation)."""
        # This operation is not supported by ravinahp/flights-mcp
        with pytest.raises(MCPError) as exc_info:
            await client.create_order(
                offer_id="off_123456",
                passengers=[],
                payment_details={},
                contact_details={},
            )

        # Check that the right error is raised
        assert "not supported" in str(exc_info.value)
        assert exc_info.value.status_code == 501  # Not Implemented

    async def test_get_order(self, client):
        """Test getting order details (unsupported operation)."""
        # This operation is not supported by ravinahp/flights-mcp
        with pytest.raises(MCPError) as exc_info:
            await client.get_order(order_id="ord_123456")

        # Check that the right error is raised
        assert "not supported" in str(exc_info.value)
        assert exc_info.value.status_code == 501  # Not Implemented

    def test_list_tools_sync(self, client):
        """Test listing available tools."""
        tools = client.list_tools_sync()

        # Check expected tools are in the list
        assert len(tools) >= 6
        tool_names = [t["name"] for t in tools]
        assert "search_flights" in tool_names
        assert "search_multi_city" in tool_names
        assert "get_airports" in tool_names
        assert "get_offer_details" in tool_names
        assert "get_flight_prices" in tool_names
        assert "track_prices" in tool_names

    def test_get_tool_metadata_sync(self, client):
        """Test getting tool metadata."""
        metadata = client.get_tool_metadata_sync("search_flights")

        # Check metadata contains expected information
        assert "description" in metadata
        assert "parameters_schema" in metadata
        assert metadata["parameters_schema"]["required"] == [
            "origin",
            "destination",
            "departure_date",
        ]


class TestFlightService:
    """Tests for the FlightService class."""

    @patch("src.mcp.flights.client.FlightsMCPClient.search_flights")
    @patch("src.mcp.flights.client.FlightsMCPClient.get_airports")
    async def test_search_best_flights(self, mock_get_airports, mock_search_flights):
        """Test searching for best flights."""
        # Mock search_flights response
        mock_search_flights.return_value = FlightSearchResponse.model_validate(
            {
                "offers": [
                    {
                        "id": "offer1",
                        "total_amount": 500.00,
                        "total_currency": "USD",
                        "passenger_count": 1,
                        "slices": [{"segments": [{"duration_minutes": 300}]}],
                    },
                    {
                        "id": "offer2",
                        "total_amount": 450.00,
                        "total_currency": "USD",
                        "passenger_count": 1,
                        "slices": [
                            {
                                "segments": [
                                    {"duration_minutes": 320},
                                    {"duration_minutes": 90},
                                ]
                            }
                        ],
                    },
                ],
                "offer_count": 2,
                "currency": "USD",
                "search_id": "search1",
            }
        )

        # Mock get_airports response when needed
        mock_get_airports.return_value = AirportSearchResponse(
            airports=[
                {
                    "iata_code": "NYC",
                    "name": "New York All Airports",
                    "city": "New York",
                    "country": "United States",
                }
            ],
            count=1,
        )

        # Create client and service
        client = FlightsMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = FlightService(client)

        # Test with IATA codes
        result = await service.search_best_flights(
            origin="JFK", destination="LAX", departure_date="2025-06-15"
        )

        # Verify search_flights was called with correct parameters
        mock_search_flights.assert_called_once_with(
            origin="JFK",
            destination="LAX",
            departure_date="2025-06-15",
            return_date=None,
            adults=1,
            max_price=None,
        )

        # Verify get_airports was not called since IATA codes were provided
        mock_get_airports.assert_not_called()

        # Verify result contains sorted offers (by value score)
        assert result["origin"]["code"] == "JFK"
        assert result["destination"]["code"] == "LAX"
        assert result["results"]["offers"][0]["id"] == "offer1"  # First is better value
        assert (
            result["results"]["offers"][1]["id"] == "offer2"
        )  # Second is worse value despite lower price

        # Reset mocks
        mock_search_flights.reset_mock()
        mock_get_airports.reset_mock()

        # Test with city names instead of IATA codes
        result = await service.search_best_flights(
            origin="New York", destination="LAX", departure_date="2025-06-15"
        )

        # Verify get_airports was called to resolve city name
        mock_get_airports.assert_called_once_with(search_term="New York")

        # Verify search_flights was called with resolved IATA code
        mock_search_flights.assert_called_once_with(
            origin="NYC",
            destination="LAX",
            departure_date="2025-06-15",
            return_date=None,
            adults=1,
            max_price=None,
        )

    @patch("src.mcp.flights.client.FlightsMCPClient.get_flight_prices")
    @patch("src.mcp.flights.client.FlightsMCPClient.search_flights")
    async def test_get_price_insights(
        self, mock_search_flights, mock_get_flight_prices
    ):
        """Test getting price insights for a route."""
        # Mock get_flight_prices response
        mock_get_flight_prices.return_value = FlightPriceResponse.model_validate(
            {
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2025-06-15",
                "return_date": None,
                "current_price": 500.00,
                "currency": "USD",
                "prices": [550.00, 530.00, 510.00, 500.00],
                "dates": ["2025-05-01", "2025-05-08", "2025-05-15", "2025-05-22"],
                "trend": "falling",
            }
        )

        # Mock search_flights response
        mock_search_flights.return_value = FlightSearchResponse.model_validate(
            {
                "offers": [
                    {
                        "id": "offer1",
                        "total_amount": 480.00,
                        "total_currency": "USD",
                        "passenger_count": 1,
                        "slices": [{"segments": [{}]}],
                    },
                    {
                        "id": "offer2",
                        "total_amount": 520.00,
                        "total_currency": "USD",
                        "passenger_count": 1,
                        "slices": [{"segments": [{}]}],
                    },
                ],
                "offer_count": 2,
                "currency": "USD",
            }
        )

        # Create client and service
        client = FlightsMCPClient(endpoint="http://test-endpoint", use_cache=False)
        service = FlightService(client)

        # Test price insights
        result = await service.get_price_insights(
            origin="JFK", destination="LAX", departure_date="2025-06-15"
        )

        # Verify both API methods were called
        mock_get_flight_prices.assert_called_once_with(
            origin="JFK",
            destination="LAX",
            departure_date="2025-06-15",
            return_date=None,
        )

        mock_search_flights.assert_called_once_with(
            origin="JFK",
            destination="LAX",
            departure_date="2025-06-15",
            return_date=None,
        )

        # Verify insights were calculated correctly
        assert result["origin"] == "JFK"
        assert result["destination"] == "LAX"
        assert result["current_price"] == 480.00  # Lowest price from offers
        assert result["historical"]["average"] == 522.50  # Average of historical prices
        assert result["historical"]["minimum"] == 500.00
        assert result["historical"]["maximum"] == 550.00
        assert result["analysis"]["trend"] == "decreasing"
        assert result["recommendation"] == "good_price"  # Below average price

        # Test edge case with no price history
        mock_get_flight_prices.return_value = FlightPriceResponse.model_validate(
            {
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2025-06-15",
                "prices": [],
                "dates": [],
            }
        )

        result = await service.get_price_insights(
            origin="JFK", destination="LAX", departure_date="2025-06-15"
        )

        # Verify a proper response with a message about insufficient data
        assert "message" in result
        assert "Insufficient price history" in result["message"]
