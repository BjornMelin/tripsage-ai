"""Tests for Google Maps service."""

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.exceptions.exceptions import CoreExternalAPIError
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
)


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock environment variables to prevent Settings validation errors."""
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "testing",
            "DATABASE_URL": "https://test.supabase.co",
            "DATABASE_PUBLIC_KEY": "test-public-key",
            "DATABASE_SERVICE_KEY": "test-service-key",
            "DATABASE_JWT_SECRET": "test-jwt-secret",
            "OPENAI_API_KEY": "test-key",
        },
    ):
        yield


class TestGoogleMapsService:
    """Test GoogleMapsService."""

    @pytest.fixture
    def mock_googlemaps(self):
        """Mock googlemaps client."""
        with patch(
            "tripsage_core.services.external_apis.google_maps_service.googlemaps"
        ) as mock:
            yield mock

    @pytest.fixture
    def service(self):
        """Create GoogleMapsService instance."""
        with patch(
            "tripsage_core.services.external_apis.google_maps_service.get_settings"
        ) as mock_settings:
            from pydantic import SecretStr

            mock_settings.return_value.google_maps_api_key = SecretStr("test-api-key")
            return GoogleMapsService()

    def test_init_creates_client(self, mock_googlemaps: Any, service: Any):
        """Test service initialization creates Google Maps client."""
        assert service.client is not None
        mock_googlemaps.Client.assert_called_once()  # type: ignore[member]

    def test_client_configuration(self, mock_googlemaps: Any, service: Any):
        """Test client is configured with API key."""
        call_args = mock_googlemaps.Client.call_args  # type: ignore[assignment]
        assert call_args is not None
        assert "api_key" in call_args.kwargs  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_geocode_success(self, mock_googlemaps: Any, service: Any):
        """Test successful geocoding."""
        mock_response = [
            {
                "formatted_address": "123 Test St",
                "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
            }
        ]

        mock_client = MagicMock()
        mock_googlemaps.Client.return_value = mock_client
        mock_client.geocode.return_value = mock_response

        service._client = mock_client

        result = await service.geocode("123 Test St")

        assert len(result) == 1
        assert result[0].formatted_address == "123 Test St"
        assert result[0].coordinates.latitude == 40.7128
        assert result[0].coordinates.longitude == -74.0060
        mock_client.geocode.assert_called_once_with("123 Test St")

    @pytest.mark.asyncio
    async def test_geocode_error(self, mock_googlemaps: Any, service: Any):
        """Test geocoding error handling."""
        from googlemaps.exceptions import ApiError

        mock_client = MagicMock()
        mock_client.geocode.side_effect = ApiError("API Error")

        service._client = mock_client

        with pytest.raises(GoogleMapsServiceError):
            await service.geocode("invalid address")

    @pytest.mark.asyncio
    async def test_places_search_success(self, mock_googlemaps: Any, service: Any):
        """Test successful places search."""
        mock_response = {
            "results": [
                {
                    "place_id": "test_place_id",
                    "name": "Test Place",
                    "formatted_address": "123 Test St",
                    "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
                }
            ]
        }

        mock_client = MagicMock()
        mock_googlemaps.Client.return_value = mock_client
        mock_client.places.return_value = mock_response

        service._client = mock_client

        result = await service.places_search(
            query="test place", location=(40.7128, -74.0060), radius=1000
        )

        assert len(result) == 1
        assert result[0].place_id == "test_place_id"
        assert result[0].name == "Test Place"
        mock_client.places.assert_called_once()

    @pytest.mark.asyncio
    async def test_directions_success(self, mock_googlemaps: Any, service: Any):
        """Test successful directions request."""
        mock_response = {
            "routes": [
                {
                    "legs": [
                        {
                            "distance": {"text": "5.2 mi", "value": 8369},
                            "duration": {"text": "12 mins", "value": 720},
                            "start_address": "Start",
                            "end_address": "End",
                        }
                    ]
                }
            ]
        }

        mock_client = MagicMock()
        mock_googlemaps.Client.return_value = mock_client
        mock_client.directions.return_value = mock_response

        service._client = mock_client

        result = await service.directions(
            origin="Start", destination="End", mode="driving"
        )

        assert len(result) == 1
        route = result[0]
        assert len(route.legs) == 1
        assert route.legs[0].distance.text == "5.2 mi"
        mock_client.directions.assert_called_once()

    @pytest.mark.asyncio
    async def test_distance_matrix_success(self, mock_googlemaps: Any, service: Any):
        """Test successful distance matrix request."""
        mock_response = {
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "5.2 mi", "value": 8369},
                            "duration": {"text": "12 mins", "value": 720},
                            "status": "OK",
                        }
                    ]
                }
            ]
        }

        mock_client = MagicMock()
        mock_googlemaps.Client.return_value = mock_client
        mock_client.distance_matrix.return_value = mock_response

        service._client = mock_client

        result = await service.distance_matrix(
            origins=["Start"], destinations=["End"], mode="driving"
        )

        assert len(result.rows) == 1
        assert len(result.rows[0].elements) == 1
        element = result.rows[0].elements[0]
        assert element.distance.text == "5.2 mi"
        assert element.duration.text == "12 mins"
        mock_client.distance_matrix.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_common_patterns(self, service: Any):
        """Test common error handling patterns."""
        from googlemaps.exceptions import ApiError, HTTPError, Timeout

        mock_client = MagicMock()
        service._client = mock_client

        # Test ApiError
        mock_client.geocode.side_effect = ApiError("API Error")
        with pytest.raises(GoogleMapsServiceError):
            await service.geocode("test")

        # Test HTTPError
        mock_client.geocode.side_effect = HTTPError("HTTP Error")
        with pytest.raises(GoogleMapsServiceError):
            await service.geocode("test")

        # Test Timeout
        mock_client.geocode.side_effect = Timeout("Timeout")
        with pytest.raises(GoogleMapsServiceError):
            await service.geocode("test")

    @pytest.mark.asyncio
    async def test_service_context_manager(self, service: Any):
        """Test service can be used as context manager."""
        with (
            patch.object(service, "connect") as mock_connect,
            patch.object(service, "disconnect") as mock_disconnect,
        ):
            async with service as s:
                assert s is service
                mock_connect.assert_called_once()

            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, service: Any):
        """Test connect and disconnect methods."""
        # These methods might be no-ops for the Google Maps service
        await service.connect()
        await service.disconnect()

        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_api_key_missing_error(self):
        """Test error when API key is missing."""
        with patch(
            "tripsage_core.services.external_apis.google_maps_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.google_maps_api_key = None

            service = GoogleMapsService()

            with pytest.raises(CoreExternalAPIError):
                await service.geocode("test")


class TestGoogleMapsServiceError:
    """Test GoogleMapsServiceError."""

    def test_error_initialization(self):
        """Test error initialization with all parameters."""
        error = GoogleMapsServiceError(
            message="Test error", original_error=Exception("Original")
        )

        assert error.message == "Test error"
        assert error.code == "GOOGLE_MAPS_API_ERROR"
        assert error.details.service == "GoogleMapsService"
        assert error.details.additional_context.get("original_error") == "Original"
        assert error.original_error is not None

    def test_error_initialization_minimal(self):
        """Test error initialization with minimal parameters."""
        error = GoogleMapsServiceError("Test error")

        assert error.message == "Test error"
        assert error.code == "GOOGLE_MAPS_API_ERROR"
        assert error.details.service == "GoogleMapsService"
        assert error.details.additional_context.get("original_error") is None
