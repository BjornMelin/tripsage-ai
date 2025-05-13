"""
Tests for the integration with external Flights MCP (ravinahp/flights-mcp).

This module contains tests for the Flights MCP client's integration with
the external ravinahp/flights-mcp server and data persistence in both
Supabase and Memory MCP.
"""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import SecretStr

from src.mcp.flights.client import FlightService, FlightsMCPClient
from src.mcp.flights.models import FlightSearchResponse
from src.utils.settings import FlightsMCPConfig


@pytest.fixture
def mock_settings():
    """Mock the settings."""
    with patch("src.mcp.flights.client.settings") as mock:
        mock.flights_mcp = FlightsMCPConfig(
            endpoint="http://test-endpoint",
            api_key=SecretStr("test-api-key"),
            duffel_api_key=SecretStr("test-duffel-api-key"),
            server_type="ravinahp/flights-mcp",
        )
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
def service(client):
    """Create a test service instance."""
    return FlightService(client)


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


class TestExternalFlightsMCPIntegration:
    """Tests for the integration with external ravinahp/flights-mcp server."""

    def test_client_initialization_with_server_type(self, client):
        """Test that the client is initialized with the correct server type."""
        assert client.server_name == "Flights"

        # Cannot directly check server_type as it's not part of the class,
        # but we can check the endpoint
        assert client.endpoint == "http://test-endpoint"

    @patch("src.mcp.flights.client.FlightsMCPClient.search_flights")
    @patch("src.mcp.flights.client.get_db_client")
    @patch("src.mcp.flights.client.get_memory_client")
    async def test_search_best_flights_data_persistence(
        self,
        mock_memory_client,
        mock_db_client,
        mock_search_flights,
        service,
        mock_flight_search_response,
    ):
        """Test that search results are stored in both Supabase and Memory MCP."""
        # Mock the search_flights response
        mock_search_flights.return_value = FlightSearchResponse.model_validate(
            mock_flight_search_response
        )

        # Mock the database client
        mock_db = AsyncMock()
        mock_db_client.return_value = mock_db

        # Mock the memory client
        mock_memory = AsyncMock()
        mock_memory_client.return_value = mock_memory

        # Perform the search
        result = await service.search_best_flights(
            origin="JFK", destination="LAX", departure_date="2025-06-15"
        )

        # Verify the search was performed
        mock_search_flights.assert_called_once()

        # Verify results were stored in Supabase
        mock_db.store_flight_search_results.assert_called_once()
        call_args = mock_db.store_flight_search_results.call_args[1]
        assert call_args["search_id"] == "srch_123456"
        assert call_args["origin"] == "JFK"
        assert call_args["destination"] == "LAX"
        assert call_args["departure_date"] == "2025-06-15"

        # Verify results were stored in Memory MCP
        mock_memory.create_entities.assert_called_once()
        entities = mock_memory.create_entities.call_args[0][0]
        assert (
            len(entities) == 3
        )  # Origin airport, destination airport, and flight search

        entity_names = [entity["name"] for entity in entities]
        assert "Airport:JFK" in entity_names
        assert "Airport:LAX" in entity_names
        assert "FlightSearch:srch_123456" in entity_names

        # Verify relations were created in Memory MCP
        mock_memory.create_relations.assert_called_once()
        relations = mock_memory.create_relations.call_args[0][0]
        assert len(relations) == 2  # departs_from and arrives_at

        relation_types = [relation["relationType"] for relation in relations]
        assert "departs_from" in relation_types
        assert "arrives_at" in relation_types

    @patch("src.mcp.flights.client.FlightsMCPClient.search_flights")
    @patch("src.mcp.flights.client.get_db_client")
    async def test_error_handling_in_data_persistence(
        self, mock_db_client, mock_search_flights, service
    ):
        """Test that errors in data persistence don't affect the main search functionality."""
        # Mock the search_flights response
        mock_search_flights.return_value = FlightSearchResponse.model_validate(
            {
                "offers": [
                    {
                        "id": "off_123456",
                        "total_amount": 499.99,
                        "total_currency": "USD",
                        "passenger_count": 1,
                        "slices": [{"segments": [{"duration_minutes": 375}]}],
                    }
                ],
                "offer_count": 1,
                "currency": "USD",
                "search_id": "srch_123456",
            }
        )

        # Make the database client raise an exception
        mock_db = AsyncMock()
        mock_db.store_flight_search_results.side_effect = Exception("Database error")
        mock_db_client.return_value = mock_db

        # Perform the search
        result = await service.search_best_flights(
            origin="JFK", destination="LAX", departure_date="2025-06-15"
        )

        # Verify the search was performed despite the database error
        mock_search_flights.assert_called_once()

        # Verify database call was attempted
        mock_db.store_flight_search_results.assert_called_once()

        # Verify we still got results despite the database error
        assert "error" not in result
        assert result["search_id"] == "srch_123456"
        assert len(result["results"]["offers"]) == 1

    @patch("src.mcp.flights.client.FlightsMCPClient.create_order")
    async def test_booking_operations_not_supported(self, mock_create_order, client):
        """Test that booking operations are correctly identified as unsupported."""
        # When trying to book a flight
        with pytest.raises(Exception) as exc_info:
            await client.create_order(
                offer_id="off_123456",
                passengers=[],
                payment_details={},
                contact_details={},
            )

        # Verify the correct error message is returned
        error_message = str(exc_info.value)
        assert "not supported" in error_message.lower()
        assert "flights-mcp" in error_message
        assert "read-only" in error_message

        # Verify the mock was not called because the error is raised before
        mock_create_order.assert_not_called()
