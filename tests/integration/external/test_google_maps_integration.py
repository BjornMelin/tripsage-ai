"""
Integration tests for Google Maps API service.

This module tests the integration with Google Maps API for location services,
geocoding, place details, and direction calculations.
"""

from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
)

class TestGoogleMapsIntegration:
    """Test Google Maps API integration."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.google_maps_api_key = "test_api_key"
        settings.google_maps_timeout = 10
        settings.google_maps_retry_timeout = 60
        return settings

    @pytest.fixture
    def google_maps_service(self, mock_settings):
        """Create Google Maps service instance."""
        with patch("googlemaps.Client") as mock_client:
            service = GoogleMapsService(settings=mock_settings)
            service._client = mock_client
            service._connected = True
            return service

    @pytest.fixture
    def sample_geocode_response(self):
        """Sample geocoding response from Google Maps."""
        return [
            {
                "address_components": [
                    {
                        "long_name": "Paris",
                        "short_name": "Paris",
                        "types": ["locality", "political"],
                    },
                    {
                        "long_name": "France",
                        "short_name": "FR",
                        "types": ["country", "political"],
                    },
                ],
                "formatted_address": "Paris, France",
                "geometry": {
                    "location": {"lat": 48.8566969, "lng": 2.3514616},
                    "location_type": "APPROXIMATE",
                    "viewport": {
                        "northeast": {"lat": 48.9021449, "lng": 2.4699208},
                        "southwest": {"lat": 48.815573, "lng": 2.224199},
                    },
                },
                "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                "types": ["locality", "political"],
            }
        ]

    @pytest.fixture
    def sample_places_response(self):
        """Sample Places API response."""
        return {
            "results": [
                {
                    "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                    "name": "Eiffel Tower",
                    "formatted_address": (
                        "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
                    ),
                    "geometry": {"location": {"lat": 48.8583701, "lng": 2.2944813}},
                    "rating": 4.6,
                    "types": [
                        "tourist_attraction",
                        "point_of_interest",
                        "establishment",
                    ],
                    "price_level": 2,
                    "opening_hours": {"open_now": True},
                    "user_ratings_total": 142045,
                }
            ],
            "next_page_token": None,
        }

    @pytest.fixture
    def sample_place_details_response(self):
        """Sample Place Details API response."""
        return {
            "result": {
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "name": "Eiffel Tower",
                "formatted_address": (
                    "Champ de Mars, 5 Avenue Anatole France, 75007 Paris, France"
                ),
                "geometry": {"location": {"lat": 48.8583701, "lng": 2.2944813}},
                "rating": 4.6,
                "user_ratings_total": 142045,
                "price_level": 2,
                "opening_hours": {
                    "open_now": True,
                    "periods": [
                        {
                            "close": {"day": 0, "time": "0000"},
                            "open": {"day": 0, "time": "0930"},
                        }
                    ],
                    "weekday_text": [
                        "Monday: 9:30 AM – 11:45 PM",
                        "Tuesday: 9:30 AM – 11:45 PM",
                    ],
                },
                "photos": [
                    {"height": 3024, "width": 4032, "photo_reference": "CmRaAAAA..."}
                ],
                "website": "https://www.toureiffel.paris/",
                "international_phone_number": "+33 892 70 12 39",
            }
        }

    @pytest.fixture
    def sample_directions_response(self):
        """Sample Directions API response."""
        return [
            {
                "bounds": {
                    "northeast": {"lat": 48.8583701, "lng": 2.2944813},
                    "southwest": {"lat": 48.8566969, "lng": 2.2944813},
                },
                "legs": [
                    {
                        "distance": {"text": "1.2 km", "value": 1200},
                        "duration": {"text": "15 mins", "value": 900},
                        "end_address": (
                            "Champ de Mars, 5 Avenue Anatole France, "
                            "75007 Paris, France"
                        ),
                        "end_location": {"lat": 48.8583701, "lng": 2.2944813},
                        "start_address": "Place Vendôme, 75001 Paris, France",
                        "start_location": {"lat": 48.8566969, "lng": 2.3286616},
                        "steps": [
                            {
                                "distance": {"text": "0.5 km", "value": 500},
                                "duration": {"text": "6 mins", "value": 360},
                                "html_instructions": (
                                    "Head <b>southwest</b> on <b>Rue de la Paix</b>"
                                ),
                                "travel_mode": "WALKING",
                            }
                        ],
                    }
                ],
                "overview_polyline": {"points": "i{~gHoa`@"},
                "summary": "Rue de la Paix",
                "warnings": [],
                "waypoint_order": [],
            }
        ]

    @pytest.mark.asyncio
    async def test_geocode_success(self, google_maps_service, sample_geocode_response):
        """Test successful address geocoding."""
        # Mock Google Maps client
        google_maps_service._client.geocode.return_value = sample_geocode_response

        result = await google_maps_service.geocode("Paris, France")

        # Assertions
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["formatted_address"] == "Paris, France"
        assert result[0]["geometry"]["location"]["lat"] == 48.8566969
        assert result[0]["geometry"]["location"]["lng"] == 2.3514616
        assert result[0]["place_id"] == "ChIJD7fiBh9u5kcRYJSMaMOCCwQ"

        # Verify client was called
        google_maps_service._client.geocode.assert_called_once_with("Paris, France")

    @pytest.mark.asyncio
    async def test_geocode_no_results(self, google_maps_service):
        """Test geocoding with no results."""
        # Mock empty response
        google_maps_service._client.geocode.return_value = []

        result = await google_maps_service.geocode("Invalid Address 123")

        assert result == []

    @pytest.mark.asyncio
    async def test_reverse_geocode_success(
        self, google_maps_service, sample_geocode_response
    ):
        """Test successful reverse geocoding."""
        # Mock Google Maps client
        google_maps_service._client.reverse_geocode.return_value = (
            sample_geocode_response
        )

        result = await google_maps_service.reverse_geocode(48.8566969, 2.3514616)

        # Assertions
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["formatted_address"] == "Paris, France"

        # Verify client was called
        google_maps_service._client.reverse_geocode.assert_called_once_with(
            (48.8566969, 2.3514616)
        )

    @pytest.mark.asyncio
    async def test_search_places_success(
        self, google_maps_service, sample_places_response
    ):
        """Test successful place search."""
        # Mock Google Maps client
        google_maps_service._client.places.return_value = sample_places_response

        result = await google_maps_service.search_places(
            query="Eiffel Tower", location=(48.8566969, 2.3514616), radius=5000
        )

        # Assertions
        assert result is not None
        assert "results" in result
        assert len(result["results"]) == 1

        place = result["results"][0]
        assert place["name"] == "Eiffel Tower"
        assert place["place_id"] == "ChIJN1t_tDeuEmsRUsoyG83frY4"
        assert place["rating"] == 4.6

    @pytest.mark.asyncio
    async def test_get_place_details_success(
        self, google_maps_service, sample_place_details_response
    ):
        """Test getting detailed place information."""
        google_maps_service._client.place.return_value = sample_place_details_response

        result = await google_maps_service.get_place_details(
            "ChIJN1t_tDeuEmsRUsoyG83frY4"
        )

        # Assertions
        assert result is not None
        assert "result" in result
        assert result["result"]["name"] == "Eiffel Tower"
        assert result["result"]["rating"] == 4.6
        assert result["result"]["website"] == "https://www.toureiffel.paris/"

    @pytest.mark.asyncio
    async def test_get_directions_success(
        self, google_maps_service, sample_directions_response
    ):
        """Test getting directions between two points."""
        # Mock Google Maps client
        google_maps_service._client.directions.return_value = sample_directions_response

        result = await google_maps_service.get_directions(
            origin="Place Vendôme, Paris",
            destination="Eiffel Tower, Paris",
            mode="walking",
        )

        # Assertions
        assert result is not None
        assert isinstance(result, list)
        assert len(result) == 1

        route = result[0]
        assert route["legs"][0]["distance"]["value"] == 1200
        assert route["legs"][0]["duration"]["value"] == 900

        # Verify client was called
        google_maps_service._client.directions.assert_called_once_with(
            origin="Place Vendôme, Paris",
            destination="Eiffel Tower, Paris",
            mode="walking",
        )

    @pytest.mark.asyncio
    async def test_distance_matrix_success(self, google_maps_service):
        """Test distance matrix calculation between points."""
        distance_matrix = {
            "rows": [
                {
                    "elements": [
                        {
                            "distance": {"text": "1.2 km", "value": 1200},
                            "duration": {"text": "15 mins", "value": 900},
                            "status": "OK",
                        }
                    ]
                }
            ],
            "status": "OK",
        }

        google_maps_service._client.distance_matrix.return_value = distance_matrix

        result = await google_maps_service.distance_matrix(
            origins=["Place Vendôme, Paris"],
            destinations=["Eiffel Tower, Paris"],
            mode="walking",
        )

        # Assertions
        assert result is not None
        assert result["status"] == "OK"
        assert result["rows"][0]["elements"][0]["distance"]["value"] == 1200

    @pytest.mark.asyncio
    async def test_api_error_handling(self, google_maps_service):
        """Test handling of Google Maps API errors."""
        # Mock API error
        import googlemaps.exceptions

        google_maps_service._client.geocode.side_effect = (
            googlemaps.exceptions.ApiError("OVER_QUERY_LIMIT")
        )

        with pytest.raises(GoogleMapsServiceError) as exc_info:
            await google_maps_service.geocode("Paris, France")

        assert "Geocoding failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_handling(self, google_maps_service):
        """Test handling of request timeouts."""
        import googlemaps.exceptions

        # Mock timeout error
        google_maps_service._client.geocode.side_effect = (
            googlemaps.exceptions.Timeout()
        )

        with pytest.raises(GoogleMapsServiceError):
            await google_maps_service.geocode("Paris, France")

    @pytest.mark.asyncio
    async def test_health_check_success(self, google_maps_service):
        """Test health check functionality."""
        # Mock successful geocode response
        google_maps_service._client.geocode.return_value = [{"status": "OK"}]

        result = await google_maps_service.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, google_maps_service):
        """Test health check failure."""
        # Mock API error
        import googlemaps.exceptions

        google_maps_service._client.geocode.side_effect = (
            googlemaps.exceptions.ApiError("API_KEY_INVALID")
        )

        result = await google_maps_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_timezone_success(self, google_maps_service):
        """Test timezone lookup."""
        timezone_response = {
            "dstOffset": 3600,
            "rawOffset": 3600,
            "status": "OK",
            "timeZoneId": "Europe/Paris",
            "timeZoneName": "Central European Summer Time",
        }

        google_maps_service._client.timezone.return_value = timezone_response

        result = await google_maps_service.get_timezone(
            location=(48.8566969, 2.3514616)
        )

        assert result is not None
        assert result["timeZoneId"] == "Europe/Paris"
        assert result["status"] == "OK"

    @pytest.mark.asyncio
    async def test_get_elevation_success(self, google_maps_service):
        """Test elevation lookup."""
        elevation_response = [
            {
                "elevation": 38.5,
                "location": {"lat": 48.8566969, "lng": 2.3514616},
                "resolution": 152.7032318115234,
            }
        ]

        google_maps_service._client.elevation.return_value = elevation_response

        result = await google_maps_service.get_elevation(
            locations=[(48.8566969, 2.3514616)]
        )

        assert result is not None
        assert isinstance(result, list)
        assert result[0]["elevation"] == 38.5
