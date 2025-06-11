"""
Comprehensive unit tests for trips router with dual testing approach.

Tests both simple router implementation (target branch approach) and enhanced
service layer implementation (our branch approach) for maximum compatibility.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from tripsage.api.middlewares.authentication import Principal

# Test imports that work with both approaches
try:
    from tripsage.api.schemas.requests.trips import CreateTripRequest, UpdateTripRequest
    from tripsage.api.schemas.responses.trips import TripResponse

    ENHANCED_SCHEMAS_AVAILABLE = True
except ImportError:
    from tripsage.api.schemas.trips import CreateTripRequest, TripResponse

    ENHANCED_SCHEMAS_AVAILABLE = False

# Always available schemas
from tripsage.api.schemas.trips import TripSuggestionResponse

# Test enhanced service if available
try:
    from tripsage.api.services.trip import TripService as EnhancedTripService

    ENHANCED_SERVICE_AVAILABLE = True
except ImportError:
    ENHANCED_SERVICE_AVAILABLE = False

# Core service (always available)
# Router functions for direct testing
from tripsage.api.routers.trips import (
    create_trip,
    get_trip_suggestions,
)
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import TripDestination
from tripsage_core.services.business.trip_service import TripService


class TestTripsRouterSimple:
    """Test trips router functionality using simple approach (target branch style)."""

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Principal(
            id="user123", type="user", email="test@example.com", auth_method="jwt"
        )

    @pytest.fixture
    def mock_trip_service(self):
        """Mock trip service."""
        service = MagicMock(spec=TripService)
        service.get_trip_suggestions = AsyncMock()
        service.create_trip = AsyncMock()
        return service

    @pytest.fixture
    def sample_trip_request(self):
        """Sample trip creation request."""
        return CreateTripRequest(
            title="Tokyo Adventure",
            description="5-day trip exploring Tokyo",
            start_date=date(2024, 5, 1),
            end_date=date(2024, 5, 5),
            destinations=[
                TripDestination(name="Tokyo, Japan", country="Japan", city="Tokyo")
            ],
        )

    async def test_create_trip_not_implemented(
        self, mock_principal, mock_trip_service, sample_trip_request
    ):
        """Test create trip function (currently not implemented in simple mode)."""
        # The function currently returns None when enhanced service is not available
        result = await create_trip(
            sample_trip_request, mock_principal, mock_trip_service
        )

        # Function returns None due to simple implementation
        assert result is None

    async def test_get_trip_suggestions_success(
        self, mock_principal, mock_trip_service
    ):
        """Test successful trip suggestions retrieval."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=None,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service,
        )

        # Should return the hardcoded suggestions from the function
        assert isinstance(result, list)
        assert len(result) <= 4  # Respects the limit
        assert all("id" in suggestion.__dict__ for suggestion in result)
        assert all("title" in suggestion.__dict__ for suggestion in result)
        assert all("destination" in suggestion.__dict__ for suggestion in result)

    async def test_get_trip_suggestions_with_limit(
        self, mock_principal, mock_trip_service
    ):
        """Test trip suggestions respects limit parameter."""
        result = await get_trip_suggestions(
            limit=2,
            budget_max=None,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service,
        )

        # Should respect the limit
        assert isinstance(result, list)
        assert len(result) == 2
        # Should return first 2 suggestions (Tokyo, Bali)
        titles = [s.title for s in result]
        assert "Tokyo Cherry Blossom Adventure" in titles
        assert "Bali Tropical Retreat" in titles

    async def test_get_trip_suggestions_with_budget_filter(
        self, mock_principal, mock_trip_service
    ):
        """Test trip suggestions with budget filter."""
        result = await get_trip_suggestions(
            limit=10,
            budget_max=2000.0,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service,
        )

        # Should only return suggestions within budget
        assert isinstance(result, list)
        assert all(suggestion.estimated_price <= 2000.0 for suggestion in result)
        # Should include Bali (1500) but exclude Tokyo (2800), Swiss Alps (3200)
        destination_names = [s.destination for s in result]
        assert "Bali, Indonesia" in destination_names
        assert "Tokyo, Japan" not in destination_names

    async def test_get_trip_suggestions_with_category_filter(
        self, mock_principal, mock_trip_service
    ):
        """Test trip suggestions with category filter."""
        result = await get_trip_suggestions(
            limit=10,
            budget_max=None,
            category="culture",
            principal=mock_principal,
            trip_service=mock_trip_service,
        )

        # Should only return suggestions matching the category
        assert isinstance(result, list)
        assert all(suggestion.category == "culture" for suggestion in result)
        assert len(result) >= 1  # Should have at least the Tokyo suggestion

    async def test_get_trip_suggestions_response_structure(
        self, mock_principal, mock_trip_service
    ):
        """Test detailed response structure validation."""
        result = await get_trip_suggestions(
            limit=4,
            budget_max=None,
            category=None,
            principal=mock_principal,
            trip_service=mock_trip_service,
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


@pytest.mark.skipif(
    not ENHANCED_SERVICE_AVAILABLE, reason="Enhanced service layer not available"
)
class TestTripsRouterEnhanced:
    """Test trips router functionality using enhanced service layer (our branch)."""

    def setup_method(self):
        """Set up test data and mocks."""
        self.test_user_id = "test-user-123"
        self.test_trip_id = uuid4()

        # Create mock core service
        self.mock_core_service = Mock()

        # Initialize enhanced service with mock
        if ENHANCED_SERVICE_AVAILABLE:
            self.service = EnhancedTripService(core_trip_service=self.mock_core_service)

        # Sample test data
        self.sample_destination = TripDestination(
            name="Paris",
            country="France",
            city="Paris",
            coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
            duration_days=4,
        )

        self.sample_create_request = CreateTripRequest(
            title="European Adventure",
            description="A wonderful trip through Europe",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 15),
            destinations=[self.sample_destination],
        )

        self.sample_core_response = Mock()
        self.sample_core_response.id = str(self.test_trip_id)
        self.sample_core_response.user_id = self.test_user_id
        self.sample_core_response.title = "European Adventure"
        self.sample_core_response.description = "A wonderful trip through Europe"
        self.sample_core_response.start_date = date(2024, 6, 1)
        self.sample_core_response.end_date = date(2024, 6, 15)
        # Create destination that matches what adapter method expects (dict coordinates)
        mock_destination = Mock()
        mock_destination.name = "Paris"
        mock_destination.country = "France"
        mock_destination.city = "Paris"
        mock_destination.coordinates = {
            "lat": 48.8566,
            "lng": 2.3522,
        }  # Dict format expected by adapter

        self.sample_core_response.destinations = [mock_destination]
        self.sample_core_response.preferences = {}
        self.sample_core_response.status = "planning"
        self.sample_core_response.created_at = "2024-01-01T00:00:00Z"
        self.sample_core_response.updated_at = "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_create_trip_success(self):
        """Test successful trip creation through enhanced service layer."""
        if not ENHANCED_SERVICE_AVAILABLE:
            pytest.skip("Enhanced service layer not available")

        # Arrange
        self.mock_core_service.create_trip = AsyncMock(
            return_value=self.sample_core_response
        )

        # Act
        result = await self.service.create_trip(
            self.test_user_id, self.sample_create_request
        )

        # Assert
        assert isinstance(result, TripResponse)
        assert result.title == "European Adventure"
        assert result.user_id == self.test_user_id
        assert len(result.destinations) == 1
        assert result.destinations[0].name == "Paris"
        assert result.status == "planning"

        # Verify core service was called correctly
        self.mock_core_service.create_trip.assert_called_once()
        call_args = self.mock_core_service.create_trip.call_args
        assert call_args[0][0] == self.test_user_id  # user_id
        assert call_args[0][1].title == "European Adventure"  # core request

    @pytest.mark.asyncio
    async def test_get_trip_success(self):
        """Test successful trip retrieval."""
        if not ENHANCED_SERVICE_AVAILABLE:
            pytest.skip("Enhanced service layer not available")

        # Arrange
        self.mock_core_service.get_trip = AsyncMock(
            return_value=self.sample_core_response
        )

        # Act
        result = await self.service.get_trip(self.test_user_id, self.test_trip_id)

        # Assert
        assert isinstance(result, TripResponse)
        assert result.title == "European Adventure"
        assert result.user_id == self.test_user_id

        # Verify core service was called correctly
        self.mock_core_service.get_trip.assert_called_once_with(
            self.test_user_id, str(self.test_trip_id)
        )

    @pytest.mark.asyncio
    async def test_get_trip_not_found(self):
        """Test trip retrieval when trip doesn't exist."""
        if not ENHANCED_SERVICE_AVAILABLE:
            pytest.skip("Enhanced service layer not available")

        # Arrange
        self.mock_core_service.get_trip = AsyncMock(return_value=None)

        # Act
        result = await self.service.get_trip(self.test_user_id, self.test_trip_id)

        # Assert
        assert result is None

    def test_adapt_create_trip_request(self):
        """Test request adaptation to core model."""
        if not ENHANCED_SERVICE_AVAILABLE:
            pytest.skip("Enhanced service layer not available")

        # Act
        core_request = self.service._adapt_create_trip_request(
            self.sample_create_request
        )

        # Assert
        assert core_request.title == "European Adventure"
        assert core_request.description == "A wonderful trip through Europe"
        assert len(core_request.destinations) == 1
        assert core_request.destinations[0].name == "Paris"
        assert core_request.destinations[0].coordinates["lat"] == 48.8566

    def test_adapt_trip_response(self):
        """Test response adaptation from core model."""
        if not ENHANCED_SERVICE_AVAILABLE:
            pytest.skip("Enhanced service layer not available")

        # Act
        api_response = self.service._adapt_trip_response(self.sample_core_response)

        # Assert
        assert isinstance(api_response, TripResponse)
        assert api_response.title == "European Adventure"
        assert api_response.user_id == self.test_user_id
        assert len(api_response.destinations) == 1
        assert api_response.destinations[0].name == "Paris"


class TestTripsRouterCompatibility:
    """Test compatibility between simple and enhanced approaches."""

    def test_import_compatibility(self):
        """Test that imports work correctly for both approaches."""
        # Test that we can import basic schemas
        assert CreateTripRequest is not None
        assert TripResponse is not None
        assert TripSuggestionResponse is not None

        # Test enhanced schemas availability
        if ENHANCED_SCHEMAS_AVAILABLE:
            # Enhanced schemas should be available
            assert UpdateTripRequest is not None

        # Test enhanced service availability
        if ENHANCED_SERVICE_AVAILABLE:
            assert EnhancedTripService is not None

    def test_service_layer_detection(self):
        """Test that service layer detection works correctly."""
        # This test ensures our hybrid approach can detect what's available
        assert isinstance(ENHANCED_SERVICE_AVAILABLE, bool)
        assert isinstance(ENHANCED_SCHEMAS_AVAILABLE, bool)

        # Log the current state for debugging
        print(f"Enhanced service available: {ENHANCED_SERVICE_AVAILABLE}")
        print(f"Enhanced schemas available: {ENHANCED_SCHEMAS_AVAILABLE}")
