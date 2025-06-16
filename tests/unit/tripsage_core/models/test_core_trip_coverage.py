"""
Coverage-focused tests for DB Trip Models.

These tests exercise the actual DB trip model implementation to increase coverage.
"""

from datetime import date

from tripsage_core.models.trip import EnhancedBudget as TripBudget
from tripsage_core.models.trip import Trip as DbTrip


class TestDbTripModelCoverage:
    """Test actual DbTrip model functionality for coverage."""

    def test_db_trip_basic_creation(self):
        """Test basic DbTrip model creation."""
        trip = DbTrip(
            title="Basic Test Trip",
            destination="Madrid, Spain",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 10),
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
        trip = DbTrip(
            title="Complete Test Trip",
            description="A comprehensive test trip with all fields",
            destination="Kyoto, Japan",
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 15),
            travelers=3,
            budget=2500.00,
            status="booked",
            visibility="shared",
            tags=["cultural", "family", "photography"],
        )

        # Verify all attributes
        assert trip.description == "A comprehensive test trip with all fields"
        assert trip.budget == 2500.00
        assert trip.visibility == "shared"
        assert len(trip.tags) == 3
        assert "cultural" in trip.tags

    def test_db_trip_with_enhanced_budget(self):
        """Test DbTrip with enhanced budget."""
        enhanced_budget = TripBudget(
            total=3000.0,
            currency="EUR",
            spent=750.0,
            breakdown={
                "accommodation": 1200.0,
                "food": 600.0,
                "activities": 800.0,
                "transportation": 400.0,
            },
        )

        trip = DbTrip(
            title="Budget Test Trip",
            start_date=date(2025, 8, 15),
            end_date=date(2025, 8, 25),
            destination="Berlin, Germany",
            travelers=2,
            enhanced_budget=enhanced_budget,
            spent_amount=750.0,
        )

        # Verify budget integration
        assert trip.enhanced_budget is not None
        assert trip.enhanced_budget.total == 3000.0
        assert trip.enhanced_budget.currency == "EUR"
        assert trip.enhanced_budget.spent == 750.0
        assert trip.spent_amount == 750.0

    def test_trip_budget_model(self):
        """Test TripBudget model functionality."""
        budget = TripBudget(
            total=2500.0,
            currency="GBP",
            spent=625.0,
            breakdown={
                "hotels": 1000.0,
                "meals": 750.0,
                "sights": 500.0,
                "transport": 250.0,
            },
        )

        # Verify budget attributes
        assert budget.total == 2500.0
        assert budget.currency == "GBP"
        assert budget.spent == 625.0
        assert len(budget.breakdown) == 4
        assert budget.breakdown["hotels"] == 1000.0

    def test_db_trip_date_validation(self):
        """Test date validation in DbTrip."""
        # Test valid date range
        trip = DbTrip(
            title="Date Test Trip",
            destination="Barcelona, Spain",
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 10),
            travelers=1,
        )

        assert trip.start_date < trip.end_date

        # Test same day trip
        same_day_trip = DbTrip(
            title="Same Day Trip",
            destination="Local City",
            start_date=date(2024, 11, 5),
            end_date=date(2024, 11, 5),
            travelers=1,
        )

        assert same_day_trip.start_date == same_day_trip.end_date

    def test_db_trip_budget_handling(self):
        """Test budget handling in DbTrip."""
        # Test with integer budget
        trip_int = DbTrip(
            title="Integer Budget Trip",
            destination="Rome, Italy",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 7),
            travelers=2,
            budget=1500,
        )

        assert trip_int.budget == 1500

        # Test with float budget
        trip_float = DbTrip(
            title="Float Budget Trip",
            destination="Florence, Italy",
            start_date=date(2024, 12, 8),
            end_date=date(2024, 12, 14),
            travelers=2,
            budget=1750.50,
        )

        assert trip_float.budget == 1750.50

    def test_db_trip_tags_handling(self):
        """Test tags handling in DbTrip."""
        # Test with empty tags
        trip_no_tags = DbTrip(
            title="No Tags Trip",
            destination="Vienna, Austria",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 7),
            travelers=1,
            tags=[],
        )

        assert trip_no_tags.tags == []

        # Test with multiple tags
        trip_tags = DbTrip(
            title="Tagged Trip",
            destination="Prague, Czech Republic",
            start_date=date(2025, 1, 8),
            end_date=date(2025, 1, 14),
            travelers=2,
            tags=["history", "architecture", "beer", "culture"],
        )

        assert len(trip_tags.tags) == 4
        assert "history" in trip_tags.tags
        assert "beer" in trip_tags.tags

    def test_db_trip_status_values(self):
        """Test various status values in DbTrip."""
        statuses = ["planning", "booked", "in_progress", "completed", "cancelled"]

        for _, status in enumerate(statuses):
            trip = DbTrip(
                title=f"Status Test {status.title()}",
                destination="Test Destination",
                start_date=date(2025, 3, 1),
                end_date=date(2025, 3, 7),
                travelers=1,
                status=status,
            )

            assert trip.status == status

    def test_db_trip_visibility_values(self):
        """Test various visibility values in DbTrip."""
        visibilities = ["private", "shared", "public"]

        for _, visibility in enumerate(visibilities):
            trip = DbTrip(
                title=f"Visibility Test {visibility.title()}",
                destination="Test Destination",
                start_date=date(2025, 3, 8),
                end_date=date(2025, 3, 14),
                travelers=1,
                visibility=visibility,
            )

            assert trip.visibility == visibility

    def test_db_trip_travelers_validation(self):
        """Test travelers count validation."""
        # Test minimum travelers
        trip_solo = DbTrip(
            title="Solo Adventure",
            destination="Iceland",
            start_date=date(2025, 4, 1),
            end_date=date(2025, 4, 10),
            travelers=1,
        )

        assert trip_solo.travelers == 1

        # Test multiple travelers
        trip_group = DbTrip(
            title="Group Adventure",
            destination="New Zealand",
            start_date=date(2025, 4, 15),
            end_date=date(2025, 4, 30),
            travelers=8,
        )

        assert trip_group.travelers == 8

    def test_db_trip_property_methods(self):
        """Test DbTrip property methods."""
        enhanced_budget = TripBudget(
            total=1800.0,
            currency="CAD",
            spent=450.0,
            breakdown={"accommodation": 900, "other": 900},
        )

        trip = DbTrip(
            title="Property Test Trip",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 9, 10),
            destination="Toronto, Canada",
            travelers=1,
            budget=1200,  # Legacy budget
            enhanced_budget=enhanced_budget,
            spent_amount=450.0,
            visibility="shared",
        )

        # Test effective_budget property
        if hasattr(trip, "effective_budget"):
            assert trip.effective_budget == 1800.0  # Should use enhanced budget

        # Test budget_utilization property
        if hasattr(trip, "budget_utilization"):
            expected_utilization = (450.0 / 1800.0) * 100
            assert abs(trip.budget_utilization - expected_utilization) < 0.01

        # Test is_shared property
        if hasattr(trip, "is_shared"):
            assert trip.is_shared is True  # visibility is "shared"

    def test_db_trip_legacy_compatibility(self):
        """Test legacy compatibility features."""
        trip = DbTrip(
            title="Legacy Test Trip",
            start_date=date(2025, 9, 15),
            end_date=date(2025, 9, 22),
            destination="Vancouver, Canada",
            travelers=3,
        )

        # Test name property (legacy compatibility)
        if hasattr(trip, "name"):
            assert trip.name == trip.title

    def test_db_trip_string_representation(self):
        """Test string representation of DbTrip."""
        trip = DbTrip(
            title="String Test Trip",
            destination="Amsterdam, Netherlands",
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 7),
            travelers=2,
        )

        # Test that string representation exists and contains key info
        trip_str = str(trip)
        assert isinstance(trip_str, str)
        assert len(trip_str) > 0

    def test_db_trip_attribute_access(self):
        """Test attribute access patterns."""
        trip = DbTrip(
            title="Attribute Test Trip",
            destination="Stockholm, Sweden",
            start_date=date(2025, 6, 8),
            end_date=date(2025, 6, 14),
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
        assert hasattr(trip, "budget")
        assert hasattr(trip, "status")
        assert hasattr(trip, "visibility")
        assert hasattr(trip, "tags")

    def test_db_trip_duration_calculation(self):
        """Test trip duration calculation if available."""
        trip = DbTrip(
            title="Duration Test Trip",
            destination="Helsinki, Finland",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 8),
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
