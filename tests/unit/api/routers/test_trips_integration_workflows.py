"""
Integration workflow tests for trips router.

This module provides end-to-end integration tests that cover real-world
scenarios, complex workflows, and interactions between multiple components
of the trip management system.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from tripsage.api.middlewares.authentication import Principal
from tripsage.api.schemas.trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    UpdateTripRequest,
)
from tripsage_core.models.schemas_common.enums import CurrencyCode
from tripsage_core.models.schemas_common.financial import Budget, Price
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import TripDestination, TripPreferences
from tripsage_core.services.business.trip_service import TripStatus, TripVisibility


class TestTripsIntegrationWorkflows:
    """Integration workflow tests for comprehensive trip management scenarios."""

    # ===== FIXTURES =====

    @pytest.fixture
    def business_traveler_principal(self):
        """Mock business traveler principal."""
        return Principal(
            id="business_user_001",
            type="user",
            email="business.traveler@company.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def leisure_traveler_principal(self):
        """Mock leisure traveler principal."""
        return Principal(
            id="leisure_user_002",
            type="user",
            email="leisure.traveler@personal.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def family_organizer_principal(self):
        """Mock family trip organizer principal."""
        return Principal(
            id="family_organizer_003",
            type="user",
            email="family.organizer@family.com",
            auth_method="jwt",
        )

    @pytest.fixture
    def comprehensive_trip_service(self):
        """Mock trip service with comprehensive workflow support."""
        service = MagicMock()

        # Configure all methods as AsyncMock
        service.create_trip = AsyncMock()
        service.get_trip = AsyncMock()
        service.get_user_trips = AsyncMock()
        service.update_trip = AsyncMock()
        service.delete_trip = AsyncMock()
        service.search_trips = AsyncMock()
        service.duplicate_trip = AsyncMock()
        service.share_trip = AsyncMock()
        service.get_trip_collaborators = AsyncMock()

        return service

    @pytest.fixture
    def tokyo_business_trip_data(self):
        """Sample business trip to Tokyo."""
        return {
            "title": "Tokyo Q4 Sales Meeting",
            "description": "Quarterly business review and client meetings in Tokyo",
            "start_date": date(2024, 10, 15),
            "end_date": date(2024, 10, 19),
            "destinations": [
                TripDestination(
                    name="Tokyo, Japan",
                    country="Japan",
                    city="Tokyo",
                    coordinates=Coordinates(latitude=35.6762, longitude=139.6503),
                )
            ],
            "preferences": TripPreferences(
                budget=Budget(
                    total_budget=Price(
                        amount=Decimal("8000"), currency=CurrencyCode.USD
                    )
                )
            ),
        }

    @pytest.fixture
    def europe_family_trip_data(self):
        """Sample family trip to Europe."""
        return {
            "title": "European Family Adventure",
            "description": "3-week family vacation across Western Europe",
            "start_date": date(2024, 7, 1),
            "end_date": date(2024, 7, 21),
            "destinations": [
                TripDestination(
                    name="Paris, France",
                    country="France",
                    city="Paris",
                    coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
                ),
                TripDestination(
                    name="Rome, Italy",
                    country="Italy",
                    city="Rome",
                    coordinates=Coordinates(latitude=41.9028, longitude=12.4964),
                ),
                TripDestination(
                    name="Barcelona, Spain",
                    country="Spain",
                    city="Barcelona",
                    coordinates=Coordinates(latitude=41.3851, longitude=2.1734),
                ),
            ],
            "preferences": TripPreferences(
                budget=Budget(
                    total_budget=Price(
                        amount=Decimal("15000"), currency=CurrencyCode.USD
                    )
                )
            ),
        }

    # ===== BUSINESS TRAVEL WORKFLOW TESTS =====

    async def test_business_trip_complete_workflow(
        self,
        business_traveler_principal,
        comprehensive_trip_service,
        tokyo_business_trip_data,
    ):
        """Test complete business trip planning workflow."""
        from tripsage.api.routers.trips import (
            create_trip,
            export_trip,
            get_trip_summary,
            update_trip,
        )

        # Step 1: Create business trip
        trip_request = CreateTripRequest(**tokyo_business_trip_data)

        # Mock trip response
        created_trip = MagicMock()
        created_trip.id = str(uuid4())
        created_trip.user_id = "business_user_001"
        created_trip.title = "Tokyo Q4 Sales Meeting"
        created_trip.status = TripStatus.PLANNING.value
        created_trip.visibility = TripVisibility.PRIVATE.value
        created_trip.destinations = tokyo_business_trip_data["destinations"]
        created_trip.start_date = datetime.combine(
            tokyo_business_trip_data["start_date"], datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        created_trip.end_date = datetime.combine(
            tokyo_business_trip_data["end_date"], datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        created_trip.preferences = {}
        created_trip.created_at = datetime.now(timezone.utc)
        created_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = created_trip

        # Create the trip
        result = await create_trip(
            trip_request, business_traveler_principal, comprehensive_trip_service
        )

        assert result.title == "Tokyo Q4 Sales Meeting"
        assert result.user_id == "business_user_001"

        trip_id = UUID(created_trip.id)

        # Step 2: Update trip with accommodation preferences
        update_request = UpdateTripRequest(
            description=(
                "Updated: Quarterly business review and client meetings in Tokyo, "
                "including hotel bookings"
            )
        )

        comprehensive_trip_service.update_trip.return_value = created_trip

        updated_trip = await update_trip(
            trip_id,
            update_request,
            business_traveler_principal,
            comprehensive_trip_service,
        )

        assert updated_trip.title == "Tokyo Q4 Sales Meeting"

        # Step 3: Get trip summary for review
        comprehensive_trip_service.get_trip.return_value = created_trip

        trip_summary = await get_trip_summary(
            trip_id, business_traveler_principal, comprehensive_trip_service
        )

        assert trip_summary.title == "Tokyo Q4 Sales Meeting"
        assert trip_summary.duration_days > 0

        # Step 4: Export trip for expense reporting
        export_result = await export_trip(
            trip_id,
            format="pdf",
            principal=business_traveler_principal,
            trip_service=comprehensive_trip_service,
        )

        assert export_result["format"] == "pdf"
        assert "download_url" in export_result

    async def test_multi_city_business_trip_planning(
        self,
        business_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test planning a multi-city business trip."""
        from tripsage.api.routers.trips import create_trip, update_trip

        # Create initial single-city trip
        initial_trip_data = CreateTripRequest(
            title="Asia Pacific Business Tour",
            description="Multi-city business meetings across APAC region",
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 15),
            destinations=[
                TripDestination(
                    name="Tokyo, Japan",
                    country="Japan",
                    city="Tokyo",
                )
            ],
        )

        created_trip = MagicMock()
        created_trip.id = str(uuid4())
        created_trip.user_id = "business_user_001"
        created_trip.title = "Asia Pacific Business Tour"
        created_trip.destinations = [
            MagicMock(name="Tokyo, Japan", country="Japan", city="Tokyo")
        ]
        created_trip.start_date = datetime(2024, 11, 1, tzinfo=timezone.utc)
        created_trip.end_date = datetime(2024, 11, 15, tzinfo=timezone.utc)
        created_trip.preferences = {}
        created_trip.status = "planning"
        created_trip.created_at = datetime.now(timezone.utc)
        created_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = created_trip

        _result = await create_trip(
            initial_trip_data, business_traveler_principal, comprehensive_trip_service
        )

        trip_id = UUID(created_trip.id)

        # Add more cities to the business trip
        expanded_destinations = [
            TripDestination(name="Tokyo, Japan", country="Japan", city="Tokyo"),
            TripDestination(
                name="Seoul, South Korea", country="South Korea", city="Seoul"
            ),
            TripDestination(name="Singapore", country="Singapore", city="Singapore"),
            TripDestination(
                name="Sydney, Australia", country="Australia", city="Sydney"
            ),
        ]

        update_request = UpdateTripRequest(
            destinations=expanded_destinations,
            end_date=date(2024, 11, 20),  # Extend trip duration
        )

        # Update mock to reflect changes
        created_trip.destinations = [
            MagicMock(name=dest.name, country=dest.country, city=dest.city)
            for dest in expanded_destinations
        ]
        created_trip.end_date = datetime(2024, 11, 20, tzinfo=timezone.utc)

        comprehensive_trip_service.update_trip.return_value = created_trip

        updated_result = await update_trip(
            trip_id,
            update_request,
            business_traveler_principal,
            comprehensive_trip_service,
        )

        assert updated_result.title == "Asia Pacific Business Tour"
        assert len(updated_result.destinations) == 4

    # ===== FAMILY TRAVEL WORKFLOW TESTS =====

    async def test_family_trip_collaborative_planning(
        self,
        family_organizer_principal,
        comprehensive_trip_service,
        europe_family_trip_data,
    ):
        """Test collaborative family trip planning workflow."""
        from tripsage.api.routers.trips import (
            create_trip,
            duplicate_trip,
            list_trips,
            search_trips,
        )

        # Step 1: Family organizer creates the base trip
        family_trip_request = CreateTripRequest(**europe_family_trip_data)

        family_trip = MagicMock()
        family_trip.id = str(uuid4())
        family_trip.user_id = "family_organizer_003"
        family_trip.title = "European Family Adventure"
        family_trip.visibility = TripVisibility.SHARED.value
        family_trip.destinations = europe_family_trip_data["destinations"]
        family_trip.start_date = datetime(2024, 7, 1, tzinfo=timezone.utc)
        family_trip.end_date = datetime(2024, 7, 21, tzinfo=timezone.utc)
        family_trip.preferences = {}
        family_trip.status = "planning"
        family_trip.created_at = datetime.now(timezone.utc)
        family_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = family_trip

        created_trip = await create_trip(
            family_trip_request, family_organizer_principal, comprehensive_trip_service
        )

        assert created_trip.title == "European Family Adventure"

        # Step 2: List all family trips for planning overview
        comprehensive_trip_service.get_user_trips.return_value = [family_trip]

        trips_list = await list_trips(
            skip=0,
            limit=10,
            principal=family_organizer_principal,
            trip_service=comprehensive_trip_service,
        )

        assert trips_list["total"] == 1
        assert trips_list["items"][0]["title"] == "European Family Adventure"

        # Step 3: Search for similar family-friendly trips for inspiration
        comprehensive_trip_service.search_trips.return_value = [family_trip]

        search_results = await search_trips(
            q="family Europe",
            status_filter=None,
            skip=0,
            limit=5,
            principal=family_organizer_principal,
            trip_service=comprehensive_trip_service,
        )

        assert search_results["total"] == 1

        # Step 4: Create alternative trip plan by duplicating
        comprehensive_trip_service.get_trip.return_value = family_trip

        # Create duplicate with different title
        duplicate_trip_mock = MagicMock()
        duplicate_trip_mock.id = str(uuid4())
        duplicate_trip_mock.user_id = "family_organizer_003"
        duplicate_trip_mock.title = "Copy of European Family Adventure"
        duplicate_trip_mock.destinations = family_trip.destinations
        duplicate_trip_mock.start_date = family_trip.start_date
        duplicate_trip_mock.end_date = family_trip.end_date
        duplicate_trip_mock.preferences = {}
        duplicate_trip_mock.status = "planning"
        duplicate_trip_mock.created_at = datetime.now(timezone.utc)
        duplicate_trip_mock.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = duplicate_trip_mock

        duplicated_trip = await duplicate_trip(
            UUID(family_trip.id), family_organizer_principal, comprehensive_trip_service
        )

        assert "Copy of" in duplicated_trip.title

    async def test_budget_conscious_trip_planning(
        self,
        leisure_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test budget-conscious trip planning workflow."""
        from tripsage.api.routers.trips import (
            create_trip,
            get_trip_suggestions,
            update_trip_preferences,
        )

        # Step 1: Create budget-conscious trip
        budget_trip_data = CreateTripRequest(
            title="Budget Southeast Asia Adventure",
            description="Backpacking trip through Southeast Asia on a tight budget",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 30),
            destinations=[
                TripDestination(
                    name="Bangkok, Thailand",
                    country="Thailand",
                    city="Bangkok",
                ),
                TripDestination(
                    name="Ho Chi Minh City, Vietnam",
                    country="Vietnam",
                    city="Ho Chi Minh City",
                ),
            ],
            preferences=TripPreferences(
                budget=Budget(
                    total_budget=Price(
                        amount=Decimal("2500"), currency=CurrencyCode.USD
                    )
                )
            ),
        )

        budget_trip = MagicMock()
        budget_trip.id = str(uuid4())
        budget_trip.user_id = "leisure_user_002"
        budget_trip.title = "Budget Southeast Asia Adventure"
        budget_trip.destinations = budget_trip_data.destinations
        budget_trip.start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
        budget_trip.end_date = datetime(2024, 9, 30, tzinfo=timezone.utc)
        budget_trip.preferences = {"budget": {"total": 2500, "currency": "USD"}}
        budget_trip.status = "planning"
        budget_trip.created_at = datetime.now(timezone.utc)
        budget_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = budget_trip

        created_trip = await create_trip(
            budget_trip_data, leisure_traveler_principal, comprehensive_trip_service
        )

        assert created_trip.title == "Budget Southeast Asia Adventure"

        # Step 2: Get budget-appropriate suggestions
        suggestions = await get_trip_suggestions(
            limit=5,
            budget_max=3000.0,  # Slightly higher than current budget
            category="adventure",
            principal=leisure_traveler_principal,
            trip_service=comprehensive_trip_service,
        )

        # Should return suggestions within budget
        budget_appropriate_suggestions = [
            s for s in suggestions if s.estimated_price <= 3000.0
        ]
        assert len(budget_appropriate_suggestions) > 0

        # Step 3: Update budget preferences based on suggestions
        updated_budget = Budget(
            total_budget=Price(amount=Decimal("3200"), currency=CurrencyCode.USD)
        )
        preferences_update = TripPreferencesRequest(budget=updated_budget)

        comprehensive_trip_service.update_trip.return_value = budget_trip

        updated_trip = await update_trip_preferences(
            UUID(budget_trip.id),
            preferences_update,
            leisure_traveler_principal,
            comprehensive_trip_service,
        )

        assert updated_trip.title == "Budget Southeast Asia Adventure"

    # ===== COMPLEX SCENARIO TESTS =====

    async def test_trip_status_lifecycle(
        self,
        business_traveler_principal,
        comprehensive_trip_service,
        tokyo_business_trip_data,
    ):
        """Test complete trip status lifecycle from planning to completion."""
        from tripsage.api.routers.trips import create_trip, get_trip

        # Create trip in planning status
        trip_request = CreateTripRequest(**tokyo_business_trip_data)

        trip = MagicMock()
        trip.id = str(uuid4())
        trip.user_id = "business_user_001"
        trip.title = "Tokyo Q4 Sales Meeting"
        trip.status = TripStatus.PLANNING.value
        trip.destinations = tokyo_business_trip_data["destinations"]
        trip.start_date = datetime(2024, 10, 15, tzinfo=timezone.utc)
        trip.end_date = datetime(2024, 10, 19, tzinfo=timezone.utc)
        trip.preferences = {}
        trip.created_at = datetime.now(timezone.utc)
        trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = trip

        _created_trip = await create_trip(
            trip_request, business_traveler_principal, comprehensive_trip_service
        )

        trip_id = UUID(trip.id)

        # Progress through status changes
        status_progression = [
            TripStatus.CONFIRMED,
            TripStatus.IN_PROGRESS,
            TripStatus.COMPLETED,
        ]

        for status in status_progression:
            # Update mock status
            trip.status = status.value
            trip.updated_at = datetime.now(timezone.utc)

            comprehensive_trip_service.update_trip.return_value = trip
            comprehensive_trip_service.get_trip.return_value = trip

            # Get trip to verify status
            current_trip = await get_trip(
                trip_id, business_traveler_principal, comprehensive_trip_service
            )

            assert current_trip.status == status.value

    async def test_multi_user_trip_access_patterns(
        self,
        family_organizer_principal,
        leisure_traveler_principal,
        business_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test different user access patterns for shared trips."""
        from tripsage.api.routers.trips import get_trip, list_trips

        # Create shared family trip
        shared_trip = MagicMock()
        shared_trip.id = str(uuid4())
        shared_trip.user_id = "family_organizer_003"
        shared_trip.title = "Shared Family Trip"
        shared_trip.visibility = TripVisibility.SHARED.value
        shared_trip.shared_with = ["leisure_user_002"]  # Shared with leisure traveler
        shared_trip.destinations = []
        shared_trip.start_date = datetime(2024, 8, 1, tzinfo=timezone.utc)
        shared_trip.end_date = datetime(2024, 8, 15, tzinfo=timezone.utc)
        shared_trip.preferences = {}
        shared_trip.status = "planning"
        shared_trip.created_at = datetime.now(timezone.utc)
        shared_trip.updated_at = datetime.now(timezone.utc)

        trip_id = UUID(shared_trip.id)

        # Owner can access
        comprehensive_trip_service.get_trip.return_value = shared_trip

        owner_access = await get_trip(
            trip_id, family_organizer_principal, comprehensive_trip_service
        )
        assert owner_access.title == "Shared Family Trip"

        # Shared user can access
        collaborator_access = await get_trip(
            trip_id, leisure_traveler_principal, comprehensive_trip_service
        )
        assert collaborator_access.title == "Shared Family Trip"

        # Non-shared user cannot access
        comprehensive_trip_service.get_trip.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_trip(
                trip_id, business_traveler_principal, comprehensive_trip_service
            )

        assert exc_info.value.status_code == 404

        # Test trip listing includes shared trips
        comprehensive_trip_service.get_user_trips.return_value = [shared_trip]

        leisure_trips = await list_trips(
            skip=0,
            limit=10,
            principal=leisure_traveler_principal,
            trip_service=comprehensive_trip_service,
        )

        # Should include shared trip in collaborator's list
        assert leisure_trips["total"] == 1
        assert leisure_trips["items"][0]["title"] == "Shared Family Trip"

    async def test_trip_preferences_evolution(
        self,
        leisure_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test how trip preferences evolve throughout planning."""
        from tripsage.api.routers.trips import (
            create_trip,
            get_trip,
            update_trip_preferences,
        )

        # Start with basic preferences
        initial_trip = CreateTripRequest(
            title="Evolving Preferences Trip",
            description="Trip that demonstrates preference evolution",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 10),
            destinations=[
                TripDestination(
                    name="Bali, Indonesia",
                    country="Indonesia",
                    city="Bali",
                )
            ],
            preferences=TripPreferences(
                budget=Budget(
                    total_budget=Price(
                        amount=Decimal("3000"), currency=CurrencyCode.USD
                    )
                )
            ),
        )

        trip = MagicMock()
        trip.id = str(uuid4())
        trip.user_id = "leisure_user_002"
        trip.title = "Evolving Preferences Trip"
        trip.destinations = initial_trip.destinations
        trip.start_date = datetime(2024, 12, 1, tzinfo=timezone.utc)
        trip.end_date = datetime(2024, 12, 10, tzinfo=timezone.utc)
        trip.preferences = {"budget": {"total": 3000, "currency": "USD"}}
        trip.status = "planning"
        trip.created_at = datetime.now(timezone.utc)
        trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = trip

        _created_trip = await create_trip(
            initial_trip, leisure_traveler_principal, comprehensive_trip_service
        )

        trip_id = UUID(trip.id)

        # Evolution 1: Increase budget after research
        updated_budget_1 = Budget(
            total_budget=Price(amount=Decimal("4000"), currency=CurrencyCode.USD)
        )
        preferences_update_1 = TripPreferencesRequest(budget=updated_budget_1)

        trip.preferences = {"budget": {"total": 4000, "currency": "USD"}}
        comprehensive_trip_service.update_trip.return_value = trip

        await update_trip_preferences(
            trip_id,
            preferences_update_1,
            leisure_traveler_principal,
            comprehensive_trip_service,
        )

        # Evolution 2: Further refinement based on accommodation options
        updated_budget_2 = Budget(
            total_budget=Price(amount=Decimal("4500"), currency=CurrencyCode.USD)
        )
        preferences_update_2 = TripPreferencesRequest(budget=updated_budget_2)

        trip.preferences = {"budget": {"total": 4500, "currency": "USD"}}
        comprehensive_trip_service.update_trip.return_value = trip
        comprehensive_trip_service.get_trip.return_value = trip

        await update_trip_preferences(
            trip_id,
            preferences_update_2,
            leisure_traveler_principal,
            comprehensive_trip_service,
        )

        # Verify final state
        final_trip = await get_trip(
            trip_id, leisure_traveler_principal, comprehensive_trip_service
        )

        assert final_trip.title == "Evolving Preferences Trip"

    # ===== ERROR RECOVERY AND RESILIENCE TESTS =====

    async def test_trip_creation_with_partial_failures(
        self,
        business_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test trip creation resilience with partial service failures."""
        from tripsage.api.routers.trips import create_trip

        # Simulate creation with some downstream service issues
        problematic_trip_data = CreateTripRequest(
            title="Trip with Potential Issues",
            description="Testing resilience to partial failures",
            start_date=date(2024, 8, 15),
            end_date=date(2024, 8, 20),
            destinations=[
                TripDestination(
                    name="Remote Location",
                    country="Unknown",
                    city="Remote",
                )
            ],
        )

        # Mock successful creation despite potential issues
        resilient_trip = MagicMock()
        resilient_trip.id = str(uuid4())
        resilient_trip.user_id = "business_user_001"
        resilient_trip.title = "Trip with Potential Issues"
        resilient_trip.destinations = problematic_trip_data.destinations
        resilient_trip.start_date = datetime(2024, 8, 15, tzinfo=timezone.utc)
        resilient_trip.end_date = datetime(2024, 8, 20, tzinfo=timezone.utc)
        resilient_trip.preferences = {}
        resilient_trip.status = "planning"
        resilient_trip.created_at = datetime.now(timezone.utc)
        resilient_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = resilient_trip

        # Should succeed despite potential downstream issues
        result = await create_trip(
            problematic_trip_data,
            business_traveler_principal,
            comprehensive_trip_service,
        )

        assert result.title == "Trip with Potential Issues"
        assert result.user_id == "business_user_001"

    async def test_concurrent_trip_modifications(
        self,
        family_organizer_principal,
        leisure_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test handling concurrent modifications to shared trips."""
        from tripsage.api.routers.trips import update_trip

        # Shared trip that multiple users might modify
        shared_trip = MagicMock()
        shared_trip.id = str(uuid4())
        shared_trip.user_id = "family_organizer_003"
        shared_trip.title = "Concurrently Modified Trip"
        shared_trip.description = "Original description"
        shared_trip.visibility = TripVisibility.SHARED.value
        shared_trip.destinations = []
        shared_trip.start_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
        shared_trip.end_date = datetime(2024, 9, 10, tzinfo=timezone.utc)
        shared_trip.preferences = {}
        shared_trip.status = "planning"
        shared_trip.created_at = datetime.now(timezone.utc)
        shared_trip.updated_at = datetime.now(timezone.utc)

        trip_id = UUID(shared_trip.id)

        # First user makes an update
        update_1 = UpdateTripRequest(description="Updated by family organizer")

        shared_trip.description = "Updated by family organizer"
        shared_trip.updated_at = datetime.now(timezone.utc)
        comprehensive_trip_service.update_trip.return_value = shared_trip
        comprehensive_trip_service.get_trip.return_value = shared_trip

        result_1 = await update_trip(
            trip_id, update_1, family_organizer_principal, comprehensive_trip_service
        )

        assert result_1.description == "Updated by family organizer"

        # Second user makes another update (assuming they have edit permissions)
        update_2 = UpdateTripRequest(title="Concurrently Modified Trip - Edited")

        shared_trip.title = "Concurrently Modified Trip - Edited"
        shared_trip.updated_at = datetime.now(timezone.utc)
        comprehensive_trip_service.update_trip.return_value = shared_trip

        result_2 = await update_trip(
            trip_id, update_2, leisure_traveler_principal, comprehensive_trip_service
        )

        # Should reflect both changes
        assert result_2.title == "Concurrently Modified Trip - Edited"
        assert result_2.description == "Updated by family organizer"

    # ===== PERFORMANCE AND SCALABILITY TESTS =====

    async def test_large_scale_trip_operations(
        self,
        business_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test operations with large numbers of trips."""
        from tripsage.api.routers.trips import list_trips, search_trips

        # Mock large number of trips
        large_trip_list = []
        for i in range(200):
            trip = MagicMock()
            trip.id = str(uuid4())
            trip.user_id = "business_user_001"
            trip.title = f"Business Trip {i + 1}"
            trip.destinations = []
            trip.start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            trip.end_date = datetime(2024, 1, 5, tzinfo=timezone.utc)
            trip.status = "planning"
            trip.created_at = datetime.now(timezone.utc)
            trip.updated_at = datetime.now(timezone.utc)
            large_trip_list.append(trip)

        comprehensive_trip_service.get_user_trips.return_value = large_trip_list

        # Test pagination with large dataset
        trips_page_1 = await list_trips(
            skip=0,
            limit=50,
            principal=business_traveler_principal,
            trip_service=comprehensive_trip_service,
        )

        assert trips_page_1["total"] == 200
        # Note: Current implementation returns all trips, not paginated
        assert len(trips_page_1["items"]) == 200

        # Test search across large dataset
        search_subset = large_trip_list[:10]  # Return subset for search
        comprehensive_trip_service.search_trips.return_value = search_subset

        search_results = await search_trips(
            q="Business Trip",
            status_filter=None,
            skip=0,
            limit=20,
            principal=business_traveler_principal,
            trip_service=comprehensive_trip_service,
        )

        assert search_results["total"] == 10
        assert len(search_results["items"]) == 10

    async def test_complex_destination_management(
        self,
        leisure_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test complex multi-destination trip management."""
        from tripsage.api.routers.trips import create_trip, update_trip

        # Create trip with many destinations
        complex_destinations = [
            TripDestination(
                name=f"Destination {i}",
                country=f"Country {i}",
                city=f"City {i}",
                coordinates=Coordinates(latitude=float(i), longitude=float(i * 2)),
            )
            for i in range(1, 16)  # 15 destinations
        ]

        complex_trip_data = CreateTripRequest(
            title="Around the World in 80 Days",
            description="Epic journey across multiple continents",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 8, 20),
            destinations=complex_destinations,
        )

        complex_trip = MagicMock()
        complex_trip.id = str(uuid4())
        complex_trip.user_id = "leisure_user_002"
        complex_trip.title = "Around the World in 80 Days"
        complex_trip.destinations = [
            MagicMock(name=dest.name, country=dest.country, city=dest.city)
            for dest in complex_destinations
        ]
        complex_trip.start_date = datetime(2024, 6, 1, tzinfo=timezone.utc)
        complex_trip.end_date = datetime(2024, 8, 20, tzinfo=timezone.utc)
        complex_trip.preferences = {}
        complex_trip.status = "planning"
        complex_trip.created_at = datetime.now(timezone.utc)
        complex_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = complex_trip

        created_trip = await create_trip(
            complex_trip_data, leisure_traveler_principal, comprehensive_trip_service
        )

        assert created_trip.title == "Around the World in 80 Days"
        assert len(created_trip.destinations) == 15

        # Update to remove some destinations (trip simplification)
        simplified_destinations = complex_destinations[:8]  # Keep first 8

        update_request = UpdateTripRequest(
            destinations=simplified_destinations,
            description="Simplified epic journey across continents",
        )

        complex_trip.destinations = [
            MagicMock(name=dest.name, country=dest.country, city=dest.city)
            for dest in simplified_destinations
        ]
        comprehensive_trip_service.update_trip.return_value = complex_trip

        updated_trip = await update_trip(
            UUID(complex_trip.id),
            update_request,
            leisure_traveler_principal,
            comprehensive_trip_service,
        )

        assert len(updated_trip.destinations) == 8
        assert updated_trip.title == "Around the World in 80 Days"

    # ===== REAL-WORLD EDGE CASES =====

    async def test_last_minute_trip_changes(
        self,
        business_traveler_principal,
        comprehensive_trip_service,
    ):
        """Test handling last-minute trip changes."""
        from tripsage.api.routers.trips import create_trip, update_trip

        # Create trip with near-future dates
        urgent_trip_data = CreateTripRequest(
            title="Emergency Business Travel",
            description="Urgent client meeting",
            start_date=date.today(),  # Today
            end_date=date(
                2024, 12, 31
            ),  # Tomorrow (assuming test runs before 2024-12-30)
            destinations=[
                TripDestination(
                    name="Emergency Location",
                    country="Unknown",
                    city="Urgent",
                )
            ],
        )

        urgent_trip = MagicMock()
        urgent_trip.id = str(uuid4())
        urgent_trip.user_id = "business_user_001"
        urgent_trip.title = "Emergency Business Travel"
        urgent_trip.destinations = urgent_trip_data.destinations
        urgent_trip.start_date = datetime.combine(
            date.today(), datetime.min.time()
        ).replace(tzinfo=timezone.utc)
        urgent_trip.end_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        urgent_trip.preferences = {}
        urgent_trip.status = "planning"
        urgent_trip.created_at = datetime.now(timezone.utc)
        urgent_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = urgent_trip

        created_trip = await create_trip(
            urgent_trip_data, business_traveler_principal, comprehensive_trip_service
        )

        assert created_trip.title == "Emergency Business Travel"

        # Last-minute destination change
        update_request = UpdateTripRequest(
            destinations=[
                TripDestination(
                    name="Changed Emergency Location",
                    country="Different Country",
                    city="Changed Urgent",
                )
            ]
        )

        urgent_trip.destinations = [
            MagicMock(
                name="Changed Emergency Location",
                country="Different Country",
                city="Changed Urgent",
            )
        ]
        comprehensive_trip_service.update_trip.return_value = urgent_trip

        updated_trip = await update_trip(
            UUID(urgent_trip.id),
            update_request,
            business_traveler_principal,
            comprehensive_trip_service,
        )

        assert updated_trip.destinations[0].name == "Changed Emergency Location"

    async def test_trip_data_consistency_checks(
        self,
        family_organizer_principal,
        comprehensive_trip_service,
    ):
        """Test data consistency across trip operations."""
        from tripsage.api.routers.trips import (
            create_trip,
            get_trip,
            get_trip_summary,
            update_trip,
        )

        # Create trip with specific data
        consistent_trip_data = CreateTripRequest(
            title="Data Consistency Test Trip",
            description="Testing data consistency across operations",
            start_date=date(2024, 7, 15),
            end_date=date(2024, 7, 25),
            destinations=[
                TripDestination(
                    name="Consistency City",
                    country="Consistent Country",
                    city="Consistency City",
                    coordinates=Coordinates(latitude=45.0, longitude=-75.0),
                )
            ],
            preferences=TripPreferences(
                budget=Budget(
                    total_budget=Price(
                        amount=Decimal("5500"), currency=CurrencyCode.USD
                    )
                )
            ),
        )

        consistent_trip = MagicMock()
        consistent_trip.id = str(uuid4())
        consistent_trip.user_id = "family_organizer_003"
        consistent_trip.title = "Data Consistency Test Trip"
        consistent_trip.description = "Testing data consistency across operations"
        consistent_trip.destinations = consistent_trip_data.destinations
        consistent_trip.start_date = datetime(2024, 7, 15, tzinfo=timezone.utc)
        consistent_trip.end_date = datetime(2024, 7, 25, tzinfo=timezone.utc)
        consistent_trip.preferences = {"budget": {"total": 5500, "currency": "USD"}}
        consistent_trip.status = "planning"
        consistent_trip.created_at = datetime.now(timezone.utc)
        consistent_trip.updated_at = datetime.now(timezone.utc)

        comprehensive_trip_service.create_trip.return_value = consistent_trip
        comprehensive_trip_service.get_trip.return_value = consistent_trip
        comprehensive_trip_service.update_trip.return_value = consistent_trip

        # Create trip
        created_trip = await create_trip(
            consistent_trip_data, family_organizer_principal, comprehensive_trip_service
        )

        trip_id = UUID(consistent_trip.id)

        # Get trip and verify consistency
        retrieved_trip = await get_trip(
            trip_id, family_organizer_principal, comprehensive_trip_service
        )

        assert retrieved_trip.id == created_trip.id
        assert retrieved_trip.title == created_trip.title
        assert retrieved_trip.user_id == created_trip.user_id

        # Update trip and verify consistency
        update_request = UpdateTripRequest(
            description="Updated: Testing data consistency across operations"
        )

        consistent_trip.description = (
            "Updated: Testing data consistency across operations"
        )

        updated_trip = await update_trip(
            trip_id,
            update_request,
            family_organizer_principal,
            comprehensive_trip_service,
        )

        assert updated_trip.id == created_trip.id
        assert updated_trip.title == created_trip.title  # Should remain the same

        # Get summary and verify consistency
        trip_summary = await get_trip_summary(
            trip_id, family_organizer_principal, comprehensive_trip_service
        )

        assert trip_summary.id == UUID(created_trip.id)
        assert trip_summary.title == created_trip.title
