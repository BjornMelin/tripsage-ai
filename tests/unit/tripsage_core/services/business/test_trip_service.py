"""
Comprehensive tests for TripService.

This module provides full test coverage for trip management operations
including trip creation, retrieval, updates, sharing, and search functionality.
Tests use actual domain models with proper mocking and async patterns.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.exceptions.exceptions import (
    CoreAuthorizationError as PermissionError,
)
from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.services.business.trip_service import (
    TripBudget,
    TripCreateRequest,
    TripLocation,
    TripResponse,
    TripService,
    TripShareRequest,
    TripStatus,
    TripUpdateRequest,
    TripVisibility,
    get_trip_service,
)


class TestTripService:
    """Test suite for TripService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service with comprehensive trip operations."""
        db = AsyncMock()
        # Set up default return values
        db.create_trip = AsyncMock()
        db.get_trip_by_id = AsyncMock()
        db.get_trips = AsyncMock(return_value=[])
        db.update_trip = AsyncMock()
        db.delete_trip = AsyncMock(return_value=True)
        db.search_trips = AsyncMock(return_value=[])
        db.add_trip_collaborator = AsyncMock()
        db.get_trip_collaborators = AsyncMock(return_value=[])
        db.get_trip_collaborator = AsyncMock(return_value=None)
        db.get_trip_related_counts = AsyncMock(
            return_value={
                "itinerary_count": 0,
                "flight_count": 0,
                "accommodation_count": 0,
            }
        )
        return db

    @pytest.fixture
    def mock_user_service(self):
        """Mock user service with user operations."""
        user_service = AsyncMock()
        # Create mock user object
        mock_user = MagicMock()
        mock_user.id = str(uuid4())
        mock_user.email = "test@example.com"

        user_service.get_user_by_email = AsyncMock(return_value=mock_user)
        user_service.get_user_by_id = AsyncMock(return_value=mock_user)
        return user_service

    @pytest.fixture
    def trip_service(self, mock_database_service, mock_user_service):
        """Create TripService instance with mocked dependencies."""
        return TripService(
            database_service=mock_database_service,
            user_service=mock_user_service,
        )

    @pytest.fixture
    def sample_trip_create_request(self):
        """Sample trip creation request using actual domain models."""
        return TripCreateRequest(
            title="Summer Europe Trip",
            description="A wonderful journey through European capitals",
            start_date=datetime.now(timezone.utc) + timedelta(days=30),
            end_date=datetime.now(timezone.utc) + timedelta(days=45),
            destinations=[
                TripLocation(
                    name="Paris",
                    country="France",
                    city="Paris",
                    coordinates={"lat": 48.8566, "lng": 2.3522},
                    timezone="Europe/Paris",
                ),
                TripLocation(
                    name="Rome",
                    country="Italy",
                    city="Rome",
                    coordinates={"lat": 41.9028, "lng": 12.4964},
                    timezone="Europe/Rome",
                ),
            ],
            budget=TripBudget(
                total_budget=5000.00,
                currency="USD",
                spent_amount=0.00,
                categories={
                    "accommodation": 2000.00,
                    "transportation": 1500.00,
                    "food": 1000.00,
                    "activities": 500.00,
                },
            ),
            visibility=TripVisibility.PRIVATE,
            tags=["vacation", "europe", "cities"],
            preferences={"travel_style": "balanced", "pace": "moderate"},
        )

    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data as returned from database."""
        trip_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return {
            "id": trip_id,
            "user_id": user_id,
            "title": "Summer Europe Trip",
            "description": "A wonderful journey through European capitals",
            "start_date": (now + timedelta(days=30)).isoformat(),
            "end_date": (now + timedelta(days=45)).isoformat(),
            "destinations": [
                {
                    "name": "Paris",
                    "country": "France",
                    "city": "Paris",
                    "coordinates": {"lat": 48.8566, "lng": 2.3522},
                    "timezone": "Europe/Paris",
                },
                {
                    "name": "Rome",
                    "country": "Italy",
                    "city": "Rome",
                    "coordinates": {"lat": 41.9028, "lng": 12.4964},
                    "timezone": "Europe/Rome",
                },
            ],
            "budget": {
                "total_budget": 5000.00,
                "currency": "USD",
                "spent_amount": 0.00,
                "categories": {
                    "accommodation": 2000.00,
                    "transportation": 1500.00,
                    "food": 1000.00,
                    "activities": 500.00,
                },
            },
            "status": TripStatus.PLANNING.value,
            "visibility": TripVisibility.PRIVATE.value,
            "tags": ["vacation", "europe", "cities"],
            "preferences": {"travel_style": "balanced", "pace": "moderate"},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

    @pytest.mark.asyncio
    async def test_create_trip_success(
        self,
        trip_service,
        mock_database_service,
        sample_trip_create_request,
        sample_trip_data,
    ):
        """Test successful trip creation."""
        user_id = str(uuid4())

        # Update sample_trip_data with the user_id we're using
        sample_trip_data["user_id"] = user_id

        # Mock database operations
        mock_database_service.create_trip.return_value = sample_trip_data

        result = await trip_service.create_trip(user_id, sample_trip_create_request)

        # Assertions
        assert result.user_id == user_id
        assert result.title == sample_trip_create_request.title
        assert result.description == sample_trip_create_request.description
        assert len(result.destinations) == 2
        assert result.destinations[0].name == "Paris"
        assert result.destinations[1].name == "Rome"
        assert result.status == TripStatus.PLANNING
        assert result.budget.total_budget == 5000.00
        assert result.budget.currency == "USD"

        # Verify service calls
        mock_database_service.create_trip.assert_called_once()
        args = mock_database_service.create_trip.call_args[0][0]
        assert args["user_id"] == user_id
        assert args["title"] == "Summer Europe Trip"

    @pytest.mark.asyncio
    async def test_create_trip_invalid_dates(self, trip_service):
        """Test trip creation with invalid dates."""
        now = datetime.now(timezone.utc)

        # Try to create a trip with end date before start date
        with pytest.raises(ValidationError) as exc_info:
            TripCreateRequest(
                title="Invalid Trip",
                description="This should fail",
                start_date=now + timedelta(days=30),
                end_date=now + timedelta(days=20),  # Before start date
                destinations=[],
                visibility=TripVisibility.PRIVATE,
            )

        assert "End date must be after start date" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_trip_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip retrieval."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        result = await trip_service.get_trip(trip_id, user_id)

        assert result is not None
        assert result.id == trip_id
        assert result.title == "Summer Europe Trip"
        assert result.status == TripStatus.PLANNING
        # get_trip_by_id is called twice: once in _check_trip_access
        # and once in get_trip
        assert mock_database_service.get_trip_by_id.call_count == 2
        mock_database_service.get_trip_by_id.assert_any_call(trip_id)

    @pytest.mark.asyncio
    async def test_get_trip_not_found(self, trip_service, mock_database_service):
        """Test trip retrieval when trip doesn't exist."""
        trip_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_trip_by_id.return_value = None

        result = await trip_service.get_trip(trip_id, user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_trip_access_denied(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip retrieval with access denied."""
        different_user_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        # User is not the owner and not a collaborator
        mock_database_service.get_trip_collaborator.return_value = None

        result = await trip_service.get_trip(trip_id, different_user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_trip_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip update."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        update_request = TripUpdateRequest(
            title="Updated Europe Trip",
            description="Updated description",
            tags=["vacation", "europe", "updated"],
        )

        # Mock the updated data
        updated_trip_data = sample_trip_data.copy()
        updated_trip_data.update(
            {
                "title": "Updated Europe Trip",
                "description": "Updated description",
                "tags": ["vacation", "europe", "updated"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        mock_database_service.update_trip.return_value = updated_trip_data

        result = await trip_service.update_trip(trip_id, user_id, update_request)

        assert result.title == "Updated Europe Trip"
        assert result.description == "Updated description"
        assert result.tags == ["vacation", "europe", "updated"]

        mock_database_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trip_not_found(self, trip_service, mock_database_service):
        """Test trip update when trip doesn't exist."""
        trip_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_trip_by_id.return_value = None

        update_request = TripUpdateRequest(title="Updated Trip")

        # Should raise PermissionError when trip not found
        # (since _check_trip_edit_access returns False)
        with pytest.raises(PermissionError) as exc_info:
            await trip_service.update_trip(trip_id, user_id, update_request)

        assert "No permission to edit this trip" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_trip_no_permission(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip update without edit permission."""
        different_user_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborator.return_value = None

        update_request = TripUpdateRequest(title="Unauthorized Update")

        with pytest.raises(PermissionError) as exc_info:
            await trip_service.update_trip(trip_id, different_user_id, update_request)

        assert "No permission to edit this trip" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_trip_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip deletion."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.delete_trip.return_value = True

        result = await trip_service.delete_trip(trip_id, user_id)

        assert result is True
        mock_database_service.delete_trip.assert_called_once_with(trip_id)

    @pytest.mark.asyncio
    async def test_delete_trip_not_owner(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip deletion by non-owner."""
        different_user_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        # Non-owner can't access the trip, so get_trip returns None
        mock_database_service.get_trip_collaborator.return_value = None

        # When get_trip returns None, delete_trip raises NotFoundError
        with pytest.raises(NotFoundError) as exc_info:
            await trip_service.delete_trip(trip_id, different_user_id)

        assert "Trip not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_trips_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful user trips listing."""
        user_id = str(uuid4())

        mock_database_service.get_trips.return_value = [sample_trip_data]

        results = await trip_service.get_user_trips(user_id)

        assert len(results) == 1
        assert results[0].id == sample_trip_data["id"]
        assert results[0].title == "Summer Europe Trip"

        mock_database_service.get_trips.assert_called_once_with(
            {"user_id": user_id}, 50, 0
        )

    @pytest.mark.asyncio
    async def test_get_user_trips_with_status_filter(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test user trips listing with status filter."""
        user_id = str(uuid4())

        mock_database_service.get_trips.return_value = [sample_trip_data]

        results = await trip_service.get_user_trips(user_id, status=TripStatus.PLANNING)

        assert len(results) == 1

        mock_database_service.get_trips.assert_called_once_with(
            {"user_id": user_id, "status": "planning"}, 50, 0
        )

    @pytest.mark.asyncio
    async def test_share_trip_success(
        self, trip_service, mock_database_service, mock_user_service, sample_trip_data
    ):
        """Test successful trip sharing."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        share_request = TripShareRequest(
            user_emails=["friend@example.com"],
            permission_level="view",
            message="Check out our trip!",
        )

        # Mock the update for visibility change
        updated_trip_data = sample_trip_data.copy()
        updated_trip_data["visibility"] = TripVisibility.SHARED.value
        mock_database_service.update_trip.return_value = updated_trip_data

        collaborators = await trip_service.share_trip(trip_id, user_id, share_request)

        assert len(collaborators) == 1
        assert collaborators[0].email == "test@example.com"
        assert collaborators[0].permission_level == "view"

        mock_database_service.add_trip_collaborator.assert_called_once()

    @pytest.mark.asyncio
    async def test_share_trip_user_not_found(
        self, trip_service, mock_database_service, mock_user_service, sample_trip_data
    ):
        """Test trip sharing when user not found."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_user_service.get_user_by_email.return_value = None

        share_request = TripShareRequest(
            user_emails=["nonexistent@example.com"],
            permission_level="view",
        )

        collaborators = await trip_service.share_trip(trip_id, user_id, share_request)

        assert len(collaborators) == 0
        mock_database_service.add_trip_collaborator.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_success(
        self, trip_service, mock_database_service, mock_user_service, sample_trip_data
    ):
        """Test getting trip collaborators."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        collaborator_data = {
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_at": datetime.now(timezone.utc).isoformat(),
        }

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborators.return_value = [collaborator_data]

        collaborators = await trip_service.get_trip_collaborators(trip_id, user_id)

        assert len(collaborators) == 1
        assert collaborators[0].email == "test@example.com"
        assert collaborators[0].permission_level == "edit"

    @pytest.mark.asyncio
    async def test_search_trips_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip search."""
        user_id = str(uuid4())

        mock_database_service.search_trips.return_value = [sample_trip_data]

        results = await trip_service.search_trips(
            user_id,
            query="Europe",
            destinations=["Paris", "Rome"],
            tags=["vacation"],
        )

        assert len(results) == 1
        assert results[0].title == "Summer Europe Trip"

        mock_database_service.search_trips.assert_called_once()
        search_filters = mock_database_service.search_trips.call_args[0][0]
        assert search_filters["query"] == "Europe"
        assert search_filters["destinations"] == ["Paris", "Rome"]
        assert search_filters["tags"] == ["vacation"]

    @pytest.mark.asyncio
    async def test_search_trips_with_date_range(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip search with date range filter."""
        user_id = str(uuid4())

        date_range = {
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc) + timedelta(days=60),
        }

        mock_database_service.search_trips.return_value = [sample_trip_data]

        results = await trip_service.search_trips(user_id, date_range=date_range)

        assert len(results) == 1

        search_filters = mock_database_service.search_trips.call_args[0][0]
        assert "date_range" in search_filters

    @pytest.mark.asyncio
    async def test_check_trip_access_owner(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip access check for owner."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        has_access = await trip_service._check_trip_access(trip_id, user_id)

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_trip_access_collaborator(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip access check for collaborator."""
        collaborator_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborator.return_value = {
            "user_id": collaborator_id,
            "permission_level": "view",
        }

        has_access = await trip_service._check_trip_access(trip_id, collaborator_id)

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_trip_access_public(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip access check for public trip."""
        random_user_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        # Make trip public
        sample_trip_data["visibility"] = TripVisibility.PUBLIC.value
        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        has_access = await trip_service._check_trip_access(trip_id, random_user_id)

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_edit_access_owner(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test edit access check for owner."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        has_access = await trip_service._check_trip_edit_access(trip_id, user_id)

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_edit_access_collaborator_with_edit(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test edit access check for collaborator with edit permission."""
        collaborator_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborator.return_value = {
            "user_id": collaborator_id,
            "permission_level": "edit",
        }

        has_access = await trip_service._check_trip_edit_access(
            trip_id, collaborator_id
        )

        assert has_access is True

    @pytest.mark.asyncio
    async def test_check_edit_access_collaborator_view_only(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test edit access check for view-only collaborator."""
        collaborator_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborator.return_value = {
            "user_id": collaborator_id,
            "permission_level": "view",
        }

        has_access = await trip_service._check_trip_edit_access(
            trip_id, collaborator_id
        )

        assert has_access is False

    @pytest.mark.asyncio
    async def test_build_trip_response(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test building trip response from database data."""
        trip_response = await trip_service._build_trip_response(sample_trip_data)

        assert isinstance(trip_response, TripResponse)
        assert trip_response.id == sample_trip_data["id"]
        assert trip_response.title == "Summer Europe Trip"
        assert len(trip_response.destinations) == 2
        assert trip_response.budget.total_budget == 5000.00
        assert trip_response.status == TripStatus.PLANNING
        assert trip_response.visibility == TripVisibility.PRIVATE

    @pytest.mark.asyncio
    @patch(
        "tripsage_core.services.infrastructure.database_service.get_database_service"
    )
    @patch("tripsage_core.services.business.user_service.UserService")
    async def test_get_trip_service_dependency(
        self, mock_user_service_class, mock_get_db_service
    ):
        """Test the dependency injection function."""
        # Mock the dependencies
        mock_db_service = AsyncMock()
        mock_get_db_service.return_value = mock_db_service
        mock_user_service = AsyncMock()
        mock_user_service_class.return_value = mock_user_service

        service = await get_trip_service()
        assert isinstance(service, TripService)

        # Verify dependencies were called correctly
        mock_get_db_service.assert_called_once()
        mock_user_service_class.assert_called_once_with(
            database_service=mock_db_service
        )

    @pytest.mark.asyncio
    async def test_invalid_date_validation(self, trip_service):
        """Test date validation in trip creation."""
        # Test with end date before start date
        with pytest.raises(ValidationError) as exc_info:
            TripCreateRequest(
                title="Invalid Trip",
                start_date=datetime.now(timezone.utc) + timedelta(days=10),
                end_date=datetime.now(timezone.utc) + timedelta(days=5),
                destinations=[],
            )

        assert "End date must be after start date" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_service_error_handling(
        self, trip_service, mock_database_service, sample_trip_create_request
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.create_trip.side_effect = Exception("Database error")

        # The service should not raise but log the error
        with pytest.raises(Exception) as exc_info:
            await trip_service.create_trip(user_id, sample_trip_create_request)

        assert "Database error" in str(exc_info.value)
