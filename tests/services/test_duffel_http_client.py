"""Tests for DuffelHTTPClient direct HTTP integration.

This module tests the direct HTTP client for Duffel API as implemented in Issue #163.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from tripsage.services.duffel_http_client import (
    DuffelAPIError,
    DuffelHTTPClient,
    DuffelRateLimitError,
)
from tripsage.tools.schemas.flights import (
    CabinClass,
    FlightSearchParams,
    FlightSearchResponse,
    AirportSearchParams,
)


class TestDuffelHTTPClient:
    """Test suite for DuffelHTTPClient."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("tripsage.services.duffel_http_client.settings") as mock_settings:
            mock_settings.flights_mcp.duffel_api_key.get_secret_value.return_value = "test-api-key"
            yield mock_settings

    @pytest.fixture
    async def client(self, mock_settings):
        """Create a test client."""
        client = DuffelHTTPClient(
            api_key="test-api-key",
            timeout=5.0,
            max_retries=1,
            retry_backoff=0.1,
        )
        yield client
        await client.close()

    @pytest.fixture
    def mock_flight_search_params(self):
        """Mock flight search parameters."""
        return FlightSearchParams(
            origin="JFK",
            destination="LAX",
            departure_date="2024-06-01",
            return_date="2024-06-08",
            adults=2,
            children=1,
            infants=0,
            cabin_class=CabinClass.ECONOMY,
            max_stops=1,
            max_price=1000.0,
            preferred_airlines=["AA", "UA"],
        )

    @pytest.fixture
    def mock_duffel_response(self):
        """Mock Duffel API response."""
        return {
            "data": {
                "id": "orq_12345",
                "offers": [
                    {
                        "id": "off_12345",
                        "total_amount": "599.99",
                        "total_currency": "USD",
                        "base_amount": "450.00",
                        "tax_amount": "149.99",
                        "slices": [
                            {
                                "origin": {"iata_code": "JFK"},
                                "destination": {"iata_code": "LAX"},
                                "segments": [
                                    {
                                        "id": "seg_12345",
                                        "origin": {"iata_code": "JFK"},
                                        "destination": {"iata_code": "LAX"},
                                        "departing_at": "2024-06-01T10:00:00",
                                        "arriving_at": "2024-06-01T13:30:00",
                                        "marketing_carrier_flight_number": "AA123",
                                        "operating_carrier": {"name": "American Airlines"},
                                        "marketing_carrier": {"name": "American Airlines"},
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "id": "off_67890",
                        "total_amount": "699.99",
                        "total_currency": "USD",
                        "base_amount": "550.00",
                        "tax_amount": "149.99",
                        "slices": [
                            {
                                "origin": {"iata_code": "JFK"},
                                "destination": {"iata_code": "LAX"},
                                "segments": [
                                    {
                                        "id": "seg_67890",
                                        "origin": {"iata_code": "JFK"},
                                        "destination": {"iata_code": "LAX"},
                                        "departing_at": "2024-06-01T14:00:00",
                                        "arriving_at": "2024-06-01T17:30:00",
                                        "marketing_carrier_flight_number": "UA456",
                                        "operating_carrier": {"name": "United Airlines"},
                                        "marketing_carrier": {"name": "United Airlines"},
                                    }
                                ],
                            }
                        ],
                    },
                ],
            }
        }

    def test_init_default_settings(self, mock_settings):
        """Test initialization with default settings."""
        client = DuffelHTTPClient()
        
        assert client.api_key == "test-api-key"
        assert client.base_url == "https://api.duffel.com"
        assert client.timeout == 30.0
        assert client.max_retries == 3
        assert client.retry_backoff == 1.0

    def test_init_custom_settings(self):
        """Test initialization with custom settings."""
        client = DuffelHTTPClient(
            api_key="custom-key",
            base_url="https://custom.api.com",
            timeout=10.0,
            max_retries=5,
            retry_backoff=2.0,
            max_connections=20,
        )
        
        assert client.api_key == "custom-key"
        assert client.base_url == "https://custom.api.com"
        assert client.timeout == 10.0
        assert client.max_retries == 5
        assert client.retry_backoff == 2.0

    def test_get_default_headers(self, client):
        """Test default headers generation."""
        headers = client._get_default_headers()
        
        assert headers["Authorization"] == "Bearer test-api-key"
        assert headers["Duffel-Version"] == "v2"
        assert headers["Accept"] == "application/json"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept-Encoding"] == "gzip"
        assert "TripSage" in headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_check_rate_limit(self, client):
        """Test rate limiting functionality."""
        # Test that rate limiting doesn't block initially
        await client._check_rate_limit()
        assert client._request_count == 1
        
        # Simulate multiple requests within window
        for _ in range(5):
            await client._check_rate_limit()
        
        assert client._request_count == 6

    @pytest.mark.asyncio
    async def test_check_rate_limit_exceeded(self, client):
        """Test rate limiting when exceeded."""
        # Set request count to limit
        client._request_count = client._max_requests_per_minute
        client._last_request_time = asyncio.get_event_loop().time()
        
        # This should trigger rate limiting delay
        start_time = asyncio.get_event_loop().time()
        await client._check_rate_limit()
        end_time = asyncio.get_event_loop().time()
        
        # Should have been reset
        assert client._request_count == 1

    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_duffel_response):
        """Test successful API request."""
        with patch.object(client.client, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_duffel_response
            mock_request.return_value = mock_response
            
            result = await client._make_request("GET", "/test", params={"test": "value"})
            
            assert result == mock_duffel_response
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_with_data(self, client, mock_duffel_response):
        """Test API request with POST data."""
        with patch.object(client.client, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_duffel_response
            mock_request.return_value = mock_response
            
            test_data = {"origin": "JFK", "destination": "LAX"}
            result = await client._make_request("POST", "/test", data=test_data)
            
            assert result == mock_duffel_response
            # Verify data was wrapped in expected format
            call_args = mock_request.call_args
            assert call_args[1]["json"] == {"data": test_data}

    @pytest.mark.asyncio
    async def test_make_request_rate_limit_error(self, client):
        """Test handling of rate limit errors."""
        with patch.object(client.client, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "1"}
            mock_request.return_value = mock_response
            
            with pytest.raises(DuffelRateLimitError) as exc_info:
                await client._make_request("GET", "/test")
            
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 1

    @pytest.mark.asyncio
    async def test_make_request_client_error(self, client):
        """Test handling of client errors (4xx)."""
        with patch.object(client.client, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"message": "Bad Request"}
            mock_request.return_value = mock_response
            
            with pytest.raises(DuffelAPIError) as exc_info:
                await client._make_request("GET", "/test")
            
            assert exc_info.value.status_code == 400
            assert "Bad Request" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_server_error_retry(self, client):
        """Test retry logic for server errors (5xx)."""
        with patch.object(client.client, "request") as mock_request:
            # First call returns 500, second call succeeds
            mock_response_error = MagicMock()
            mock_response_error.status_code = 500
            mock_response_error.json.return_value = {"message": "Server Error"}
            
            mock_response_success = MagicMock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"data": "success"}
            
            mock_request.side_effect = [mock_response_error, mock_response_success]
            
            result = await client._make_request("GET", "/test")
            
            assert result == {"data": "success"}
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_network_error_retry(self, client):
        """Test retry logic for network errors."""
        with patch.object(client.client, "request") as mock_request:
            # First call raises network error, second call succeeds
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "success"}
            
            mock_request.side_effect = [httpx.NetworkError("Network error"), mock_response]
            
            result = await client._make_request("GET", "/test")
            
            assert result == {"data": "success"}
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_make_request_exhausted_retries(self, client):
        """Test when retries are exhausted."""
        with patch.object(client.client, "request") as mock_request:
            mock_request.side_effect = httpx.NetworkError("Persistent error")
            
            with pytest.raises(DuffelAPIError) as exc_info:
                await client._make_request("GET", "/test")
            
            assert "Persistent error" in str(exc_info.value)
            assert mock_request.call_count == 2  # 1 initial + 1 retry

    @pytest.mark.asyncio
    async def test_search_flights_success(self, client, mock_flight_search_params, mock_duffel_response):
        """Test successful flight search."""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = mock_duffel_response
            
            result = await client.search_flights(mock_flight_search_params)
            
            assert isinstance(result, FlightSearchResponse)
            assert len(result.offers) == 2
            assert result.offers[0]["id"] == "off_12345"
            assert result.offers[0]["total_amount"] == 599.99
            assert result.offers[1]["id"] == "off_67890"
            assert result.offers[1]["total_amount"] == 699.99
            assert result.cheapest_price == 599.99
            
            # Verify API call was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0] == ("POST",)
            assert call_args[0][1] == "/air/offer_requests"

    @pytest.mark.asyncio
    async def test_search_flights_request_format(self, client, mock_flight_search_params):
        """Test that flight search request is formatted correctly."""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": {"id": "test", "offers": []}}
            
            await client.search_flights(mock_flight_search_params)
            
            # Check the request data format
            call_args = mock_request.call_args
            request_data = call_args[1]["data"]
            
            assert "slices" in request_data
            assert len(request_data["slices"]) == 2  # Round trip
            assert request_data["slices"][0]["origin"] == "JFK"
            assert request_data["slices"][0]["destination"] == "LAX"
            assert request_data["slices"][1]["origin"] == "LAX"  # Return flight
            assert request_data["slices"][1]["destination"] == "JFK"
            
            assert "passengers" in request_data
            assert len(request_data["passengers"]) == 3  # 2 adults + 1 child
            assert request_data["passengers"][0]["type"] == "adult"
            assert request_data["passengers"][2]["type"] == "child"
            
            assert request_data["cabin_class"] == "economy"
            assert request_data["max_connections"] == 1

    @pytest.mark.asyncio
    async def test_search_flights_one_way(self, client):
        """Test one-way flight search."""
        one_way_params = FlightSearchParams(
            origin="JFK",
            destination="LAX",
            departure_date="2024-06-01",
            adults=1,
            cabin_class=CabinClass.BUSINESS,
        )
        
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": {"id": "test", "offers": []}}
            
            await client.search_flights(one_way_params)
            
            # Check the request data format
            call_args = mock_request.call_args
            request_data = call_args[1]["data"]
            
            assert len(request_data["slices"]) == 1  # One way
            assert len(request_data["passengers"]) == 1  # 1 adult
            assert request_data["cabin_class"] == "business"

    @pytest.mark.asyncio
    async def test_search_flights_validation_error(self, client, mock_flight_search_params):
        """Test handling of validation errors."""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": {"invalid": "format"}}
            
            with pytest.raises(DuffelAPIError) as exc_info:
                await client.search_flights(mock_flight_search_params)
            
            assert "Invalid response format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_aircraft_success(self, client):
        """Test successful aircraft retrieval."""
        aircraft_data = {
            "data": {
                "id": "arc_12345",
                "name": "Boeing 737-800",
                "iata_code": "738"
            }
        }
        
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = aircraft_data
            
            result = await client.get_aircraft("arc_12345")
            
            assert result == aircraft_data["data"]
            mock_request.assert_called_once_with("GET", "/air/aircraft/arc_12345")

    @pytest.mark.asyncio
    async def test_get_aircraft_not_found(self, client):
        """Test aircraft retrieval when not found."""
        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = DuffelAPIError("Not found", status_code=404)
            
            result = await client.get_aircraft("invalid_id")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_list_aircraft_success(self, client):
        """Test successful aircraft listing."""
        aircraft_list = {
            "data": [
                {"id": "arc_1", "name": "Boeing 737", "iata_code": "737"},
                {"id": "arc_2", "name": "Airbus A320", "iata_code": "320"},
            ]
        }
        
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = aircraft_list
            
            result = await client.list_aircraft(limit=10)
            
            assert len(result) == 2
            assert result[0]["name"] == "Boeing 737"
            mock_request.assert_called_once_with("GET", "/air/aircraft", params={"limit": 10})

    @pytest.mark.asyncio
    async def test_get_airports(self, client):
        """Test airport search (placeholder implementation)."""
        search_params = AirportSearchParams(search_term="New York")
        
        result = await client.get_airports(search_params)
        
        assert result.count == 0
        assert "not implemented" in result.error.lower()

    @pytest.mark.asyncio
    async def test_health_check_success(self, client):
        """Test successful health check."""
        with patch.object(client, "get_aircraft") as mock_get_aircraft:
            mock_get_aircraft.return_value = {"id": "test"}
            
            result = await client.health_check()
            
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client):
        """Test failed health check."""
        with patch.object(client, "get_aircraft") as mock_get_aircraft:
            mock_get_aircraft.side_effect = DuffelAPIError("API Error")
            
            result = await client.health_check()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test client closing."""
        with patch.object(client.client, "aclose") as mock_close:
            await client.close()
            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_settings):
        """Test async context manager usage."""
        async with DuffelHTTPClient(api_key="test") as client:
            assert client is not None
            with patch.object(client.client, "aclose") as mock_close:
                pass
        
        # aclose should have been called
        mock_close.assert_called_once()


class TestDuffelAPIError:
    """Test suite for DuffelAPIError exceptions."""

    def test_duffel_api_error_basic(self):
        """Test basic DuffelAPIError."""
        error = DuffelAPIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
        assert error.response_data == {}

    def test_duffel_api_error_with_details(self):
        """Test DuffelAPIError with details."""
        response_data = {"error_code": "INVALID_REQUEST"}
        error = DuffelAPIError("Test error", status_code=400, response_data=response_data)
        
        assert str(error) == "Test error"
        assert error.status_code == 400
        assert error.response_data == response_data

    def test_duffel_rate_limit_error(self):
        """Test DuffelRateLimitError."""
        error = DuffelRateLimitError("Rate limited", retry_after=60)
        
        assert str(error) == "Rate limited"
        assert error.status_code == 429
        assert error.retry_after == 60


@pytest.mark.integration
class TestDuffelHTTPClientIntegration:
    """Integration tests for DuffelHTTPClient (requires valid API key)."""

    @pytest.fixture
    def integration_client(self):
        """Create client for integration testing."""
        import os
        api_key = os.getenv("DUFFEL_API_KEY")
        if not api_key:
            pytest.skip("DUFFEL_API_KEY not set")
        
        return DuffelHTTPClient(api_key=api_key, timeout=10.0)

    @pytest.mark.asyncio
    async def test_real_aircraft_request(self, integration_client):
        """Test real aircraft API request."""
        result = await integration_client.list_aircraft(limit=5)
        assert isinstance(result, list)
        if result:
            assert "id" in result[0]
            assert "name" in result[0]

    @pytest.mark.asyncio
    async def test_real_health_check(self, integration_client):
        """Test real health check."""
        result = await integration_client.health_check()
        assert isinstance(result, bool)