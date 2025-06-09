"""
Comprehensive tests for ActivityService with full coverage.

Tests cover:
- Google Maps Places API integration
- Activity search functionality
- Place details retrieval
- Caching behavior
- Error handling
- Input validation
- Response formatting
- Category mapping
- Price and duration estimation
"""

import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict, Any
import hashlib
import json

import pytest
from pydantic import ValidationError

from tripsage_core.services.business.activity_service import (
    ActivityService,
    ActivityServiceError,
)
from tripsage_core.services.external_apis.google_maps_service import GoogleMapsServiceError
from tripsage.api.schemas.requests.activities import ActivitySearchRequest
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
    ActivityCoordinates,
)


class TestActivityService:
    """Test ActivityService class."""

    @pytest.fixture
    def mock_google_maps_service(self):
        """Create mock Google Maps service."""
        mock = AsyncMock()
        mock.geocode = AsyncMock()
        mock.search_places = AsyncMock()
        mock.get_place_details = AsyncMock()
        return mock

    @pytest.fixture
    def mock_cache_service(self):
        """Create mock cache service."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        return mock

    @pytest.fixture
    def activity_service(self, mock_google_maps_service, mock_cache_service):
        """Create ActivityService instance with mocked dependencies."""
        return ActivityService(
            google_maps_service=mock_google_maps_service,
            cache_service=mock_cache_service
        )

    @pytest.fixture
    def sample_search_request(self):
        """Create sample search request."""
        return ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            categories=["cultural", "entertainment"],
            price_range=(0, 100),
            rating=4.0,
            duration=180,
            wheelchair_accessible=True,
            instant_confirmation=False
        )

    @pytest.fixture
    def sample_geocode_response(self):
        """Create sample geocode response."""
        return {
            "lat": 40.7128,
            "lng": -74.0060
        }

    @pytest.fixture
    def sample_places_response(self):
        """Create sample places search response."""
        return [
            {
                "place_id": "gmp_museum123",
                "name": "Metropolitan Museum of Art",
                "types": ["museum", "tourist_attraction", "point_of_interest"],
                "formatted_address": "1000 5th Ave, New York, NY 10028",
                "geometry": {
                    "location": {
                        "lat": 40.7794,
                        "lng": -73.9632
                    }
                },
                "rating": 4.6,
                "user_ratings_total": 85432,
                "price_level": 2,
                "opening_hours": {
                    "open_now": True,
                    "weekday_text": [
                        "Monday: 10:00 AM – 5:00 PM",
                        "Tuesday: 10:00 AM – 5:00 PM",
                        "Wednesday: 10:00 AM – 5:00 PM",
                        "Thursday: 10:00 AM – 5:00 PM",
                        "Friday: 10:00 AM – 9:00 PM",
                        "Saturday: 10:00 AM – 9:00 PM",
                        "Sunday: 10:00 AM – 5:00 PM"
                    ]
                },
                "photos": [
                    {"photo_reference": "photo123"}
                ]
            },
            {
                "place_id": "gmp_theater456",
                "name": "Broadway Theatre",
                "types": ["performing_arts_theater", "point_of_interest"],
                "formatted_address": "1681 Broadway, New York, NY 10019",
                "geometry": {
                    "location": {
                        "lat": 40.7631,
                        "lng": -73.9829
                    }
                },
                "rating": 4.5,
                "user_ratings_total": 12543,
                "price_level": 3,
                "opening_hours": {
                    "open_now": False
                }
            }
        ]

    @pytest.fixture
    def sample_place_details(self):
        """Create sample place details response."""
        return {
            "place_id": "gmp_museum123",
            "name": "Metropolitan Museum of Art",
            "types": ["museum", "tourist_attraction", "point_of_interest"],
            "formatted_address": "1000 5th Ave, New York, NY 10028",
            "geometry": {
                "location": {
                    "lat": 40.7794,
                    "lng": -73.9632
                }
            },
            "rating": 4.6,
            "user_ratings_total": 85432,
            "price_level": 2,
            "opening_hours": {
                "open_now": True,
                "weekday_text": [
                    "Monday: 10:00 AM – 5:00 PM",
                    "Tuesday: 10:00 AM – 5:00 PM",
                    "Wednesday: 10:00 AM – 5:00 PM",
                    "Thursday: 10:00 AM – 5:00 PM",
                    "Friday: 10:00 AM – 9:00 PM",
                    "Saturday: 10:00 AM – 9:00 PM",
                    "Sunday: 10:00 AM – 5:00 PM"
                ]
            },
            "photos": [
                {"photo_reference": "photo123"},
                {"photo_reference": "photo456"}
            ],
            "website": "https://www.metmuseum.org",
            "formatted_phone_number": "(212) 535-7710",
            "wheelchair_accessible_entrance": True,
            "editorial_summary": {
                "overview": "One of the world's largest and most comprehensive art museums."
            },
            "reviews": [
                {
                    "rating": 5,
                    "text": "Amazing collection!",
                    "time": 1704153600
                }
            ]
        }

    async def test_search_activities_success(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_search_request,
        sample_geocode_response,
        sample_places_response
    ):
        """Test successful activity search."""
        # Setup mocks
        mock_cache_service.get.return_value = None  # Cache miss
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = sample_places_response

        # Execute search
        result = await activity_service.search_activities(sample_search_request)

        # Verify result
        assert isinstance(result, ActivitySearchResponse)
        assert result.total == 2
        assert len(result.activities) == 2
        assert result.activities[0].name == "Metropolitan Museum of Art"
        assert result.activities[0].type == "cultural"
        assert result.activities[0].rating == 4.6
        assert result.activities[0].wheelchair_accessible is True
        assert result.activities[1].name == "Broadway Theatre"
        assert result.activities[1].type == "entertainment"
        assert not result.cached

        # Verify mock calls
        mock_google_maps_service.geocode.assert_called_once_with("New York, NY")
        assert mock_google_maps_service.search_places.call_count == 2  # One for each category
        mock_cache_service.set.assert_called_once()

    async def test_search_activities_with_cache_hit(
        self,
        activity_service,
        mock_cache_service,
        sample_search_request
    ):
        """Test activity search with cache hit."""
        # Setup cached response
        cached_response = {
            "activities": [
                {
                    "id": "cached_123",
                    "name": "Cached Activity",
                    "type": "cultural",
                    "location": "Cached Location",
                    "date": sample_search_request.start_date.isoformat(),
                    "duration": 120,
                    "price": 50.0,
                    "rating": 4.5,
                    "description": "Cached description",
                    "provider": "Google Maps",
                    "coordinates": {"lat": 40.7, "lng": -74.0},
                    "images": [],
                    "availability": "Open",
                    "wheelchair_accessible": False,
                    "instant_confirmation": False
                }
            ],
            "total": 1,
            "skip": 0,
            "limit": 20,
            "search_id": "cached_search",
            "filters_applied": {},
            "cached": True
        }
        
        mock_cache_service.get.return_value = cached_response

        # Execute search
        result = await activity_service.search_activities(sample_search_request)

        # Verify cached result
        assert result.cached is True
        assert result.total == 1
        assert result.activities[0].name == "Cached Activity"

        # Verify no API calls were made
        activity_service.google_maps_service.geocode.assert_not_called()
        activity_service.google_maps_service.search_places.assert_not_called()

    async def test_search_activities_filter_by_categories(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response,
        sample_places_response
    ):
        """Test activity search with category filtering."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = sample_places_response

        # Request with only cultural category
        request = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            categories=["cultural"]
        )

        # Execute search
        result = await activity_service.search_activities(request)

        # Verify only cultural activities returned
        assert result.total >= 1
        cultural_activities = [a for a in result.activities if a.type == "cultural"]
        assert len(cultural_activities) >= 1
        assert cultural_activities[0].name == "Metropolitan Museum of Art"

    async def test_search_activities_filter_by_rating(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response,
        sample_places_response
    ):
        """Test activity search with rating filter."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = sample_places_response

        # Request with high rating requirement
        request = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            rating=4.6
        )

        # Execute search
        result = await activity_service.search_activities(request)

        # Verify only high-rated activities returned
        high_rated = [a for a in result.activities if a.rating >= 4.6]
        assert len(high_rated) >= 1

    async def test_search_activities_geocode_error(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_search_request
    ):
        """Test activity search with geocoding error."""
        # Setup mock to raise error
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.side_effect = GoogleMapsServiceError("Geocoding failed")

        # Execute and verify error
        with pytest.raises(ActivityServiceError) as exc_info:
            await activity_service.search_activities(sample_search_request)
        
        assert "Failed to geocode destination" in str(exc_info.value)

    async def test_search_activities_places_api_error(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_search_request,
        sample_geocode_response
    ):
        """Test activity search with places API error."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.side_effect = GoogleMapsServiceError("API quota exceeded")

        # Execute and verify error
        with pytest.raises(ActivityServiceError) as exc_info:
            await activity_service.search_activities(sample_search_request)
        
        assert "Failed to search activities" in str(exc_info.value)

    async def test_search_activities_empty_results(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_search_request,
        sample_geocode_response
    ):
        """Test activity search with no results."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = []

        # Execute search
        result = await activity_service.search_activities(sample_search_request)

        # Verify empty result
        assert result.total == 0
        assert len(result.activities) == 0
        assert not result.cached

    async def test_get_activity_details_success(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_place_details
    ):
        """Test successful activity details retrieval."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = sample_place_details

        # Execute
        result = await activity_service.get_activity_details("gmp_museum123")

        # Verify result
        assert isinstance(result, ActivityResponse)
        assert result.id == "gmp_museum123"
        assert result.name == "Metropolitan Museum of Art"
        assert result.type == "cultural"
        assert result.wheelchair_accessible is True
        assert len(result.images) == 2
        assert result.languages == ["en"]  # Default language

        # Verify mock calls
        mock_google_maps_service.get_place_details.assert_called_once_with("gmp_museum123")
        mock_cache_service.set.assert_called_once()

    async def test_get_activity_details_with_cache(
        self,
        activity_service,
        mock_cache_service
    ):
        """Test activity details retrieval from cache."""
        # Setup cached details
        cached_details = {
            "id": "cached_123",
            "name": "Cached Museum",
            "type": "cultural",
            "location": "Cached Address",
            "date": "2025-07-15",
            "duration": 180,
            "price": 25.0,
            "rating": 4.7,
            "description": "Cached description",
            "provider": "Google Maps",
            "coordinates": {"lat": 40.7, "lng": -74.0},
            "images": [],
            "availability": "Open",
            "wheelchair_accessible": False,
            "instant_confirmation": False
        }
        
        mock_cache_service.get.return_value = cached_details

        # Execute
        result = await activity_service.get_activity_details("cached_123")

        # Verify cached result
        assert result.id == "cached_123"
        assert result.name == "Cached Museum"

        # Verify no API call was made
        activity_service.google_maps_service.get_place_details.assert_not_called()

    async def test_get_activity_details_not_found(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test activity details when not found."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = None

        # Execute
        result = await activity_service.get_activity_details("nonexistent_id")

        # Verify None returned
        assert result is None

    async def test_get_activity_details_api_error(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test activity details with API error."""
        # Setup mock to raise error
        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.side_effect = GoogleMapsServiceError("API error")

        # Execute and verify error
        with pytest.raises(ActivityServiceError) as exc_info:
            await activity_service.get_activity_details("error_id")
        
        assert "Failed to get activity details" in str(exc_info.value)

    async def test_category_mapping(self, activity_service):
        """Test Google Places type to category mapping."""
        # Test various place types
        test_cases = [
            (["museum", "art_gallery"], "cultural"),
            (["amusement_park", "zoo"], "adventure"),
            (["restaurant", "cafe"], "food"),
            (["night_club", "bar"], "entertainment"),
            (["park", "hiking_area"], "outdoor"),
            (["shopping_mall", "store"], "shopping"),
            (["spa", "gym"], "wellness"),
            (["school", "library"], "educational"),
            (["church", "mosque"], "religious"),
            (["unknown_type"], "other")
        ]

        for types, expected_category in test_cases:
            result = activity_service._map_place_type_to_category(types)
            assert result == expected_category

    async def test_price_estimation(self, activity_service):
        """Test price level to price estimation."""
        test_cases = [
            (None, 0.0),
            (0, 0.0),
            (1, 10.0),
            (2, 25.0),
            (3, 50.0),
            (4, 100.0),
            (5, 100.0)  # Should cap at 4
        ]

        for price_level, expected_price in test_cases:
            result = activity_service._estimate_price(price_level)
            assert result == expected_price

    async def test_duration_estimation(self, activity_service):
        """Test activity duration estimation."""
        test_cases = [
            (["museum"], 180),
            (["park"], 120),
            (["restaurant"], 90),
            (["amusement_park"], 240),
            (["shopping_mall"], 120),
            (["spa"], 120),
            (["night_club"], 180),
            (["unknown"], 120)  # Default
        ]

        for types, expected_duration in test_cases:
            result = activity_service._estimate_duration(types)
            assert result == expected_duration

    async def test_concurrent_searches(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response,
        sample_places_response
    ):
        """Test concurrent activity searches."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = sample_places_response

        # Create multiple search requests
        requests = [
            ActivitySearchRequest(
                destination=f"City {i}",
                start_date=date(2025, 7, i+1)
            )
            for i in range(5)
        ]

        # Execute concurrent searches
        results = await asyncio.gather(*[
            activity_service.search_activities(req) for req in requests
        ])

        # Verify all completed successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, ActivitySearchResponse)

    async def test_search_with_all_filters(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response
    ):
        """Test search with all possible filters applied."""
        # Create comprehensive search request
        request = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            end_date=date(2025, 7, 20),
            categories=["cultural", "entertainment"],
            price_range=(20, 80),
            rating=4.5,
            duration=150,
            wheelchair_accessible=True,
            instant_confirmation=True,
            group_size=4,
            language="en",
            skip=10,
            limit=50
        )

        # Setup mock with varied activities
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = [
            {
                "place_id": f"gmp_{i}",
                "name": f"Activity {i}",
                "types": ["museum" if i % 2 == 0 else "theater"],
                "formatted_address": f"{i} Test St",
                "geometry": {"location": {"lat": 40.7 + i*0.01, "lng": -74.0}},
                "rating": 4.0 + i*0.1,
                "price_level": i % 4,
                "opening_hours": {"open_now": True}
            }
            for i in range(20)
        ]

        # Execute search
        result = await activity_service.search_activities(request)

        # Verify filters were applied
        assert result.skip == 10
        assert result.limit == 50
        assert all(a.rating >= 4.5 for a in result.activities if a.rating)
        assert all(20 <= a.price <= 80 for a in result.activities if a.price)

    async def test_search_with_invalid_destination(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test search with destination that cannot be geocoded."""
        # Setup mock to return None for geocoding
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = None

        request = ActivitySearchRequest(
            destination="Invalid Location XYZ123",
            start_date=date(2025, 7, 15)
        )

        # Execute and verify error
        with pytest.raises(ActivityServiceError) as exc_info:
            await activity_service.search_activities(request)
        
        assert "Could not find location" in str(exc_info.value)

    async def test_cache_key_generation(self, activity_service):
        """Test cache key generation for different requests."""
        # Test that different requests generate different keys
        request1 = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            categories=["cultural"]
        )
        
        request2 = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            categories=["entertainment"]
        )
        
        key1 = activity_service._generate_cache_key("search", request1.model_dump())
        key2 = activity_service._generate_cache_key("search", request2.model_dump())
        
        assert key1 != key2
        assert key1.startswith("activity:search:")
        assert key2.startswith("activity:search:")

    async def test_cache_ttl_settings(
        self,
        activity_service,
        mock_cache_service,
        sample_search_request,
        sample_geocode_response,
        sample_places_response
    ):
        """Test cache TTL is set correctly."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service = activity_service.google_maps_service
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = sample_places_response

        # Execute search
        await activity_service.search_activities(sample_search_request)

        # Verify cache set was called with correct TTL
        mock_cache_service.set.assert_called_once()
        call_args = mock_cache_service.set.call_args
        assert call_args[1]['ttl'] == 3600  # 1 hour TTL

    async def test_error_handling_and_logging(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_search_request
    ):
        """Test comprehensive error handling and logging."""
        # Test various error scenarios
        error_scenarios = [
            (
                GoogleMapsServiceError("API quota exceeded"),
                "Failed to search activities"
            ),
            (
                ValueError("Invalid parameter"),
                "Failed to search activities"
            ),
            (
                ConnectionError("Network error"),
                "Failed to search activities"
            )
        ]

        for error, expected_message in error_scenarios:
            mock_cache_service.get.return_value = None
            mock_google_maps_service.geocode.return_value = {"lat": 40.7, "lng": -74.0}
            mock_google_maps_service.search_places.side_effect = error

            with pytest.raises(ActivityServiceError) as exc_info:
                await activity_service.search_activities(sample_search_request)
            
            assert expected_message in str(exc_info.value)

    async def test_filter_by_price_range(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response
    ):
        """Test filtering activities by price range."""
        # Setup mocks with varied price levels
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = [
            {
                "place_id": "cheap",
                "name": "Cheap Activity",
                "types": ["museum"],
                "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                "price_level": 1,  # $10
                "rating": 4.5
            },
            {
                "place_id": "expensive",
                "name": "Expensive Activity",
                "types": ["museum"],
                "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                "price_level": 4,  # $100
                "rating": 4.5
            }
        ]

        request = ActivitySearchRequest(
            destination="Test City",
            start_date=date(2025, 7, 15),
            price_range=(0, 50)
        )

        # Execute search
        result = await activity_service.search_activities(request)

        # Verify price filtering
        assert len(result.activities) == 1
        assert result.activities[0].name == "Cheap Activity"
        assert result.activities[0].price == 10.0

    async def test_filter_by_duration(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response
    ):
        """Test filtering activities by maximum duration."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = [
            {
                "place_id": "quick",
                "name": "Quick Visit",
                "types": ["cafe"],  # 90 min duration
                "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                "rating": 4.5
            },
            {
                "place_id": "long",
                "name": "All Day Activity",
                "types": ["amusement_park"],  # 240 min duration
                "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                "rating": 4.5
            }
        ]

        request = ActivitySearchRequest(
            destination="Test City",
            start_date=date(2025, 7, 15),
            duration=120  # Max 2 hours
        )

        # Execute search
        result = await activity_service.search_activities(request)

        # Verify duration filtering
        assert len(result.activities) == 1
        assert result.activities[0].name == "Quick Visit"
        assert result.activities[0].duration == 90

    async def test_search_without_categories(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service,
        sample_geocode_response,
        sample_places_response
    ):
        """Test search without specific categories (general search)."""
        # Setup mocks
        mock_cache_service.get.return_value = None
        mock_google_maps_service.geocode.return_value = sample_geocode_response
        mock_google_maps_service.search_places.return_value = sample_places_response

        request = ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15)
            # No categories specified
        )

        # Execute search
        result = await activity_service.search_activities(request)

        # Verify general search was performed
        assert result.total > 0
        # Should call search_places with generic types
        calls = mock_google_maps_service.search_places.call_args_list
        assert any("tourist_attraction" in str(call) for call in calls)

    async def test_place_details_with_missing_fields(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test place details with some missing fields."""
        # Minimal place details
        minimal_details = {
            "place_id": "gmp_minimal",
            "name": "Minimal Place",
            "types": ["establishment"]
        }

        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = minimal_details

        # Execute
        result = await activity_service.get_activity_details("gmp_minimal")

        # Verify defaults are applied
        assert result.name == "Minimal Place"
        assert result.type == "other"
        assert result.rating == 0.0
        assert result.price == 0.0
        assert result.description == "A popular destination"
        assert result.availability == "Contact for hours"

    async def test_invalid_activity_id_format(
        self,
        activity_service,
        mock_cache_service
    ):
        """Test get_activity_details with non-Google Maps ID."""
        mock_cache_service.get.return_value = None

        # Non-Google Maps ID (doesn't start with 'gmp_')
        result = await activity_service.get_activity_details("custom_id_123")

        # Should return None for non-Google Maps IDs
        assert result is None
        activity_service.google_maps_service.get_place_details.assert_not_called()

    async def test_wheelchair_accessibility_mapping(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test wheelchair accessibility is properly mapped."""
        # Place with accessibility info
        accessible_place = {
            "place_id": "gmp_accessible",
            "name": "Accessible Museum",
            "types": ["museum"],
            "wheelchair_accessible_entrance": True,
            "geometry": {"location": {"lat": 40.7, "lng": -74.0}}
        }

        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = accessible_place

        # Execute
        result = await activity_service.get_activity_details("gmp_accessible")

        # Verify accessibility
        assert result.wheelchair_accessible is True

    async def test_activity_images_mapping(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test activity images are properly mapped."""
        # Place with photos
        place_with_photos = {
            "place_id": "gmp_photos",
            "name": "Photogenic Place",
            "types": ["tourist_attraction"],
            "photos": [
                {"photo_reference": "ref1", "width": 1024},
                {"photo_reference": "ref2", "width": 768}
            ],
            "geometry": {"location": {"lat": 40.7, "lng": -74.0}}
        }

        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = place_with_photos

        # Execute
        result = await activity_service.get_activity_details("gmp_photos")

        # Verify images
        assert len(result.images) == 2
        assert all(img.startswith("https://maps.googleapis.com/maps/api/place/photo") for img in result.images)

    async def test_opening_hours_parsing(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test opening hours are properly parsed."""
        # Place with detailed opening hours
        place_with_hours = {
            "place_id": "gmp_hours",
            "name": "Museum with Hours",
            "types": ["museum"],
            "opening_hours": {
                "open_now": True,
                "weekday_text": [
                    "Monday: 9:00 AM – 5:00 PM",
                    "Tuesday: 9:00 AM – 5:00 PM",
                    "Wednesday: 9:00 AM – 8:00 PM",
                    "Thursday: 9:00 AM – 5:00 PM",
                    "Friday: 9:00 AM – 5:00 PM",
                    "Saturday: 10:00 AM – 6:00 PM",
                    "Sunday: 10:00 AM – 6:00 PM"
                ]
            },
            "geometry": {"location": {"lat": 40.7, "lng": -74.0}}
        }

        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = place_with_hours

        # Execute
        result = await activity_service.get_activity_details("gmp_hours")

        # Verify availability
        assert result.availability == "Open now"
        assert result.meeting_point == "Main entrance"

    async def test_reviews_aggregation(
        self,
        activity_service,
        mock_google_maps_service,
        mock_cache_service
    ):
        """Test reviews are properly aggregated in description."""
        # Place with reviews
        place_with_reviews = {
            "place_id": "gmp_reviews",
            "name": "Reviewed Place",
            "types": ["restaurant"],
            "reviews": [
                {"text": "Great food and atmosphere!", "rating": 5},
                {"text": "Service was excellent.", "rating": 4},
                {"text": "A bit pricey but worth it.", "rating": 4}
            ],
            "editorial_summary": {"overview": "Popular dining spot"},
            "geometry": {"location": {"lat": 40.7, "lng": -74.0}}
        }

        mock_cache_service.get.return_value = None
        mock_google_maps_service.get_place_details.return_value = place_with_reviews

        # Execute
        result = await activity_service.get_activity_details("gmp_reviews")

        # Verify reviews in description
        assert "Popular dining spot" in result.description
        assert "Great food and atmosphere!" in result.description
        assert "Service was excellent." in result.description