"""Tests for FlightService with feature flag integration.

This module tests the FlightService integration with both MCP and direct HTTP
approaches as implemented in Issue #163.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

from tripsage.api.services.flight import FlightService
from tripsage.api.models.flights import FlightSearchRequest
from tripsage.models.flight import CabinClass
from tripsage.config.feature_flags import IntegrationMode
from tripsage.services.duffel_http_client import DuffelHTTPClient, DuffelAPIError
from tripsage.tools.schemas.flights import FlightSearchResponse


class TestFlightServiceIntegration:
    """Test suite for FlightService with feature flag integration."""

    @pytest.fixture
    def mock_feature_flags(self):
        """Mock feature flags for testing."""
        with patch("tripsage.api.services.flight.feature_flags") as mock_flags:
            yield mock_flags

    @pytest.fixture
    def mock_mcp_manager(self):
        """Mock MCP manager for testing."""
        with patch("tripsage.api.services.flight.mcp_manager") as mock_manager:
            yield mock_manager

    @pytest.fixture
    def flight_request(self):
        """Sample flight search request."""
        return FlightSearchRequest(
            origin="JFK",
            destination="LAX",
            departure_date=date(2024, 6, 1),
            return_date=date(2024, 6, 8),
            cabin_class=CabinClass.ECONOMY,
            trip_id="trip_123",
        )

    @pytest.fixture
    def mock_duffel_response(self):
        """Mock Duffel HTTP response."""
        return FlightSearchResponse(
            offers=[
                {
                    "id": "off_12345",
                    "total_amount": 599.99,
                    "total_currency": "USD",
                    "base_amount": 450.00,
                    "tax_amount": 149.99,
                    "slices": [
                        {
                            "origin": {"iata_code": "JFK"},
                            "destination": {"iata_code": "LAX"},
                            "segments": [
                                {
                                    "origin": {"iata_code": "JFK"},
                                    "destination": {"iata_code": "LAX"},
                                    "departing_at": "2024-06-01T10:00:00",
                                    "arriving_at": "2024-06-01T13:30:00",
                                    "marketing_carrier_flight_number": "AA123",
                                }
                            ],
                        }
                    ],
                    "passenger_count": 1,
                }
            ],
            offer_count=1,
            currency="USD",
            search_id="search_123",
            cheapest_price=599.99,
        )

    def test_init_direct_mode(self, mock_feature_flags):
        """Test service initialization in direct mode."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            service = FlightService()
            
            assert service.duffel_client is not None
            mock_client_class.assert_called_once()

    def test_init_mcp_mode(self, mock_feature_flags):
        """Test service initialization in MCP mode."""
        mock_feature_flags.flights_integration = IntegrationMode.MCP
        
        service = FlightService()
        
        assert service.duffel_client is None

    @pytest.mark.asyncio
    async def test_search_flights_direct_mode_success(
        self, mock_feature_flags, flight_request, mock_duffel_response
    ):
        """Test successful flight search in direct mode."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.search_flights.return_value = mock_duffel_response
            mock_client_class.return_value = mock_client
            
            service = FlightService()
            result = await service.search_flights(flight_request)
            
            assert result is not None
            assert len(result.results) >= 1
            mock_client.search_flights.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_flights_direct_mode_fallback(
        self, mock_feature_flags, flight_request
    ):
        """Test fallback to mock data when direct mode fails."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.search_flights.side_effect = DuffelAPIError("API Error")
            mock_client_class.return_value = mock_client
            
            service = FlightService()
            result = await service.search_flights(flight_request)
            
            # Should fall back to mock data
            assert result is not None
            assert len(result.results) == 1
            assert result.results[0].airline == "AA"  # Mock data indicator

    @pytest.mark.asyncio
    async def test_search_flights_mcp_mode_success(
        self, mock_feature_flags, mock_mcp_manager, flight_request, mock_duffel_response
    ):
        """Test successful flight search in MCP mode."""
        mock_feature_flags.flights_integration = IntegrationMode.MCP
        mock_mcp_manager.invoke.return_value = mock_duffel_response
        
        service = FlightService()
        result = await service.search_flights(flight_request)
        
        assert result is not None
        mock_mcp_manager.invoke.assert_called_once()
        call_args = mock_mcp_manager.invoke.call_args
        assert call_args[1]["mcp_name"] == "duffel_flights"
        assert call_args[1]["method_name"] == "search_flights"

    @pytest.mark.asyncio
    async def test_search_flights_mcp_mode_fallback(
        self, mock_feature_flags, mock_mcp_manager, flight_request
    ):
        """Test fallback to mock data when MCP mode fails."""
        mock_feature_flags.flights_integration = IntegrationMode.MCP
        mock_mcp_manager.invoke.side_effect = Exception("MCP Error")
        
        service = FlightService()
        result = await service.search_flights(flight_request)
        
        # Should fall back to mock data
        assert result is not None
        assert len(result.results) == 1
        assert result.results[0].airline == "AA"  # Mock data indicator

    @pytest.mark.asyncio
    async def test_convert_api_models_to_flight_search_params(self):
        """Test conversion from API models to internal params."""
        service = FlightService()
        
        request = FlightSearchRequest(
            origin="JFK",
            destination="LAX",
            departure_date=date(2024, 6, 1),
            return_date=date(2024, 6, 8),
            cabin_class=CabinClass.BUSINESS,
            trip_id="trip_123",
        )
        
        params = await service._convert_api_models_to_flight_search_params(request)
        
        assert params.origin == "JFK"
        assert params.destination == "LAX"
        assert params.departure_date == "2024-06-01"
        assert params.return_date == "2024-06-08"
        assert params.cabin_class == CabinClass.BUSINESS
        assert params.adults == 1  # Default
        assert params.children == 0  # Default

    @pytest.mark.asyncio
    async def test_convert_duffel_response_to_api_models(self, flight_request, mock_duffel_response):
        """Test conversion from Duffel response to API models."""
        service = FlightService()
        
        result = await service._convert_duffel_response_to_api_models(
            mock_duffel_response, flight_request
        )
        
        assert len(result.results) == 1
        assert result.results[0].id == "off_12345"
        assert result.results[0].price == 599.99
        assert result.results[0].currency == "USD"
        assert result.results[0].origin == "JFK"
        assert result.results[0].destination == "LAX"
        assert result.trip_id == "trip_123"

    @pytest.mark.asyncio
    async def test_health_check_direct_mode(self, mock_feature_flags):
        """Test health check in direct mode."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = True
            mock_client_class.return_value = mock_client
            
            service = FlightService()
            result = await service.health_check()
            
            assert result is True
            mock_client.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_mcp_mode(self, mock_feature_flags, mock_mcp_manager):
        """Test health check in MCP mode."""
        mock_feature_flags.flights_integration = IntegrationMode.MCP
        
        service = FlightService()
        result = await service.health_check()
        
        assert result is True  # Basic check that mcp_manager exists

    @pytest.mark.asyncio
    async def test_close_direct_mode(self, mock_feature_flags):
        """Test closing connections in direct mode."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            service = FlightService()
            await service.close()
            
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_mcp_mode(self, mock_feature_flags):
        """Test closing connections in MCP mode."""
        mock_feature_flags.flights_integration = IntegrationMode.MCP
        
        service = FlightService()
        await service.close()  # Should not raise any errors

    @pytest.mark.asyncio
    async def test_get_mock_flight_response(self, flight_request):
        """Test mock flight response generation."""
        service = FlightService()
        
        result = await service._get_mock_flight_response(flight_request)
        
        assert result is not None
        assert len(result.results) == 1
        assert result.results[0].origin == "JFK"
        assert result.results[0].destination == "LAX"
        assert result.results[0].airline == "AA"
        assert result.results[0].price == 499.99
        assert result.trip_id == "trip_123"

    @pytest.mark.asyncio
    async def test_lazy_client_initialization(self, mock_feature_flags):
        """Test that client is initialized lazily when needed."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        service = FlightService()
        # Initially should have a client from __init__
        assert service.duffel_client is not None
        
        # Set to None to test lazy initialization
        service.duffel_client = None
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.health_check.return_value = True
            mock_client_class.return_value = mock_client
            
            result = await service.health_check()
            
            assert result is True
            assert service.duffel_client is not None
            mock_client_class.assert_called_once()

    def test_feature_flag_logging(self, mock_feature_flags, flight_request):
        """Test that feature flag usage is logged correctly."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.logger") as mock_logger:
            with patch("tripsage.api.services.flight.DuffelHTTPClient"):
                service = FlightService()
                
                # Check initialization logging
                mock_logger.info.assert_called_with(
                    "FlightService initialized with direct HTTP client"
                )


class TestFlightServiceErrorHandling:
    """Test error handling in FlightService."""

    @pytest.fixture
    def mock_feature_flags(self):
        """Mock feature flags for testing."""
        with patch("tripsage.api.services.flight.feature_flags") as mock_flags:
            mock_flags.flights_integration = IntegrationMode.DIRECT
            yield mock_flags

    @pytest.fixture
    def flight_request(self):
        """Sample flight search request."""
        return FlightSearchRequest(
            origin="JFK",
            destination="LAX",
            departure_date=date(2024, 6, 1),
            cabin_class=CabinClass.ECONOMY,
            trip_id="trip_123",
        )

    @pytest.mark.asyncio
    async def test_duffel_client_initialization_error(self, mock_feature_flags, flight_request):
        """Test handling of client initialization errors."""
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Initialization error")
            
            service = FlightService()
            # Should still work with fallback
            result = await service.search_flights(flight_request)
            
            assert result is not None
            assert len(result.results) == 1  # Mock data

    @pytest.mark.asyncio
    async def test_conversion_error_handling(self, mock_feature_flags, flight_request):
        """Test handling of conversion errors."""
        mock_feature_flags.flights_integration = IntegrationMode.DIRECT
        
        with patch("tripsage.api.services.flight.DuffelHTTPClient") as mock_client_class:
            mock_client = AsyncMock()
            # Return invalid response that will cause conversion errors
            mock_client.search_flights.return_value = "invalid_response"
            mock_client_class.return_value = mock_client
            
            service = FlightService()
            result = await service.search_flights(flight_request)
            
            # Should fall back to mock data
            assert result is not None
            assert len(result.results) == 1


@pytest.mark.integration
class TestFlightServiceRealIntegration:
    """Integration tests with real services (requires proper configuration)."""

    @pytest.mark.asyncio
    async def test_real_direct_integration(self):
        """Test real integration with Duffel API."""
        import os
        if not os.getenv("DUFFEL_API_KEY"):
            pytest.skip("DUFFEL_API_KEY not set")
        
        with patch("tripsage.api.services.flight.feature_flags") as mock_flags:
            mock_flags.flights_integration = IntegrationMode.DIRECT
            
            service = FlightService()
            health = await service.health_check()
            
            # Should be able to connect to real API
            assert isinstance(health, bool)