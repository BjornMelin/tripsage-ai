"""Comprehensive tests for ItineraryService.

This module provides full test coverage for itinerary management operations
including itinerary creation, optimization, conflict detection, and collaboration.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.itinerary_service import (
    ConflictType,
    Itinerary,
    ItineraryCreateRequest,
    ItineraryDay,
    ItineraryItem,
    ItineraryItemType,
    ItineraryService,
    ItineraryStatus,
    ItineraryUpdateRequest,
    OptimizationGoal,
    get_itinerary_service,
)


class TestItineraryService:
    """Test suite for ItineraryService."""

    @pytest.fixture
    def mock_database_service(self):
        """Mock database service."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_optimization_service(self):
        """Mock optimization service."""
        optimization = AsyncMock()
        return optimization

    @pytest.fixture
    def mock_maps_service(self):
        """Mock maps service."""
        maps = AsyncMock()
        return maps

    @pytest.fixture
    def mock_activity_service(self):
        """Mock activity service."""
        activity = AsyncMock()
        return activity

    @pytest.fixture
    def mock_collaboration_service(self):
        """Mock collaboration service."""
        collaboration = AsyncMock()
        return collaboration

    @pytest.fixture
    def itinerary_service(
        self,
        mock_database_service,
        mock_optimization_service,
        mock_maps_service,
        mock_activity_service,
        mock_collaboration_service,
    ):
        """Create ItineraryService instance with mocked dependencies."""
        return ItineraryService(
            database_service=mock_database_service,
            optimization_service=mock_optimization_service,
            maps_service=mock_maps_service,
            activity_service=mock_activity_service,
            collaboration_service=mock_collaboration_service,
        )

    @pytest.fixture
    def sample_itinerary_create_request(self):
        """Sample itinerary creation request."""
        base_date = datetime.now(UTC) + timedelta(days=30)

        return ItineraryCreateRequest(
            trip_id=str(uuid4()),
            title="Paris Adventure",
            description="A wonderful week exploring Paris",
            start_date=base_date,
            end_date=base_date + timedelta(days=6),
            destination="Paris, France",
            budget=Decimal("2000.00"),
            currency="EUR",
            preferences={
                "activity_types": ["sightseeing", "museums", "food"],
                "pace": "moderate",
                "transportation": "walking_public",
                "accessibility": [],
            },
        )

    @pytest.fixture
    def sample_itinerary_item(self):
        """Sample itinerary item."""
        return ItineraryItem(
            id=str(uuid4()),
            title="Visit Eiffel Tower",
            description="Iconic iron tower and symbol of Paris",
            activity_type=ItineraryItemType.SIGHTSEEING,
            location={
                "name": "Eiffel Tower",
                "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris",
                "coordinates": {"latitude": 48.8584, "longitude": 2.2945},
            },
            start_time=datetime.now(UTC) + timedelta(days=30, hours=10),
            end_time=datetime.now(UTC) + timedelta(days=30, hours=12),
            duration=timedelta(hours=2),
            cost=Decimal("25.00"),
            currency="EUR",
            booking_info={
                "required": True,
                "booking_url": "https://example.com/book",
                "contact": "+33123456789",
            },
            notes="Book tickets in advance to skip the line",
            tags=["landmark", "must-see", "photo-opportunity"],
            priority=1,
            status="planned",
        )

    @pytest.fixture
    def sample_itinerary_day(self, sample_itinerary_item):
        """Sample itinerary day."""
        day_date = datetime.now(UTC) + timedelta(days=30)

        return ItineraryDay(
            date=day_date.date(),
            title="Classic Paris Day",
            items=[sample_itinerary_item],
            total_cost=Decimal("125.00"),
            total_duration=timedelta(hours=8),
            transportation_between_items=[
                {
                    "from_item_id": sample_itinerary_item.id,
                    "to_item_id": str(uuid4()),
                    "mode": "walking",
                    "duration": timedelta(minutes=15),
                    "cost": Decimal("0.00"),
                }
            ],
            notes="Start early to avoid crowds",
            weather_forecast={
                "temperature": 20,
                "condition": "Partly cloudy",
                "precipitation_chance": 20,
            },
        )

    @pytest.fixture
    def sample_itinerary(self, sample_itinerary_day):
        """Sample itinerary object."""
        itinerary_id = str(uuid4())
        user_id = str(uuid4())
        trip_id = str(uuid4())
        now = datetime.now(UTC)

        return Itinerary(
            id=itinerary_id,
            user_id=user_id,
            trip_id=trip_id,
            title="Paris Adventure",
            description="A wonderful week exploring Paris",
            start_date=(now + timedelta(days=30)).date(),
            end_date=(now + timedelta(days=36)).date(),
            destination="Paris, France",
            status=ItineraryStatus.DRAFT,
            days=[sample_itinerary_day],
            total_cost=Decimal("875.00"),
            currency="EUR",
            budget=Decimal("2000.00"),
            preferences={
                "activity_types": ["sightseeing", "museums", "food"],
                "pace": "moderate",
                "transportation": "walking_public",
            },
            version=1,
            created_at=now,
            updated_at=now,
            last_optimized=None,
            collaborators=[],
            metadata={
                "created_from": "scratch",
                "optimization_history": [],
                "user_customizations": [],
            },
        )

    @pytest.mark.asyncio
    async def test_create_itinerary_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_activity_service,
        sample_itinerary_create_request,
    ):
        """Test successful itinerary creation."""
        user_id = str(uuid4())

        # Mock activity suggestions
        suggested_activities = [
            {
                "name": "Eiffel Tower",
                "type": "sightseeing",
                "duration_hours": 2,
                "cost": 25.00,
                "priority": 1,
            },
            {
                "name": "Louvre Museum",
                "type": "museum",
                "duration_hours": 4,
                "cost": 15.00,
                "priority": 2,
            },
        ]
        mock_activity_service.get_destination_activities.return_value = (
            suggested_activities
        )

        # Mock database operations
        mock_database_service.store_itinerary.return_value = None

        result = await itinerary_service.create_itinerary(
            user_id, sample_itinerary_create_request
        )

        # Assertions
        assert result.user_id == user_id
        assert result.trip_id == sample_itinerary_create_request.trip_id
        assert result.title == sample_itinerary_create_request.title
        assert result.status == ItineraryStatus.DRAFT
        assert result.budget == sample_itinerary_create_request.budget
        assert len(result.days) == 7  # 7 days from start to end date

        # Verify service calls
        mock_activity_service.get_destination_activities.assert_called_once()
        mock_database_service.store_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_itinerary_invalid_dates(
        self, itinerary_service, sample_itinerary_create_request
    ):
        """Test itinerary creation with invalid dates."""
        user_id = str(uuid4())

        # Set end date before start date
        sample_itinerary_create_request.end_date = (
            sample_itinerary_create_request.start_date - timedelta(days=1)
        )

        with pytest.raises(ValidationError, match="End date must be after start date"):
            await itinerary_service.create_itinerary(
                user_id, sample_itinerary_create_request
            )

    @pytest.mark.asyncio
    async def test_get_itinerary_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful itinerary retrieval."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        result = await itinerary_service.get_itinerary(
            sample_itinerary.id, sample_itinerary.user_id
        )

        assert result is not None
        assert result.id == sample_itinerary.id
        assert result.title == sample_itinerary.title
        mock_database_service.get_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_itinerary_access_denied(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test itinerary retrieval with access denied."""
        different_user_id = str(uuid4())

        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        result = await itinerary_service.get_itinerary(
            sample_itinerary.id, different_user_id
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_itinerary_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful itinerary update."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.update_itinerary.return_value = None

        update_request = ItineraryUpdateRequest(
            title="Updated Paris Adventure",
            description="Updated description for my Paris trip",
            budget=Decimal("2500.00"),
        )

        result = await itinerary_service.update_itinerary(
            sample_itinerary.id, sample_itinerary.user_id, update_request
        )

        assert result.title == "Updated Paris Adventure"
        assert result.description == "Updated description for my Paris trip"
        assert result.budget == Decimal("2500.00")
        assert result.version == 2  # Version incremented
        assert result.updated_at > sample_itinerary.updated_at

        mock_database_service.update_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_item_to_itinerary_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_maps_service,
        sample_itinerary,
        sample_itinerary_item,
    ):
        """Test successful item addition to itinerary."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.update_itinerary.return_value = None

        # Mock travel time calculation
        mock_maps_service.calculate_travel_time.return_value = {
            "duration": timedelta(minutes=20),
            "mode": "walking",
        }

        day_index = 0

        result = await itinerary_service.add_item_to_day(
            sample_itinerary.id,
            sample_itinerary.user_id,
            day_index,
            sample_itinerary_item,
        )

        assert len(result.days[day_index].items) == 2  # Original + new item
        assert result.version == 2  # Version incremented

        mock_database_service.update_itinerary.assert_called_once()
        mock_maps_service.calculate_travel_time.assert_called()

    @pytest.mark.asyncio
    async def test_remove_item_from_itinerary_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful item removal from itinerary."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.update_itinerary.return_value = None

        item_id = sample_itinerary.days[0].items[0].id
        day_index = 0

        result = await itinerary_service.remove_item_from_day(
            sample_itinerary.id, sample_itinerary.user_id, day_index, item_id
        )

        assert len(result.days[day_index].items) == 0  # Item removed
        assert result.version == 2  # Version incremented

        mock_database_service.update_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_optimize_itinerary_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_optimization_service,
        sample_itinerary,
    ):
        """Test successful itinerary optimization."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.update_itinerary.return_value = None

        optimization_params = {
            "goal": OptimizationGoal.MINIMIZE_TRAVEL_TIME,
            "constraints": {
                "max_daily_duration": 8,
                "required_items": [sample_itinerary.days[0].items[0].id],
            },
        }

        # Mock optimization result
        optimization_result = {
            "optimized_itinerary": sample_itinerary.model_dump(),
            "improvements": {
                "travel_time_saved": timedelta(minutes=45),
                "cost_saved": Decimal("25.00"),
                "efficiency_score": 0.85,
            },
            "changes_made": [
                "Reordered items in Day 1 for better routing",
                "Adjusted timing to avoid peak hours",
            ],
        }
        mock_optimization_service.optimize_itinerary.return_value = optimization_result

        result = await itinerary_service.optimize_itinerary(
            sample_itinerary.id, sample_itinerary.user_id, optimization_params
        )

        assert "improvements" in result
        assert "changes_made" in result
        assert result["improvements"]["efficiency_score"] == 0.85

        mock_optimization_service.optimize_itinerary.assert_called_once()
        mock_database_service.update_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_conflicts_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful conflict detection."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        # Add overlapping items to create conflicts
        overlapping_item = ItineraryItem(
            id=str(uuid4()),
            title="Overlapping Activity",
            activity_type=ItineraryItemType.DINING,
            start_time=sample_itinerary.days[0].items[0].start_time,
            end_time=sample_itinerary.days[0].items[0].end_time + timedelta(hours=1),
            duration=timedelta(hours=3),
        )

        sample_itinerary.days[0].items.append(overlapping_item)

        conflicts = await itinerary_service.detect_conflicts(
            sample_itinerary.id, sample_itinerary.user_id
        )

        assert len(conflicts) >= 1
        assert any(conflict.type == ConflictType.TIME_OVERLAP for conflict in conflicts)

    @pytest.mark.asyncio
    async def test_suggest_improvements_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_optimization_service,
        sample_itinerary,
    ):
        """Test successful improvement suggestions."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        # Mock improvement suggestions
        suggestions = {
            "efficiency_improvements": [
                {
                    "type": "reorder_items",
                    "description": "Reorder Day 1 items to reduce travel time",
                    "impact": "Save 30 minutes",
                    "difficulty": "easy",
                }
            ],
            "cost_optimizations": [
                {
                    "type": "alternative_activity",
                    "description": "Replace expensive restaurant with local bistro",
                    "impact": "Save €40",
                    "difficulty": "medium",
                }
            ],
            "experience_enhancements": [
                {
                    "type": "add_local_experience",
                    "description": "Add Seine river cruise at sunset",
                    "impact": "Enhanced experience",
                    "difficulty": "easy",
                }
            ],
        }
        mock_optimization_service.suggest_improvements.return_value = suggestions

        result = await itinerary_service.suggest_improvements(
            sample_itinerary.id, sample_itinerary.user_id
        )

        assert "efficiency_improvements" in result
        assert "cost_optimizations" in result
        assert "experience_enhancements" in result
        assert len(result["efficiency_improvements"]) == 1

        mock_optimization_service.suggest_improvements.assert_called_once()

    @pytest.mark.asyncio
    async def test_share_itinerary_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_collaboration_service,
        sample_itinerary,
    ):
        """Test successful itinerary sharing."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.update_itinerary.return_value = None

        share_options = {
            "share_type": "view_only",
            "expiry_date": datetime.now(UTC) + timedelta(days=30),
            "password_protected": False,
            "allow_comments": True,
        }

        # Mock share link generation
        share_link = "https://tripsage.com/shared/itinerary/abc123"
        mock_collaboration_service.create_share_link.return_value = share_link

        result = await itinerary_service.share_itinerary(
            sample_itinerary.id, sample_itinerary.user_id, share_options
        )

        assert result["share_url"] == share_link
        assert result["share_type"] == "view_only"
        assert "expiry_date" in result

        mock_collaboration_service.create_share_link.assert_called_once()
        mock_database_service.update_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_collaborator_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_collaboration_service,
        sample_itinerary,
    ):
        """Test successful collaborator addition."""
        collaborator_id = str(uuid4())

        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.update_itinerary.return_value = None
        mock_collaboration_service.notify_collaborator.return_value = None

        permissions = {
            "can_edit": True,
            "can_add_items": True,
            "can_remove_items": False,
            "can_invite_others": False,
        }

        result = await itinerary_service.add_collaborator(
            sample_itinerary.id, sample_itinerary.user_id, collaborator_id, permissions
        )

        assert len(result.collaborators) == 1
        assert result.collaborators[0]["user_id"] == collaborator_id
        assert result.collaborators[0]["permissions"] == permissions

        mock_collaboration_service.notify_collaborator.assert_called_once()
        mock_database_service.update_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_itinerary_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful itinerary export."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        export_options = {
            "format": "pdf",
            "include_maps": True,
            "include_contacts": True,
            "include_weather": True,
        }

        # Mock export generation
        with patch.object(itinerary_service, "_generate_export") as mock_export:
            export_result = {
                "export_url": "https://storage.example.com/exports/itinerary_123.pdf",
                "format": "pdf",
                "file_size": 2048576,
                "generated_at": datetime.now(UTC),
            }
            mock_export.return_value = export_result

            result = await itinerary_service.export_itinerary(
                sample_itinerary.id, sample_itinerary.user_id, export_options
            )

            assert result["export_url"] == export_result["export_url"]
            assert result["format"] == "pdf"
            assert result["file_size"] > 0
            mock_export.assert_called_once()

    @pytest.mark.asyncio
    async def test_clone_itinerary_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful itinerary cloning."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.store_itinerary.return_value = None

        clone_options = {
            "new_dates": {
                "start_date": datetime.now(UTC) + timedelta(days=60),
                "end_date": datetime.now(UTC) + timedelta(days=66),
            },
            "adjust_for_season": True,
            "new_title": "Paris Adventure - Spring Edition",
        }

        result = await itinerary_service.clone_itinerary(
            sample_itinerary.id, sample_itinerary.user_id, clone_options
        )

        assert result.id != sample_itinerary.id  # Different ID
        assert result.title == "Paris Adventure - Spring Edition"
        assert result.start_date != sample_itinerary.start_date  # Different dates
        assert result.version == 1  # New itinerary version

        mock_database_service.store_itinerary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_itineraries_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful user itineraries retrieval."""
        user_id = str(uuid4())

        mock_database_service.get_user_itineraries.return_value = [
            sample_itinerary.model_dump()
        ]

        results = await itinerary_service.get_user_itineraries(user_id)

        assert len(results) == 1
        assert results[0].id == sample_itinerary.id
        mock_database_service.get_user_itineraries.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_itinerary_analytics_success(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test successful itinerary analytics retrieval."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        # Mock analytics calculation
        with patch.object(itinerary_service, "_calculate_analytics") as mock_analytics:
            analytics_data = {
                "overview": {
                    "total_items": 15,
                    "total_duration": timedelta(hours=48),
                    "total_cost": Decimal("875.00"),
                    "efficiency_score": 0.82,
                },
                "daily_breakdown": [
                    {
                        "date": sample_itinerary.start_date,
                        "items_count": 5,
                        "duration": timedelta(hours=8),
                        "cost": Decimal("125.00"),
                    }
                ],
                "category_distribution": {
                    "sightseeing": 40,
                    "dining": 30,
                    "museums": 20,
                    "entertainment": 10,
                },
                "optimization_opportunities": [
                    "Reorder Day 2 items to reduce travel time",
                    "Consider lunch reservations for popular restaurants",
                ],
            }
            mock_analytics.return_value = analytics_data

            result = await itinerary_service.get_itinerary_analytics(
                sample_itinerary.id, sample_itinerary.user_id
            )

            assert result["overview"]["total_items"] == 15
            assert result["overview"]["efficiency_score"] == 0.82
            assert len(result["daily_breakdown"]) == 1
            mock_analytics.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_itinerary_feasibility_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_maps_service,
        sample_itinerary,
    ):
        """Test successful itinerary feasibility validation."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        # Mock travel time calculations
        mock_maps_service.calculate_route_times.return_value = {
            "total_travel_time": timedelta(hours=2),
            "feasible": True,
            "bottlenecks": [],
        }

        validation_result = await itinerary_service.validate_feasibility(
            sample_itinerary.id, sample_itinerary.user_id
        )

        assert validation_result["is_feasible"] is True
        assert "travel_analysis" in validation_result
        assert "timing_analysis" in validation_result
        assert "budget_analysis" in validation_result

        mock_maps_service.calculate_route_times.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_alternative_itineraries_success(
        self,
        itinerary_service,
        mock_database_service,
        mock_optimization_service,
        sample_itinerary,
    ):
        """Test successful alternative itinerary generation."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()

        # Mock alternative generation
        alternatives = [
            {
                "variant": "budget_optimized",
                "description": "Focus on free and low-cost activities",
                "estimated_savings": Decimal("200.00"),
                "trade_offs": ["Fewer premium experiences"],
            },
            {
                "variant": "time_optimized",
                "description": "Minimize travel time between activities",
                "time_saved": timedelta(hours=3),
                "trade_offs": ["Less flexible schedule"],
            },
        ]
        mock_optimization_service.generate_alternatives.return_value = alternatives

        result = await itinerary_service.generate_alternative_itineraries(
            sample_itinerary.id, sample_itinerary.user_id
        )

        assert len(result) == 2
        assert result[0]["variant"] == "budget_optimized"
        assert result[0]["estimated_savings"] == Decimal("200.00")

        mock_optimization_service.generate_alternatives.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_error_handling(
        self, itinerary_service, mock_database_service, sample_itinerary_create_request
    ):
        """Test service error handling."""
        user_id = str(uuid4())

        # Mock database to raise an exception
        mock_database_service.store_itinerary.side_effect = Exception("Database error")

        with pytest.raises(ServiceError, match="Failed to create itinerary"):
            await itinerary_service.create_itinerary(
                user_id, sample_itinerary_create_request
            )

    def test_get_itinerary_service_dependency(self):
        """Test the dependency injection function."""
        service = get_itinerary_service()
        assert isinstance(service, ItineraryService)

    def test_time_conflict_detection(self, itinerary_service):
        """Test time conflict detection algorithm."""
        items = [
            {
                "id": "item1",
                "start_time": datetime(2024, 7, 15, 10, 0),
                "end_time": datetime(2024, 7, 15, 12, 0),
            },
            {
                "id": "item2",
                "start_time": datetime(2024, 7, 15, 11, 30),
                "end_time": datetime(2024, 7, 15, 13, 30),
            },
        ]

        conflicts = itinerary_service._detect_time_conflicts(items)

        assert len(conflicts) == 1
        assert conflicts[0]["type"] == "time_overlap"
        assert "item1" in conflicts[0]["affected_items"]
        assert "item2" in conflicts[0]["affected_items"]

    def test_travel_time_calculation(self, itinerary_service):
        """Test travel time calculation between activities."""
        location1 = {"latitude": 48.8584, "longitude": 2.2945}  # Eiffel Tower
        location2 = {"latitude": 48.8606, "longitude": 2.3376}  # Louvre

        # Mock calculation
        with patch.object(itinerary_service, "_calculate_travel_time") as mock_calc:
            mock_calc.return_value = {
                "walking": timedelta(minutes=45),
                "public_transport": timedelta(minutes=20),
                "taxi": timedelta(minutes=15),
            }

            travel_times = itinerary_service._calculate_travel_time(
                location1, location2
            )

            assert travel_times["walking"] == timedelta(minutes=45)
            assert travel_times["public_transport"] == timedelta(minutes=20)
            mock_calc.assert_called_once()

    def test_budget_tracking(self, itinerary_service, sample_itinerary):
        """Test budget tracking and analysis."""
        budget_analysis = itinerary_service._analyze_budget_utilization(
            sample_itinerary
        )

        assert "total_spent" in budget_analysis
        assert "remaining_budget" in budget_analysis
        assert "utilization_percentage" in budget_analysis
        assert budget_analysis["total_spent"] == sample_itinerary.total_cost
        assert (
            budget_analysis["remaining_budget"]
            == sample_itinerary.budget - sample_itinerary.total_cost
        )

    @pytest.mark.asyncio
    async def test_real_time_updates(
        self, itinerary_service, mock_collaboration_service, sample_itinerary
    ):
        """Test real-time collaborative updates."""
        update_data = {
            "type": "item_added",
            "day_index": 0,
            "item": {
                "title": "New Activity",
                "start_time": datetime.now(UTC) + timedelta(days=1),
            },
            "user_id": str(uuid4()),
        }

        # Mock real-time notification
        mock_collaboration_service.broadcast_update.return_value = None

        await itinerary_service.broadcast_itinerary_update(
            sample_itinerary.id, update_data
        )

        mock_collaboration_service.broadcast_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_version_control(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test itinerary version control."""
        mock_database_service.get_itinerary.return_value = sample_itinerary.model_dump()
        mock_database_service.get_itinerary_versions.return_value = [
            {
                "version": 1,
                "timestamp": datetime.now(UTC) - timedelta(hours=2),
            },
            {
                "version": 2,
                "timestamp": datetime.now(UTC) - timedelta(hours=1),
            },
        ]

        versions = await itinerary_service.get_itinerary_versions(
            sample_itinerary.id, sample_itinerary.user_id
        )

        assert len(versions) == 2
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2

    @pytest.mark.asyncio
    async def test_smart_scheduling(
        self, itinerary_service, mock_optimization_service, sample_itinerary
    ):
        """Test smart scheduling optimization."""
        scheduling_constraints = {
            "opening_hours": {
                "museums": {"open": 9, "close": 18},
                "restaurants": {"open": 12, "close": 22},
            },
            "user_preferences": {"early_riser": False, "evening_person": True},
        }

        # Mock smart scheduling
        optimized_schedule = {
            "schedule_changes": [
                "Moved museum visits to afternoon",
                "Scheduled dinner later in the evening",
            ],
            "efficiency_gain": 0.15,
            "satisfaction_score": 0.89,
        }
        mock_optimization_service.optimize_schedule.return_value = optimized_schedule

        result = await itinerary_service.apply_smart_scheduling(
            sample_itinerary.id, sample_itinerary.user_id, scheduling_constraints
        )

        assert result["efficiency_gain"] == 0.15
        assert result["satisfaction_score"] == 0.89
        assert len(result["schedule_changes"]) == 2

    @pytest.mark.asyncio
    async def test_personalization_engine(
        self, itinerary_service, mock_database_service, sample_itinerary
    ):
        """Test personalization engine."""
        user_id = str(uuid4())

        # Mock user profile
        user_profile = {
            "travel_history": ["London", "Barcelona"],
            "preferences": {
                "activity_types": ["museums", "food"],
                "pace": "relaxed",
                "budget_style": "mid-range",
            },
            "accessibility_needs": [],
            "group_type": "couple",
        }
        mock_database_service.get_user_travel_profile.return_value = user_profile

        personalization_suggestions = (
            await itinerary_service.get_personalization_suggestions(
                sample_itinerary.id, user_id
            )
        )

        assert "recommended_additions" in personalization_suggestions
        assert "suggested_modifications" in personalization_suggestions
        assert "timing_adjustments" in personalization_suggestions
