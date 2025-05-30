"""
Comprehensive tests for TripService.

This module provides full test coverage for trip management operations
including trip creation, itinerary management, sharing, and optimization.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreResourceNotFoundError as NotFoundError,
)
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.trip_service import (
    TripBudget,
    TripCreateRequest,
    TripService,
    TripStatus,
    TripUpdateRequest,
    get_trip_service,
)
from tripsage_core.services.business.trip_service import (
    TripVisibility as TripPrivacy,
)


# Define mock classes for testing
class BudgetCategory(str, Enum):
    ACCOMMODATION = "accommodation"
    TRANSPORTATION = "transportation"
    FOOD = "food"
    ACTIVITIES = "activities"


class ParticipantRole(str, Enum):
    ORGANIZER = "organizer"
    MEMBER = "member"
    VIEWER = "viewer"


# Mock data classes
class Trip(TripSageModel):
    id: str
    user_id: str
    title: str
    description: str
    start_date: datetime
    end_date: datetime
    destination: str
    status: TripStatus
    privacy: TripPrivacy
    created_at: datetime
    updated_at: datetime
    tags: list[str]
    itinerary: "TripItinerary"
    budget: TripBudget
    participants: list["TripParticipant"]
    metadata: dict


class TripItinerary(TripSageModel):
    trip_id: str
    days: list
    accommodations: list
    flights: list
    activities: list
    notes: list


class TripParticipant(TripSageModel):
    trip_id: str
    user_id: str
    role: ParticipantRole
    joined_at: datetime
    permissions: list[str]


class TripSearchRequest(TripSageModel):
    query: Optional[str] = None
    destinations: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    status: Optional[list[TripStatus]] = None
    limit: int = 10


class TestTripService:
    """Test suite for TripService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_memory_service(self):
        """Mock memory service."""
        memory = AsyncMock()
        return memory

    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service."""
        notification = AsyncMock()
        return notification

    @pytest.fixture
    def trip_service(
        self, mock_database_service, mock_memory_service, mock_notification_service
    ):
        """Create TripService instance with mocked dependencies."""
        return TripService(
            database_service=mock_database_service,
            memory_service=mock_memory_service,
            notification_service=mock_notification_service,
        )

    @pytest.fixture
    def sample_trip_create_request(self):
        """Sample trip creation request."""
        return TripCreateRequest(
            title="Summer Europe Trip",
            description="A wonderful journey through European capitals",
            start_date=datetime.now(timezone.utc) + timedelta(days=30),
            end_date=datetime.now(timezone.utc) + timedelta(days=45),
            destination="Europe",
            budget_amount=Decimal("5000.00"),
            budget_currency="USD",
            privacy=TripPrivacy.PRIVATE,
            tags=["vacation", "europe", "cities"],
        )

    @pytest.fixture
    def sample_trip(self):
        """Sample trip object."""
        trip_id = str(uuid4())
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return Trip(
            id=trip_id,
            user_id=user_id,
            title="Summer Europe Trip",
            description="A wonderful journey through European capitals",
            start_date=now + timedelta(days=30),
            end_date=now + timedelta(days=45),
            destination="Europe",
            status=TripStatus.PLANNING,
            privacy=TripPrivacy.PRIVATE,
            created_at=now,
            updated_at=now,
            tags=["vacation", "europe", "cities"],
            itinerary=TripItinerary(
                trip_id=trip_id,
                days=[],
                accommodations=[],
                flights=[],
                activities=[],
                notes=[],
            ),
            budget=TripBudget(
                trip_id=trip_id,
                total_amount=Decimal("5000.00"),
                currency="USD",
                spent_amount=Decimal("0.00"),
                categories={
                    BudgetCategory.ACCOMMODATION: Decimal("2000.00"),
                    BudgetCategory.TRANSPORTATION: Decimal("1500.00"),
                    BudgetCategory.FOOD: Decimal("1000.00"),
                    BudgetCategory.ACTIVITIES: Decimal("500.00"),
                },
            ),
            participants=[
                TripParticipant(
                    trip_id=trip_id,
                    user_id=user_id,
                    role=ParticipantRole.ORGANIZER,
                    joined_at=now,
                    permissions=["edit", "invite", "delete"],
                )
            ],
            metadata={
                "climate": "temperate",
                "time_zones": ["CET", "GMT"],
                "languages": ["en", "fr", "de", "it"],
            },
        )

    async def test_create_trip_success(
        self,
        trip_service,
        mock_database_service,
        mock_memory_service,
        sample_trip_create_request,
    ):
        """Test successful trip creation."""
        user_id = str(uuid4())

        # Mock database operations
        mock_database_service.store_trip.return_value = None
        mock_database_service.add_trip_participant.return_value = None

        # Mock memory service
        mock_memory_service.create_trip_context.return_value = None

        result = await trip_service.create_trip(user_id, sample_trip_create_request)

        # Assertions
        assert result.user_id == user_id
        assert result.title == sample_trip_create_request.title
        assert result.description == sample_trip_create_request.description
        assert result.destination == sample_trip_create_request.destination
        assert result.status == TripStatus.PLANNING
        assert result.budget.total_amount == sample_trip_create_request.budget_amount
        assert len(result.participants) == 1
        assert result.participants[0].role == ParticipantRole.ORGANIZER

        # Verify service calls
        mock_database_service.store_trip.assert_called_once()
        mock_memory_service.create_trip_context.assert_called_once()

    async def test_create_trip_invalid_dates(
        self, trip_service, sample_trip_create_request
    ):
        """Test trip creation with invalid dates."""
        user_id = str(uuid4())

        # Set end date before start date
        sample_trip_create_request.end_date = (
            sample_trip_create_request.start_date - timedelta(days=1)
        )

        with pytest.raises(ValidationError, match="End date must be after start date"):
            await trip_service.create_trip(user_id, sample_trip_create_request)

    async def test_create_trip_past_dates(
        self, trip_service, sample_trip_create_request
    ):
        """Test trip creation with past dates."""
        user_id = str(uuid4())

        # Set dates in the past
        sample_trip_create_request.start_date = datetime.now(timezone.utc) - timedelta(
            days=1
        )
        sample_trip_create_request.end_date = datetime.now(timezone.utc) + timedelta(
            days=5
        )

        with pytest.raises(ValidationError, match="Start date cannot be in the past"):
            await trip_service.create_trip(user_id, sample_trip_create_request)

    async def test_get_trip_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful trip retrieval."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()

        result = await trip_service.get_trip(sample_trip.id, sample_trip.user_id)

        assert result is not None
        assert result.id == sample_trip.id
        assert result.title == sample_trip.title
        mock_database_service.get_trip.assert_called_once()

    async def test_get_trip_not_found(self, trip_service, mock_database_service):
        """Test trip retrieval when trip doesn't exist."""
        trip_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_trip.return_value = None

        result = await trip_service.get_trip(trip_id, user_id)

        assert result is None

    async def test_get_trip_access_denied(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test trip retrieval with access denied."""
        different_user_id = str(uuid4())

        mock_database_service.get_trip.return_value = sample_trip.model_dump()

        result = await trip_service.get_trip(sample_trip.id, different_user_id)

        assert result is None

    async def test_update_trip_success(
        self, trip_service, mock_database_service, mock_memory_service, sample_trip
    ):
        """Test successful trip update."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.update_trip.return_value = None
        mock_memory_service.update_trip_context.return_value = None

        update_request = TripUpdateRequest(
            title="Updated Europe Trip",
            description="Updated description",
            tags=["vacation", "europe", "updated"],
        )

        result = await trip_service.update_trip(
            sample_trip.id, sample_trip.user_id, update_request
        )

        assert result.title == "Updated Europe Trip"
        assert result.description == "Updated description"
        assert result.tags == ["vacation", "europe", "updated"]
        assert result.updated_at > sample_trip.updated_at

        mock_database_service.update_trip.assert_called_once()
        mock_memory_service.update_trip_context.assert_called_once()

    async def test_update_trip_not_found(self, trip_service, mock_database_service):
        """Test trip update when trip doesn't exist."""
        trip_id = str(uuid4())
        user_id = str(uuid4())

        mock_database_service.get_trip.return_value = None

        update_request = TripUpdateRequest(title="Updated Trip")

        with pytest.raises(NotFoundError, match="Trip not found"):
            await trip_service.update_trip(trip_id, user_id, update_request)

    async def test_delete_trip_success(
        self, trip_service, mock_database_service, mock_memory_service, sample_trip
    ):
        """Test successful trip deletion."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.delete_trip.return_value = True
        mock_memory_service.delete_trip_context.return_value = None

        result = await trip_service.delete_trip(sample_trip.id, sample_trip.user_id)

        assert result is True
        mock_database_service.delete_trip.assert_called_once()
        mock_memory_service.delete_trip_context.assert_called_once()

    async def test_delete_trip_not_organizer(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test trip deletion by non-organizer."""
        different_user_id = str(uuid4())

        # Add non-organizer participant
        sample_trip.participants.append(
            TripParticipant(
                trip_id=sample_trip.id,
                user_id=different_user_id,
                role=ParticipantRole.MEMBER,
                joined_at=datetime.now(timezone.utc),
                permissions=["view"],
            )
        )

        mock_database_service.get_trip.return_value = sample_trip.model_dump()

        with pytest.raises(ValidationError, match="Only trip organizer can delete"):
            await trip_service.delete_trip(sample_trip.id, different_user_id)

    async def test_list_user_trips_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful user trips listing."""
        user_id = str(uuid4())

        mock_database_service.get_user_trips.return_value = [sample_trip.model_dump()]

        results = await trip_service.list_user_trips(user_id)

        assert len(results) == 1
        assert results[0].id == sample_trip.id
        mock_database_service.get_user_trips.assert_called_once()

    async def test_search_trips_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful trip search."""
        user_id = str(uuid4())

        search_request = TripSearchRequest(
            query="Europe",
            destinations=["Europe"],
            tags=["vacation"],
            status=[TripStatus.PLANNING],
            limit=10,
        )

        mock_database_service.search_trips.return_value = [sample_trip.model_dump()]

        results = await trip_service.search_trips(user_id, search_request)

        assert len(results) == 1
        assert results[0].destination == "Europe"
        mock_database_service.search_trips.assert_called_once()

    async def test_add_participant_success(
        self,
        trip_service,
        mock_database_service,
        mock_notification_service,
        sample_trip,
    ):
        """Test successful participant addition."""
        new_participant_id = str(uuid4())

        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.add_trip_participant.return_value = None
        mock_notification_service.send_trip_invitation.return_value = None

        result = await trip_service.add_participant(
            sample_trip.id,
            sample_trip.user_id,
            new_participant_id,
            ParticipantRole.MEMBER,
        )

        assert result.user_id == new_participant_id
        assert result.role == ParticipantRole.MEMBER
        assert "view" in result.permissions

        mock_database_service.add_trip_participant.assert_called_once()
        mock_notification_service.send_trip_invitation.assert_called_once()

    async def test_add_participant_already_exists(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test adding participant who already exists."""
        # Try to add the organizer again
        existing_participant_id = sample_trip.user_id

        mock_database_service.get_trip.return_value = sample_trip.model_dump()

        with pytest.raises(ValidationError, match="User is already a participant"):
            await trip_service.add_participant(
                sample_trip.id,
                sample_trip.user_id,
                existing_participant_id,
                ParticipantRole.MEMBER,
            )

    async def test_remove_participant_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful participant removal."""
        participant_to_remove = str(uuid4())

        # Add a member participant
        sample_trip.participants.append(
            TripParticipant(
                trip_id=sample_trip.id,
                user_id=participant_to_remove,
                role=ParticipantRole.MEMBER,
                joined_at=datetime.now(timezone.utc),
                permissions=["view"],
            )
        )

        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.remove_trip_participant.return_value = True

        result = await trip_service.remove_participant(
            sample_trip.id, sample_trip.user_id, participant_to_remove
        )

        assert result is True
        mock_database_service.remove_trip_participant.assert_called_once()

    async def test_remove_participant_organizer(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test removing organizer participant."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()

        with pytest.raises(ValidationError, match="Cannot remove trip organizer"):
            await trip_service.remove_participant(
                sample_trip.id,
                sample_trip.user_id,
                sample_trip.user_id,  # Try to remove organizer
            )

    async def test_update_budget_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful budget update."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.update_trip_budget.return_value = None

        new_budget_data = {
            "total_amount": Decimal("6000.00"),
            "categories": {
                BudgetCategory.ACCOMMODATION: Decimal("2500.00"),
                BudgetCategory.TRANSPORTATION: Decimal("2000.00"),
                BudgetCategory.FOOD: Decimal("1000.00"),
                BudgetCategory.ACTIVITIES: Decimal("500.00"),
            },
        }

        result = await trip_service.update_budget(
            sample_trip.id, sample_trip.user_id, new_budget_data
        )

        assert result.total_amount == Decimal("6000.00")
        assert result.categories[BudgetCategory.ACCOMMODATION] == Decimal("2500.00")
        mock_database_service.update_trip_budget.assert_called_once()

    async def test_record_expense_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful expense recording."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.record_trip_expense.return_value = None

        expense_data = {
            "amount": Decimal("150.00"),
            "currency": "USD",
            "category": BudgetCategory.FOOD,
            "description": "Dinner at restaurant",
            "date": datetime.now(timezone.utc),
            "location": "Paris, France",
        }

        await trip_service.record_expense(
            sample_trip.id, sample_trip.user_id, expense_data
        )

        mock_database_service.record_trip_expense.assert_called_once()

    async def test_get_trip_statistics_success(
        self, trip_service, mock_database_service
    ):
        """Test successful trip statistics retrieval."""
        user_id = str(uuid4())

        stats_data = {
            "total_trips": 15,
            "active_trips": 3,
            "completed_trips": 10,
            "cancelled_trips": 2,
            "total_destinations": 25,
            "total_budget_spent": Decimal("45000.00"),
            "average_trip_duration": 8.5,
            "favorite_destinations": ["Europe", "Asia", "North America"],
            "trips_by_month": {},
            "budget_by_category": {},
        }

        mock_database_service.get_user_trip_statistics.return_value = stats_data

        result = await trip_service.get_trip_statistics(user_id)

        assert result["total_trips"] == 15
        assert result["active_trips"] == 3
        assert result["total_budget_spent"] == Decimal("45000.00")

    async def test_clone_trip_success(
        self, trip_service, mock_database_service, mock_memory_service, sample_trip
    ):
        """Test successful trip cloning."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.store_trip.return_value = None
        mock_database_service.add_trip_participant.return_value = None
        mock_memory_service.create_trip_context.return_value = None

        clone_options = {
            "include_itinerary": True,
            "include_budget": True,
            "include_participants": False,
            "new_dates": {
                "start_date": datetime.now(timezone.utc) + timedelta(days=90),
                "end_date": datetime.now(timezone.utc) + timedelta(days=105),
            },
        }

        result = await trip_service.clone_trip(
            sample_trip.id, sample_trip.user_id, clone_options
        )

        assert result.id != sample_trip.id  # Different ID
        assert result.title.startswith("Copy of ")
        assert len(result.participants) == 1  # Only organizer
        assert result.participants[0].user_id == sample_trip.user_id

    async def test_optimize_itinerary_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful itinerary optimization."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.update_trip_itinerary.return_value = None

        optimization_options = {
            "optimize_for": "cost",  # or "time", "experience"
            "constraints": {
                "max_travel_time_per_day": 4,
                "preferred_accommodation_type": "hotel",
            },
        }

        # Mock optimization result
        with patch.object(
            trip_service, "_optimize_itinerary_algorithm"
        ) as mock_optimize:
            mock_optimize.return_value = {
                "optimized_score": 0.85,
                "changes_made": 5,
                "estimated_savings": Decimal("200.00"),
            }

            result = await trip_service.optimize_itinerary(
                sample_trip.id, sample_trip.user_id, optimization_options
            )

            assert result["optimized_score"] == 0.85
            assert result["changes_made"] == 5
            mock_optimize.assert_called_once()

    async def test_share_trip_success(
        self,
        trip_service,
        mock_database_service,
        mock_notification_service,
        sample_trip,
    ):
        """Test successful trip sharing."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.create_trip_share_link.return_value = (
            "https://tripsage.com/shared/abc123"
        )
        mock_notification_service.send_trip_share_notification.return_value = None

        share_options = {
            "share_type": "view_only",
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
            "password_protected": False,
            "share_with_emails": ["friend@example.com"],
        }

        result = await trip_service.share_trip(
            sample_trip.id, sample_trip.user_id, share_options
        )

        assert result["share_url"] == "https://tripsage.com/shared/abc123"
        assert "expires_at" in result
        mock_notification_service.send_trip_share_notification.assert_called_once()

    async def test_generate_trip_report_success(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test successful trip report generation."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.get_trip_expenses.return_value = []

        report_options = {
            "format": "pdf",
            "include_budget": True,
            "include_itinerary": True,
            "include_photos": False,
        }

        # Mock report generation
        with patch.object(trip_service, "_generate_report_content") as mock_generate:
            mock_generate.return_value = {
                "report_url": "https://storage.example.com/reports/trip_123.pdf",
                "generated_at": datetime.now(timezone.utc),
                "file_size": 2048576,
            }

            result = await trip_service.generate_trip_report(
                sample_trip.id, sample_trip.user_id, report_options
            )

            assert "report_url" in result
            assert result["file_size"] > 0
            mock_generate.assert_called_once()

    def test_calculate_trip_duration(self, trip_service, sample_trip):
        """Test trip duration calculation."""
        duration = trip_service._calculate_trip_duration(sample_trip)
        expected_duration = (sample_trip.end_date - sample_trip.start_date).days
        assert duration == expected_duration

    def test_validate_budget_categories(self, trip_service):
        """Test budget category validation."""
        valid_budget = {
            BudgetCategory.ACCOMMODATION: Decimal("2000.00"),
            BudgetCategory.TRANSPORTATION: Decimal("1500.00"),
            BudgetCategory.FOOD: Decimal("1000.00"),
        }

        total = trip_service._calculate_budget_total(valid_budget)
        assert total == Decimal("4500.00")

    async def test_check_trip_access_permissions(self, trip_service, sample_trip):
        """Test trip access permission checking."""
        # Organizer should have full access
        has_access = await trip_service._check_trip_access(
            sample_trip, sample_trip.user_id, "edit"
        )
        assert has_access is True

        # Non-participant should not have access
        random_user_id = str(uuid4())
        has_access = await trip_service._check_trip_access(
            sample_trip, random_user_id, "view"
        )
        assert has_access is False

    async def test_service_error_handling(
        self, trip_service, mock_database_service, sample_trip_create_request
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.store_trip.side_effect = Exception("Database error")

        with pytest.raises(ServiceError, match="Failed to create trip"):
            await trip_service.create_trip(user_id, sample_trip_create_request)

    def test_get_trip_service_dependency(self):
        """Test the dependency injection function."""
        service = get_trip_service()
        assert isinstance(service, TripService)

    async def test_trip_status_transitions(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test valid trip status transitions."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.update_trip.return_value = None

        # Planning -> Active (valid)
        sample_trip.status = TripStatus.PLANNING
        is_valid = await trip_service._validate_status_transition(
            sample_trip.status, TripStatus.ACTIVE
        )
        assert is_valid is True

        # Active -> Completed (valid)
        is_valid = await trip_service._validate_status_transition(
            TripStatus.ACTIVE, TripStatus.COMPLETED
        )
        assert is_valid is True

        # Completed -> Planning (invalid)
        is_valid = await trip_service._validate_status_transition(
            TripStatus.COMPLETED, TripStatus.PLANNING
        )
        assert is_valid is False

    async def test_participant_permission_management(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test participant permission management."""
        participant_id = str(uuid4())

        # Add participant with limited permissions
        sample_trip.participants.append(
            TripParticipant(
                trip_id=sample_trip.id,
                user_id=participant_id,
                role=ParticipantRole.MEMBER,
                joined_at=datetime.now(timezone.utc),
                permissions=["view"],
            )
        )

        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.update_trip_participant.return_value = None

        # Update permissions
        new_permissions = ["view", "edit_itinerary", "add_expenses"]
        result = await trip_service.update_participant_permissions(
            sample_trip.id,
            sample_trip.user_id,  # Organizer updating permissions
            participant_id,
            new_permissions,
        )

        assert result is True
        mock_database_service.update_trip_participant.assert_called_once()

    async def test_trip_collaboration_features(
        self,
        trip_service,
        mock_database_service,
        mock_notification_service,
        sample_trip,
    ):
        """Test trip collaboration features."""
        collaborator_id = str(uuid4())

        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.add_trip_comment.return_value = None
        mock_notification_service.notify_trip_participants.return_value = None

        comment_data = {
            "content": "Great idea for the itinerary!",
            "context": "day_2_activities",
            "mentioned_users": [sample_trip.user_id],
        }

        await trip_service.add_trip_comment(
            sample_trip.id, collaborator_id, comment_data
        )

        mock_database_service.add_trip_comment.assert_called_once()
        mock_notification_service.notify_trip_participants.assert_called_once()

    async def test_trip_recommendation_engine(
        self, trip_service, mock_database_service, sample_trip
    ):
        """Test trip recommendation engine."""
        mock_database_service.get_trip.return_value = sample_trip.model_dump()
        mock_database_service.get_user_trip_history.return_value = []

        # Mock recommendation algorithm
        with patch.object(trip_service, "_generate_recommendations") as mock_recommend:
            mock_recommend.return_value = {
                "destinations": ["Barcelona", "Amsterdam", "Prague"],
                "activities": ["City walking tour", "Museum visits", "Local food tour"],
                "accommodations": ["Boutique hotel", "Historic inn"],
                "confidence_scores": [0.9, 0.85, 0.8],
            }

            recommendations = await trip_service.get_trip_recommendations(
                sample_trip.id, sample_trip.user_id
            )

            assert len(recommendations["destinations"]) == 3
            assert recommendations["confidence_scores"][0] == 0.9
            mock_recommend.assert_called_once()
