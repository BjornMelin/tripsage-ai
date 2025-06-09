"""
Comprehensive tests for UnifiedSearchService.

Tests cover:
- Unified search across multiple resource types
- Cache integration and performance
- Error handling and resilience
- Search filtering and sorting
- Facet generation
- Search suggestions
- Service coordination and lazy loading
"""

import asyncio
import uuid
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any, Optional

import pytest
from pytest import raises

from tripsage.api.schemas.requests.search import (
    UnifiedSearchRequest,
    SearchFilters,
)
from tripsage.api.schemas.responses.search import (
    SearchFacet,
    SearchMetadata,
    SearchResultItem,
    UnifiedSearchResponse,
)
from tripsage.api.schemas.responses.activities import (
    ActivityResponse,
    ActivitySearchResponse,
    ActivityCoordinates,
)
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchService,
    UnifiedSearchServiceError,
    RESOURCE_TYPES,
    DEFAULT_SEARCH_TYPES,
    get_unified_search_service,
    close_unified_search_service,
)


class TestUnifiedSearchServiceError:
    """Test UnifiedSearchServiceError exception."""

    def test_unified_search_service_error_with_message_only(self):
        """Test creating UnifiedSearchServiceError with message only."""
        error = UnifiedSearchServiceError("Test error message")
        
        assert error.message == "Test error message"
        assert error.code == "UNIFIED_SEARCH_ERROR"
        assert error.service == "UnifiedSearchService"
        assert error.details == {"original_error": None}
        assert error.original_error is None

    def test_unified_search_service_error_with_original_error(self):
        """Test creating UnifiedSearchServiceError with original error."""
        original_error = ValueError("Original error")
        error = UnifiedSearchServiceError("Test error message", original_error)
        
        assert error.message == "Test error message"
        assert error.code == "UNIFIED_SEARCH_ERROR"
        assert error.service == "UnifiedSearchService"
        assert error.details == {"original_error": "Original error"}
        assert error.original_error == original_error

    def test_unified_search_service_error_inheritance(self):
        """Test that UnifiedSearchServiceError inherits from CoreServiceError."""
        error = UnifiedSearchServiceError("Test error")
        assert isinstance(error, CoreServiceError)


class TestUnifiedSearchService:
    """Test UnifiedSearchService class."""

    @pytest.fixture
    def mock_cache_service(self):
        """Create mock cache service."""
        return AsyncMock()

    @pytest.fixture
    def mock_destination_service(self):
        """Create mock destination service."""
        return AsyncMock()

    @pytest.fixture
    def mock_activity_service(self):
        """Create mock activity service."""
        mock_service = AsyncMock()
        
        # Setup default activity search response
        mock_activity = ActivityResponse(
            id="act_123",
            name="Test Museum",
            type="cultural",
            location="123 Test St, New York, NY",
            date="2025-07-15",
            duration=120,
            price=25.0,
            rating=4.5,
            description="Great museum to visit",
            images=[],
            provider="Google Maps",
            availability="Open now",
            wheelchair_accessible=True,
            instant_confirmation=False,
            coordinates=ActivityCoordinates(lat=40.7128, lng=-74.0060)
        )
        
        mock_response = ActivitySearchResponse(
            activities=[mock_activity],
            total=1,
            skip=0,
            limit=20,
            search_id="search_123",
            filters_applied={"destination": "New York"},
            cached=False
        )
        
        mock_service.search_activities.return_value = mock_response
        return mock_service

    @pytest.fixture
    def unified_search_service(self, mock_cache_service):
        """Create UnifiedSearchService instance with mocked dependencies."""
        service = UnifiedSearchService(cache_service=mock_cache_service)
        return service

    @pytest.fixture
    def sample_search_request(self):
        """Create sample unified search request."""
        return UnifiedSearchRequest(
            query="things to do in New York",
            destination="New York, NY",
            start_date=date(2025, 7, 15),
            end_date=date(2025, 7, 20),
            adults=2,
            children=0,
            infants=0,
            types=["destination", "activity"],
            sort_by="relevance",
            sort_order="desc"
        )

    @pytest.fixture
    def sample_search_filters(self):
        """Create sample search filters."""
        return SearchFilters(
            price_min=10.0,
            price_max=100.0,
            rating_min=4.0,
            latitude=40.7128,
            longitude=-74.0060,
            radius_km=10.0
        )

    async def test_init_with_cache_service(self, mock_cache_service):
        """Test UnifiedSearchService initialization with cache service."""
        service = UnifiedSearchService(cache_service=mock_cache_service)
        
        assert service._cache_service == mock_cache_service
        assert service._cache_ttl == 300
        assert service._cache_prefix == "unified_search"
        assert service._destination_service is None
        assert service._flight_service is None
        assert service._accommodation_service is None
        assert service._activity_service is None

    async def test_init_without_cache_service(self):
        """Test UnifiedSearchService initialization without cache service."""
        service = UnifiedSearchService()
        
        assert service._cache_service is None
        assert service._cache_ttl == 300
        assert service._cache_prefix == "unified_search"

    async def test_ensure_services_with_none_services(self):
        """Test ensure_services when services are None."""
        service = UnifiedSearchService()
        
        with patch('tripsage_core.services.business.unified_search_service.get_cache_service') as mock_get_cache, \
             patch('tripsage_core.services.business.unified_search_service.get_destination_service') as mock_get_dest, \
             patch('tripsage_core.services.business.unified_search_service.get_activity_service') as mock_get_act:
            
            mock_cache = AsyncMock()
            mock_dest = AsyncMock()
            mock_act = AsyncMock()
            mock_get_cache.return_value = mock_cache
            mock_get_dest.return_value = mock_dest
            mock_get_act.return_value = mock_act
            
            await service.ensure_services()
            
            assert service._cache_service == mock_cache
            assert service._destination_service == mock_dest
            assert service._activity_service == mock_act
            mock_get_cache.assert_called_once()
            mock_get_dest.assert_called_once()
            mock_get_act.assert_called_once()

    async def test_ensure_services_with_existing_services(self, unified_search_service):
        """Test ensure_services when services already exist."""
        original_cache = unified_search_service._cache_service
        
        with patch('tripsage_core.services.business.unified_search_service.get_cache_service') as mock_get_cache, \
             patch('tripsage_core.services.business.unified_search_service.get_destination_service') as mock_get_dest, \
             patch('tripsage_core.services.business.unified_search_service.get_activity_service') as mock_get_act:
            
            await unified_search_service.ensure_services()
            
            # Cache service should remain unchanged
            assert unified_search_service._cache_service == original_cache
            mock_get_cache.assert_not_called()
            # Other services should be initialized
            mock_get_dest.assert_called_once()
            mock_get_act.assert_called_once()

    def test_get_cache_fields_basic(self, unified_search_service, sample_search_request):
        """Test get_cache_fields with basic request."""
        cache_fields = unified_search_service.get_cache_fields(sample_search_request)
        
        expected_fields = {
            "query": "things to do in New York",
            "types": ["activity", "destination"],  # Sorted
            "destination": "New York, NY",
            "start_date": "2025-07-15",
            "end_date": "2025-07-20",
            "origin": None,
            "adults": 2,
            "children": 0,
            "infants": 0,
            "sort_by": "relevance",
            "sort_order": "desc",
        }
        
        assert cache_fields == expected_fields

    def test_get_cache_fields_with_filters(self, unified_search_service, sample_search_filters):
        """Test get_cache_fields with filters included."""
        request = UnifiedSearchRequest(
            query="test query",
            destination="Test City",
            filters=sample_search_filters
        )
        
        cache_fields = unified_search_service.get_cache_fields(request)
        
        assert cache_fields["price_min"] == 10.0
        assert cache_fields["price_max"] == 100.0
        assert cache_fields["rating_min"] == 4.0
        assert cache_fields["latitude"] == 40.7128
        assert cache_fields["longitude"] == -74.0060
        assert cache_fields["radius_km"] == 10.0

    def test_get_cache_fields_with_none_dates(self, unified_search_service):
        """Test get_cache_fields with None dates."""
        request = UnifiedSearchRequest(
            query="test query",
            destination="Test City"
            # No dates specified
        )
        
        cache_fields = unified_search_service.get_cache_fields(request)
        
        assert cache_fields["start_date"] is None
        assert cache_fields["end_date"] is None

    def test_get_cache_fields_default_types(self, unified_search_service):
        """Test get_cache_fields with default types."""
        request = UnifiedSearchRequest(
            query="test query",
            destination="Test City"
            # No types specified
        )
        
        cache_fields = unified_search_service.get_cache_fields(request)
        
        assert cache_fields["types"] == sorted(DEFAULT_SEARCH_TYPES)

    def test_get_response_class(self, unified_search_service):
        """Test _get_response_class method."""
        response_class = unified_search_service._get_response_class()
        assert response_class == UnifiedSearchResponse

    async def test_unified_search_success(self, unified_search_service, sample_search_request, mock_activity_service):
        """Test successful unified search."""
        unified_search_service._activity_service = mock_activity_service
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            result = await unified_search_service.unified_search(sample_search_request)
            
            assert isinstance(result, UnifiedSearchResponse)
            assert len(result.results) > 0
            assert result.metadata.total_results > 0
            assert result.metadata.search_id is not None
            assert "destination" in result.metadata.providers_queried
            assert "activity" in result.metadata.providers_queried
            
            # Check that we have both destination and activity results
            result_types = [r.type for r in result.results]
            assert "destination" in result_types
            assert "activity" in result_types

    async def test_unified_search_cached_result(self, unified_search_service, sample_search_request):
        """Test unified search with cached result."""
        cached_response = UnifiedSearchResponse(
            results=[],
            facets=[],
            metadata=SearchMetadata(
                total_results=0,
                returned_results=0,
                search_time_ms=100,
                search_id="cached_123",
                providers_queried=["cache"]
            ),
            results_by_type={},
        )
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=cached_response), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            result = await unified_search_service.unified_search(sample_search_request)
            
            assert result == cached_response
            assert result.metadata.search_id == "cached_123"

    async def test_unified_search_no_search_types(self, unified_search_service):
        """Test unified search with no valid search types."""
        request = UnifiedSearchRequest(
            query="test query",
            types=[]  # Empty types list
        )
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            result = await unified_search_service.unified_search(request)
            
            assert isinstance(result, UnifiedSearchResponse)
            assert len(result.results) == 0
            assert result.metadata.total_results == 0

    async def test_unified_search_service_error(self, unified_search_service, sample_search_request):
        """Test unified search with service error."""
        with patch.object(unified_search_service, 'ensure_services', side_effect=Exception("Service error")), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            with raises(UnifiedSearchServiceError) as exc_info:
                await unified_search_service.unified_search(sample_search_request)
            
            assert "Unified search failed" in str(exc_info.value)

    async def test_search_destinations_success(self, unified_search_service):
        """Test _search_destinations method."""
        request = UnifiedSearchRequest(
            query="paris tourism",
            destination="Paris, France"
        )
        
        results = await unified_search_service._search_destinations(request)
        
        assert isinstance(results, list)
        assert len(results) == 1
        
        result = results[0]
        assert result.type == "destination"
        assert result.title == "Paris, France"
        assert "Paris, France" in result.description
        assert result.location == "Paris, France"
        assert result.relevance_score == 0.9

    async def test_search_destinations_query_only(self, unified_search_service):
        """Test _search_destinations with query containing destination."""
        request = UnifiedSearchRequest(
            query="things to do in tokyo destination guide"
        )
        
        results = await unified_search_service._search_destinations(request)
        
        assert isinstance(results, list)
        assert len(results) == 1
        
        result = results[0]
        assert result.type == "destination"
        assert "destination" in result.title.lower()

    async def test_search_destinations_no_match(self, unified_search_service):
        """Test _search_destinations with no destination match."""
        request = UnifiedSearchRequest(
            query="restaurant recommendations"
        )
        
        results = await unified_search_service._search_destinations(request)
        
        assert isinstance(results, list)
        assert len(results) == 0

    async def test_search_destinations_error(self, unified_search_service):
        """Test _search_destinations with error."""
        request = UnifiedSearchRequest(
            query="test",
            destination=None  # This might cause issues in some implementations
        )
        
        # Should handle gracefully and return empty list
        results = await unified_search_service._search_destinations(request)
        assert isinstance(results, list)

    async def test_search_activities_success(self, unified_search_service, mock_activity_service):
        """Test _search_activities method."""
        unified_search_service._activity_service = mock_activity_service
        
        request = UnifiedSearchRequest(
            query="museums in new york",
            destination="New York, NY",
            start_date=date(2025, 7, 15)
        )
        
        results = await unified_search_service._search_activities(request)
        
        assert isinstance(results, list)
        assert len(results) == 1
        
        result = results[0]
        assert result.type == "activity"
        assert result.title == "Test Museum"
        assert result.price == 25.0
        assert result.rating == 4.5
        assert result.location == "123 Test St, New York, NY"
        assert result.metadata["activity_type"] == "cultural"
        assert result.metadata["duration"] == 120

    async def test_search_activities_no_destination(self, unified_search_service):
        """Test _search_activities without destination."""
        request = UnifiedSearchRequest(
            query="museums"
            # No destination
        )
        
        results = await unified_search_service._search_activities(request)
        
        assert isinstance(results, list)
        assert len(results) == 0

    async def test_search_activities_with_filters(self, unified_search_service, mock_activity_service, sample_search_filters):
        """Test _search_activities with filters."""
        unified_search_service._activity_service = mock_activity_service
        
        request = UnifiedSearchRequest(
            query="activities",
            destination="Paris, France",
            filters=sample_search_filters
        )
        
        results = await unified_search_service._search_activities(request)
        
        # Verify the activity service was called with filters
        mock_activity_service.search_activities.assert_called_once()
        call_args = mock_activity_service.search_activities.call_args[0][0]
        assert call_args.rating == sample_search_filters.rating_min

    async def test_search_activities_error(self, unified_search_service):
        """Test _search_activities with service error."""
        mock_service = AsyncMock()
        mock_service.search_activities.side_effect = Exception("API Error")
        unified_search_service._activity_service = mock_service
        
        request = UnifiedSearchRequest(
            query="activities",
            destination="Test City"
        )
        
        # Should handle gracefully and return empty list
        results = await unified_search_service._search_activities(request)
        assert isinstance(results, list)
        assert len(results) == 0

    async def test_search_flights_not_implemented(self, unified_search_service):
        """Test _search_flights method (not yet implemented)."""
        request = UnifiedSearchRequest(
            query="flights",
            origin="NYC",
            destination="LAX"
        )
        
        results = await unified_search_service._search_flights(request)
        
        assert isinstance(results, list)
        assert len(results) == 0

    async def test_search_accommodations_not_implemented(self, unified_search_service):
        """Test _search_accommodations method (not yet implemented)."""
        request = UnifiedSearchRequest(
            query="hotels",
            destination="Paris, France"
        )
        
        results = await unified_search_service._search_accommodations(request)
        
        assert isinstance(results, list)
        assert len(results) == 0

    def test_apply_unified_filters_no_filters(self, unified_search_service):
        """Test _apply_unified_filters without filters."""
        results = [
            SearchResultItem(
                id="1", type="activity", title="Test", relevance_score=0.8,
                price=50.0, rating=4.0
            )
        ]
        
        request = UnifiedSearchRequest(query="test")
        
        filtered = unified_search_service._apply_unified_filters(results, request)
        
        assert filtered == results

    def test_apply_unified_filters_price_range(self, unified_search_service):
        """Test _apply_unified_filters with price range."""
        results = [
            SearchResultItem(id="1", type="activity", title="Expensive", relevance_score=0.8, price=150.0),
            SearchResultItem(id="2", type="activity", title="Affordable", relevance_score=0.7, price=25.0),
            SearchResultItem(id="3", type="activity", title="Free", relevance_score=0.6, price=None),
        ]
        
        filters = SearchFilters(price_min=20.0, price_max=100.0)
        request = UnifiedSearchRequest(query="test", filters=filters)
        
        filtered = unified_search_service._apply_unified_filters(results, request)
        
        assert len(filtered) == 2  # Affordable + Free (None price passes through)
        titles = [r.title for r in filtered]
        assert "Affordable" in titles
        assert "Free" in titles
        assert "Expensive" not in titles

    def test_apply_unified_filters_rating(self, unified_search_service):
        """Test _apply_unified_filters with rating filter."""
        results = [
            SearchResultItem(id="1", type="activity", title="High Rated", relevance_score=0.8, rating=4.5),
            SearchResultItem(id="2", type="activity", title="Low Rated", relevance_score=0.7, rating=3.0),
            SearchResultItem(id="3", type="activity", title="No Rating", relevance_score=0.6, rating=None),
        ]
        
        filters = SearchFilters(rating_min=4.0)
        request = UnifiedSearchRequest(query="test", filters=filters)
        
        filtered = unified_search_service._apply_unified_filters(results, request)
        
        assert len(filtered) == 2  # High Rated + No Rating (None rating passes through)
        titles = [r.title for r in filtered]
        assert "High Rated" in titles
        assert "No Rating" in titles
        assert "Low Rated" not in titles

    def test_sort_unified_results_by_price(self, unified_search_service):
        """Test _sort_unified_results by price."""
        results = [
            SearchResultItem(id="1", type="activity", title="Expensive", relevance_score=0.8, price=100.0),
            SearchResultItem(id="2", type="activity", title="Cheap", relevance_score=0.7, price=20.0),
            SearchResultItem(id="3", type="activity", title="Free", relevance_score=0.6, price=None),
        ]
        
        request = UnifiedSearchRequest(query="test", sort_by="price", sort_order="asc")
        
        sorted_results = unified_search_service._sort_unified_results(results, request)
        
        # Should be: Cheap, Expensive, Free (None prices go to end)
        assert sorted_results[0].title == "Cheap"
        assert sorted_results[1].title == "Expensive"
        assert sorted_results[2].title == "Free"

    def test_sort_unified_results_by_price_desc(self, unified_search_service):
        """Test _sort_unified_results by price descending."""
        results = [
            SearchResultItem(id="1", type="activity", title="Expensive", relevance_score=0.8, price=100.0),
            SearchResultItem(id="2", type="activity", title="Cheap", relevance_score=0.7, price=20.0),
            SearchResultItem(id="3", type="activity", title="Free", relevance_score=0.6, price=None),
        ]
        
        request = UnifiedSearchRequest(query="test", sort_by="price", sort_order="desc")
        
        sorted_results = unified_search_service._sort_unified_results(results, request)
        
        # Should be: Expensive, Cheap, Free (None prices go to end)
        assert sorted_results[0].title == "Expensive"
        assert sorted_results[1].title == "Cheap"
        assert sorted_results[2].title == "Free"

    def test_sort_unified_results_by_rating(self, unified_search_service):
        """Test _sort_unified_results by rating."""
        results = [
            SearchResultItem(id="1", type="activity", title="High Rated", relevance_score=0.8, rating=4.5),
            SearchResultItem(id="2", type="activity", title="Low Rated", relevance_score=0.7, rating=3.0),
            SearchResultItem(id="3", type="activity", title="No Rating", relevance_score=0.6, rating=None),
        ]
        
        request = UnifiedSearchRequest(query="test", sort_by="rating", sort_order="desc")
        
        sorted_results = unified_search_service._sort_unified_results(results, request)
        
        # Should be: High Rated, Low Rated, No Rating (None ratings go to end)
        assert sorted_results[0].title == "High Rated"
        assert sorted_results[1].title == "Low Rated"
        assert sorted_results[2].title == "No Rating"

    def test_sort_unified_results_by_relevance(self, unified_search_service):
        """Test _sort_unified_results by relevance (default)."""
        results = [
            SearchResultItem(id="1", type="activity", title="Medium", relevance_score=0.5),
            SearchResultItem(id="2", type="activity", title="High", relevance_score=0.9),
            SearchResultItem(id="3", type="activity", title="Low", relevance_score=0.2),
        ]
        
        request = UnifiedSearchRequest(query="test")  # Default sort
        
        sorted_results = unified_search_service._sort_unified_results(results, request)
        
        # Should be: High, Medium, Low (always descending for relevance)
        assert sorted_results[0].title == "High"
        assert sorted_results[1].title == "Medium"
        assert sorted_results[2].title == "Low"

    def test_generate_facets_empty_results(self, unified_search_service):
        """Test _generate_facets with empty results."""
        facets = unified_search_service._generate_facets([])
        
        assert isinstance(facets, list)
        assert len(facets) == 0

    def test_generate_facets_with_results(self, unified_search_service):
        """Test _generate_facets with various results."""
        results = [
            SearchResultItem(id="1", type="activity", title="Museum", price=25.0, rating=4.5),
            SearchResultItem(id="2", type="activity", title="Tour", price=50.0, rating=4.0),
            SearchResultItem(id="3", type="destination", title="City", price=None, rating=None),
        ]
        
        facets = unified_search_service._generate_facets(results)
        
        assert isinstance(facets, list)
        assert len(facets) == 3  # Type, Price, Rating facets
        
        # Check type facet
        type_facet = next(f for f in facets if f.field == "type")
        assert type_facet.type == "terms"
        assert len(type_facet.values) == 2  # activity, destination
        
        # Check price facet
        price_facet = next(f for f in facets if f.field == "price")
        assert price_facet.type == "range"
        assert price_facet.values[0]["min"] == 25.0
        assert price_facet.values[0]["max"] == 50.0
        
        # Check rating facet
        rating_facet = next(f for f in facets if f.field == "rating")
        assert rating_facet.type == "range"
        assert rating_facet.values[0]["min"] == 4.0
        assert rating_facet.values[0]["max"] == 4.5

    def test_generate_facets_no_prices_or_ratings(self, unified_search_service):
        """Test _generate_facets with results having no prices or ratings."""
        results = [
            SearchResultItem(id="1", type="activity", title="Free Activity", price=None, rating=None),
            SearchResultItem(id="2", type="destination", title="City", price=None, rating=None),
        ]
        
        facets = unified_search_service._generate_facets(results)
        
        assert len(facets) == 1  # Only type facet
        assert facets[0].field == "type"

    async def test_get_search_suggestions_destination_match(self, unified_search_service):
        """Test get_search_suggestions with destination match."""
        with patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            suggestions = await unified_search_service.get_search_suggestions("par", limit=5)
            
            assert isinstance(suggestions, list)
            assert any("Paris" in s for s in suggestions)

    async def test_get_search_suggestions_activity_types(self, unified_search_service):
        """Test get_search_suggestions with activity type suggestions."""
        with patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            suggestions = await unified_search_service.get_search_suggestions("tokyo", limit=10)
            
            assert isinstance(suggestions, list)
            # Should include activity suggestions for tokyo
            assert any("museums in tokyo" in s for s in suggestions)

    async def test_get_search_suggestions_short_query(self, unified_search_service):
        """Test get_search_suggestions with short query."""
        with patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            suggestions = await unified_search_service.get_search_suggestions("ny", limit=5)
            
            assert isinstance(suggestions, list)
            # Should still return some destination suggestions

    async def test_get_search_suggestions_limit(self, unified_search_service):
        """Test get_search_suggestions respects limit."""
        with patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            suggestions = await unified_search_service.get_search_suggestions("new", limit=3)
            
            assert isinstance(suggestions, list)
            assert len(suggestions) <= 3

    async def test_get_search_suggestions_error(self, unified_search_service):
        """Test get_search_suggestions with error."""
        with patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            with patch.object(unified_search_service, 'get_search_suggestions', side_effect=Exception("Error")):
                
                with raises(UnifiedSearchServiceError):
                    await unified_search_service.get_search_suggestions("test")


class TestGlobalServiceFunctions:
    """Test global service management functions."""

    async def test_get_unified_search_service_new_instance(self):
        """Test get_unified_search_service creates new instance."""
        # Ensure no existing instance
        await close_unified_search_service()
        
        with patch('tripsage_core.services.business.unified_search_service.UnifiedSearchService') as MockService:
            mock_instance = AsyncMock()
            MockService.return_value = mock_instance
            
            result = await get_unified_search_service()
            
            assert result == mock_instance
            MockService.assert_called_once()
            mock_instance.ensure_services.assert_called_once()

    async def test_get_unified_search_service_existing_instance(self):
        """Test get_unified_search_service returns existing instance."""
        # First call to create instance
        await close_unified_search_service()
        
        with patch('tripsage_core.services.business.unified_search_service.UnifiedSearchService') as MockService:
            mock_instance = AsyncMock()
            MockService.return_value = mock_instance
            
            result1 = await get_unified_search_service()
            result2 = await get_unified_search_service()
            
            assert result1 == result2 == mock_instance
            MockService.assert_called_once()  # Only called once
            mock_instance.ensure_services.assert_called_once()  # Only called once

    async def test_close_unified_search_service(self):
        """Test close_unified_search_service."""
        # Create an instance first
        await get_unified_search_service()
        
        # Close it
        await close_unified_search_service()
        
        # Next call should create a new instance
        with patch('tripsage_core.services.business.unified_search_service.UnifiedSearchService') as MockService:
            mock_instance = AsyncMock()
            MockService.return_value = mock_instance
            
            result = await get_unified_search_service()
            
            assert result == mock_instance
            MockService.assert_called_once()


class TestConstants:
    """Test module constants."""

    def test_resource_types_mapping(self):
        """Test RESOURCE_TYPES constant."""
        assert isinstance(RESOURCE_TYPES, dict)
        assert RESOURCE_TYPES["destination"] == "destinations"
        assert RESOURCE_TYPES["flight"] == "flights"
        assert RESOURCE_TYPES["accommodation"] == "accommodations"
        assert RESOURCE_TYPES["activity"] == "activities"

    def test_default_search_types(self):
        """Test DEFAULT_SEARCH_TYPES constant."""
        assert isinstance(DEFAULT_SEARCH_TYPES, list)
        assert "destination" in DEFAULT_SEARCH_TYPES
        assert "activity" in DEFAULT_SEARCH_TYPES
        assert "accommodation" in DEFAULT_SEARCH_TYPES


class TestSearchCacheMixin:
    """Test SearchCacheMixin functionality."""

    async def test_cache_integration(self, unified_search_service, sample_search_request):
        """Test cache integration through SearchCacheMixin."""
        # Test that cache methods are available
        assert hasattr(unified_search_service, 'get_cached_search')
        assert hasattr(unified_search_service, 'cache_search_results')
        
        # Test get_cache_fields method
        cache_fields = unified_search_service.get_cache_fields(sample_search_request)
        assert isinstance(cache_fields, dict)
        assert "query" in cache_fields
        
        # Test _get_response_class method
        response_class = unified_search_service._get_response_class()
        assert response_class == UnifiedSearchResponse


class TestConcurrency:
    """Test concurrent operations."""

    async def test_concurrent_searches(self, unified_search_service, mock_activity_service):
        """Test concurrent unified searches."""
        unified_search_service._activity_service = mock_activity_service
        
        requests = [
            UnifiedSearchRequest(
                query=f"test {i}",
                destination=f"City {i}",
                types=["activity"]
            )
            for i in range(3)
        ]
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            # Execute searches concurrently
            tasks = [unified_search_service.unified_search(req) for req in requests]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            for result in results:
                assert isinstance(result, UnifiedSearchResponse)

    async def test_parallel_service_calls(self, unified_search_service, mock_activity_service):
        """Test that search services are called in parallel."""
        unified_search_service._activity_service = mock_activity_service
        
        request = UnifiedSearchRequest(
            query="test",
            destination="Test City",
            types=["destination", "activity"]
        )
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch.object(unified_search_service, '_search_destinations') as mock_dest, \
             patch.object(unified_search_service, '_search_activities') as mock_act, \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            mock_dest.return_value = []
            mock_act.return_value = []
            
            await unified_search_service.unified_search(request)
            
            # Both should be called
            mock_dest.assert_called_once()
            mock_act.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    async def test_partial_service_failures(self, unified_search_service):
        """Test handling partial service failures."""
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch.object(unified_search_service, '_search_destinations', side_effect=Exception("Dest error")), \
             patch.object(unified_search_service, '_search_activities', return_value=[]), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            request = UnifiedSearchRequest(
                query="test",
                destination="Test City",
                types=["destination", "activity"]
            )
            
            result = await unified_search_service.unified_search(request)
            
            assert isinstance(result, UnifiedSearchResponse)
            assert result.errors is not None
            assert "destination" in result.errors
            assert "Dest error" in result.errors["destination"]

    async def test_empty_query(self, unified_search_service):
        """Test handling empty query."""
        request = UnifiedSearchRequest(
            query="",
            destination="Test City"
        )
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            result = await unified_search_service.unified_search(request)
            
            assert isinstance(result, UnifiedSearchResponse)

    async def test_invalid_search_types(self, unified_search_service):
        """Test handling invalid search types."""
        request = UnifiedSearchRequest(
            query="test",
            destination="Test City",
            types=["invalid_type", "another_invalid"]
        )
        
        with patch.object(unified_search_service, 'get_cached_search', return_value=None), \
             patch.object(unified_search_service, 'cache_search_results'), \
             patch('tripsage_core.services.business.unified_search_service.with_error_handling'):
            
            result = await unified_search_service.unified_search(request)
            
            # Should handle gracefully
            assert isinstance(result, UnifiedSearchResponse)

    def test_sort_with_none_values(self, unified_search_service):
        """Test sorting with None values in scores."""
        results = [
            SearchResultItem(id="1", type="activity", title="Valid", relevance_score=0.8),
            SearchResultItem(id="2", type="activity", title="None Score", relevance_score=None),
        ]
        
        request = UnifiedSearchRequest(query="test", sort_by="relevance")
        
        sorted_results = unified_search_service._sort_unified_results(results, request)
        
        # Should handle None values gracefully
        assert len(sorted_results) == 2
        assert sorted_results[0].title == "Valid"  # Non-None score should come first