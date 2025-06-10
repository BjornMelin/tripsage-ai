"""
Clean tests for trips router.

Tests the actual implemented functionality: trip suggestions endpoint.
Follows TripSage standards for focused, actionable testing.
"""

import pytest
from unittest.mock import MagicMock

from tripsage.api.routers.trips import get_trip_suggestions
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.services.business.trip_service import TripService


class TestTripsRouter:
    """Test trips router functionality by testing the actual functions directly."""

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt"
        )

    @pytest.fixture
    def mock_trip_service(self):
        """Mock trip service."""
        return MagicMock(spec=TripService)

    async def test_get_trip_suggestions_success(self, mock_principal, mock_trip_service):
        """Test successful trip suggestions retrieval."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=None,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        # Verify response structure
        assert isinstance(result, list)
        assert len(result) >= 1  # Should have at least one suggestion
        
        # Verify first suggestion has required fields
        first_suggestion = result[0]
        required_fields = [
            "id", "title", "destination", "description", 
            "estimated_price", "currency", "duration", "rating", "category"
        ]
        for field in required_fields:
            assert hasattr(first_suggestion, field)
            assert getattr(first_suggestion, field) is not None

    async def test_get_trip_suggestions_with_limit(self, mock_principal, mock_trip_service):
        """Test trip suggestions with limit parameter."""
        result = await get_trip_suggestions(
            limit=2,
            budget_max=None,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        assert isinstance(result, list)
        assert len(result) <= 2

    async def test_get_trip_suggestions_with_budget_filter(self, mock_principal, mock_trip_service):
        """Test trip suggestions with budget filter."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=2000,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        # All suggestions should be within budget
        for suggestion in result:
            assert suggestion.estimated_price <= 2000

    async def test_get_trip_suggestions_with_category_filter(self, mock_principal, mock_trip_service):
        """Test trip suggestions with category filter."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=None,
            category="relaxation",
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        # All suggestions should match category
        for suggestion in result:
            assert suggestion.category == "relaxation"

    async def test_get_trip_suggestions_combined_filters(self, mock_principal, mock_trip_service):
        """Test trip suggestions with multiple filters."""
        result = await get_trip_suggestions(
            limit=2,
            budget_max=2500,
            category="relaxation",
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        # Should respect both filters
        assert len(result) <= 2
        for suggestion in result:
            assert suggestion.estimated_price <= 2500
            assert suggestion.category == "relaxation"

    async def test_get_trip_suggestions_no_results_after_filtering(self, mock_principal, mock_trip_service):
        """Test trip suggestions when filters exclude all results."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=100,  # Very low budget
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        # Should return empty list when no suggestions match
        assert isinstance(result, list)
        assert len(result) == 0

    async def test_get_trip_suggestions_response_structure(self, mock_principal, mock_trip_service):
        """Test detailed response structure validation."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=None,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service
        )
        
        # Verify detailed structure of first suggestion
        if result:
            suggestion = result[0]
            
            # Required string fields
            assert isinstance(suggestion.id, str)
            assert isinstance(suggestion.title, str)
            assert isinstance(suggestion.destination, str)
            assert isinstance(suggestion.description, str)
            assert isinstance(suggestion.currency, str)
            assert isinstance(suggestion.category, str)
            
            # Required numeric fields
            assert isinstance(suggestion.estimated_price, (int, float))
            assert isinstance(suggestion.duration, int)
            assert isinstance(suggestion.rating, (int, float))
            
            # Validate ranges
            assert suggestion.estimated_price > 0
            assert suggestion.duration > 0
            assert 0 <= suggestion.rating <= 5
            
            # Optional arrays
            if hasattr(suggestion, "highlights") and suggestion.highlights:
                assert isinstance(suggestion.highlights, list)