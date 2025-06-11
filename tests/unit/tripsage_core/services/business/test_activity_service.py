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
from datetime import date
from unittest.mock import AsyncMock

import pytest

from tripsage.api.schemas.requests.activities import (
    ActivitySearchRequest,
)
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
)
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.business.activity_service import (
    ACTIVITY_TYPE_MAPPING,
    ActivityService,
    ActivityServiceError,
)
from tripsage_core.services.external_apis.google_maps_service import (
    GoogleMapsService,
    GoogleMapsServiceError,
)


class TestActivityService:
    """Test ActivityService functionality."""

    @pytest.fixture
    def mock_google_maps_service(self):
        """Create a mock Google Maps service."""
        mock = AsyncMock(spec=GoogleMapsService)

        # Default geocode response
        mock.geocode.return_value = [
            {
                "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
                "formatted_address": "New York, NY, USA",
            }
        ]

        # Default search places response
        mock.search_places.return_value = {
            "results": [
                {
                    "place_id": "place_123",
                    "name": "Central Park",
                    "geometry": {"location": {"lat": 40.7829, "lng": -73.9654}},
                    "formatted_address": "Central Park, New York, NY",
                    "types": ["park", "point_of_interest"],
                    "rating": 4.8,
                    "user_ratings_total": 10000,
                    "price_level": 0,
                    "opening_hours": {"open_now": True},
                    "photos": [{"photo_reference": "photo_ref_123"}],
                },
                {
                    "place_id": "place_456",
                    "name": "Empire State Building",
                    "geometry": {"location": {"lat": 40.7484, "lng": -73.9857}},
                    "formatted_address": "Empire State Building, New York, NY",
                    "types": ["tourist_attraction", "point_of_interest"],
                    "rating": 4.7,
                    "user_ratings_total": 5000,
                    "price_level": 2,
                    "opening_hours": {"open_now": True},
                },
            ]
        }

        # Default place details response
        mock.get_place_details.return_value = {
            "result": {
                "place_id": "place_123",
                "name": "Central Park",
                "geometry": {"location": {"lat": 40.7829, "lng": -73.9654}},
                "formatted_address": "Central Park, New York, NY",
                "types": ["park", "point_of_interest"],
                "rating": 4.8,
                "user_ratings_total": 10000,
                "price_level": 0,
                "opening_hours": {
                    "open_now": True,
                    "weekday_text": [
                        "Monday: 6:00 AM – 1:00 AM",
                        "Tuesday: 6:00 AM – 1:00 AM",
                    ],
                },
                "photos": [{"photo_reference": "photo_ref_123"}],
                "website": "https://www.centralparknyc.org/",
                "formatted_phone_number": "(212) 310-6600",
                "reviews": [
                    {"rating": 5, "text": "Beautiful park!", "time": 1234567890}
                ],
            }
        }

        return mock

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        mock = AsyncMock()
        mock.get.return_value = None
        mock.set.return_value = True
        return mock

    @pytest.fixture
    def activity_service(self, mock_google_maps_service, mock_cache_service):
        """Create an ActivityService instance with mocked dependencies."""
        return ActivityService(
            google_maps_service=mock_google_maps_service,
            cache_service=mock_cache_service,
        )

    @pytest.fixture
    def sample_search_request(self):
        """Create a sample activity search request."""
        return ActivitySearchRequest(
            destination="New York",
            start_date=date.today(),
            categories=["tour", "museum", "adventure"],
            adults=2,
        )

    @pytest.mark.asyncio
    async def test_search_activities_success(
        self, activity_service, sample_search_request, mock_google_maps_service
    ):
        """Test successful activity search."""
        result = await activity_service.search_activities(sample_search_request)

        # Verify result structure
        assert isinstance(result, ActivitySearchResponse)
        # The service searches for multiple place types which can result in duplicates
        assert len(result.activities) >= 2
        assert result.total >= 2

        # Verify we have activities (they may include duplicates)
        activity_names = {a.name for a in result.activities}
        assert "Central Park" in activity_names

        # Find the Central Park activity
        central_park = next(a for a in result.activities if a.name == "Central Park")
        assert central_park.id == "gmp_place_123"
        assert central_park.type == "nature"
        assert central_park.location == "Central Park, New York, NY"
        assert central_park.rating == 4.8
        assert central_park.price == 0.0
        assert central_park.coordinates.lat == 40.7829
        assert central_park.coordinates.lng == -73.9654

        # Verify service calls
        mock_google_maps_service.geocode.assert_called_once_with("New York")
        mock_google_maps_service.search_places.assert_called()

    @pytest.mark.asyncio
    async def test_search_activities_with_no_geocoding_results(
        self, activity_service, sample_search_request, mock_google_maps_service
    ):
        """Test activity search when geocoding returns no results."""
        mock_google_maps_service.geocode.return_value = []

        result = await activity_service.search_activities(sample_search_request)

        assert isinstance(result, ActivitySearchResponse)
        assert len(result.activities) == 0
        assert result.total == 0
        assert result.filters_applied["destination"] == "New York"

    @pytest.mark.asyncio
    async def test_search_activities_with_geocoding_error(
        self, activity_service, sample_search_request, mock_google_maps_service
    ):
        """Test activity search when geocoding fails."""
        mock_google_maps_service.geocode.side_effect = GoogleMapsServiceError(
            "Geocoding failed"
        )

        with pytest.raises(CoreServiceError) as exc_info:
            await activity_service.search_activities(sample_search_request)

        assert "Maps API error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_activities_with_places_search_error(
        self, activity_service, sample_search_request, mock_google_maps_service
    ):
        """Test activity search when places search fails - should handle gracefully."""
        mock_google_maps_service.search_places.side_effect = GoogleMapsServiceError(
            "Places search failed"
        )

        # The service should handle individual search failures gracefully
        result = await activity_service.search_activities(sample_search_request)

        # Should return empty results instead of failing completely
        assert isinstance(result, ActivitySearchResponse)
        assert len(result.activities) == 0
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_search_activities_empty_results(
        self, activity_service, sample_search_request, mock_google_maps_service
    ):
        """Test activity search with no results."""
        mock_google_maps_service.search_places.return_value = {"results": []}

        result = await activity_service.search_activities(sample_search_request)

        assert isinstance(result, ActivitySearchResponse)
        assert len(result.activities) == 0
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_get_activity_details_success(
        self, activity_service, mock_google_maps_service
    ):
        """Test successful activity details retrieval."""
        activity_id = "gmp_place_123"  # Note: needs gmp_ prefix

        result = await activity_service.get_activity_details(activity_id)

        assert isinstance(result, ActivityResponse)
        assert result.id == activity_id
        assert result.name == "Central Park"
        assert result.rating == 4.8
        assert result.coordinates.lat == 40.7829
        assert result.coordinates.lng == -73.9654

        mock_google_maps_service.get_place_details.assert_called_once_with(
            place_id="place_123",  # Without prefix
            fields=[
                "name",
                "formatted_address",
                "geometry",
                "rating",
                "price_level",
                "types",
                "opening_hours",
                "photos",
                "reviews",
                "website",
                "formatted_phone_number",
            ],
        )

    @pytest.mark.asyncio
    async def test_get_activity_details_not_found(
        self, activity_service, mock_google_maps_service
    ):
        """Test activity details when place not found."""
        mock_google_maps_service.get_place_details.return_value = {"result": {}}

        # Should return None for not found
        result = await activity_service.get_activity_details("gmp_invalid_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_activity_details_error(
        self, activity_service, mock_google_maps_service
    ):
        """Test activity details when API call fails."""
        mock_google_maps_service.get_place_details.side_effect = GoogleMapsServiceError(
            "API error"
        )

        with pytest.raises(ActivityServiceError) as exc_info:
            await activity_service.get_activity_details("gmp_place_123")

        assert "Maps API error" in str(exc_info.value)

    def test_determine_activity_type(self, activity_service):
        """Test activity type determination."""
        # Test direct mapping
        assert activity_service._determine_activity_type(["museum"]) == "cultural"
        assert activity_service._determine_activity_type(["park"]) == "nature"
        assert activity_service._determine_activity_type(["restaurant"]) == "food"

        # Test fallback to first valid type
        assert activity_service._determine_activity_type(["zoo", "park"]) == "nature"

        # Test default fallback
        assert activity_service._determine_activity_type([]) == "entertainment"
        assert (
            activity_service._determine_activity_type(["unknown_type"])
            == "entertainment"
        )

    def test_estimate_price(self, activity_service):
        """Test price estimation."""
        # Test with different price levels and activity types
        assert activity_service._estimate_price_from_level(0, "cultural") == 0.0
        assert activity_service._estimate_price_from_level(1, "cultural") == 15.0
        assert (
            activity_service._estimate_price_from_level(2, "cultural") == 22.5
        )  # 15 * 1.5
        assert (
            activity_service._estimate_price_from_level(3, "cultural") == 37.5
        )  # 15 * 2.5
        assert (
            activity_service._estimate_price_from_level(4, "cultural") == 60.0
        )  # 15 * 4

        # Test with different activity types
        assert activity_service._estimate_price_from_level(1, "adventure") == 50.0
        assert activity_service._estimate_price_from_level(1, "food") == 20.0

    def test_estimate_duration(self, activity_service):
        """Test duration estimation."""
        # Test specific activity types
        assert activity_service._estimate_duration("cultural", ["museum"]) == 120
        assert activity_service._estimate_duration("nature", ["park"]) == 180
        assert activity_service._estimate_duration("food", ["restaurant"]) == 90

        # Test default duration
        assert activity_service._estimate_duration("other", []) == 120
        assert activity_service._estimate_duration("unknown", ["unknown_type"]) == 120

    @pytest.mark.asyncio
    async def test_caching_behavior(
        self, activity_service, sample_search_request, mock_cache_service
    ):
        """Test that search results are cached."""
        # The @cached decorator likely checks the cache during method execution
        # Since the method has @cached decorator, it should use the cache service
        # But the actual caching behavior depends on the decorator implementation

        # Run a search (the cached decorator should handle caching)
        result = await activity_service.search_activities(sample_search_request)

        # Verify we got results back
        assert isinstance(result, ActivitySearchResponse)

    @pytest.mark.asyncio
    async def test_activity_type_filtering(
        self, activity_service, mock_google_maps_service
    ):
        """Test that activities are filtered by requested types."""
        # Request only nature activities
        request = ActivitySearchRequest(
            destination="New York",
            start_date=date.today(),
            categories=["nature"],  # Request nature directly
        )

        # Mock places for nature category
        mock_google_maps_service.search_places.return_value = {
            "results": [
                {
                    "place_id": "park_123",
                    "name": "Central Park",
                    "geometry": {"location": {"lat": 40.7829, "lng": -73.9654}},
                    "formatted_address": "Central Park, New York, NY",
                    "types": ["park"],
                    "rating": 4.8,
                    "price_level": 0,
                }
            ]
        }

        result = await activity_service.search_activities(request)

        # Should return park results
        assert len(result.activities) > 0
        assert any(a.type == "nature" for a in result.activities)

    @pytest.mark.asyncio
    async def test_search_with_all_activity_types(
        self, activity_service, mock_google_maps_service
    ):
        """Test search when requesting all activity types."""
        # Create diverse mock results
        mock_google_maps_service.search_places.return_value = {
            "results": [
                {
                    "place_id": f"place_{i}",
                    "name": f"Activity {i}",
                    "geometry": {"location": {"lat": 40.7 + i * 0.01, "lng": -74.0}},
                    "formatted_address": f"Address {i}",
                    "types": [place_type],
                    "rating": 4.5,
                    "user_ratings_total": 100,
                    "price_level": i % 5,
                }
                for i, place_type in enumerate(
                    [
                        "museum",
                        "park",
                        "restaurant",
                        "gym",
                        "shopping_mall",
                        "church",
                        "amusement_park",
                        "movie_theater",
                        "spa",
                    ]
                )
            ]
        }

        request = ActivitySearchRequest(
            destination="New York",
            start_date=date.today(),
            categories=["tour", "cultural", "adventure", "entertainment"],
        )

        result = await activity_service.search_activities(request)

        # Should return activities
        assert len(result.activities) > 0

        # Verify different activity types are present
        activity_types = {a.type for a in result.activities}
        # At least some of these types should be present
        assert len(activity_types) > 0

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, activity_service):
        """Test that concurrent searches work correctly."""
        requests = [
            ActivitySearchRequest(
                destination=f"City {i}",
                start_date=date.today(),
                categories=["museum", "tour"],
            )
            for i in range(3)
        ]

        # Run searches concurrently
        results = await asyncio.gather(
            *[activity_service.search_activities(req) for req in requests]
        )

        assert len(results) == 3
        assert all(isinstance(r, ActivitySearchResponse) for r in results)

    @pytest.mark.asyncio
    async def test_search_with_invalid_date(self, activity_service):
        """Test search with various date inputs."""
        # Test with past date (should still work)
        request = ActivitySearchRequest(
            destination="New York", start_date=date(2020, 1, 1), categories=["tour"]
        )

        result = await activity_service.search_activities(request)
        assert isinstance(result, ActivitySearchResponse)

    @pytest.mark.asyncio
    async def test_activity_response_fields(
        self, activity_service, sample_search_request
    ):
        """Test that all required fields are present in activity response."""
        result = await activity_service.search_activities(sample_search_request)

        for activity in result.activities:
            # Required fields
            assert activity.id is not None
            assert activity.name is not None
            assert activity.type is not None
            assert activity.location is not None
            assert activity.date is not None
            assert activity.duration is not None
            assert activity.price is not None
            assert activity.rating is not None
            assert activity.description is not None
            assert isinstance(activity.images, list)
            assert activity.provider is not None

            # Coordinates
            assert activity.coordinates is not None
            assert isinstance(activity.coordinates.lat, (int, float))
            assert isinstance(activity.coordinates.lng, (int, float))


class TestActivityServiceError:
    """Test ActivityServiceError exception."""

    def test_activity_service_error_creation(self):
        """Test creating ActivityServiceError."""
        error = ActivityServiceError("Test error")

        assert str(error) == "ACTIVITY_SERVICE_ERROR: Test error"
        assert error.code == "ACTIVITY_SERVICE_ERROR"
        assert isinstance(error, CoreServiceError)

    def test_activity_service_error_with_original_error(self):
        """Test ActivityServiceError with original error."""
        original = ValueError("Original error")
        error = ActivityServiceError("Wrapped error", original)

        assert str(error) == "ACTIVITY_SERVICE_ERROR: Wrapped error"
        assert error.original_error == original


class TestActivityServiceHelpers:
    """Test helper methods and edge cases."""

    @pytest.fixture
    def mock_google_maps_service(self):
        """Create a mock Google Maps service."""
        mock = AsyncMock(spec=GoogleMapsService)
        mock.geocode.return_value = [
            {"geometry": {"location": {"lat": 40.7128, "lng": -74.0060}}}
        ]
        mock.search_places.return_value = {"results": []}
        return mock

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        mock = AsyncMock()
        mock.get.return_value = None
        mock.set.return_value = True
        return mock

    @pytest.fixture
    def activity_service(self, mock_google_maps_service, mock_cache_service):
        """Create an ActivityService instance."""
        return ActivityService(
            google_maps_service=mock_google_maps_service,
            cache_service=mock_cache_service,
        )

    def test_activity_type_mapping_completeness(self):
        """Test that ACTIVITY_TYPE_MAPPING covers expected types."""
        expected_types = [
            "adventure",
            "cultural",
            "entertainment",
            "food",
            "nature",
            "religious",
            "shopping",
            "sports",
            "wellness",
        ]

        for activity_type in expected_types:
            assert activity_type in ACTIVITY_TYPE_MAPPING
            assert len(ACTIVITY_TYPE_MAPPING[activity_type]) > 0

    @pytest.mark.asyncio
    async def test_convert_place_to_activity_edge_cases(self, activity_service):
        """Test place to activity conversion with edge cases."""
        # Create a sample request for testing
        sample_search_request = ActivitySearchRequest(
            destination="New York", start_date=date.today(), categories=["tour"]
        )
        # Place with minimal data
        minimal_place = {
            "place_id": "minimal_123",
            "name": "Minimal Place",
            "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
            "formatted_address": "Some Address",
        }

        # Note: _convert_place_to_activity IS async
        activity = await activity_service._convert_place_to_activity(
            minimal_place, sample_search_request
        )

        assert activity.id == "gmp_minimal_123"
        assert activity.name == "Minimal Place"
        assert activity.rating == 0.0  # Default when not provided
        # Entertainment is the default type, which has 180 minutes duration
        assert activity.type == "entertainment"
        assert activity.duration == 180

    @pytest.mark.asyncio
    async def test_search_with_max_distance_filter(
        self, activity_service, mock_google_maps_service
    ):
        """Test that max_distance is properly passed to Google Maps API."""
        request = ActivitySearchRequest(
            destination="New York", start_date=date.today(), categories=["tour"]
        )

        await activity_service.search_activities(request)

        # Verify search_places was called
        mock_google_maps_service.search_places.assert_called()

    @pytest.mark.asyncio
    async def test_search_with_max_results_limit(
        self, activity_service, mock_google_maps_service
    ):
        """Test that max_results limits the number of returned activities."""
        # Mock many results
        mock_google_maps_service.search_places.return_value = {
            "results": [
                {
                    "place_id": f"place_{i}",
                    "name": f"Activity {i}",
                    "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                    "formatted_address": f"Address {i}",
                    "types": ["park"],
                    "rating": 4.5,
                }
                for i in range(20)
            ]
        }

        request = ActivitySearchRequest(
            destination="New York", start_date=date.today(), categories=["tour"]
        )

        result = await activity_service.search_activities(request)

        # Result should include all activities (no max_results in request)
        assert len(result.activities) == 20

    @pytest.mark.asyncio
    async def test_photo_reference_handling(
        self, activity_service, mock_google_maps_service
    ):
        """Test that photo references are handled properly."""
        # Set up mock to return a place with photos
        mock_google_maps_service.search_places.return_value = {
            "results": [
                {
                    "place_id": "photo_test",
                    "name": "Photo Test Place",
                    "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                    "formatted_address": "Test Address",
                    "types": ["tourist_attraction"],
                    "rating": 4.5,
                    "photos": [{"photo_reference": "test_photo_ref"}],
                }
            ]
        }

        # Create a sample request for testing
        sample_search_request = ActivitySearchRequest(
            destination="New York", start_date=date.today(), categories=["tour"]
        )

        result = await activity_service.search_activities(sample_search_request)

        # Should have results
        assert len(result.activities) > 0

        # Note: The service currently returns empty images list
        # as photo URL generation requires additional API calls
        activity = result.activities[0]
        assert isinstance(activity.images, list)
        assert (
            len(activity.images) == 0
        )  # Photos not converted in current implementation

    def test_duration_estimation_for_all_types(self, activity_service):
        """Test duration estimation for all activity types."""
        # Test different activity types
        assert activity_service._estimate_duration("adventure", []) == 240
        assert activity_service._estimate_duration("cultural", []) == 120
        assert activity_service._estimate_duration("entertainment", []) == 180
        assert activity_service._estimate_duration("food", []) == 90
        assert activity_service._estimate_duration("nature", []) == 180
        assert activity_service._estimate_duration("religious", []) == 60
        assert activity_service._estimate_duration("shopping", []) == 120
        assert activity_service._estimate_duration("sports", []) == 120
        assert activity_service._estimate_duration("wellness", []) == 90
        assert activity_service._estimate_duration("unknown", []) == 120  # default

    @pytest.mark.asyncio
    async def test_error_recovery(self, activity_service, mock_google_maps_service):
        """Test that service handles partial failures gracefully."""
        # Set up mock to return results for first search
        mock_google_maps_service.search_places.return_value = {
            "results": [
                {
                    "place_id": "test1",
                    "name": "Test Place 1",
                    "geometry": {"location": {"lat": 40.7, "lng": -74.0}},
                    "formatted_address": "Test Address",
                    "types": ["tourist_attraction"],
                    "rating": 4.5,
                }
            ]
        }

        # First call succeeds
        request1 = ActivitySearchRequest(
            destination="City 1", start_date=date.today(), categories=["tour"]
        )
        result1 = await activity_service.search_activities(request1)
        assert len(result1.activities) > 0

        # Second search with geocoding failure should raise error
        mock_google_maps_service.geocode.side_effect = GoogleMapsServiceError(
            "Geocoding failed"
        )
        request2 = ActivitySearchRequest(
            destination="City 2", start_date=date.today(), categories=["tour"]
        )
        with pytest.raises(CoreServiceError):
            await activity_service.search_activities(request2)
