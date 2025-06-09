"""
Comprehensive tests for UnifiedSearchService with full coverage.

Tests cover:
- Cross-resource search functionality
- Parallel search execution
- Result aggregation and filtering
- Facet generation
- Caching behavior
- Error handling
- Edge cases
"""

import asyncio
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict, Any
import uuid

import pytest
from pydantic import ValidationError

from tripsage_core.services.business.unified_search_service import (
    UnifiedSearchService,
    UnifiedSearchServiceError,
)
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.business.flight_service import FlightServiceError
from tripsage_core.services.business.accommodation_service import AccommodationServiceError
from tripsage_core.services.business.activity_service import ActivityServiceError
from tripsage_core.services.business.destination_service import DestinationServiceError


class TestUnifiedSearchService:
    """Test UnifiedSearchService class."""

    @pytest.fixture
    def mock_flight_service(self):
        """Create mock flight service."""
        mock = AsyncMock()
        mock.search_flights.return_value = {
            "results": [
                {
                    "id": "flight_1",
                    "airline": "Test Air",
                    "origin": "JFK",
                    "destination": "LAX",
                    "departure_time": "2025-07-15T10:00:00",
                    "arrival_time": "2025-07-15T13:00:00",
                    "price": 350.0,
                    "duration": 180
                }
            ],
            "total": 1
        }
        return mock

    @pytest.fixture
    def mock_accommodation_service(self):
        """Create mock accommodation service."""
        mock = AsyncMock()
        mock.search_accommodations.return_value = {
            "accommodations": [
                {
                    "id": "hotel_1",
                    "name": "Test Hotel",
                    "location": "New York, NY",
                    "price_per_night": 200.0,
                    "rating": 4.5,
                    "amenities": ["wifi", "pool"]
                }
            ],
            "total": 1
        }
        return mock

    @pytest.fixture
    def mock_activity_service(self):
        """Create mock activity service."""
        mock = AsyncMock()
        mock.search_activities.return_value = {
            "activities": [
                {
                    "id": "activity_1",
                    "name": "City Tour",
                    "type": "tour",
                    "location": "New York, NY",
                    "price": 75.0,
                    "duration": 120,
                    "rating": 4.7
                }
            ],
            "total": 1
        }
        return mock

    @pytest.fixture
    def mock_destination_service(self):
        """Create mock destination service."""
        mock = AsyncMock()
        mock.search_destinations.return_value = {
            "destinations": [
                {
                    "id": "dest_1",
                    "name": "New York City",
                    "country": "USA",
                    "description": "The Big Apple",
                    "best_time_to_visit": "April-June, September-November"
                }
            ],
            "total": 1
        }
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
    def unified_search_service(
        self,
        mock_flight_service,
        mock_accommodation_service,
        mock_activity_service,
        mock_destination_service,
        mock_cache_service
    ):
        """Create UnifiedSearchService instance with mocked dependencies."""
        return UnifiedSearchService(
            flight_service=mock_flight_service,
            accommodation_service=mock_accommodation_service,
            activity_service=mock_activity_service,
            destination_service=mock_destination_service,
            cache_service=mock_cache_service
        )

    async def test_search_all_resources_success(self, unified_search_service):
        """Test successful search across all resources."""
        result = await unified_search_service.search(
            query="New York",
            location="New York, NY",
            resource_types=["flights", "accommodations", "activities", "destinations"]
        )

        assert result["total"] == 4
        assert len(result["results"]) == 4
        assert result["search_id"] is not None
        assert not result["cached"]
        
        # Check results by type
        flight_results = [r for r in result["results"] if r["type"] == "flight"]
        hotel_results = [r for r in result["results"] if r["type"] == "accommodation"]
        activity_results = [r for r in result["results"] if r["type"] == "activity"]
        destination_results = [r for r in result["results"] if r["type"] == "destination"]
        
        assert len(flight_results) == 1
        assert len(hotel_results) == 1
        assert len(activity_results) == 1
        assert len(destination_results) == 1

    async def test_search_specific_resources(self, unified_search_service):
        """Test search with specific resource types."""
        result = await unified_search_service.search(
            query="beach resort",
            location="Miami, FL",
            resource_types=["accommodations", "activities"]
        )

        assert result["total"] == 2
        assert len(result["results"]) == 2
        
        # Verify only requested types are searched
        unified_search_service.flight_service.search_flights.assert_not_called()
        unified_search_service.destination_service.search_destinations.assert_not_called()

    async def test_search_single_resource(self, unified_search_service):
        """Test search with single resource type."""
        result = await unified_search_service.search(
            query="direct flight",
            location="Los Angeles, CA",
            resource_types=["flights"]
        )

        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "flight"

    async def test_search_with_filters(self, unified_search_service):
        """Test search with various filters."""
        filters = {
            "price_min": 100,
            "price_max": 500,
            "rating_min": 4.0,
            "start_date": date(2025, 7, 15),
            "end_date": date(2025, 7, 20)
        }
        
        result = await unified_search_service.search(
            query="luxury",
            location="Paris, France",
            resource_types=["accommodations"],
            filters=filters
        )

        assert result["total"] >= 0
        assert "filters" in result
        assert result["filters"]["price_min"] == 100
        assert result["filters"]["price_max"] == 500

    async def test_search_with_sorting(self, unified_search_service):
        """Test search with sorting options."""
        # Mock multiple results for sorting
        unified_search_service.accommodation_service.search_accommodations.return_value = {
            "accommodations": [
                {"id": "h1", "name": "Hotel A", "price_per_night": 300.0, "rating": 4.2},
                {"id": "h2", "name": "Hotel B", "price_per_night": 150.0, "rating": 4.8},
                {"id": "h3", "name": "Hotel C", "price_per_night": 200.0, "rating": 4.5}
            ],
            "total": 3
        }

        result = await unified_search_service.search(
            query="hotel",
            location="London, UK",
            resource_types=["accommodations"],
            sort_by="price",
            sort_order="asc"
        )

        # Verify results are sorted by price ascending
        prices = [r["price"] for r in result["results"]]
        assert prices == sorted(prices)

    async def test_search_with_pagination(self, unified_search_service):
        """Test search with pagination."""
        result = await unified_search_service.search(
            query="restaurant",
            location="Tokyo, Japan",
            resource_types=["activities"],
            limit=10,
            offset=20
        )

        assert result["limit"] == 10
        assert result["offset"] == 20

    async def test_search_with_cache_hit(self, unified_search_service):
        """Test search with cache hit."""
        cached_result = {
            "results": [{"type": "cached", "id": "cached_1"}],
            "total": 1,
            "cached": True
        }
        unified_search_service.cache_service.get.return_value = cached_result

        result = await unified_search_service.search(
            query="cached query",
            location="Cached City"
        )

        assert result["cached"] is True
        assert result["total"] == 1
        
        # Verify no service calls were made
        unified_search_service.flight_service.search_flights.assert_not_called()
        unified_search_service.accommodation_service.search_accommodations.assert_not_called()

    async def test_search_empty_results(self, unified_search_service):
        """Test search with no results."""
        # Mock empty results
        unified_search_service.flight_service.search_flights.return_value = {"results": [], "total": 0}
        unified_search_service.accommodation_service.search_accommodations.return_value = {"accommodations": [], "total": 0}
        unified_search_service.activity_service.search_activities.return_value = {"activities": [], "total": 0}
        unified_search_service.destination_service.search_destinations.return_value = {"destinations": [], "total": 0}

        result = await unified_search_service.search(
            query="nonexistent place",
            location="Nowhere"
        )

        assert result["total"] == 0
        assert len(result["results"]) == 0

    async def test_search_with_service_error(self, unified_search_service):
        """Test search when one service fails."""
        # Make flight service fail
        unified_search_service.flight_service.search_flights.side_effect = FlightServiceError("API error")

        result = await unified_search_service.search(
            query="test",
            location="Test City",
            resource_types=["flights", "accommodations"]
        )

        # Should still return results from working services
        assert result["total"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "accommodation"

    async def test_search_all_services_error(self, unified_search_service):
        """Test search when all services fail."""
        unified_search_service.flight_service.search_flights.side_effect = Exception("Error")
        unified_search_service.accommodation_service.search_accommodations.side_effect = Exception("Error")
        unified_search_service.activity_service.search_activities.side_effect = Exception("Error")
        unified_search_service.destination_service.search_destinations.side_effect = Exception("Error")

        with pytest.raises(UnifiedSearchServiceError) as exc_info:
            await unified_search_service.search(
                query="test",
                location="Test City"
            )
        
        assert "All search services failed" in str(exc_info.value)

    async def test_get_search_suggestions(self, unified_search_service):
        """Test search suggestions generation."""
        # Mock service to return varied results
        unified_search_service.accommodation_service.search_accommodations.return_value = {
            "accommodations": [
                {"name": "Beach Resort Hotel", "location": "Miami Beach"},
                {"name": "Beach Paradise Inn", "location": "Miami Beach"},
                {"name": "Oceanfront Beach Hotel", "location": "Miami"}
            ],
            "total": 3
        }

        result = await unified_search_service.get_search_suggestions(
            query="beach",
            location="Miami"
        )

        assert len(result["suggestions"]) > 0
        assert all("beach" in s.lower() for s in result["suggestions"])
        assert result["query"] == "beach"

    async def test_search_suggestions_empty_query(self, unified_search_service):
        """Test search suggestions with empty query."""
        result = await unified_search_service.get_search_suggestions(
            query="",
            location="London"
        )

        assert result["suggestions"] == []
        assert result["query"] == ""

    async def test_search_suggestions_with_cache(self, unified_search_service):
        """Test search suggestions with cache hit."""
        cached_suggestions = {
            "suggestions": ["cached suggestion 1", "cached suggestion 2"],
            "query": "test"
        }
        unified_search_service.cache_service.get.return_value = cached_suggestions

        result = await unified_search_service.get_search_suggestions(
            query="test",
            location="Test City"
        )

        assert result == cached_suggestions
        unified_search_service.accommodation_service.search_accommodations.assert_not_called()

    async def test_search_suggestions_error_handling(self, unified_search_service):
        """Test search suggestions error handling."""
        unified_search_service.accommodation_service.search_accommodations.side_effect = Exception("Error")
        unified_search_service.activity_service.search_activities.side_effect = Exception("Error")
        unified_search_service.destination_service.search_destinations.side_effect = Exception("Error")

        result = await unified_search_service.get_search_suggestions(
            query="test",
            location="Test City"
        )

        # Should return empty suggestions on error
        assert result["suggestions"] == []
        assert result["query"] == "test"

    async def test_facet_generation(self, unified_search_service):
        """Test facet generation from search results."""
        # Mock varied results for faceting
        unified_search_service.accommodation_service.search_accommodations.return_value = {
            "accommodations": [
                {"type": "hotel", "price_per_night": 150, "rating": 4.5, "location": "Downtown"},
                {"type": "resort", "price_per_night": 300, "rating": 4.8, "location": "Beach"},
                {"type": "hotel", "price_per_night": 200, "rating": 4.2, "location": "Downtown"}
            ],
            "total": 3
        }

        result = await unified_search_service.search(
            query="accommodation",
            location="Miami",
            resource_types=["accommodations"]
        )

        assert "facets" in result
        facets = result["facets"]
        
        # Check type facets
        assert "resource_type" in facets
        assert any(f["value"] == "accommodation" for f in facets["resource_type"])
        
        # Check location facets
        assert "location" in facets
        location_values = [f["value"] for f in facets["location"]]
        assert "Downtown" in location_values
        assert "Beach" in location_values

    async def test_result_relevance_scoring(self, unified_search_service):
        """Test result relevance scoring."""
        # Mock results with different relevance
        unified_search_service.activity_service.search_activities.return_value = {
            "activities": [
                {"name": "New York City Tour", "description": "Explore New York"},
                {"name": "Manhattan Walking Tour", "description": "Walk through NYC"},
                {"name": "Brooklyn Bridge Tour", "description": "See the bridge"}
            ],
            "total": 3
        }

        result = await unified_search_service.search(
            query="New York",
            location="New York, NY",
            resource_types=["activities"]
        )

        # Results should have relevance scores
        for res in result["results"]:
            assert "relevance_score" in res
            assert 0 <= res["relevance_score"] <= 1

    async def test_concurrent_search_performance(self, unified_search_service):
        """Test concurrent search execution."""
        # Add delays to simulate real API calls
        async def delayed_search(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"results": [], "total": 0}

        unified_search_service.flight_service.search_flights = delayed_search
        unified_search_service.accommodation_service.search_accommodations = delayed_search
        unified_search_service.activity_service.search_activities = delayed_search
        unified_search_service.destination_service.search_destinations = delayed_search

        start_time = datetime.now()
        
        result = await unified_search_service.search(
            query="test",
            location="Test City"
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete in ~0.1s (concurrent) not ~0.4s (sequential)
        assert duration < 0.2

    async def test_search_with_invalid_resource_type(self, unified_search_service):
        """Test search with invalid resource type."""
        result = await unified_search_service.search(
            query="test",
            location="Test City",
            resource_types=["invalid_type"]
        )

        # Should ignore invalid types
        assert result["total"] == 0

    async def test_search_with_empty_location(self, unified_search_service):
        """Test search without location."""
        result = await unified_search_service.search(
            query="beach resorts",
            location=""
        )

        # Should still work without location
        assert result["total"] >= 0

    async def test_normalize_results_error_handling(self, unified_search_service):
        """Test result normalization with malformed data."""
        # Mock service returning malformed data
        unified_search_service.flight_service.search_flights.return_value = {
            "results": [{"malformed": "data"}],
            "total": 1
        }

        result = await unified_search_service.search(
            query="flight",
            location="NYC",
            resource_types=["flights"]
        )

        # Should handle gracefully
        assert result["total"] == 0

    async def test_filter_application(self, unified_search_service):
        """Test filter application on results."""
        # Mock results with different prices
        unified_search_service.accommodation_service.search_accommodations.return_value = {
            "accommodations": [
                {"id": "h1", "price_per_night": 50},
                {"id": "h2", "price_per_night": 150},
                {"id": "h3", "price_per_night": 250}
            ],
            "total": 3
        }

        result = await unified_search_service.search(
            query="hotel",
            location="NYC",
            resource_types=["accommodations"],
            filters={"price_min": 100, "price_max": 200}
        )

        # Should filter by price
        prices = [r["price"] for r in result["results"]]
        assert all(100 <= p <= 200 for p in prices)

    async def test_search_timeout_handling(self, unified_search_service):
        """Test search with service timeout."""
        async def timeout_search(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate timeout
            return {"results": [], "total": 0}

        unified_search_service.flight_service.search_flights = timeout_search

        # Should handle timeout gracefully
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
            result = await unified_search_service.search(
                query="test",
                location="Test City",
                resource_types=["flights", "accommodations"]
            )

            # Should return results from non-timed-out services
            assert result["total"] >= 0

    async def test_search_with_special_characters(self, unified_search_service):
        """Test search with special characters in query."""
        special_queries = [
            "test & travel",
            "café paris",
            "50% discount",
            "email@example.com",
            "C++ conference"
        ]

        for query in special_queries:
            result = await unified_search_service.search(
                query=query,
                location="Test City",
                resource_types=["activities"]
            )
            
            assert isinstance(result, dict)
            assert "error" not in result

    async def test_search_suggestions_deduplication(self, unified_search_service):
        """Test suggestion deduplication."""
        # Mock results with duplicate names
        unified_search_service.accommodation_service.search_accommodations.return_value = {
            "accommodations": [
                {"name": "Beach Hotel"},
                {"name": "Beach Hotel"},
                {"name": "Beach Resort"}
            ],
            "total": 3
        }

        result = await unified_search_service.get_search_suggestions(
            query="beach",
            location="Miami"
        )

        # Should not have duplicates
        suggestions = result["suggestions"]
        assert len(suggestions) == len(set(suggestions))

    async def test_cache_key_generation(self, unified_search_service):
        """Test cache key generation for different queries."""
        # Two identical searches should use same cache key
        key1 = unified_search_service._generate_cache_key(
            "search",
            query="test",
            location="NYC",
            resource_types=["flights"],
            filters={"price_min": 100}
        )
        
        key2 = unified_search_service._generate_cache_key(
            "search",
            query="test",
            location="NYC",
            resource_types=["flights"],
            filters={"price_min": 100}
        )
        
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = unified_search_service._generate_cache_key(
            "search",
            query="test",
            location="LA",
            resource_types=["flights"],
            filters={"price_min": 100}
        )
        
        assert key1 != key3

    async def test_service_initialization(self):
        """Test service initialization without dependencies."""
        service = UnifiedSearchService()
        
        assert service.flight_service is None
        assert service.accommodation_service is None
        assert service.activity_service is None
        assert service.destination_service is None
        assert service.cache_service is None

    async def test_error_aggregation(self, unified_search_service):
        """Test error aggregation from multiple services."""
        # Make multiple services fail with different errors
        unified_search_service.flight_service.search_flights.side_effect = FlightServiceError("Flight API down")
        unified_search_service.accommodation_service.search_accommodations.side_effect = AccommodationServiceError("Hotel API error")
        unified_search_service.activity_service.search_activities.side_effect = ActivityServiceError("Activity timeout")
        
        # One service should work
        unified_search_service.destination_service.search_destinations.return_value = {
            "destinations": [{"id": "d1"}],
            "total": 1
        }

        result = await unified_search_service.search(
            query="test",
            location="Test City"
        )

        # Should include error summary
        assert "errors" in result
        assert len(result["errors"]) == 3
        assert result["total"] == 1  # From the working service

    async def test_search_with_all_filters(self, unified_search_service):
        """Test search with comprehensive filters."""
        filters = {
            "price_min": 50,
            "price_max": 500,
            "rating_min": 4.0,
            "start_date": date(2025, 7, 15),
            "end_date": date(2025, 7, 20),
            "amenities": ["wifi", "pool"],
            "categories": ["luxury", "business"],
            "airlines": ["AA", "UA"],
            "stops": 0,
            "duration_max": 240
        }

        result = await unified_search_service.search(
            query="comprehensive test",
            location="Global",
            resource_types=["flights", "accommodations", "activities", "destinations"],
            filters=filters,
            sort_by="relevance",
            sort_order="desc",
            limit=50,
            offset=0
        )

        assert isinstance(result, dict)
        assert result["filters"] == filters
        assert result["limit"] == 50