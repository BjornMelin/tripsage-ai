"""Unit tests for Google Maps Service.

This module tests the direct Google Maps SDK integration service with
mocked Google Maps responses.
"""

from unittest.mock import Mock, patch

import pytest
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError

from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
    get_google_maps_service,
)


class TestGoogleMapsService:
    """Test cases for GoogleMapsService."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.google_maps_api_key = Mock()
        settings.google_maps_api_key.get_secret_value.return_value = "test-api-key"
        settings.google_maps_timeout = 30.0
        settings.google_maps_retry_timeout = 60
        settings.google_maps_queries_per_second = 10
        return settings

    @pytest.fixture
    def google_maps_service(self, mock_settings):
        """Create GoogleMapsService instance with mocked settings."""
        with patch(
            "tripsage_core.services.external_apis.google_maps_service.get_settings",
            return_value=mock_settings,
        ):
            return GoogleMapsService()

    @pytest.fixture
    def mock_client(self):
        """Mock Google Maps client."""
        return Mock()

    def test_client_initialization(self, google_maps_service, mock_settings):
        """Test that client is properly initialized with settings."""
        with patch(
            "tripsage_core.services.external_apis.google_maps_service.googlemaps.Client"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Access client property to trigger initialization
            client = google_maps_service.client

            # Verify client was created with correct parameters
            mock_client_class.assert_called_once_with(
                key="test-api-key",
                timeout=30.0,
                retry_timeout=60,
                queries_per_second=10,
                retry_over_query_limit=True,
                channel=None,
            )
            assert client == mock_client

    def test_client_initialization_no_api_key(self, mock_settings):
        """Test that CoreServiceError is raised when no API key is provided."""
        mock_settings.google_maps_api_key = None

        with patch(
            "tripsage_core.services.external_apis.google_maps_service.get_settings",
            return_value=mock_settings,
        ):
            service = GoogleMapsService()
            with pytest.raises(
                CoreServiceError, match="Google Maps API key not configured"
            ):
                _ = service.client

    @pytest.mark.asyncio
    async def test_geocode_success(self, google_maps_service, mock_client):
        """Test successful geocoding."""
        # Setup
        expected_result = [
            {
                "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA",
                "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}},
            }
        ]
        mock_client.geocode.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.geocode(
            "1600 Amphitheatre Parkway, Mountain View, CA"
        )

        # Verify
        assert result == expected_result
        mock_client.geocode.assert_called_once_with(
            "1600 Amphitheatre Parkway, Mountain View, CA"
        )

    @pytest.mark.asyncio
    async def test_geocode_api_error(self, google_maps_service, mock_client):
        """Test geocoding with API error."""
        # Setup
        mock_client.geocode.side_effect = ApiError("Invalid request")
        google_maps_service._client = mock_client

        # Execute and verify
        with pytest.raises(GoogleMapsServiceError, match="Geocoding failed"):
            await google_maps_service.geocode("invalid address")

    @pytest.mark.asyncio
    async def test_reverse_geocode_success(self, google_maps_service, mock_client):
        """Test successful reverse geocoding."""
        # Setup
        expected_result = [
            {
                "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA",
                "types": ["street_address"],
            }
        ]
        mock_client.reverse_geocode.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.reverse_geocode(37.4224764, -122.0842499)

        # Verify
        assert result == expected_result
        mock_client.reverse_geocode.assert_called_once_with((37.4224764, -122.0842499))

    @pytest.mark.asyncio
    async def test_reverse_geocode_timeout(self, google_maps_service, mock_client):
        """Test reverse geocoding with timeout error."""
        # Setup
        mock_client.reverse_geocode.side_effect = Timeout("Request timed out")
        google_maps_service._client = mock_client

        # Execute and verify
        with pytest.raises(GoogleMapsServiceError, match="Reverse geocoding failed"):
            await google_maps_service.reverse_geocode(37.4224764, -122.0842499)

    @pytest.mark.asyncio
    async def test_search_places_success(self, google_maps_service, mock_client):
        """Test successful place search."""
        # Setup
        expected_result = {
            "results": [
                {"name": "Test Restaurant", "place_id": "test_place_id", "rating": 4.5}
            ],
            "status": "OK",
        }
        mock_client.places.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.search_places(
            "restaurants", location=(37.4224764, -122.0842499), radius=1000
        )

        # Verify
        assert result == expected_result
        mock_client.places.assert_called_once_with(
            query="restaurants", location=(37.4224764, -122.0842499), radius=1000
        )

    @pytest.mark.asyncio
    async def test_search_places_no_location(self, google_maps_service, mock_client):
        """Test place search without location constraints."""
        # Setup
        expected_result = {"results": [], "status": "OK"}
        mock_client.places.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.search_places("restaurants")

        # Verify
        assert result == expected_result
        mock_client.places.assert_called_once_with(query="restaurants")

    @pytest.mark.asyncio
    async def test_get_place_details_success(self, google_maps_service, mock_client):
        """Test successful place details retrieval."""
        # Setup
        expected_result = {
            "result": {
                "name": "Test Place",
                "formatted_address": "123 Test St",
                "rating": 4.2,
                "photos": [],
            },
            "status": "OK",
        }
        mock_client.place.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.get_place_details(
            "test_place_id", fields=["name", "formatted_address", "rating"]
        )

        # Verify
        assert result == expected_result
        mock_client.place.assert_called_once_with(
            place_id="test_place_id", fields=["name", "formatted_address", "rating"]
        )

    @pytest.mark.asyncio
    async def test_get_directions_success(self, google_maps_service, mock_client):
        """Test successful directions retrieval."""
        # Setup
        expected_result = [
            {
                "legs": [
                    {
                        "distance": {"text": "10.2 km", "value": 10200},
                        "duration": {"text": "15 mins", "value": 900},
                    }
                ]
            }
        ]
        mock_client.directions.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.get_directions(
            "San Francisco, CA", "Oakland, CA", mode="driving"
        )

        # Verify
        assert result == expected_result
        mock_client.directions.assert_called_once_with(
            origin="San Francisco, CA", destination="Oakland, CA", mode="driving"
        )

    @pytest.mark.asyncio
    async def test_distance_matrix_success(self, google_maps_service, mock_client):
        """Test successful distance matrix calculation."""
        # Setup
        expected_result = {
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "10.2 km", "value": 10200},
                            "duration": {"text": "15 mins", "value": 900},
                            "status": "OK",
                        }
                    ]
                }
            ],
            "status": "OK",
        }
        mock_client.distance_matrix.return_value = expected_result
        google_maps_service._client = mock_client

        # Execute
        result = await google_maps_service.distance_matrix(
            origins=["San Francisco, CA"], destinations=["Oakland, CA"], mode="driving"
        )

        # Verify
        assert result == expected_result
        mock_client.distance_matrix.assert_called_once_with(
            origins=["San Francisco, CA"], destinations=["Oakland, CA"], mode="driving"
        )

    @pytest.mark.asyncio
    async def test_get_elevation_success(self, google_maps_service, mock_client):
        """Test successful elevation data retrieval."""
        # Setup
        expected_result = [
            {
                "elevation": 1608.637939453125,
                "location": {"lat": 39.73915360, "lng": -104.9847034},
                "resolution": 4.771975994110107,
            }
        ]
        mock_client.elevation.return_value = expected_result
        google_maps_service._client = mock_client

        locations = [(39.73915360, -104.9847034)]

        # Execute
        result = await google_maps_service.get_elevation(locations)

        # Verify
        assert result == expected_result
        mock_client.elevation.assert_called_once_with(locations)

    @pytest.mark.asyncio
    async def test_get_timezone_success(self, google_maps_service, mock_client):
        """Test successful timezone retrieval."""
        # Setup
        expected_result = {
            "timeZoneId": "America/Denver",
            "timeZoneName": "Mountain Standard Time",
            "dstOffset": 0,
            "rawOffset": -25200,
            "status": "OK",
        }
        mock_client.timezone.return_value = expected_result
        google_maps_service._client = mock_client

        location = (39.73915360, -104.9847034)

        # Execute
        result = await google_maps_service.get_timezone(location, timestamp=1331161200)

        # Verify
        assert result == expected_result
        mock_client.timezone.assert_called_once_with(
            location=location, timestamp=1331161200
        )

    @pytest.mark.asyncio
    async def test_get_timezone_no_timestamp(self, google_maps_service, mock_client):
        """Test timezone retrieval without timestamp."""
        # Setup
        expected_result = {"timeZoneId": "America/Denver", "status": "OK"}
        mock_client.timezone.return_value = expected_result
        google_maps_service._client = mock_client

        location = (39.73915360, -104.9847034)

        # Execute
        result = await google_maps_service.get_timezone(location)

        # Verify
        assert result == expected_result
        mock_client.timezone.assert_called_once_with(location=location)

    @pytest.mark.asyncio
    async def test_http_error_handling(self, google_maps_service, mock_client):
        """Test handling of HTTP errors."""
        # Setup
        mock_client.geocode.side_effect = HTTPError("HTTP 500 Server Error")
        google_maps_service._client = mock_client

        # Execute and verify
        with pytest.raises(GoogleMapsServiceError, match="Geocoding failed"):
            await google_maps_service.geocode("test address")

    @pytest.mark.asyncio
    async def test_transport_error_handling(self, google_maps_service, mock_client):
        """Test handling of transport errors."""
        # Setup
        mock_client.search_places.side_effect = TransportError("Network error")
        google_maps_service._client = mock_client

        # Execute and verify
        with pytest.raises(GoogleMapsServiceError, match="Place search failed"):
            await google_maps_service.search_places("test query")

    def test_singleton_service(self):
        """Test that get_google_maps_service returns a singleton."""
        service1 = get_google_maps_service()
        service2 = get_google_maps_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_with_error_handling_decorator(
        self, google_maps_service, mock_client
    ):
        """Test that the error handling decorator works correctly."""
        # Setup
        mock_client.geocode.side_effect = Exception("Unexpected error")
        google_maps_service._client = mock_client

        # Execute and verify
        with pytest.raises(Exception, match="Unexpected error"):
            await google_maps_service.geocode("test address")


class TestGoogleMapsServiceErrorException:
    """Test the GoogleMapsServiceError exception."""

    def test_error_creation(self):
        """Test GoogleMapsServiceError creation."""
        error = GoogleMapsServiceError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self):
        """Test that GoogleMapsServiceError inherits from Exception."""
        error = GoogleMapsServiceError("Test error")
        assert isinstance(error, Exception)


class TestAsyncToThreadIntegration:
    """Test async integration with blocking Google Maps client."""

    @pytest.mark.asyncio
    async def test_asyncio_to_thread_integration(self):
        """Test that asyncio.to_thread is used correctly."""
        # This is a basic integration test to ensure async wrapper works
        with (
            patch(
                "tripsage_core.services.external_apis.google_maps_service.get_settings"
            ) as mock_get_settings,
            patch(
                "tripsage_core.services.external_apis.google_maps_service.googlemaps.Client"
            ) as mock_client_class,
            patch("asyncio.to_thread") as mock_to_thread,
        ):
            # Setup mocks
            mock_settings = Mock()
            mock_settings.google_maps_api_key = Mock()
            mock_settings.google_maps_api_key.get_secret_value.return_value = "test-key"
            mock_settings.google_maps_timeout = 30.0
            mock_settings.google_maps_retry_timeout = 60
            mock_settings.google_maps_queries_per_second = 10
            mock_get_settings.return_value = mock_settings

            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_to_thread.return_value = [{"test": "result"}]

            # Test
            service = GoogleMapsService()
            result = await service.geocode("test address")

            # Verify
            mock_to_thread.assert_called_once()
            assert result == [{"test": "result"}]
