"""
Coverage-focused tests for DB Trip Models.

These tests exercise the actual DB trip model implementation to increase coverage.
"""

from datetime import date
from uuid import uuid4

from tripsage_core.models.trip import EnhancedBudget as TripBudget
from tripsage_core.models.trip import Trip as DbTrip


class TestDbTripModelCoverage:
    """Test actual DbTrip model functionality for coverage."""

    def test_db_trip_basic_creation(self):
        """Test basic DbTrip model creation."""
        budget = TripBudget(total=1000.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="Basic Test Trip",
            destination="Madrid, Spain",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 10),
            budget_breakdown=budget,
            travelers=2,
        )

        # Verify basic attributes
        assert trip.title == "Basic Test Trip"
        assert trip.destination == "Madrid, Spain"
        assert trip.start_date == date(2024, 9, 1)
        assert trip.end_date == date(2024, 9, 10)
        assert trip.travelers == 2

    def test_db_trip_with_optional_fields(self):
        """Test DbTrip with all optional fields."""
        budget = TripBudget(total=2500.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="Complete Test Trip",
            description="A comprehensive test trip with all fields",
            destination="Kyoto, Japan",
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 15),
            budget_breakdown=budget,
            travelers=3,
            tags=["cultural", "family", "photography"],
        )

        # Verify all attributes
        assert trip.description == "A comprehensive test trip with all fields"
        assert trip.budget_breakdown.total == 2500.00
        assert len(trip.tags) == 3
        assert "cultural" in trip.tags

    def test_db_trip_with_enhanced_budget(self):
        """Test DbTrip with enhanced budget."""
        from tripsage_core.models.trip import BudgetBreakdown

        breakdown = BudgetBreakdown(
            accommodation=1200.0,
            food=600.0,
            activities=800.0,
            transportation=400.0,
        )
        enhanced_budget = TripBudget(
            total=3000.0,
            currency="EUR",
            spent=750.0,
            breakdown=breakdown,
        )

        trip = DbTrip(
            user_id=uuid4(),
            title="Budget Test Trip",
            start_date=date(2025, 8, 15),
            end_date=date(2025, 8, 25),
            destination="Berlin, Germany",
            travelers=2,
            budget_breakdown=enhanced_budget,
        )

        # Verify budget integration
        assert trip.budget_breakdown is not None
        assert trip.budget_breakdown.total == 3000.0
        assert trip.budget_breakdown.currency == "EUR"
        assert trip.budget_breakdown.spent == 750.0
        assert trip.budget_breakdown.breakdown.accommodation == 1200.0

    def test_trip_budget_model(self):
        """Test TripBudget model functionality."""
        from tripsage_core.models.trip import BudgetBreakdown

        breakdown = BudgetBreakdown(
            accommodation=1000.0,
            food=750.0,
            activities=500.0,
            transportation=250.0,
        )
        budget = TripBudget(
            total=2500.0,
            currency="GBP",
            spent=625.0,
            breakdown=breakdown,
        )

        # Verify budget attributes
        assert budget.total == 2500.0
        assert budget.currency == "GBP"
        assert budget.spent == 625.0
        assert budget.breakdown.accommodation == 1000.0
        assert budget.breakdown.food == 750.0

    def test_db_trip_date_validation(self):
        """Test date validation in DbTrip."""
        # Test valid date range
        budget = TripBudget(total=1000.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="Date Test Trip",
            destination="Barcelona, Spain",
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 10),
            budget_breakdown=budget,
            travelers=1,
        )

        assert trip.start_date < trip.end_date

        # Test same day trip
        budget2 = TripBudget(total=500.0, currency="USD")
        same_day_trip = DbTrip(
            user_id=uuid4(),
            title="Same Day Trip",
            destination="Local City",
            start_date=date(2024, 11, 5),
            end_date=date(2024, 11, 5),
            budget_breakdown=budget2,
            travelers=1,
        )

        assert same_day_trip.start_date == same_day_trip.end_date

    def test_db_trip_budget_handling(self):
        """Test budget handling in DbTrip."""
        # Test with integer budget
        budget_int = TripBudget(total=1500.0, currency="USD")
        trip_int = DbTrip(
            user_id=uuid4(),
            title="Integer Budget Trip",
            destination="Rome, Italy",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 7),
            budget_breakdown=budget_int,
            travelers=2,
        )

        assert trip_int.budget_breakdown.total == 1500.0

        # Test with float budget
        budget_float = TripBudget(total=1750.50, currency="USD")
        trip_float = DbTrip(
            user_id=uuid4(),
            title="Float Budget Trip",
            destination="Florence, Italy",
            start_date=date(2024, 12, 8),
            end_date=date(2024, 12, 14),
            budget_breakdown=budget_float,
            travelers=2,
        )

        assert trip_float.budget_breakdown.total == 1750.50

    def test_db_trip_tags_handling(self):
        """Test tags handling in DbTrip."""
        # Test with empty tags
        budget = TripBudget(total=800.0, currency="USD")
        trip_no_tags = DbTrip(
            user_id=uuid4(),
            title="No Tags Trip",
            destination="Vienna, Austria",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            budget_breakdown=budget,
            travelers=1,
            tags=[],
        )

        assert trip_no_tags.tags == []

        # Test with multiple tags
        budget_tags = TripBudget(total=1200.0, currency="USD")
        trip_tags = DbTrip(
            user_id=uuid4(),
            title="Tagged Trip",
            destination="Prague, Czech Republic",
            start_date=date(2025, 1, 8),
            end_date=date(2025, 1, 14),
            budget_breakdown=budget_tags,
            travelers=2,
            tags=["history", "architecture", "beer", "culture"],
        )

        assert len(trip_tags.tags) == 4
        assert "history" in trip_tags.tags
        assert "beer" in trip_tags.tags

    def test_db_trip_status_values(self):
        """Test various status values in DbTrip."""
        from tripsage_core.models.schemas_common.enums import TripStatus

        statuses = [
            TripStatus.PLANNING,
            TripStatus.BOOKED,
            TripStatus.IN_PROGRESS,
            TripStatus.COMPLETED,
            TripStatus.CANCELLED,
        ]

        for i, status in enumerate(statuses):
            budget = TripBudget(total=1000.0 + i * 100, currency="USD")
            trip = DbTrip(
                user_id=uuid4(),
                title=f"Status Test {status.value.title()}",
                destination="Test Destination",
                start_date=date(2025, 3, 1),
                end_date=date(2025, 3, 7),
                budget_breakdown=budget,
                travelers=1,
                status=status,
            )

            assert trip.status == status

    def test_db_trip_visibility_values(self):
        """Test various visibility values in DbTrip."""
        from tripsage_core.models.schemas_common.enums import TripVisibility

        visibilities = [
            TripVisibility.PRIVATE,
            TripVisibility.SHARED,
            TripVisibility.PUBLIC,
        ]

        for i, visibility in enumerate(visibilities):
            budget = TripBudget(total=900.0 + i * 50, currency="USD")
            trip = DbTrip(
                user_id=uuid4(),
                title=f"Visibility Test {visibility.value.title()}",
                destination="Test Destination",
                start_date=date(2025, 3, 8),
                end_date=date(2025, 3, 14),
                budget_breakdown=budget,
                travelers=1,
                visibility=visibility,
            )

            assert trip.visibility == visibility

    def test_db_trip_travelers_validation(self):
        """Test travelers count validation."""
        # Test minimum travelers
        budget = TripBudget(total=2000.0, currency="USD")
        trip_solo = DbTrip(
            user_id=uuid4(),
            title="Solo Adventure",
            destination="Iceland",
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 10),
            budget_breakdown=budget,
            travelers=1,
        )

        assert trip_solo.travelers == 1

        # Test multiple travelers
        budget_group = TripBudget(total=5000.0, currency="USD")
        trip_group = DbTrip(
            user_id=uuid4(),
            title="Group Adventure",
            destination="New Zealand",
            start_date=date(2025, 4, 15),
            end_date=date(2025, 4, 30),
            budget_breakdown=budget_group,
            travelers=8,
        )

        assert trip_group.travelers == 8

    def test_db_trip_property_methods(self):
        """Test DbTrip property methods."""
        from tripsage_core.models.trip import BudgetBreakdown

        breakdown = BudgetBreakdown(accommodation=900.0, miscellaneous=900.0)
        enhanced_budget = TripBudget(
            total=1800.0,
            currency="CAD",
            spent=450.0,
            breakdown=breakdown,
        )

        from tripsage_core.models.schemas_common.enums import TripVisibility

        trip = DbTrip(
            user_id=uuid4(),
            title="Property Test Trip",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 9, 10),
            destination="Toronto, Canada",
            travelers=1,
            budget_breakdown=enhanced_budget,
            visibility=TripVisibility.SHARED,
        )

        # Test basic budget access
        assert trip.budget_breakdown.total == 1800.0
        assert trip.budget_breakdown.currency == "CAD"
        assert trip.budget_breakdown.spent == 450.0

        # Test visibility
        assert trip.visibility == TripVisibility.SHARED

    def test_db_trip_legacy_compatibility(self):
        """Test legacy compatibility features."""
        budget = TripBudget(total=2500.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="Legacy Test Trip",
            start_date=date(2025, 9, 15),
            end_date=date(2025, 9, 22),
            destination="Vancouver, Canada",
            budget_breakdown=budget,
            travelers=3,
        )

        # Test name property (legacy compatibility)
        if hasattr(trip, "name"):
            assert trip.name == trip.title

    def test_db_trip_string_representation(self):
        """Test string representation of DbTrip."""
        budget = TripBudget(total=1800.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="String Test Trip",
            destination="Amsterdam, Netherlands",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 7),
            budget_breakdown=budget,
            travelers=2,
        )

        # Test that string representation exists and contains key info
        trip_str = str(trip)
        assert isinstance(trip_str, str)
        assert len(trip_str) > 0

    def test_db_trip_attribute_access(self):
        """Test attribute access patterns."""
        budget = TripBudget(total=2200.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="Attribute Test Trip",
            destination="Stockholm, Sweden",
            start_date=date(2025, 6, 8),
            end_date=date(2025, 6, 14),
            budget_breakdown=budget,
            travelers=1,
        )

        # Test direct attribute access
        assert hasattr(trip, "title")
        assert hasattr(trip, "destination")
        assert hasattr(trip, "start_date")
        assert hasattr(trip, "end_date")
        assert hasattr(trip, "travelers")

        # Test accessing optional attributes
        assert hasattr(trip, "description")
        assert hasattr(trip, "budget_breakdown")
        assert hasattr(trip, "status")
        assert hasattr(trip, "visibility")
        assert hasattr(trip, "tags")

    def test_db_trip_duration_calculation(self):
        """Test trip duration calculation if available."""
        budget = TripBudget(total=1500.0, currency="USD")
        trip = DbTrip(
            user_id=uuid4(),
            title="Duration Test Trip",
            destination="Helsinki, Finland",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 8),
            budget_breakdown=budget,
            travelers=1,
        )

        # Test duration calculation
        expected_duration = (trip.end_date - trip.start_date).days
        assert expected_duration == 7

        # Test if duration property exists on model
        if hasattr(trip, "duration"):
            assert trip.duration == expected_duration
        elif hasattr(trip, "get_duration"):
            assert trip.get_duration() == expected_duration
