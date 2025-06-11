"""
Unit tests for trips router.

Tests the trips router implementation using the core trip service.
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.routers.trips import (
    create_trip,
    delete_trip,
    duplicate_trip,
    export_trip,
    get_trip,
    get_trip_itinerary,
    get_trip_suggestions,
    get_trip_summary,
    list_trips,
    search_trips,
    update_trip,
    update_trip_preferences,
)
from tripsage.api.schemas.trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    UpdateTripRequest,
)
from tripsage_core.models.schemas_common.travel import TripDestination
from tripsage_core.services.business.trip_service import TripService


class TestTripsRouter:
    """Test trips router functionality."""

    @pytest.fixture
    def mock_principal(self):
        """Mock authenticated principal."""
        return Principal(
            id="user123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def mock_trip_service(self):
        """Mock trip service."""
        service = MagicMock(spec=TripService)
        service.create_trip = AsyncMock()
        service.get_trip = AsyncMock()
        service.get_user_trips = AsyncMock()
        service.update_trip = AsyncMock()
        service.delete_trip = AsyncMock()
        service.search_trips = AsyncMock()
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

    @pytest.fixture
    def sample_trip_response(self):
        """Sample trip response from core service."""
        # Create a proper mock destination object
        destination_mock = MagicMock()
        destination_mock.name = "Tokyo, Japan"
        destination_mock.country = "Japan"
        destination_mock.city = "Tokyo"
        destination_mock.coordinates = {"lat": 35.6762, "lng": 139.6503}

        trip_mock = MagicMock()
        trip_mock.id = str(uuid4())
        trip_mock.user_id = "user123"
        trip_mock.title = "Tokyo Adventure"
        trip_mock.description = "5-day trip exploring Tokyo"
        trip_mock.start_date = datetime(2024, 5, 1, tzinfo=timezone.utc)
        trip_mock.end_date = datetime(2024, 5, 5, tzinfo=timezone.utc)
        trip_mock.destinations = [destination_mock]
        trip_mock.preferences = {}
        trip_mock.status = "planning"
        trip_mock.created_at = datetime.now(timezone.utc)
        trip_mock.updated_at = datetime.now(timezone.utc)

        return trip_mock

    async def test_create_trip_success(
        self,
        mock_principal,
        mock_trip_service,
        sample_trip_request,
        sample_trip_response,
    ):
        """Test successful trip creation."""
        # Setup mock
        mock_trip_service.create_trip.return_value = sample_trip_response

        # Call function
        result = await create_trip(
            sample_trip_request, mock_principal, mock_trip_service
        )

        # Verify service was called correctly
        mock_trip_service.create_trip.assert_called_once()
        call_args = mock_trip_service.create_trip.call_args
        assert call_args.kwargs["user_id"] == "user123"
        assert call_args.kwargs["trip_data"].title == "Tokyo Adventure"

        # Verify response
        assert result.title == "Tokyo Adventure"
        assert result.user_id == "user123"
        assert len(result.destinations) == 1
        assert result.destinations[0].name == "Tokyo, Japan"

    async def test_create_trip_error(
        self, mock_principal, mock_trip_service, sample_trip_request
    ):
        """Test trip creation error handling."""
        # Setup mock to raise exception
        mock_trip_service.create_trip.side_effect = Exception("Database error")

        # Test that HTTPException is raised
        with pytest.raises(HTTPException) as exc_info:
            await create_trip(sample_trip_request, mock_principal, mock_trip_service)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to create trip"

    async def test_get_trip_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip retrieval."""
        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = sample_trip_response

        result = await get_trip(trip_id, mock_principal, mock_trip_service)

        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id="user123"
        )
        assert result.title == "Tokyo Adventure"

    async def test_get_trip_not_found(self, mock_principal, mock_trip_service):
        """Test trip not found error."""
        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(trip_id, mock_principal, mock_trip_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Trip not found"

    async def test_list_trips_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trips listing."""
        mock_trip_service.get_user_trips.return_value = [sample_trip_response]

        result = await list_trips(
            skip=0, limit=10, principal=mock_principal, trip_service=mock_trip_service
        )

        mock_trip_service.get_user_trips.assert_called_once_with(
            user_id="user123", limit=10, offset=0
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "Tokyo Adventure"

    async def test_update_trip_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip update."""
        trip_id = uuid4()
        update_request = UpdateTripRequest(
            title="Updated Tokyo Adventure", description="Updated description"
        )
        mock_trip_service.update_trip.return_value = sample_trip_response

        result = await update_trip(
            trip_id, update_request, mock_principal, mock_trip_service
        )

        mock_trip_service.update_trip.assert_called_once()
        assert result.title == "Tokyo Adventure"

    async def test_delete_trip_success(self, mock_principal, mock_trip_service):
        """Test successful trip deletion."""
        trip_id = uuid4()
        mock_trip_service.delete_trip.return_value = True

        # Should not raise any exception
        await delete_trip(trip_id, mock_principal, mock_trip_service)

        mock_trip_service.delete_trip.assert_called_once_with(
            user_id="user123", trip_id=str(trip_id)
        )

    async def test_delete_trip_not_found(self, mock_principal, mock_trip_service):
        """Test trip deletion when trip not found."""
        trip_id = uuid4()
        mock_trip_service.delete_trip.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            await delete_trip(trip_id, mock_principal, mock_trip_service)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Trip not found"

    async def test_get_trip_summary_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip summary retrieval."""
        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = sample_trip_response

        result = await get_trip_summary(trip_id, mock_principal, mock_trip_service)

        assert result.id == UUID(sample_trip_response.id)
        assert result.title == "Tokyo Adventure"
        assert "Tokyo, Japan" in result.destinations
        assert result.duration_days == 4  # May - May = 4 days

    async def test_update_trip_preferences_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip preferences update."""
        from decimal import Decimal

        from tripsage_core.models.schemas_common.enums import CurrencyCode
        from tripsage_core.models.schemas_common.financial import Budget, Price

        trip_id = uuid4()
        budget = Budget(
            total_budget=Price(amount=Decimal("5000"), currency=CurrencyCode.USD)
        )
        preferences = TripPreferencesRequest(budget=budget)
        mock_trip_service.update_trip.return_value = sample_trip_response

        await update_trip_preferences(
            trip_id, preferences, mock_principal, mock_trip_service
        )

        mock_trip_service.update_trip.assert_called_once()
        call_args = mock_trip_service.update_trip.call_args
        assert "preferences" in call_args.kwargs["request"]

    async def test_duplicate_trip_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip duplication."""
        from tripsage_core.services.business.trip_service import TripLocation

        trip_id = uuid4()

        # Create proper TripLocation objects for the mock
        trip_location = TripLocation(
            name="Tokyo, Japan",
            country="Japan",
            city="Tokyo",
            coordinates={"lat": 35.6762, "lng": 139.6503},
        )

        # Enhance the mock to have the attributes needed by duplicate_trip
        sample_trip_response.title = "Tokyo Adventure"
        sample_trip_response.description = "5-day trip exploring Tokyo"
        sample_trip_response.start_date = datetime(2024, 5, 1, tzinfo=timezone.utc)
        sample_trip_response.end_date = datetime(2024, 5, 5, tzinfo=timezone.utc)
        sample_trip_response.destinations = [trip_location]
        sample_trip_response.preferences = {}

        mock_trip_service.get_trip.return_value = sample_trip_response
        mock_trip_service.create_trip.return_value = sample_trip_response

        result = await duplicate_trip(trip_id, mock_principal, mock_trip_service)

        # Verify get_trip was called
        mock_trip_service.get_trip.assert_called_once_with(
            trip_id=str(trip_id), user_id="user123"
        )
        # Verify create_trip was called
        mock_trip_service.create_trip.assert_called_once()
        assert result.title == "Tokyo Adventure"

    async def test_search_trips_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip search."""
        mock_trip_service.search_trips.return_value = [sample_trip_response]

        result = await search_trips(
            q="Tokyo",
            status_filter=None,
            skip=0,
            limit=10,
            principal=mock_principal,
            trip_service=mock_trip_service,
        )

        mock_trip_service.search_trips.assert_called_once_with(
            user_id="user123", query="Tokyo", limit=10
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1

    async def test_get_trip_itinerary_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip itinerary retrieval."""
        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = sample_trip_response

        result = await get_trip_itinerary(trip_id, mock_principal, mock_trip_service)

        assert "trip_id" in result
        assert result["trip_id"] == str(trip_id)
        assert "items" in result
        assert result["total_items"] == 1

    async def test_export_trip_success(
        self, mock_principal, mock_trip_service, sample_trip_response
    ):
        """Test successful trip export."""
        trip_id = uuid4()
        mock_trip_service.get_trip.return_value = sample_trip_response

        result = await export_trip(
            trip_id,
            format="pdf",
            principal=mock_principal,
            trip_service=mock_trip_service,
        )

        assert result["format"] == "pdf"
        assert "download_url" in result
        assert f"trip-{trip_id}.pdf" in result["download_url"]

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
        assert all(hasattr(suggestion, "id") for suggestion in result)
        assert all(hasattr(suggestion, "title") for suggestion in result)
        assert all(hasattr(suggestion, "destination") for suggestion in result)

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
