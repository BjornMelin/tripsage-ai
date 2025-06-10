"""
Integration tests for Duffel API service.

This module tests the integration with the Duffel flight booking API,
ensuring proper authentication, search functionality, and booking workflows.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.services.external_apis.duffel_http_client import DuffelHTTPClient


class TestDuffelAPIIntegration:
    """Test Duffel API integration."""

    @pytest.fixture
    def mock_duffel_client(self):
        """Mock Duffel HTTP client."""
        client = AsyncMock(spec=DuffelHTTPClient)
        return client

    @pytest.fixture
    def flights_service(self, mock_duffel_client):
        """Create flights service with mocked Duffel client."""
        service = FlightService(database_service=AsyncMock(), cache_service=AsyncMock())
        service.duffel_client = mock_duffel_client
        return service

    @pytest.fixture
    def sample_flight_search_request(self):
        """Sample flight search request."""
        tomorrow = datetime.now() + timedelta(days=1)
        return {
            "origin": "LAX",
            "destination": "JFK",
            "departure_date": tomorrow.strftime("%Y-%m-%d"),
            "return_date": (tomorrow + timedelta(days=7)).strftime("%Y-%m-%d"),
            "passengers": {"adults": 1, "children": 0, "infants": 0},
            "cabin_class": "economy",
        }

    @pytest.fixture
    def mock_duffel_flight_response(self):
        """Mock Duffel API flight search response."""
        return {
            "data": [
                {
                    "id": "off_123456789",
                    "type": "offer",
                    "attributes": {
                        "total_amount": "324.50",
                        "total_currency": "USD",
                        "base_amount": "284.50",
                        "tax_amount": "40.00",
                        "slices": [
                            {
                                "id": "sli_123456789",
                                "segments": [
                                    {
                                        "id": "seg_123456789",
                                        "origin": {
                                            "iata_code": "LAX",
                                            "name": "Los Angeles International Airport",
                                            "city_name": "Los Angeles",
                                            "time_zone": "America/Los_Angeles",
                                        },
                                        "destination": {
                                            "iata_code": "JFK",
                                            "name": (
                                                "John F. Kennedy International Airport"
                                            ),
                                            "city_name": "New York",
                                            "time_zone": "America/New_York",
                                        },
                                        "departing_at": "2024-06-01T10:00:00Z",
                                        "arriving_at": "2024-06-01T18:30:00Z",
                                        "marketing_carrier": {
                                            "iata_code": "AA",
                                            "name": "American Airlines",
                                        },
                                        "aircraft": {"name": "Boeing 737-800"},
                                        "duration": "PT5H30M",
                                    }
                                ],
                                "duration": "PT5H30M",
                            }
                        ],
                        "passengers": [{"type": "adult", "age": 30}],
                    },
                }
            ],
            "meta": {"count": 1, "currency": "USD"},
        }

    @pytest.mark.asyncio
    async def test_search_flights_success(
        self,
        flights_service,
        mock_duffel_client,
        sample_flight_search_request,
        mock_duffel_flight_response,
    ):
        """Test successful flight search via Duffel API."""
        # Mock Duffel API response
        mock_duffel_client.search_flights.return_value = mock_duffel_flight_response

        result = await flights_service.search_flights(sample_flight_search_request)

        # Assertions
        assert result is not None
        assert "flights" in result
        assert len(result["flights"]) == 1

        flight = result["flights"][0]
        assert flight["id"] == "off_123456789"
        assert flight["price"]["total"] == Decimal("324.50")
        assert flight["price"]["currency"] == "USD"
        assert flight["origin"] == "LAX"
        assert flight["destination"] == "JFK"
        assert flight["airline"]["code"] == "AA"
        assert flight["airline"]["name"] == "American Airlines"

        # Verify Duffel client was called
        mock_duffel_client.search_flights.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_flights_no_results(
        self, flights_service, mock_duffel_client, sample_flight_search_request
    ):
        """Test flight search with no results."""
        # Mock empty response
        mock_duffel_client.search_flights.return_value = {
            "data": [],
            "meta": {"count": 0, "currency": "USD"},
        }

        result = await flights_service.search_flights(sample_flight_search_request)

        assert result is not None
        assert "flights" in result
        assert len(result["flights"]) == 0
        assert result["total_results"] == 0

    @pytest.mark.asyncio
    async def test_search_flights_api_error(
        self, flights_service, mock_duffel_client, sample_flight_search_request
    ):
        """Test flight search with API error."""
        # Mock API error
        mock_duffel_client.search_flights.side_effect = Exception("Duffel API Error")

        with pytest.raises(Exception, match="Duffel API Error"):
            await flights_service.search_flights(sample_flight_search_request)

    @pytest.mark.asyncio
    async def test_get_flight_details_success(
        self, flights_service, mock_duffel_client
    ):
        """Test getting flight offer details."""
        offer_id = "off_123456789"
        mock_flight_details = {
            "data": {
                "id": offer_id,
                "type": "offer",
                "attributes": {
                    "total_amount": "324.50",
                    "total_currency": "USD",
                    "expires_at": "2024-06-01T12:00:00Z",
                    "conditions": {
                        "change_before_departure": {
                            "allowed": True,
                            "penalty_amount": "50.00",
                        },
                        "cancel_before_departure": {
                            "allowed": True,
                            "penalty_amount": "100.00",
                        },
                    },
                },
            }
        }

        mock_duffel_client.get_offer.return_value = mock_flight_details

        result = await flights_service.get_flight_details(offer_id)

        assert result is not None
        assert result["id"] == offer_id
        assert result["price"]["total"] == Decimal("324.50")
        assert result["expires_at"] is not None
        assert "conditions" in result

    @pytest.mark.asyncio
    async def test_create_booking_success(self, flights_service, mock_duffel_client):
        """Test successful flight booking."""
        booking_request = {
            "offer_id": "off_123456789",
            "passengers": [
                {
                    "type": "adult",
                    "title": "mr",
                    "given_name": "John",
                    "family_name": "Doe",
                    "born_on": "1990-01-01",
                    "email": "john.doe@example.com",
                    "phone_number": "+1234567890",
                }
            ],
            "payments": [{"type": "balance", "amount": "324.50", "currency": "USD"}],
        }

        mock_booking_response = {
            "data": {
                "id": "ord_123456789",
                "type": "order",
                "attributes": {
                    "reference": "DUFFEL123",
                    "booking_reference": "ABCDEF",
                    "total_amount": "324.50",
                    "total_currency": "USD",
                    "created_at": "2024-06-01T10:00:00Z",
                    "documents": [
                        {"type": "eticket", "unique_identifier": "1234567890123"}
                    ],
                },
            }
        }

        mock_duffel_client.create_order.return_value = mock_booking_response

        result = await flights_service.create_booking(booking_request)

        assert result is not None
        assert result["id"] == "ord_123456789"
        assert result["reference"] == "DUFFEL123"
        assert result["booking_reference"] == "ABCDEF"
        assert result["total_amount"] == Decimal("324.50")
        assert len(result["documents"]) == 1

    @pytest.mark.asyncio
    async def test_cancel_booking_success(self, flights_service, mock_duffel_client):
        """Test successful booking cancellation."""
        order_id = "ord_123456789"

        mock_cancellation_response = {
            "data": {
                "id": "orc_123456789",
                "type": "order_cancellation",
                "attributes": {
                    "refund_amount": "224.50",
                    "refund_currency": "USD",
                    "created_at": "2024-06-01T12:00:00Z",
                },
            }
        }

        mock_duffel_client.cancel_order.return_value = mock_cancellation_response

        result = await flights_service.cancel_booking(order_id)

        assert result is not None
        assert result["id"] == "orc_123456789"
        assert result["refund_amount"] == Decimal("224.50")
        assert result["refund_currency"] == "USD"

    @pytest.mark.asyncio
    async def test_authentication_error(
        self, flights_service, mock_duffel_client, sample_flight_search_request
    ):
        """Test handling of authentication errors."""
        # Mock authentication error
        from tripsage_core.exceptions.exceptions import CoreAuthenticationError

        mock_duffel_client.search_flights.side_effect = CoreAuthenticationError(
            "Invalid API key"
        )

        with pytest.raises(CoreAuthenticationError):
            await flights_service.search_flights(sample_flight_search_request)

    @pytest.mark.asyncio
    async def test_rate_limit_handling(
        self, flights_service, mock_duffel_client, sample_flight_search_request
    ):
        """Test handling of rate limit errors."""
        # Mock rate limit error
        mock_duffel_client.search_flights.side_effect = Exception("Rate limit exceeded")

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await flights_service.search_flights(sample_flight_search_request)

    @pytest.mark.asyncio
    async def test_timeout_handling(
        self, flights_service, mock_duffel_client, sample_flight_search_request
    ):
        """Test handling of request timeouts."""
        import asyncio

        # Mock timeout error
        mock_duffel_client.search_flights.side_effect = asyncio.TimeoutError()

        with pytest.raises(asyncio.TimeoutError):
            await flights_service.search_flights(sample_flight_search_request)

    @pytest.mark.asyncio
    async def test_invalid_request_handling(self, flights_service, mock_duffel_client):
        """Test handling of invalid requests."""
        invalid_request = {"origin": "INVALID", "destination": "ALSOINVALID"}

        # Mock validation error
        mock_duffel_client.search_flights.side_effect = ValueError(
            "Invalid airport codes"
        )

        with pytest.raises(ValueError, match="Invalid airport codes"):
            await flights_service.search_flights(invalid_request)

    @pytest.mark.asyncio
    async def test_network_error_handling(
        self, flights_service, mock_duffel_client, sample_flight_search_request
    ):
        """Test handling of network errors."""
        import aiohttp

        # Mock network error
        mock_duffel_client.search_flights.side_effect = aiohttp.ClientError(
            "Network connection failed"
        )

        with pytest.raises(aiohttp.ClientError):
            await flights_service.search_flights(sample_flight_search_request)
