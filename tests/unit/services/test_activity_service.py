"""
Comprehensive unit tests for ActivityService.

Tests cover search functionality, caching, error handling, and Google Maps API integration.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from tripsage.api.schemas.requests.activities import ActivitySearchRequest
from tripsage.api.schemas.responses.activities import (
    ActivitySearchResponse,
    Activity,
    ActivityType,
    Coordinates,
)
from tripsage_core.services.business.activity_service import (
    ActivityService,
    ActivityServiceError,
    get_activity_service,
)


class TestActivityService:
    """Test suite for ActivityService."""

    @pytest.fixture
    def mock_google_maps_service(self):
        """Create a mock Google Maps service."""
        mock_service = AsyncMock()
        mock_service.geocode = AsyncMock()
        mock_service.places_nearby_search = AsyncMock()
        mock_service.place_details = AsyncMock()
        return mock_service

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        return mock_cache

    @pytest.fixture
    def activity_service(self, mock_google_maps_service, mock_cache_service):
        """Create an ActivityService instance with mocked dependencies."""
        service = ActivityService(
            google_maps_service=mock_google_maps_service,
            cache_service=mock_cache_service,
        )
        return service

    @pytest.fixture
    def sample_search_request(self):
        """Create a sample activity search request."""
        return ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 1, 15),
            adults=2,
            children=1,
            infants=0,
            activity_types=[ActivityType.MUSEUM, ActivityType.PARK],
            budget_min=0,
            budget_max=500,
            rating=4.0,
        )

    @pytest.fixture
    def sample_geocode_response(self):
        """Sample geocode response from Google Maps."""
        return [{
            "geometry": {
                "location": {
                    "lat": 40.7128,
                    "lng": -74.0060
                }
            }
        }]

    @pytest.fixture
    def sample_places_response(self):
        """Sample places response from Google Maps."""
        return {
            "results": [
                {
                    "place_id": "place123",
                    "name": "Museum of Modern Art",
                    "vicinity": "11 W 53rd St, New York",
                    "geometry": {
                        "location": {"lat": 40.7614, "lng": -73.9776}
                    },
                    "rating": 4.5,
                    "user_ratings_total": 20000,
                    "types": ["museum", "point_of_interest"],
                    "price_level": 3,
                    "photos": [{
                        "photo_reference": "photo123",
                        "width": 1024,
                        "height": 768
                    }]
                },
                {
                    "place_id": "place456",
                    "name": "Central Park",
                    "vicinity": "New York",
                    "geometry": {
                        "location": {"lat": 40.7829, "lng": -73.9654}
                    },
                    "rating": 4.8,
                    "user_ratings_total": 50000,
                    "types": ["park", "point_of_interest"],
                    "photos": []
                }
            ]
        }

    @pytest.fixture
    def sample_place_details_response(self):
        """Sample place details response from Google Maps."""
        return {
            "result": {
                "formatted_phone_number": "(212) 708-9400",
                "website": "https://www.moma.org",
                "opening_hours": {
                    "weekday_text": [
                        "Monday: 10:30 AM – 5:30 PM",
                        "Tuesday: 10:30 AM – 5:30 PM",
                        "Wednesday: 10:30 AM – 5:30 PM",
                        "Thursday: 10:30 AM – 5:30 PM",
                        "Friday: 10:30 AM – 9:00 PM",
                        "Saturday: 10:30 AM – 5:30 PM",
                        "Sunday: 10:30 AM – 5:30 PM"
                    ],
                    "open_now": True
                },
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Amazing collection of modern art!"
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_search_activities_success(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_search_request,
        sample_geocode_response,
        sample_places_response,
        sample_place_details_response,
    ):
        """Test successful activity search."""
        # Setup mocks
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.places_nearby_search.return_value = sample_places_response
        mock_google_maps_service.place_details.return_value = sample_place_details_response
        mock_cache_service.get.return_value = None  # No cache hit

        # Perform search
        response = await activity_service.search_activities(sample_search_request)

        # Verify response
        assert isinstance(response, ActivitySearchResponse)
        assert len(response.activities) == 2
        assert response.total_results == 2
        assert response.destination == "New York, NY"

        # Verify first activity
        museum = response.activities[0]
        assert museum.name == "Museum of Modern Art"
        assert museum.type == ActivityType.MUSEUM
        assert museum.rating == 4.5
        assert museum.price == 150.0  # Price level 3 * 50
        assert museum.coordinates.latitude == 40.7614
        assert museum.coordinates.longitude == -73.9776

        # Verify second activity
        park = response.activities[1]
        assert park.name == "Central Park"
        assert park.type == ActivityType.PARK
        assert park.rating == 4.8
        assert park.price == 0.0  # No price level means free

        # Verify service calls
        mock_google_maps_service.geocode.assert_called_once_with("New York, NY")
        assert mock_google_maps_service.places_nearby_search.call_count == 2
        assert mock_google_maps_service.place_details.call_count == 2
        
        # Verify caching
        assert mock_cache_service.set.called

    @pytest.mark.asyncio
    async def test_search_activities_with_cache_hit(
        self,
        activity_service,
        mock_cache_service,
        sample_search_request,
    ):
        """Test activity search with cache hit."""
        # Setup cached response
        cached_response = ActivitySearchResponse(
            activities=[
                Activity(
                    id="cached123",
                    name="Cached Museum",
                    type=ActivityType.MUSEUM,
                    description="From cache",
                    location="New York",
                    coordinates=Coordinates(latitude=40.7, longitude=-74.0),
                    rating=4.5,
                    price=100.0,
                    provider="cache",
                )
            ],
            total_results=1,
            destination="New York, NY",
            search_date=date.today(),
        )
        mock_cache_service.get.return_value = cached_response.model_dump_json()

        # Perform search
        response = await activity_service.search_activities(sample_search_request)

        # Verify cached response returned
        assert len(response.activities) == 1
        assert response.activities[0].name == "Cached Museum"
        assert response.activities[0].provider == "cache"
        
        # Verify no Google Maps calls
        activity_service._google_maps_service.geocode.assert_not_called()
        activity_service._google_maps_service.places_nearby_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_activities_geocoding_failure(
        self,
        activity_service,
        mock_google_maps_service,
        sample_search_request,
    ):
        """Test activity search when geocoding fails."""
        # Setup mock to raise exception
        mock_google_maps_service.geocode.side_effect = Exception("Geocoding failed")

        # Perform search and expect error
        with pytest.raises(ActivityServiceError) as exc_info:
            await activity_service.search_activities(sample_search_request)
        
        assert "Failed to geocode destination" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_activities_no_results(
        self,
        activity_service,
        mock_google_maps_service,
        sample_search_request,
        sample_geocode_response,
    ):
        """Test activity search with no results."""
        # Setup mocks
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.places_nearby_search.return_value = {"results": []}

        # Perform search
        response = await activity_service.search_activities(sample_search_request)

        # Verify empty response
        assert len(response.activities) == 0
        assert response.total_results == 0

    @pytest.mark.asyncio
    async def test_search_activities_rating_filter(
        self,
        activity_service,
        mock_google_maps_service,
        sample_search_request,
        sample_geocode_response,
        sample_places_response,
    ):
        """Test activity search with rating filter."""
        # Setup mocks
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.places_nearby_search.return_value = sample_places_response
        
        # Set high rating filter
        sample_search_request.rating = 4.7

        # Perform search
        response = await activity_service.search_activities(sample_search_request)

        # Only Central Park (4.8) should pass the filter
        assert len(response.activities) == 1
        assert response.activities[0].name == "Central Park"
        assert response.activities[0].rating == 4.8

    @pytest.mark.asyncio
    async def test_search_activities_budget_filter(
        self,
        activity_service,
        mock_google_maps_service,
        sample_search_request,
        sample_geocode_response,
        sample_places_response,
        sample_place_details_response,
    ):
        """Test activity search with budget filter."""
        # Setup mocks
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.places_nearby_search.return_value = sample_places_response
        mock_google_maps_service.place_details.return_value = sample_place_details_response
        
        # Set low budget
        sample_search_request.budget_min = 0
        sample_search_request.budget_max = 50

        # Perform search
        response = await activity_service.search_activities(sample_search_request)

        # Only Central Park (free) should pass the filter
        assert len(response.activities) == 1
        assert response.activities[0].name == "Central Park"
        assert response.activities[0].price == 0.0

    @pytest.mark.asyncio
    async def test_search_activities_all_types(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response,
    ):
        """Test activity search with all activity types."""
        # Create request with no specific types (search all)
        request = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 1, 15),
            adults=2,
        )
        
        # Setup mocks
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.places_nearby_search.return_value = {"results": []}

        # Perform search
        await activity_service.search_activities(request)

        # Verify all activity types were searched
        expected_calls = len(list(ActivityType))
        assert mock_google_maps_service.places_nearby_search.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_get_activity_service_singleton(self):
        """Test that get_activity_service returns singleton instance."""
        service1 = await get_activity_service()
        service2 = await get_activity_service()
        
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_activity_type_mapping(self, activity_service):
        """Test activity type mapping from Google types."""
        test_cases = [
            (["museum"], ActivityType.MUSEUM),
            (["park"], ActivityType.PARK),
            (["restaurant", "food"], ActivityType.RESTAURANT),
            (["night_club", "bar"], ActivityType.NIGHTLIFE),
            (["shopping_mall"], ActivityType.SHOPPING),
            (["tourist_attraction"], ActivityType.TOUR),
            (["gym", "stadium"], ActivityType.OUTDOOR),
            (["art_gallery"], ActivityType.CULTURAL),
            (["unknown_type"], ActivityType.TOUR),  # Default
        ]
        
        for google_types, expected_type in test_cases:
            result_type = activity_service._map_activity_type(google_types)
            assert result_type == expected_type

    @pytest.mark.asyncio
    async def test_search_activities_error_handling(
        self,
        activity_service,
        mock_google_maps_service,
        sample_search_request,
        sample_geocode_response,
    ):
        """Test error handling during activity search."""
        # Setup mocks
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.places_nearby_search.side_effect = Exception("API Error")

        # Perform search - should not raise exception
        response = await activity_service.search_activities(sample_search_request)

        # Should return empty results on error
        assert len(response.activities) == 0
        assert response.total_results == 0

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, activity_service):
        """Test cache key generation for different requests."""
        request1 = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 1, 15),
            adults=2,
            activity_types=[ActivityType.MUSEUM],
        )
        
        request2 = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 1, 15),
            adults=2,
            activity_types=[ActivityType.PARK],
        )
        
        key1 = activity_service.get_cache_fields(request1)
        key2 = activity_service.get_cache_fields(request2)
        
        # Keys should be different due to different activity types
        assert key1 != key2
        assert key1["activity_types"] == ["museum"]
        assert key2["activity_types"] == ["park"]