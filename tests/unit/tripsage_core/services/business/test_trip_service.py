"""
Comprehensive test suite for TripService.

This module tests the TripService with realistic test data that aligns
with the actual service implementation. Uses modern pytest patterns
and proper mocking of dependencies.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.exceptions import (
    CoreAuthorizationError,
    CoreResourceNotFoundError,
)
from tripsage_core.models.schemas_common.enums import (
    TripStatus,
    TripType,
    TripVisibility,
)
from tripsage_core.models.trip import BudgetBreakdown, EnhancedBudget, TripPreferences
from tripsage_core.services.business.trip_service import (
    TripCreateRequest,
    TripLocation,
    TripResponse,
    TripService,
    TripUpdateRequest,
    get_trip_service,
)


class TestTripService:
    """Test suite for TripService functionality."""

    @pytest.fixture
    def mock_database_service(self):
        """Create mock database service with comprehensive trip operations."""
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
        db.get_trip_related_counts = AsyncMock(
            return_value={
                "notes": 0,
                "attachments": 0,
                "collaborators": 0,
            }
        )
        return db

    @pytest.fixture
    def mock_user_service(self):
        """Create mock user service."""
        return AsyncMock()

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
        from datetime import timedelta

        now = datetime.now(timezone.utc).replace(microsecond=0)
        return TripCreateRequest(
            title="Summer Europe Trip",
            description="A wonderful journey through European capitals",
            start_date=now,
            end_date=now + timedelta(days=7),
            destination="Paris, France",
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
            budget=EnhancedBudget(
                total=5000.00,
                currency="USD",
                spent=0.00,
                breakdown=BudgetBreakdown(
                    accommodation=2000.00,
                    transportation=1500.00,
                    food=1000.00,
                    activities=500.00,
                ),
            ),
            travelers=2,
            trip_type=TripType.LEISURE,
            visibility=TripVisibility.PRIVATE,
            tags=["vacation", "europe", "cities"],
            preferences=TripPreferences(),
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
            "start_date": now,
            "end_date": now,
            "destination": "Paris, France",
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
            "budget_breakdown": {
                "total": 5000.00,
                "currency": "USD",
                "spent": 0.00,
                "breakdown": {
                    "accommodation": 2000.00,
                    "transportation": 1500.00,
                    "food": 1000.00,
                    "activities": 500.00,
                },
            },
            "travelers": 2,
            "trip_type": TripType.LEISURE.value,
            "status": TripStatus.PLANNING.value,
            "visibility": TripVisibility.PRIVATE.value,
            "tags": ["vacation", "europe", "cities"],
            "preferences_extended": {},
            "created_at": now,
            "updated_at": now,
        }

    # Test Trip Creation

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
        sample_trip_data["user_id"] = user_id

        # Mock database operations
        mock_database_service.create_trip.return_value = sample_trip_data

        result = await trip_service.create_trip(user_id, sample_trip_create_request)

        # Assertions
        assert isinstance(result, TripResponse)
        assert str(result.user_id) == user_id
        assert result.title == sample_trip_create_request.title
        assert result.description == sample_trip_create_request.description
        assert len(result.destinations) == 2
        assert result.destinations[0].name == "Paris"
        assert result.destinations[1].name == "Rome"
        assert result.status == TripStatus.PLANNING
        assert result.budget.total == 5000.00
        assert result.budget.currency == "USD"

        # Verify service calls
        mock_database_service.create_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_trip_invalid_dates(self, trip_service):
        """Test trip creation with invalid dates (end before start)."""
        now = datetime.now(timezone.utc)

        # This should raise ValidationError during model creation
        with pytest.raises(ValidationError) as exc_info:
            TripCreateRequest(
                title="Invalid Trip",
                description="This should fail",
                start_date=now,
                end_date=now,  # Same as start date, should fail
                destination="Test City",
                budget=EnhancedBudget(
                    total=1000.00,
                    currency="USD",
                    spent=0.00,
                    breakdown=BudgetBreakdown(
                        accommodation=500.00,
                        transportation=300.00,
                        food=200.00,
                        activities=0.00,
                    ),
                ),
            )

        assert "End date must be after start date" in str(exc_info.value)

    # Test Trip Retrieval

    @pytest.mark.asyncio
    async def test_get_trip_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip retrieval."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        # Mock the access check to return True (user owns the trip)
        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        result = await trip_service.get_trip(trip_id, user_id)

        assert result is not None
        assert isinstance(result, TripResponse)
        assert str(result.id) == trip_id
        assert result.title == "Summer Europe Trip"
        assert result.status == TripStatus.PLANNING

        # get_trip_by_id called twice: once in _check_trip_access, once in get_trip
        assert mock_database_service.get_trip_by_id.call_count == 2

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

        # User is not the owner
        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborators.return_value = []

        result = await trip_service.get_trip(trip_id, different_user_id)

        assert result is None

    # Test Trip Updates

    @pytest.mark.asyncio
    async def test_update_trip_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip update."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        # Mock access check to return the trip
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
                "updated_at": datetime.now(timezone.utc),
            }
        )
        mock_database_service.update_trip.return_value = updated_trip_data

        result = await trip_service.update_trip(trip_id, user_id, update_request)

        assert isinstance(result, TripResponse)
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

        with pytest.raises(CoreAuthorizationError) as exc_info:
            await trip_service.update_trip(trip_id, user_id, update_request)

        assert "You don't have permission to update this trip" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_trip_no_permission(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test trip update without permission."""
        different_user_id = str(uuid4())
        trip_id = sample_trip_data["id"]

        mock_database_service.get_trip_by_id.return_value = sample_trip_data
        mock_database_service.get_trip_collaborators.return_value = []

        update_request = TripUpdateRequest(title="Unauthorized Update")

        with pytest.raises(CoreAuthorizationError) as exc_info:
            await trip_service.update_trip(trip_id, different_user_id, update_request)

        assert "You don't have permission to update this trip" in str(exc_info.value)

    # Test Trip Deletion

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
        mock_database_service.get_trip_collaborators.return_value = []

        with pytest.raises(CoreAuthorizationError) as exc_info:
            await trip_service.delete_trip(trip_id, different_user_id)

        assert "You don't have permission to delete this trip" in str(exc_info.value)

    # Test User Trips Listing

    @pytest.mark.asyncio
    async def test_get_user_trips_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful user trips listing."""
        user_id = str(uuid4())

        mock_database_service.get_trips.return_value = [sample_trip_data]

        results = await trip_service.get_user_trips(user_id)

        assert len(results) == 1
        assert isinstance(results[0], TripResponse)
        assert str(results[0].id) == sample_trip_data["id"]
        assert results[0].title == "Summer Europe Trip"

        mock_database_service.get_trips.assert_called_once_with(
            filters={"user_id": user_id}, limit=50, offset=0
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
            filters={"user_id": user_id, "status": "planning"}, limit=50, offset=0
        )

    # Test Trip Sharing

    @pytest.mark.asyncio
    async def test_share_trip_success(
        self, trip_service, mock_database_service, mock_user_service, sample_trip_data
    ):
        """Test successful trip sharing."""
        user_id = str(uuid4())
        trip_id = sample_trip_data["id"]
        sample_trip_data["user_id"] = user_id

        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        # Mock user lookup
        mock_collaborator = AsyncMock()
        mock_collaborator.id = str(uuid4())
        mock_collaborator.email = "friend@example.com"
        mock_user_service.get_user_by_email.return_value = mock_collaborator

        # Mock successful sharing
        mock_database_service.add_trip_collaborator.return_value = True

        result = await trip_service.share_trip(
            trip_id, user_id, mock_collaborator.id, "view"
        )

        assert result is True
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
        mock_user_service.get_user.return_value = None

        # The service will raise NotFoundError for non-existent user
        with pytest.raises(CoreResourceNotFoundError):
            await trip_service.share_trip(
                trip_id, user_id, "nonexistent_user_id", "view"
            )

    # Test Search Functionality

    @pytest.mark.asyncio
    async def test_search_trips_success(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test successful trip search."""
        user_id = str(uuid4())
        sample_trip_data["user_id"] = user_id  # Make sure user owns the trip

        mock_database_service.search_trips.return_value = [sample_trip_data]
        # Mock the access check - search calls _check_trip_access for each result
        mock_database_service.get_trip_by_id.return_value = sample_trip_data

        results = await trip_service.search_trips(user_id, query="Europe")

        assert len(results) == 1
        assert isinstance(results[0], TripResponse)
        assert results[0].title == "Summer Europe Trip"

        mock_database_service.search_trips.assert_called_once_with(
            query="Europe", filters={"user_id": user_id}, limit=50, offset=0
        )

    # Test Access Control

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
        mock_database_service.get_trip_collaborators.return_value = [
            {"user_id": collaborator_id, "permission": "view"}
        ]

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

    # Test Response Building

    @pytest.mark.asyncio
    async def test_build_trip_response(
        self, trip_service, mock_database_service, sample_trip_data
    ):
        """Test building trip response from database data."""
        trip_response = await trip_service._build_trip_response(sample_trip_data)

        assert isinstance(trip_response, TripResponse)
        assert str(trip_response.id) == sample_trip_data["id"]
        assert trip_response.title == "Summer Europe Trip"
        assert len(trip_response.destinations) == 2
        assert trip_response.budget.total == 5000.00
        assert trip_response.status == TripStatus.PLANNING
        assert trip_response.visibility == TripVisibility.PRIVATE

    # Test Dependency Injection

    @pytest.mark.asyncio
    @patch("tripsage_core.services.infrastructure.database_service.DatabaseService")
    @patch("tripsage_core.services.business.user_service.UserService")
    async def test_get_trip_service_dependency(
        self, mock_user_service_class, mock_database_service_class
    ):
        """Test the dependency injection function."""
        # Mock the service classes
        mock_db_service = AsyncMock()
        mock_database_service_class.return_value = mock_db_service
        mock_user_service = AsyncMock()
        mock_user_service_class.return_value = mock_user_service

        service = await get_trip_service()
        assert isinstance(service, TripService)

        # Verify dependencies were instantiated
        mock_database_service_class.assert_called_once()
        mock_user_service_class.assert_called_once()

    # Test Error Handling

    @pytest.mark.asyncio
    async def test_service_error_handling(
        self, trip_service, mock_database_service, sample_trip_create_request
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.create_trip.side_effect = Exception("Database error")

        # The service should propagate the error
        with pytest.raises(Exception) as exc_info:
            await trip_service.create_trip(user_id, sample_trip_create_request)

        assert "Database error" in str(exc_info.value)

    # Test Edge Cases

    @pytest.mark.asyncio
    async def test_create_trip_minimal_data(self, trip_service, mock_database_service):
        """Test trip creation with minimal required data."""
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        minimal_request = TripCreateRequest(
            title="Minimal Trip",
            start_date=now,
            end_date=now.replace(hour=23, minute=59, second=59),
            destination="Test City",
            budget=EnhancedBudget(
                total=1000.00,
                currency="USD",
                spent=0.00,
                breakdown=BudgetBreakdown(
                    accommodation=400.00,
                    transportation=300.00,
                    food=200.00,
                    activities=100.00,
                ),
            ),
        )

        # Mock successful creation
        mock_trip_data = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": "Minimal Trip",
            "description": None,
            "start_date": now,
            "end_date": now.replace(hour=23, minute=59, second=59),
            "destination": "Test City",
            "destinations": [],
            "budget_breakdown": {
                "total": 1000.00,
                "currency": "USD",
                "spent": 0.00,
                "breakdown": {
                    "accommodation": 400.00,
                    "transportation": 300.00,
                    "food": 200.00,
                    "activities": 100.00,
                },
            },
            "travelers": 1,
            "trip_type": TripType.LEISURE.value,
            "status": TripStatus.PLANNING.value,
            "visibility": TripVisibility.PRIVATE.value,
            "tags": [],
            "preferences_extended": {},
            "created_at": now,
            "updated_at": now,
        }
        mock_database_service.create_trip.return_value = mock_trip_data

        result = await trip_service.create_trip(user_id, minimal_request)

        assert isinstance(result, TripResponse)
        assert result.title == "Minimal Trip"
        assert result.travelers == 1
        assert len(result.destinations) == 0
        assert len(result.tags) == 0
