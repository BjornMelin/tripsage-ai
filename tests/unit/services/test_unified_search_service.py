"""
Comprehensive unit tests for UnifiedSearchService.

Tests cover unified search functionality, result aggregation, filtering, and caching.
"""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List
import uuid

from tripsage.api.schemas.requests.search import UnifiedSearchRequest, SearchFilters
from tripsage.api.schemas.responses.search import (
    UnifiedSearchResponse,
    SearchResultItem,
    SearchFacet,
    SearchMetadata,
)
from tripsage.api.schemas.responses.activities import (
    ActivitySearchResponse,
    ActivityResponse,
    ActivityCoordinates,
)
from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchService,
    UnifiedSearchServiceError,
    get_unified_search_service,
)


class TestUnifiedSearchService:
    """Test suite for UnifiedSearchService."""

    @pytest.fixture
    def mock_cache_service(self):
        """Create a mock cache service."""
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()
        return mock_cache

    @pytest.fixture
    def mock_destination_service(self):
        """Create a mock destination service."""
        return AsyncMock()

    @pytest.fixture
    def mock_activity_service(self):
        """Create a mock activity service."""
        mock_service = AsyncMock()
        mock_service.search_activities = AsyncMock()
        return mock_service

    @pytest.fixture
    def unified_search_service(
        self,
        mock_cache_service,
        mock_destination_service,
        mock_activity_service,
    ):
        """Create a UnifiedSearchService instance with mocked dependencies."""
        service = UnifiedSearchService(cache_service=mock_cache_service)
        service._destination_service = mock_destination_service
        service._activity_service = mock_activity_service
        return service

    @pytest.fixture
    def sample_search_request(self):
        """Create a sample unified search request."""
        return UnifiedSearchRequest(
            query="museums in new york",
            types=["destination", "activity"],
            destination="New York, NY",
            start_date=date(2025, 1, 15),
            end_date=date(2025, 1, 20),
            adults=2,
            children=0,
            filters=SearchFilters(
                price_min=0,
                price_max=200,
                rating_min=4.0,
            ),
            sort_by="relevance",
            sort_order="desc",
        )

    @pytest.fixture
    def sample_activity_response(self):
        """Create a sample activity search response."""
        return ActivitySearchResponse(
            activities=[
                ActivityResponse(
                    id="act1",
                    name="Museum of Modern Art",
                    type="cultural",
                    description="World-class modern art museum",
                    location="New York, NY",
                    coordinates=ActivityCoordinates(lat=40.7614, lng=-73.9776),
                    rating=4.5,
                    price=25.0,
                    provider="google_maps",
                    date="2025-01-15",
                    duration=120,
                    images=[],
                    availability="Open",
                    wheelchair_accessible=False,
                    instant_confirmation=False,
                ),
                ActivityResponse(
                    id="act2",
                    name="Metropolitan Museum",
                    type="cultural",
                    description="One of the world's largest art museums",
                    location="New York, NY",
                    coordinates=ActivityCoordinates(lat=40.7794, lng=-73.9632),
                    rating=4.8,
                    price=30.0,
                    provider="google_maps",
                    date="2025-01-15",
                    duration=180,
                    images=[],
                    availability="Open",
                    wheelchair_accessible=True,
                    instant_confirmation=False,
                ),
            ],
            total_results=2,
            destination="New York, NY",
            search_date=date.today(),
        )

    @pytest.mark.asyncio
    async def test_unified_search_success(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
        sample_activity_response,
    ):
        """Test successful unified search across multiple types."""
        # Setup mocks
        mock_activity_service.search_activities.return_value = sample_activity_response

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Verify response
        assert isinstance(response, UnifiedSearchResponse)
        assert len(response.results) == 3  # 1 destination + 2 activities
        assert response.metadata.total_results == 3
        assert response.metadata.returned_results == 3
        assert "destination" in response.metadata.providers_queried
        assert "activity" in response.metadata.providers_queried

        # Verify destination result
        dest_result = next(r for r in response.results if r.type == "destination")
        assert dest_result.title == "New York, Ny"
        assert dest_result.type == "destination"
        assert dest_result.relevance_score == 0.9

        # Verify activity results
        activity_results = [r for r in response.results if r.type == "activity"]
        assert len(activity_results) == 2
        assert activity_results[0].title == "Museum of Modern Art"
        assert activity_results[0].price == 25.0
        assert activity_results[0].rating == 4.5

    @pytest.mark.asyncio
    async def test_unified_search_with_cache_hit(
        self,
        unified_search_service,
        mock_cache_service,
        sample_search_request,
    ):
        """Test unified search with cache hit."""
        # Setup cached response
        cached_response = UnifiedSearchResponse(
            results=[
                SearchResultItem(
                    id="cached1",
                    type="destination",
                    title="Cached Destination",
                    description="From cache",
                    location="New York",
                    relevance_score=1.0,
                )
            ],
            facets=[],
            metadata=SearchMetadata(
                total_results=1,
                returned_results=1,
                search_time_ms=10,
                search_id="cached-id",
                providers_queried=["cache"],
            ),
        )
        mock_cache_service.get.return_value = cached_response.model_dump_json()

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Verify cached response returned
        assert len(response.results) == 1
        assert response.results[0].title == "Cached Destination"
        assert response.metadata.search_id == "cached-id"
        
        # Verify no service calls made
        unified_search_service._activity_service.search_activities.assert_not_called()

    @pytest.mark.asyncio
    async def test_unified_search_filtering(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
        sample_activity_response,
    ):
        """Test unified search with price and rating filters."""
        # Add expensive activity that should be filtered out
        expensive_activity = ActivityResponse(
            id="act3",
            name="Expensive Tour",
            type="tour",
            description="Very expensive tour",
            location="New York, NY",
            rating=4.9,
            price=300.0,  # Above max price filter
            provider="google_maps",
            date="2025-01-15",
            duration=240,
            images=[],
            availability="Open",
            wheelchair_accessible=False,
            instant_confirmation=True,
        )
        sample_activity_response.activities.append(expensive_activity)
        mock_activity_service.search_activities.return_value = sample_activity_response

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Verify filtering - expensive activity should be excluded
        activity_results = [r for r in response.results if r.type == "activity"]
        assert len(activity_results) == 2  # Expensive one filtered out
        assert all(r.price <= 200 for r in activity_results)
        assert all(r.rating >= 4.0 for r in activity_results if r.rating)

    @pytest.mark.asyncio
    async def test_unified_search_sorting_by_price(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
        sample_activity_response,
    ):
        """Test unified search with price sorting."""
        # Change sort criteria
        sample_search_request.sort_by = "price"
        sample_search_request.sort_order = "asc"
        
        mock_activity_service.search_activities.return_value = sample_activity_response

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Verify sorting - activities should be sorted by price ascending
        activity_results = [r for r in response.results if r.type == "activity"]
        prices = [r.price for r in activity_results if r.price is not None]
        assert prices == sorted(prices)

    @pytest.mark.asyncio
    async def test_unified_search_sorting_by_rating(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
        sample_activity_response,
    ):
        """Test unified search with rating sorting."""
        # Change sort criteria
        sample_search_request.sort_by = "rating"
        sample_search_request.sort_order = "desc"
        
        mock_activity_service.search_activities.return_value = sample_activity_response

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Verify sorting - activities should be sorted by rating descending
        activity_results = [r for r in response.results if r.type == "activity"]
        ratings = [r.rating for r in activity_results if r.rating is not None]
        assert ratings == sorted(ratings, reverse=True)

    @pytest.mark.asyncio
    async def test_unified_search_facet_generation(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
        sample_activity_response,
    ):
        """Test facet generation for search results."""
        mock_activity_service.search_activities.return_value = sample_activity_response

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Verify facets
        assert len(response.facets) > 0
        
        # Check type facet
        type_facet = next((f for f in response.facets if f.field == "type"), None)
        assert type_facet is not None
        assert type_facet.type == "terms"
        assert len(type_facet.values) == 2  # destination and activity
        
        # Check price facet
        price_facet = next((f for f in response.facets if f.field == "price"), None)
        assert price_facet is not None
        assert price_facet.type == "range"
        assert price_facet.values[0]["min"] == 25.0
        assert price_facet.values[0]["max"] == 30.0
        
        # Check rating facet
        rating_facet = next((f for f in response.facets if f.field == "rating"), None)
        assert rating_facet is not None
        assert rating_facet.type == "range"

    @pytest.mark.asyncio
    async def test_unified_search_error_handling(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
    ):
        """Test error handling in unified search."""
        # Setup activity service to raise exception
        mock_activity_service.search_activities.side_effect = Exception("Activity API Error")

        # Perform search - should handle error gracefully
        response = await unified_search_service.unified_search(sample_search_request)

        # Should still return destination results
        assert len(response.results) == 1  # Only destination
        assert response.results[0].type == "destination"
        
        # Should record provider error
        assert "activity" in response.metadata.provider_errors
        assert "Activity API Error" in response.metadata.provider_errors["activity"]

    @pytest.mark.asyncio
    async def test_unified_search_no_destination(
        self,
        unified_search_service,
        sample_search_request,
    ):
        """Test unified search without destination specified."""
        # Remove destination
        sample_search_request.destination = None

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Should return empty results for activities
        assert len(response.results) == 0
        assert response.metadata.total_results == 0

    @pytest.mark.asyncio
    async def test_unified_search_custom_types(
        self,
        unified_search_service,
        sample_search_request,
    ):
        """Test unified search with custom type selection."""
        # Only search for activities
        sample_search_request.types = ["activity"]

        # Perform search
        response = await unified_search_service.unified_search(sample_search_request)

        # Should not include destination results
        assert all(r.type == "activity" for r in response.results)
        assert "destination" not in response.metadata.providers_queried

    @pytest.mark.asyncio
    async def test_get_search_suggestions(
        self,
        unified_search_service,
    ):
        """Test search suggestions generation."""
        # Test with partial query
        suggestions = await unified_search_service.get_search_suggestions("par", limit=5)

        # Verify suggestions
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 5
        assert any("Paris" in s for s in suggestions)
        
        # Test with longer query
        suggestions = await unified_search_service.get_search_suggestions("new y", limit=10)
        assert any("New York" in s for s in suggestions)

    @pytest.mark.asyncio
    async def test_get_search_suggestions_error_handling(
        self,
        unified_search_service,
    ):
        """Test error handling in search suggestions."""
        # Mock an internal error
        with patch.object(unified_search_service, '_get_destination_suggestions', side_effect=Exception("Error")):
            with pytest.raises(UnifiedSearchServiceError):
                await unified_search_service.get_search_suggestions("test")

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, unified_search_service):
        """Test cache key generation for different requests."""
        request1 = UnifiedSearchRequest(
            query="museums",
            destination="New York",
            types=["activity"],
        )
        
        request2 = UnifiedSearchRequest(
            query="museums",
            destination="Boston",
            types=["activity"],
        )
        
        fields1 = unified_search_service.get_cache_fields(request1)
        fields2 = unified_search_service.get_cache_fields(request2)
        
        # Keys should be different due to different destinations
        assert fields1["destination"] != fields2["destination"]
        assert fields1["query"] == fields2["query"]

    @pytest.mark.asyncio
    async def test_unified_search_parallel_execution(
        self,
        unified_search_service,
        mock_activity_service,
        sample_search_request,
        sample_activity_response,
    ):
        """Test that searches execute in parallel."""
        import asyncio
        
        # Add delay to activity service
        async def delayed_search(*args, **kwargs):
            await asyncio.sleep(0.1)
            return sample_activity_response
        
        mock_activity_service.search_activities = delayed_search
        
        # Time the search
        start_time = asyncio.get_event_loop().time()
        response = await unified_search_service.unified_search(sample_search_request)
        end_time = asyncio.get_event_loop().time()
        
        # Should complete faster than sequential execution would
        # (destination search is instant, activity search has 0.1s delay)
        assert end_time - start_time < 0.2  # Would be ~0.2s if sequential
        assert len(response.results) > 0

    @pytest.mark.asyncio
    async def test_get_unified_search_service_singleton(self):
        """Test that get_unified_search_service returns singleton instance."""
        service1 = await get_unified_search_service()
        service2 = await get_unified_search_service()
        
        assert service1 is service2