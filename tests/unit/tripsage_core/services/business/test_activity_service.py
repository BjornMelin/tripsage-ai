"""
Comprehensive tests for ActivityService.

Tests cover:
- Activity search functionality with Google Maps integration
- Error handling and edge cases
- Caching and performance
- Activity filtering and sorting
- Activity details retrieval
- Price estimation and duration calculation
- Activity type mapping and categorization
"""

import asyncio
import uuid
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional

import pytest
from pytest import raises

# Mock the problematic import before importing the service
with patch.dict('sys.modules', {'agents': MagicMock()}):
    pass

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
    SaveActivityRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityCoordinates,
    ActivityResponse,
    ActivitySearchResponse,
    SavedActivityResponse,
)
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.business.activity_service import (
    ActivityService,
    ActivityServiceError,
    ACTIVITY_TYPE_MAPPING,
    get_activity_service,
    close_activity_service,
)
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsServiceError,
)


class TestActivityServiceError:
    """Test ActivityServiceError exception."""

    def test_activity_service_error_with_message_only(self):
        """Test creating ActivityServiceError with message only."""
        error = ActivityServiceError("Test error message")
        
        assert error.message == "Test error message"
        assert error.code == "ACTIVITY_SERVICE_ERROR"
        assert error.service == "ActivityService"
        assert error.details == {"original_error": None}
        assert error.original_error is None

    def test_activity_service_error_with_original_error(self):
        """Test creating ActivityServiceError with original error."""
        original_error = ValueError("Original error")
        error = ActivityServiceError("Test error message", original_error)
        
        assert error.message == "Test error message"
        assert error.code == "ACTIVITY_SERVICE_ERROR"
        assert error.service == "ActivityService"
        assert error.details == {"original_error": "Original error"}
        assert error.original_error == original_error

    def test_activity_service_error_inheritance(self):
        """Test that ActivityServiceError inherits from CoreServiceError."""
        error = ActivityServiceError("Test error")
        assert isinstance(error, CoreServiceError)


class TestActivityService:
    """Test ActivityService class."""

    @pytest.fixture
    def mock_google_maps_service(self):
        """Create mock Google Maps service."""
        mock_service = AsyncMock()
        mock_service.geocode.return_value = [
            {
                "geometry": {
                    "location": {"lat": 40.7128, "lng": -74.0060}
                },
                "formatted_address": "New York, NY, USA"
            }
        ]
        mock_service.search_places.return_value = {
            "results": [
                {
                    "place_id": "test_place_id",
                    "name": "Test Activity",
                    "geometry": {
                        "location": {"lat": 40.7128, "lng": -74.0060}
                    },
                    "rating": 4.5,
                    "price_level": 2,
                    "types": ["tourist_attraction"],
                    "vicinity": "New York, NY"
                }
            ]
        }
        mock_service.get_place_details.return_value = {
            "result": {
                "place_id": "test_place_id",
                "name": "Test Activity Details",
                "formatted_address": "123 Test St, New York, NY",
                "geometry": {
                    "location": {"lat": 40.7128, "lng": -74.0060}
                },
                "rating": 4.8,
                "price_level": 3,
                "types": ["museum", "tourist_attraction"],
                "opening_hours": {"open_now": True},
                "reviews": [
                    {"text": "Great place to visit with lots of interesting exhibits!"}
                ],
                "website": "https://test-activity.com",
                "formatted_phone_number": "(555) 123-4567"
            }
        }
        return mock_service

    @pytest.fixture
    def mock_cache_service(self):
        """Create mock cache service."""
        return AsyncMock()

    @pytest.fixture
    def mock_web_search_tool(self):
        """Create mock web search tool."""
        return MagicMock()

    @pytest.fixture
    def activity_service(self, mock_google_maps_service, mock_cache_service):
        """Create ActivityService instance with mocked dependencies."""
        service = ActivityService(
            google_maps_service=mock_google_maps_service,
            cache_service=mock_cache_service
        )
        return service

    @pytest.fixture
    def sample_activity_request(self):
        """Create sample activity search request."""
        return ActivitySearchRequest(
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            categories=["cultural", "entertainment"],
            rating=4.0,
            duration=180,  # 3 hours
            wheelchair_accessible=False
        )

    async def test_init_with_dependencies(self, mock_google_maps_service, mock_cache_service):
        """Test ActivityService initialization with dependencies."""
        service = ActivityService(
            google_maps_service=mock_google_maps_service,
            cache_service=mock_cache_service
        )
        
        assert service.google_maps_service == mock_google_maps_service
        assert service.cache_service == mock_cache_service
        assert service.web_search_tool is not None

    async def test_init_without_dependencies(self):
        """Test ActivityService initialization without dependencies."""
        service = ActivityService()
        
        assert service.google_maps_service is None
        assert service.cache_service is None
        assert service.web_search_tool is not None

    async def test_ensure_services_with_none_services(self):
        """Test ensure_services when services are None."""
        service = ActivityService()
        
        with patch('tripsage_core.services.business.activity_service.get_google_maps_service') as mock_get_gms, \
             patch('tripsage_core.services.business.activity_service.get_cache_service') as mock_get_cs:
            
            mock_google_maps = AsyncMock()
            mock_cache = AsyncMock()
            mock_get_gms.return_value = mock_google_maps
            mock_get_cs.return_value = mock_cache
            
            await service.ensure_services()
            
            assert service.google_maps_service == mock_google_maps
            assert service.cache_service == mock_cache
            mock_get_gms.assert_called_once()
            mock_get_cs.assert_called_once()

    async def test_ensure_services_with_existing_services(self, activity_service):
        """Test ensure_services when services already exist."""
        original_gms = activity_service.google_maps_service
        original_cs = activity_service.cache_service
        
        with patch('tripsage_core.services.business.activity_service.get_google_maps_service') as mock_get_gms, \
             patch('tripsage_core.services.business.activity_service.get_cache_service') as mock_get_cs:
            
            await activity_service.ensure_services()
            
            # Services should remain unchanged
            assert activity_service.google_maps_service == original_gms
            assert activity_service.cache_service == original_cs
            mock_get_gms.assert_not_called()
            mock_get_cs.assert_not_called()

    async def test_search_activities_success(self, activity_service, sample_activity_request):
        """Test successful activity search."""
        # Mock the decorators to avoid caching and error handling interference
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            result = await activity_service.search_activities(sample_activity_request)
            
            assert isinstance(result, ActivitySearchResponse)
            assert len(result.activities) > 0
            assert result.total > 0
            assert result.search_id is not None
            assert result.filters_applied["destination"] == "New York, NY"
            
            # Check first activity
            activity = result.activities[0]
            assert activity.name == "Test Activity"
            assert activity.type in ACTIVITY_TYPE_MAPPING.keys()
            assert activity.rating == 4.5
            assert activity.coordinates is not None
            assert activity.coordinates.lat == 40.7128
            assert activity.coordinates.lng == -74.0060

    async def test_search_activities_no_geocoding_results(self, activity_service, sample_activity_request):
        """Test activity search when geocoding returns no results."""
        activity_service.google_maps_service.geocode.return_value = []
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            result = await activity_service.search_activities(sample_activity_request)
            
            assert isinstance(result, ActivitySearchResponse)
            assert len(result.activities) == 0
            assert result.total == 0
            assert result.filters_applied["destination"] == "New York, NY"

    async def test_search_activities_geocoding_error(self, activity_service, sample_activity_request):
        """Test activity search when geocoding fails."""
        activity_service.google_maps_service.geocode.side_effect = GoogleMapsServiceError("Geocoding failed")
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            with raises(ActivityServiceError) as exc_info:
                await activity_service.search_activities(sample_activity_request)
            
            assert "Maps API error" in str(exc_info.value)
            assert isinstance(exc_info.value.original_error, GoogleMapsServiceError)

    async def test_search_activities_places_search_error(self, activity_service, sample_activity_request):
        """Test activity search when places search fails."""
        activity_service.google_maps_service.search_places.side_effect = Exception("Places search failed")
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            with raises(ActivityServiceError) as exc_info:
                await activity_service.search_activities(sample_activity_request)
            
            assert "Activity search failed" in str(exc_info.value)

    async def test_search_activities_with_categories(self, activity_service):
        """Test activity search with specific categories."""
        request = ActivitySearchRequest(
            destination="Paris, France",
            start_date=date(2025, 8, 1),
            categories=["cultural", "food"]
        )
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            result = await activity_service.search_activities(request)
            
            assert isinstance(result, ActivitySearchResponse)
            # Should call search_places for each category type
            assert activity_service.google_maps_service.search_places.call_count >= 2

    async def test_search_activities_general_search(self, activity_service):
        """Test activity search without specific categories (general search)."""
        request = ActivitySearchRequest(
            destination="Tokyo, Japan",
            start_date=date(2025, 9, 1),
            categories=[]  # No specific categories
        )
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            result = await activity_service.search_activities(request)
            
            assert isinstance(result, ActivitySearchResponse)
            # Should perform general search
            activity_service.google_maps_service.search_places.assert_called()

    async def test_search_places_by_type_success(self, activity_service, sample_activity_request):
        """Test _search_places_by_type method."""
        location = (40.7128, -74.0060)
        place_type = "museum"
        radius = 10000
        
        result = await activity_service._search_places_by_type(
            location, place_type, radius, sample_activity_request
        )
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], ActivityResponse)

    async def test_search_places_by_type_error(self, activity_service, sample_activity_request):
        """Test _search_places_by_type with API error."""
        activity_service.google_maps_service.search_places.side_effect = Exception("API Error")
        
        location = (40.7128, -74.0060)
        place_type = "museum"
        radius = 10000
        
        result = await activity_service._search_places_by_type(
            location, place_type, radius, sample_activity_request
        )
        
        # Should return empty list on error
        assert result == []

    async def test_convert_place_to_activity_success(self, activity_service, sample_activity_request):
        """Test _convert_place_to_activity method."""
        place = {
            "place_id": "test_id",
            "name": "Test Museum",
            "geometry": {
                "location": {"lat": 40.7128, "lng": -74.0060}
            },
            "rating": 4.2,
            "price_level": 1,
            "types": ["museum", "tourist_attraction"],
            "vicinity": "Manhattan, NY"
        }
        
        result = await activity_service._convert_place_to_activity(place, sample_activity_request)
        
        assert isinstance(result, ActivityResponse)
        assert result.name == "Test Museum"
        assert result.type == "cultural"  # Museum maps to cultural
        assert result.rating == 4.2
        assert result.coordinates.lat == 40.7128
        assert result.coordinates.lng == -74.0060
        assert result.id.startswith("gmp_")

    async def test_convert_place_to_activity_minimal_data(self, activity_service, sample_activity_request):
        """Test _convert_place_to_activity with minimal place data."""
        place = {
            "name": "Minimal Place",
            "types": ["establishment"]
        }
        
        result = await activity_service._convert_place_to_activity(place, sample_activity_request)
        
        assert isinstance(result, ActivityResponse)
        assert result.name == "Minimal Place"
        assert result.type == "entertainment"  # Default type
        assert result.rating == 0.0
        assert result.coordinates is None

    async def test_convert_place_to_activity_error(self, activity_service, sample_activity_request):
        """Test _convert_place_to_activity with invalid data."""
        place = None  # Invalid place data
        
        with raises(Exception):
            await activity_service._convert_place_to_activity(place, sample_activity_request)

    def test_get_place_types_for_categories(self, activity_service):
        """Test _get_place_types_for_categories method."""
        categories = ["cultural", "food", "nature"]
        
        result = activity_service._get_place_types_for_categories(categories)
        
        assert isinstance(result, list)
        assert "museum" in result  # From cultural
        assert "restaurant" in result  # From food
        assert "park" in result  # From nature
        assert len(set(result)) == len(result)  # No duplicates

    def test_get_place_types_for_empty_categories(self, activity_service):
        """Test _get_place_types_for_categories with empty categories."""
        result = activity_service._get_place_types_for_categories([])
        assert result == []

    def test_get_place_types_for_unknown_categories(self, activity_service):
        """Test _get_place_types_for_categories with unknown categories."""
        result = activity_service._get_place_types_for_categories(["unknown", "invalid"])
        assert result == []

    def test_determine_activity_type_from_mapping(self, activity_service):
        """Test _determine_activity_type with types in mapping."""
        place_types = ["museum", "art_gallery"]
        result = activity_service._determine_activity_type(place_types)
        assert result == "cultural"

    def test_determine_activity_type_fallback_restaurant(self, activity_service):
        """Test _determine_activity_type fallback for restaurant."""
        place_types = ["restaurant", "establishment"]
        result = activity_service._determine_activity_type(place_types)
        assert result == "food"

    def test_determine_activity_type_fallback_tourist_attraction(self, activity_service):
        """Test _determine_activity_type fallback for tourist attraction."""
        place_types = ["tourist_attraction", "establishment"]
        result = activity_service._determine_activity_type(place_types)
        assert result == "tour"

    def test_determine_activity_type_fallback_museum(self, activity_service):
        """Test _determine_activity_type fallback for museum."""
        place_types = ["museum", "establishment"]
        result = activity_service._determine_activity_type(place_types)
        assert result == "cultural"

    def test_determine_activity_type_fallback_park(self, activity_service):
        """Test _determine_activity_type fallback for park."""
        place_types = ["park", "establishment"]
        result = activity_service._determine_activity_type(place_types)
        assert result == "nature"

    def test_determine_activity_type_default(self, activity_service):
        """Test _determine_activity_type default case."""
        place_types = ["establishment", "unknown_type"]
        result = activity_service._determine_activity_type(place_types)
        assert result == "entertainment"

    def test_estimate_price_from_level_various_types(self, activity_service):
        """Test _estimate_price_from_level for various activity types."""
        # Test different activity types and price levels
        assert activity_service._estimate_price_from_level(0, "religious") == 0.0
        assert activity_service._estimate_price_from_level(1, "nature") == 10.0
        assert activity_service._estimate_price_from_level(2, "cultural") == 22.5  # 15.0 * 1.5
        assert activity_service._estimate_price_from_level(3, "adventure") == 125.0  # 50.0 * 2.5
        assert activity_service._estimate_price_from_level(4, "wellness") == 240.0  # 60.0 * 4.0

    def test_estimate_price_from_level_unknown_type(self, activity_service):
        """Test _estimate_price_from_level for unknown activity type."""
        result = activity_service._estimate_price_from_level(2, "unknown_type")
        assert result == 37.5  # 25.0 (default) * 1.5

    def test_estimate_price_from_level_invalid_level(self, activity_service):
        """Test _estimate_price_from_level with invalid price level."""
        result = activity_service._estimate_price_from_level(10, "cultural")  # Level > 4
        assert result == 60.0  # 15.0 * 4.0 (capped at max multiplier)

    def test_estimate_duration_various_types(self, activity_service):
        """Test _estimate_duration for various activity types."""
        assert activity_service._estimate_duration("adventure", []) == 240
        assert activity_service._estimate_duration("cultural", []) == 120
        assert activity_service._estimate_duration("food", []) == 90
        assert activity_service._estimate_duration("religious", []) == 60

    def test_estimate_duration_unknown_type(self, activity_service):
        """Test _estimate_duration for unknown activity type."""
        result = activity_service._estimate_duration("unknown_type", [])
        assert result == 120  # Default duration

    def test_apply_filters_rating(self, activity_service):
        """Test _apply_filters with rating filter."""
        activities = [
            ActivityResponse(
                id="1", name="High Rated", type="cultural", location="Test",
                date="2025-07-15", duration=120, price=20.0, rating=4.5,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            ),
            ActivityResponse(
                id="2", name="Low Rated", type="cultural", location="Test",
                date="2025-07-15", duration=120, price=20.0, rating=3.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            )
        ]
        
        request = ActivitySearchRequest(
            destination="Test",
            start_date=date(2025, 7, 15),
            rating=4.0
        )
        
        result = activity_service._apply_filters(activities, request)
        
        assert len(result) == 1
        assert result[0].name == "High Rated"

    def test_apply_filters_price_range(self, activity_service):
        """Test _apply_filters with price range filter."""
        from tripsage.api.schemas.requests.activities import PriceRange
        
        activities = [
            ActivityResponse(
                id="1", name="Expensive", type="cultural", location="Test",
                date="2025-07-15", duration=120, price=100.0, rating=4.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            ),
            ActivityResponse(
                id="2", name="Affordable", type="cultural", location="Test",
                date="2025-07-15", duration=120, price=25.0, rating=4.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            )
        ]
        
        request = ActivitySearchRequest(
            destination="Test",
            start_date=date(2025, 7, 15),
            price_range=PriceRange(min=20.0, max=50.0)
        )
        
        result = activity_service._apply_filters(activities, request)
        
        assert len(result) == 1
        assert result[0].name == "Affordable"

    def test_apply_filters_duration(self, activity_service):
        """Test _apply_filters with duration filter."""
        activities = [
            ActivityResponse(
                id="1", name="Long Activity", type="cultural", location="Test",
                date="2025-07-15", duration=300, price=20.0, rating=4.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            ),
            ActivityResponse(
                id="2", name="Short Activity", type="cultural", location="Test",
                date="2025-07-15", duration=60, price=20.0, rating=4.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            )
        ]
        
        request = ActivitySearchRequest(
            destination="Test",
            start_date=date(2025, 7, 15),
            duration=120
        )
        
        result = activity_service._apply_filters(activities, request)
        
        assert len(result) == 1
        assert result[0].name == "Short Activity"

    def test_apply_filters_wheelchair_accessible(self, activity_service):
        """Test _apply_filters with wheelchair accessibility filter."""
        activities = [
            ActivityResponse(
                id="1", name="Accessible", type="cultural", location="Test",
                date="2025-07-15", duration=120, price=20.0, rating=4.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=True,
                instant_confirmation=False
            ),
            ActivityResponse(
                id="2", name="Not Accessible", type="cultural", location="Test",
                date="2025-07-15", duration=120, price=20.0, rating=4.0,
                description="Test", images=[], provider="Test",
                availability="Test", wheelchair_accessible=False,
                instant_confirmation=False
            )
        ]
        
        request = ActivitySearchRequest(
            destination="Test",
            start_date=date(2025, 7, 15),
            wheelchair_accessible=True
        )
        
        result = activity_service._apply_filters(activities, request)
        
        assert len(result) == 1
        assert result[0].name == "Accessible"

    async def test_get_activity_details_success(self, activity_service):
        """Test successful get_activity_details."""
        activity_id = "gmp_test_place_id"
        
        with patch('tripsage_core.services.business.activity_service.with_error_handling'):
            result = await activity_service.get_activity_details(activity_id)
            
            assert isinstance(result, ActivityResponse)
            assert result.name == "Test Activity Details"
            assert result.type == "cultural"  # Museum maps to cultural
            assert result.rating == 4.8
            assert result.availability == "Open now"
            assert "Great place to visit" in result.description

    async def test_get_activity_details_non_google_maps_id(self, activity_service):
        """Test get_activity_details with non-Google Maps ID."""
        activity_id = "custom_activity_123"
        
        with patch('tripsage_core.services.business.activity_service.with_error_handling'):
            result = await activity_service.get_activity_details(activity_id)
            
            assert result is None

    async def test_get_activity_details_place_not_found(self, activity_service):
        """Test get_activity_details when place is not found."""
        activity_service.google_maps_service.get_place_details.return_value = {"result": None}
        activity_id = "gmp_nonexistent"
        
        with patch('tripsage_core.services.business.activity_service.with_error_handling'):
            result = await activity_service.get_activity_details(activity_id)
            
            assert result is None

    async def test_get_activity_details_google_maps_error(self, activity_service):
        """Test get_activity_details with Google Maps API error."""
        activity_service.google_maps_service.get_place_details.side_effect = GoogleMapsServiceError("API Error")
        activity_id = "gmp_test_place_id"
        
        with patch('tripsage_core.services.business.activity_service.with_error_handling'):
            with raises(ActivityServiceError) as exc_info:
                await activity_service.get_activity_details(activity_id)
            
            assert "Maps API error" in str(exc_info.value)

    async def test_get_activity_details_unexpected_error(self, activity_service):
        """Test get_activity_details with unexpected error."""
        activity_service.google_maps_service.get_place_details.side_effect = Exception("Unexpected error")
        activity_id = "gmp_test_place_id"
        
        with patch('tripsage_core.services.business.activity_service.with_error_handling'):
            with raises(ActivityServiceError) as exc_info:
                await activity_service.get_activity_details(activity_id)
            
            assert "Failed to get activity details" in str(exc_info.value)

    async def test_convert_detailed_place_to_activity_full_data(self, activity_service):
        """Test _convert_detailed_place_to_activity with full place data."""
        place = {
            "name": "Detailed Museum",
            "formatted_address": "456 Museum Ave, New York, NY",
            "geometry": {
                "location": {"lat": 40.7829, "lng": -73.9654}
            },
            "rating": 4.7,
            "price_level": 2,
            "types": ["museum", "art_gallery"],
            "opening_hours": {"open_now": False},
            "reviews": [
                {"text": "Amazing collection of artwork and historical artifacts!"}
            ],
            "website": "https://detailed-museum.org",
            "formatted_phone_number": "(212) 555-0123"
        }
        activity_id = "gmp_detailed_test"
        
        result = await activity_service._convert_detailed_place_to_activity(place, activity_id)
        
        assert isinstance(result, ActivityResponse)
        assert result.name == "Detailed Museum"
        assert result.location == "456 Museum Ave, New York, NY"
        assert result.type == "cultural"
        assert result.rating == 4.7
        assert result.availability == "Currently closed"
        assert "Amazing collection" in result.description

    async def test_convert_detailed_place_to_activity_minimal_data(self, activity_service):
        """Test _convert_detailed_place_to_activity with minimal place data."""
        place = {
            "name": "Simple Place",
            "types": ["establishment"]
        }
        activity_id = "gmp_simple"
        
        result = await activity_service._convert_detailed_place_to_activity(place, activity_id)
        
        assert isinstance(result, ActivityResponse)
        assert result.name == "Simple Place"
        assert result.type == "entertainment"
        assert result.availability == "Contact venue"
        assert result.description == "Popular entertainment"


class TestGlobalServiceFunctions:
    """Test global service management functions."""

    async def test_get_activity_service_new_instance(self):
        """Test get_activity_service creates new instance."""
        # Ensure no existing instance
        await close_activity_service()
        
        with patch('tripsage_core.services.business.activity_service.ActivityService') as MockService:
            mock_instance = AsyncMock()
            MockService.return_value = mock_instance
            
            result = await get_activity_service()
            
            assert result == mock_instance
            MockService.assert_called_once()
            mock_instance.ensure_services.assert_called_once()

    async def test_get_activity_service_existing_instance(self):
        """Test get_activity_service returns existing instance."""
        # First call to create instance
        await close_activity_service()
        
        with patch('tripsage_core.services.business.activity_service.ActivityService') as MockService:
            mock_instance = AsyncMock()
            MockService.return_value = mock_instance
            
            result1 = await get_activity_service()
            result2 = await get_activity_service()
            
            assert result1 == result2 == mock_instance
            MockService.assert_called_once()  # Only called once
            mock_instance.ensure_services.assert_called_once()  # Only called once

    async def test_close_activity_service(self):
        """Test close_activity_service."""
        # Create an instance first
        await get_activity_service()
        
        # Close it
        await close_activity_service()
        
        # Next call should create a new instance
        with patch('tripsage_core.services.business.activity_service.ActivityService') as MockService:
            mock_instance = AsyncMock()
            MockService.return_value = mock_instance
            
            result = await get_activity_service()
            
            assert result == mock_instance
            MockService.assert_called_once()


class TestActivityTypeMapping:
    """Test ACTIVITY_TYPE_MAPPING constant."""

    def test_activity_type_mapping_structure(self):
        """Test that ACTIVITY_TYPE_MAPPING has expected structure."""
        assert isinstance(ACTIVITY_TYPE_MAPPING, dict)
        assert len(ACTIVITY_TYPE_MAPPING) > 0
        
        for category, google_types in ACTIVITY_TYPE_MAPPING.items():
            assert isinstance(category, str)
            assert isinstance(google_types, list)
            assert len(google_types) > 0
            for google_type in google_types:
                assert isinstance(google_type, str)

    def test_activity_type_mapping_categories(self):
        """Test that expected categories exist in mapping."""
        expected_categories = [
            "adventure", "cultural", "entertainment", "food", "nature",
            "religious", "shopping", "sports", "tour", "wellness"
        ]
        
        for category in expected_categories:
            assert category in ACTIVITY_TYPE_MAPPING

    def test_activity_type_mapping_no_duplicates_in_category(self):
        """Test that each category has no duplicate Google types."""
        for category, google_types in ACTIVITY_TYPE_MAPPING.items():
            assert len(google_types) == len(set(google_types))


class TestAsyncBehavior:
    """Test async behavior and concurrency."""

    async def test_concurrent_activity_searches(self, activity_service):
        """Test concurrent activity searches."""
        requests = [
            ActivitySearchRequest(
                destination=f"City {i}",
                start_date=date(2025, 7, 15)
            )
            for i in range(3)
        ]
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            # Execute searches concurrently
            tasks = [activity_service.search_activities(req) for req in requests]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for result in results:
                assert isinstance(result, ActivitySearchResponse)

    async def test_concurrent_activity_details(self, activity_service):
        """Test concurrent activity details retrieval."""
        activity_ids = [f"gmp_test_{i}" for i in range(3)]
        
        with patch('tripsage_core.services.business.activity_service.with_error_handling'):
            # Execute details retrieval concurrently
            tasks = [activity_service.get_activity_details(aid) for aid in activity_ids]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for result in results:
                assert isinstance(result, ActivityResponse)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    async def test_empty_search_results(self, activity_service, sample_activity_request):
        """Test handling of empty search results."""
        activity_service.google_maps_service.search_places.return_value = {"results": []}
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            result = await activity_service.search_activities(sample_activity_request)
            
            assert isinstance(result, ActivitySearchResponse)
            assert len(result.activities) == 0
            assert result.total == 0

    async def test_malformed_geocoding_response(self, activity_service, sample_activity_request):
        """Test handling of malformed geocoding response."""
        activity_service.google_maps_service.geocode.return_value = [{}]  # Missing required fields
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            with raises(Exception):  # Should raise an error due to missing geometry
                await activity_service.search_activities(sample_activity_request)

    async def test_malformed_place_data(self, activity_service, sample_activity_request):
        """Test handling of malformed place data."""
        activity_service.google_maps_service.search_places.return_value = {
            "results": [{"invalid": "data"}]  # Missing required fields
        }
        
        with patch('tripsage_core.services.business.activity_service.cached'), \
             patch('tripsage_core.services.business.activity_service.with_error_handling'):
            
            result = await activity_service.search_activities(sample_activity_request)
            
            # Should handle gracefully and return empty results
            assert isinstance(result, ActivitySearchResponse)
            assert len(result.activities) == 0

    def test_invalid_price_level_negative(self, activity_service):
        """Test price estimation with negative price level."""
        result = activity_service._estimate_price_from_level(-1, "cultural")
        assert result == 0.0  # Should handle gracefully

    def test_none_categories(self, activity_service):
        """Test get_place_types_for_categories with None."""
        with raises(TypeError):  # Should raise TypeError when trying to iterate None
            activity_service._get_place_types_for_categories(None)

    def test_none_place_types(self, activity_service):
        """Test determine_activity_type with None."""
        with raises(TypeError):  # Should raise TypeError when trying to iterate None
            activity_service._determine_activity_type(None)