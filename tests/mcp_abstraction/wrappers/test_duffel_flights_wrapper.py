from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.asyncio

from tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper import (  # noqa: E402
    DuffelFlightsMCPWrapper,
)


@pytest.fixture
def mock_mcp_settings():
    """Mock mcp_settings configuration."""
    with patch(
        "tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper.mcp_settings"
    ) as mock_settings:
        mock_settings.duffel_flights = MagicMock()
        mock_settings.duffel_flights.enabled = True
        mock_settings.duffel_flights.url = "https://flights.example.com"
        mock_settings.duffel_flights.api_key = MagicMock()
        mock_settings.duffel_flights.api_key.get_secret_value.return_value = (
            "test-api-key"
        )
        mock_settings.duffel_flights.timeout = 30
        mock_settings.duffel_flights.retry_attempts = 3
        mock_settings.duffel_flights.retry_backoff = 5
        yield mock_settings


@pytest.fixture
def mock_flights_client():
    """Mock FlightsMCPClient."""
    with patch(
        "tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper.FlightsMCPClient"
    ) as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client


class TestDuffelFlightsMCPWrapper:
    """Test DuffelFlightsMCPWrapper functionality."""

    async def test_init_enabled(self, mock_mcp_settings, mock_flights_client):
        """Test initialization with enabled configuration."""
        wrapper = DuffelFlightsMCPWrapper()

        assert wrapper.is_available
        assert wrapper.client is not None
        assert wrapper.mcp_name == "duffel_flights"

    async def test_init_disabled(self):
        """Test initialization with disabled configuration."""
        with patch(
            "tripsage.mcp_abstraction.wrappers.duffel_flights_wrapper.mcp_settings"
        ) as mock_settings:
            mock_settings.duffel_flights = MagicMock()
            mock_settings.duffel_flights.enabled = False

            with pytest.raises(
                ValueError, match="Duffel Flights MCP is not enabled in configuration"
            ):
                DuffelFlightsMCPWrapper()

    def test_build_method_map(self, mock_mcp_settings, mock_flights_client):
        """Test method map building with appropriate mappings."""
        wrapper = DuffelFlightsMCPWrapper()

        expected_mappings = {
            # Search operations
            "search_flights": "search_flights",
            "search_flight_offers": "search_flights",
            "search_multi_city": "search_multi_city",
            # Airport operations
            "get_airports": "get_airports",
            "search_airports": "get_airports",
            # Offer operations
            "get_offer_details": "get_offer_details",
            "get_flight_offer": "get_offer_details",
            # Price operations
            "get_flight_prices": "get_flight_prices",
            "get_price_history": "get_flight_prices",
            "track_prices": "track_prices",
            "track_flight_prices": "track_prices",
            # Booking operations
            "create_order": "create_order",
            "book_flight": "create_order",
            "book_order": "create_order",
            "create_order_quote": "create_order",
            # Order operations
            "get_order": "get_order",
            "get_order_details": "get_order",
        }

        assert wrapper._method_map == expected_mappings

    @pytest.mark.parametrize(
        "method_alias,standard_method",
        [
            ("search_flight_offers", "search_flights"),
            ("search_airports", "get_airports"),
            ("get_flight_offer", "get_offer_details"),
            ("get_price_history", "get_flight_prices"),
            ("track_flight_prices", "track_prices"),
            ("book_flight", "create_order"),
            ("book_order", "create_order"),
            ("create_order_quote", "create_order"),
            ("get_order_details", "get_order"),
        ],
    )
    async def test_method_aliases(
        self, mock_mcp_settings, mock_flights_client, method_alias, standard_method
    ):
        """Test that method aliases correctly call standard methods."""
        wrapper = DuffelFlightsMCPWrapper()

        # Mock the standard method
        mock_standard_method = AsyncMock(return_value={"success": True})
        setattr(mock_flights_client, standard_method, mock_standard_method)

        # Call through the alias
        result = await wrapper.call_tool(method_alias, {"test": "params"})

        # Verify the standard method was called
        mock_standard_method.assert_called_once_with({"test": "params"})
        assert result == {"success": True}

    @pytest.mark.parametrize(
        "method_name,params",
        [
            (
                "search_flights",
                {
                    "origin": "LHR",
                    "destination": "JFK",
                    "departure_date": "2025-06-01",
                    "return_date": "2025-06-10",
                },
            ),
            (
                "search_multi_city",
                {
                    "segments": [
                        {"origin": "LHR", "destination": "JFK", "date": "2025-06-01"},
                        {"origin": "JFK", "destination": "SFO", "date": "2025-06-05"},
                    ]
                },
            ),
            ("get_airports", {"query": "London"}),
            ("get_offer_details", {"offer_id": "off_123"}),
            (
                "get_flight_prices",
                {
                    "origin": "LHR",
                    "destination": "JFK",
                    "departure_date": "2025-06-01",
                },
            ),
            (
                "track_prices",
                {
                    "origin": "LHR",
                    "destination": "JFK",
                    "departure_date": "2025-06-01",
                    "email": "user@example.com",
                },
            ),
            (
                "create_order",
                {
                    "offer_id": "off_123",
                    "passengers": [{"first_name": "John", "last_name": "Doe"}],
                },
            ),
            ("get_order", {"order_id": "ord_123"}),
        ],
    )
    async def test_standard_method_invocation(
        self, mock_mcp_settings, mock_flights_client, method_name, params
    ):
        """Test standard method invocation."""
        wrapper = DuffelFlightsMCPWrapper()

        # Mock the method on the client
        mock_method = AsyncMock(return_value={"success": True})
        setattr(mock_flights_client, method_name, mock_method)

        # Call the method
        result = await wrapper.call_tool(method_name, params)

        # Verify the call
        mock_method.assert_called_once_with(params)
        assert result == {"success": True}

    async def test_method_not_found_error(self, mock_mcp_settings, mock_flights_client):
        """Test error when calling non-existent method."""
        wrapper = DuffelFlightsMCPWrapper()

        with pytest.raises(
            AttributeError,
            match="DuffelFlightsMCPWrapper does not support method: invalid_method",
        ):
            await wrapper.call_tool("invalid_method", {})

    async def test_async_method_compatibility(
        self, mock_mcp_settings, mock_flights_client
    ):
        """Test async method compatibility."""
        wrapper = DuffelFlightsMCPWrapper()

        # Test with async method
        async_method = AsyncMock(return_value={"async": True})
        mock_flights_client.search_flights = async_method

        result = await wrapper.call_tool("search_flights", {})
        assert result == {"async": True}

        # Test with sync method (should be wrapped)
        sync_method = MagicMock(return_value={"sync": True})
        mock_flights_client.search_flights = sync_method

        result = await wrapper.call_tool("search_flights", {})
        assert result == {"sync": True}

    async def test_get_available_methods(self, mock_mcp_settings, mock_flights_client):
        """Test getting available methods."""
        wrapper = DuffelFlightsMCPWrapper()

        methods = await wrapper.get_available_methods()

        expected_methods = [
            "search_flights",
            "search_flight_offers",
            "search_multi_city",
            "get_airports",
            "search_airports",
            "get_offer_details",
            "get_flight_offer",
            "get_flight_prices",
            "get_price_history",
            "track_prices",
            "track_flight_prices",
            "create_order",
            "book_flight",
            "book_order",
            "create_order_quote",
            "get_order",
            "get_order_details",
        ]

        assert sorted(methods) == sorted(expected_methods)

    async def test_client_initialization_parameters(
        self, mock_mcp_settings, mock_flights_client
    ):
        """Test that client is initialized with correct parameters from config."""
        from tripsage.mcp.flights.client import FlightsMCPClient

        DuffelFlightsMCPWrapper()

        FlightsMCPClient.assert_called_once_with(
            endpoint="https://flights.example.com",
            api_key="test-api-key",
            timeout=30,
            use_cache=True,
            cache_ttl=300,  # 5 minutes * 60 seconds
            server_name="Duffel Flights",
        )
