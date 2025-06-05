"""
Integration tests for Google Maps API service.

This module tests the integration with Google Maps API for location services,
geocoding, place details, and direction calculations.
"""

from unittest.mock import patch

import pytest

from tripsage_core.services.external_apis.google_maps_service import GoogleMapsService


class TestGoogleMapsIntegration:
    """Test Google Maps API integration."""

    @pytest.fixture
    def google_maps_service(self):
        """Create Google Maps service instance."""
        with patch("googlemaps.Client") as mock_client:
            service = GoogleMapsService(api_key="test_api_key")
            service.client = mock_client
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
            "candidates": [
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
                }
            ],
            "status": "OK",
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
    async def test_geocode_address_success(
        self, google_maps_service, sample_geocode_response
    ):
        """Test successful address geocoding."""
        # Mock Google Maps client
        google_maps_service.client.geocode.return_value = sample_geocode_response

        result = await google_maps_service.geocode_address("Paris, France")

        # Assertions
        assert result is not None
        assert result["address"] == "Paris, France"
        assert result["latitude"] == 48.8566969
        assert result["longitude"] == 2.3514616
        assert result["place_id"] == "ChIJD7fiBh9u5kcRYJSMaMOCCwQ"
        assert result["country"] == "France"

        # Verify client was called
        google_maps_service.client.geocode.assert_called_once_with("Paris, France")

    @pytest.mark.asyncio
    async def test_geocode_address_no_results(self, google_maps_service):
        """Test geocoding with no results."""
        # Mock empty response
        google_maps_service.client.geocode.return_value = []

        result = await google_maps_service.geocode_address("Invalid Address 123")

        assert result is None

    @pytest.mark.asyncio
    async def test_reverse_geocode_success(
        self, google_maps_service, sample_geocode_response
    ):
        """Test successful reverse geocoding."""
        # Mock Google Maps client
        google_maps_service.client.reverse_geocode.return_value = (
            sample_geocode_response
        )

        result = await google_maps_service.reverse_geocode(48.8566969, 2.3514616)

        # Assertions
        assert result is not None
        assert result["address"] == "Paris, France"
        assert result["latitude"] == 48.8566969
        assert result["longitude"] == 2.3514616

        # Verify client was called
        google_maps_service.client.reverse_geocode.assert_called_once_with(
            (48.8566969, 2.3514616)
        )

    @pytest.mark.asyncio
    async def test_search_places_success(
        self, google_maps_service, sample_places_response
    ):
        """Test successful place search."""
        # Mock Google Maps client
        google_maps_service.client.find_place.return_value = sample_places_response

        result = await google_maps_service.search_places(
            query="Eiffel Tower", location=(48.8566969, 2.3514616), radius=5000
        )

        # Assertions
        assert result is not None
        assert "places" in result
        assert len(result["places"]) == 1

        place = result["places"][0]
        assert place["name"] == "Eiffel Tower"
        assert place["place_id"] == "ChIJN1t_tDeuEmsRUsoyG83frY4"
        assert place["rating"] == 4.6
        assert place["location"]["lat"] == 48.8583701
        assert place["location"]["lng"] == 2.2944813

    @pytest.mark.asyncio
    async def test_get_place_details_success(self, google_maps_service):
        """Test getting detailed place information."""
        place_details = {
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

        google_maps_service.client.place.return_value = place_details

        result = await google_maps_service.get_place_details(
            "ChIJN1t_tDeuEmsRUsoyG83frY4"
        )

        # Assertions
        assert result is not None
        assert result["name"] == "Eiffel Tower"
        assert result["rating"] == 4.6
        assert result["website"] == "https://www.toureiffel.paris/"
        assert result["phone"] == "+33 892 70 12 39"
        assert "opening_hours" in result
        assert "photos" in result

    @pytest.mark.asyncio
    async def test_get_directions_success(
        self, google_maps_service, sample_directions_response
    ):
        """Test getting directions between two points."""
        # Mock Google Maps client
        google_maps_service.client.directions.return_value = sample_directions_response

        result = await google_maps_service.get_directions(
            origin="Place Vendôme, Paris",
            destination="Eiffel Tower, Paris",
            mode="walking",
        )

        # Assertions
        assert result is not None
        assert "routes" in result
        assert len(result["routes"]) == 1

        route = result["routes"][0]
        assert route["distance"]["value"] == 1200
        assert route["duration"]["value"] == 900
        assert route["distance"]["text"] == "1.2 km"
        assert route["duration"]["text"] == "15 mins"

        # Verify client was called
        google_maps_service.client.directions.assert_called_once_with(
            origin="Place Vendôme, Paris",
            destination="Eiffel Tower, Paris",
            mode="walking",
        )

    @pytest.mark.asyncio
    async def test_calculate_distance_success(self, google_maps_service):
        """Test distance calculation between points."""
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

        google_maps_service.client.distance_matrix.return_value = distance_matrix

        result = await google_maps_service.calculate_distance(
            origins=["Place Vendôme, Paris"],
            destinations=["Eiffel Tower, Paris"],
            mode="walking",
        )

        # Assertions
        assert result is not None
        assert result["distance_km"] == 1.2
        assert result["duration_minutes"] == 15
        assert result["status"] == "OK"

    @pytest.mark.asyncio
    async def test_nearby_search_success(self, google_maps_service):
        """Test nearby places search."""
        nearby_results = {
            "results": [
                {
                    "place_id": "ChIJmda",
                    "name": "Restaurant Le Jules Verne",
                    "vicinity": "Eiffel Tower, Avenue Gustave Eiffel",
                    "geometry": {"location": {"lat": 48.8583701, "lng": 2.2944813}},
                    "rating": 4.3,
                    "price_level": 4,
                    "types": ["restaurant", "food", "point_of_interest"],
                    "opening_hours": {"open_now": False},
                }
            ],
            "status": "OK",
        }

        google_maps_service.client.places_nearby.return_value = nearby_results

        result = await google_maps_service.search_nearby_places(
            location=(48.8583701, 2.2944813), radius=1000, place_type="restaurant"
        )

        # Assertions
        assert result is not None
        assert "places" in result
        assert len(result["places"]) == 1

        place = result["places"][0]
        assert place["name"] == "Restaurant Le Jules Verne"
        assert place["rating"] == 4.3
        assert place["price_level"] == 4

    @pytest.mark.asyncio
    async def test_api_error_handling(self, google_maps_service):
        """Test handling of Google Maps API errors."""
        # Mock API error
        import googlemaps.exceptions

        google_maps_service.client.geocode.side_effect = googlemaps.exceptions.ApiError(
            "OVER_QUERY_LIMIT"
        )

        with pytest.raises(googlemaps.exceptions.ApiError):
            await google_maps_service.geocode_address("Paris, France")

    @pytest.mark.asyncio
    async def test_timeout_handling(self, google_maps_service):
        """Test handling of request timeouts."""
        import googlemaps.exceptions

        # Mock timeout error
        google_maps_service.client.geocode.side_effect = googlemaps.exceptions.Timeout()

        with pytest.raises(googlemaps.exceptions.Timeout):
            await google_maps_service.geocode_address("Paris, France")

    @pytest.mark.asyncio
    async def test_invalid_api_key_handling(self, google_maps_service):
        """Test handling of invalid API key."""
        import googlemaps.exceptions

        # Mock invalid API key error
        google_maps_service.client.geocode.side_effect = googlemaps.exceptions.ApiError(
            "REQUEST_DENIED"
        )

        with pytest.raises(googlemaps.exceptions.ApiError):
            await google_maps_service.geocode_address("Paris, France")

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, google_maps_service):
        """Test handling of rate limit errors."""
        import googlemaps.exceptions

        # Mock rate limit error
        google_maps_service.client.geocode.side_effect = googlemaps.exceptions.ApiError(
            "OVER_QUERY_LIMIT"
        )

        with pytest.raises(googlemaps.exceptions.ApiError):
            await google_maps_service.geocode_address("Paris, France")

    @pytest.mark.asyncio
    async def test_autocomplete_success(self, google_maps_service):
        """Test place autocomplete functionality."""
        autocomplete_results = {
            "predictions": [
                {
                    "description": "Paris, France",
                    "place_id": "ChIJD7fiBh9u5kcRYJSMaMOCCwQ",
                    "structured_formatting": {
                        "main_text": "Paris",
                        "secondary_text": "France",
                    },
                    "types": ["locality", "political"],
                },
                {
                    "description": "Paris, TX, USA",
                    "place_id": "ChIJ4zGFAZpYSoYRbMeyyKAmTJ0",
                    "structured_formatting": {
                        "main_text": "Paris",
                        "secondary_text": "TX, USA",
                    },
                    "types": ["locality", "political"],
                },
            ],
            "status": "OK",
        }

        google_maps_service.client.places_autocomplete.return_value = (
            autocomplete_results
        )

        result = await google_maps_service.autocomplete_places("Paris")

        # Assertions
        assert result is not None
        assert "predictions" in result
        assert len(result["predictions"]) == 2

        first_prediction = result["predictions"][0]
        assert first_prediction["description"] == "Paris, France"
        assert first_prediction["place_id"] == "ChIJD7fiBh9u5kcRYJSMaMOCCwQ"
