"""Comprehensive unit tests for the unified Trip model.

This test suite provides 90%+ coverage for the Trip model,
testing all validations, properties, and business logic.
"""

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from tripsage_core.models.schemas_common.enums import TripStatus, TripType
from tripsage_core.models.trip import (
    BudgetBreakdown,
    EnhancedBudget,
    Trip,
    TripPreferences,
    TripVisibility,
)


class TestBudgetBreakdown:
    """Test BudgetBreakdown model."""

    def test_budget_breakdown_defaults(self):
        """Test BudgetBreakdown with default values."""
        breakdown = BudgetBreakdown()
        assert breakdown.accommodation == 0.0
        assert breakdown.transportation == 0.0
        assert breakdown.food == 0.0
        assert breakdown.activities == 0.0
        assert breakdown.miscellaneous == 0.0

    def test_budget_breakdown_with_values(self):
        """Test BudgetBreakdown with specific values."""
        breakdown = BudgetBreakdown(
            accommodation=1000.0,
            transportation=500.0,
            food=300.0,
            activities=200.0,
            miscellaneous=100.0,
        )
        assert breakdown.accommodation == 1000.0
        assert breakdown.transportation == 500.0
        assert breakdown.food == 300.0
        assert breakdown.activities == 200.0
        assert breakdown.miscellaneous == 100.0

    def test_budget_breakdown_negative_values_rejected(self):
        """Test BudgetBreakdown rejects negative values."""
        with pytest.raises(ValidationError):
            BudgetBreakdown(accommodation=-100.0)


class TestEnhancedBudget:
    """Test EnhancedBudget model."""

    def test_enhanced_budget_required_fields(self):
        """Test EnhancedBudget with required fields only."""
        budget = EnhancedBudget(total=5000.0)
        assert budget.total == 5000.0
        assert budget.currency == "USD"
        assert budget.spent == 0.0
        assert isinstance(budget.breakdown, BudgetBreakdown)

    def test_enhanced_budget_full_data(self):
        """Test EnhancedBudget with all fields."""
        breakdown = BudgetBreakdown(
            accommodation=2000.0,
            transportation=1000.0,
            food=800.0,
            activities=700.0,
            miscellaneous=500.0,
        )
        budget = EnhancedBudget(
            total=5000.0, currency="EUR", spent=1500.0, breakdown=breakdown
        )
        assert budget.total == 5000.0
        assert budget.currency == "EUR"
        assert budget.spent == 1500.0
        assert budget.breakdown.accommodation == 2000.0

    def test_enhanced_budget_negative_total_rejected(self):
        """Test EnhancedBudget rejects negative total."""
        with pytest.raises(ValidationError):
            EnhancedBudget(total=-1000.0)

    def test_enhanced_budget_negative_spent_rejected(self):
        """Test EnhancedBudget rejects negative spent amount."""
        with pytest.raises(ValidationError):
            EnhancedBudget(total=1000.0, spent=-100.0)


class TestTripPreferences:
    """Test TripPreferences model."""

    def test_trip_preferences_defaults(self):
        """Test TripPreferences with default values."""
        prefs = TripPreferences()
        assert prefs.budget_flexibility == 0.1
        assert prefs.date_flexibility == 0
        assert prefs.destination_flexibility is False
        assert prefs.accommodation_preferences == {}
        assert prefs.transportation_preferences == {}
        assert prefs.activity_preferences == []
        assert prefs.dietary_restrictions == []
        assert prefs.accessibility_needs == []

    def test_trip_preferences_with_values(self):
        """Test TripPreferences with custom values."""
        prefs = TripPreferences(
            budget_flexibility=0.2,
            date_flexibility=3,
            destination_flexibility=True,
            accommodation_preferences={"type": "hotel", "rating": 4},
            transportation_preferences={"mode": "train", "class": "first"},
            activity_preferences=["hiking", "museums"],
            dietary_restrictions=["vegetarian", "gluten-free"],
            accessibility_needs=["wheelchair"],
        )
        assert prefs.budget_flexibility == 0.2
        assert prefs.date_flexibility == 3
        assert prefs.destination_flexibility is True
        assert prefs.accommodation_preferences["type"] == "hotel"
        assert "hiking" in prefs.activity_preferences

    def test_trip_preferences_budget_flexibility_validation(self):
        """Test budget flexibility validation."""
        # Valid range
        prefs = TripPreferences(budget_flexibility=0.5)
        assert prefs.budget_flexibility == 0.5

        # Invalid: too low
        with pytest.raises(ValidationError):
            TripPreferences(budget_flexibility=-0.1)

        # Invalid: too high
        with pytest.raises(ValidationError):
            TripPreferences(budget_flexibility=1.5)

    def test_trip_preferences_date_flexibility_validation(self):
        """Test date flexibility validation."""
        # Valid
        prefs = TripPreferences(date_flexibility=7)
        assert prefs.date_flexibility == 7

        # Invalid: negative
        with pytest.raises(ValidationError):
            TripPreferences(date_flexibility=-1)


class TestTrip:
    """Test the unified Trip model."""

    @pytest.fixture
    def valid_trip_data(self):
        """Provide valid trip data for testing."""
        return {
            "user_id": uuid4(),
            "title": "European Adventure",
            "description": "A two-week journey through Europe",
            "start_date": date.today() + timedelta(days=30),
            "end_date": date.today() + timedelta(days=44),
            "destination": "Europe",
            "budget_breakdown": EnhancedBudget(
                total=5000.0,
                currency="EUR",
                breakdown=BudgetBreakdown(
                    accommodation=2000.0,
                    transportation=1500.0,
                    food=1000.0,
                    activities=500.0,
                ),
            ),
            "travelers": 2,
            "trip_type": TripType.LEISURE,
            "visibility": TripVisibility.PRIVATE,
            "tags": ["europe", "adventure", "culture"],
        }

    def test_trip_creation_with_defaults(self, valid_trip_data):
        """Test Trip creation with default values."""
        trip = Trip(**valid_trip_data)

        # Check required fields
        assert isinstance(trip.id, UUID)
        assert trip.user_id == valid_trip_data["user_id"]
        assert trip.title == "European Adventure"
        assert trip.destination == "Europe"

        # Check defaults
        assert trip.status == TripStatus.PLANNING
        assert trip.visibility == TripVisibility.PRIVATE
        assert isinstance(trip.preferences_extended, TripPreferences)
        assert trip.notes == []
        assert trip.search_metadata == {}
        assert isinstance(trip.created_at, datetime)
        assert isinstance(trip.updated_at, datetime)

    def test_trip_creation_with_all_fields(self, valid_trip_data):
        """Test Trip creation with all fields specified."""
        preferences = TripPreferences(
            budget_flexibility=0.15,
            date_flexibility=2,
            activity_preferences=["museums", "hiking"],
        )

        trip = Trip(
            **valid_trip_data,
            status=TripStatus.BOOKED,
            preferences_extended=preferences,
            notes=[{"content": "Check visa requirements", "created_at": "2025-01-01"}],
            search_metadata={"source": "manual", "version": "1.0"},
        )

        assert trip.status == TripStatus.BOOKED
        assert trip.preferences_extended.budget_flexibility == 0.15
        assert len(trip.notes) == 1
        assert trip.search_metadata["source"] == "manual"

    def test_trip_date_validation(self, valid_trip_data):
        """Test trip date validation."""
        # Valid: end date after start date
        trip = Trip(**valid_trip_data)
        assert trip.end_date > trip.start_date

        # Invalid: end date before start date
        invalid_data = valid_trip_data.copy()
        invalid_data["end_date"] = invalid_data["start_date"] - timedelta(days=1)
        with pytest.raises(ValidationError) as exc_info:
            Trip(**invalid_data)
        assert "End date must not be before start date" in str(exc_info.value)

        # Valid: same day trip
        same_day_data = valid_trip_data.copy()
        same_day_data["end_date"] = same_day_data["start_date"]
        trip = Trip(**same_day_data)
        assert trip.duration_days == 1

    def test_trip_travelers_validation(self, valid_trip_data):
        """Test travelers validation."""
        # Valid
        trip = Trip(**valid_trip_data)
        assert trip.travelers == 2

        # Invalid: zero travelers
        invalid_data = valid_trip_data.copy()
        invalid_data["travelers"] = 0
        with pytest.raises(ValidationError):
            Trip(**invalid_data)

        # Invalid: negative travelers
        invalid_data["travelers"] = -1
        with pytest.raises(ValidationError):
            Trip(**invalid_data)

    def test_trip_title_validation(self, valid_trip_data):
        """Test title validation."""
        # Valid
        trip = Trip(**valid_trip_data)
        assert trip.title == "European Adventure"

        # Invalid: empty title
        invalid_data = valid_trip_data.copy()
        invalid_data["title"] = ""
        with pytest.raises(ValidationError):
            Trip(**invalid_data)

        # Valid: max length title
        max_title = "A" * 200
        valid_data = valid_trip_data.copy()
        valid_data["title"] = max_title
        trip = Trip(**valid_data)
        assert len(trip.title) == 200

        # Invalid: too long title
        invalid_data["title"] = "A" * 201
        with pytest.raises(ValidationError):
            Trip(**invalid_data)

    def test_trip_tags_validation(self, valid_trip_data):
        """Test tags validation and cleaning."""
        # Test duplicate removal
        data = valid_trip_data.copy()
        data["tags"] = ["europe", "adventure", "europe", "  culture  ", ""]
        trip = Trip(**data)
        assert len(trip.tags) == 3
        assert "europe" in trip.tags
        assert "culture" in trip.tags
        assert "" not in trip.tags

        # Test max tags limit
        data["tags"] = [f"tag{i}" for i in range(25)]
        with pytest.raises(ValidationError) as exc_info:
            Trip(**data)
        assert "at most 20 items" in str(exc_info.value)

    def test_trip_visibility_validation(self, valid_trip_data):
        """Test visibility validation."""
        # Valid values
        for visibility in ["private", "shared", "public"]:
            data = valid_trip_data.copy()
            data["visibility"] = visibility
            trip = Trip(**data)
            assert trip.visibility == visibility

        # Invalid value
        invalid_data = valid_trip_data.copy()
        invalid_data["visibility"] = "secret"
        with pytest.raises(ValidationError):
            Trip(**invalid_data)

    def test_trip_properties(self, valid_trip_data):
        """Test Trip computed properties."""
        trip = Trip(**valid_trip_data)

        # Duration
        assert trip.duration_days == 15

        # Budget calculations
        assert trip.budget_per_day == 5000.0 / 15
        assert trip.budget_per_person == 5000.0 / 2
        assert trip.budget_utilization == 0.0
        assert trip.remaining_budget == 5000.0

        # Update spent amount
        trip.budget_breakdown.spent = 2500.0
        assert trip.budget_utilization == 50.0
        assert trip.remaining_budget == 2500.0

        # Status checks
        assert trip.is_active is True
        assert trip.is_completed is False
        assert trip.is_cancelable is True
        assert trip.is_shared is False

        # Change visibility
        trip.visibility = TripVisibility.PUBLIC
        assert trip.is_shared is True

    def test_trip_can_modify(self, valid_trip_data):
        """Test can_modify method."""
        # Future trip in planning status
        trip = Trip(**valid_trip_data)
        assert trip.can_modify() is True

        # Future trip in booked status
        trip.status = TripStatus.BOOKED
        assert trip.can_modify() is True

        # Completed trip
        trip.status = TripStatus.COMPLETED
        assert trip.can_modify() is False

        # Cancelled trip
        trip.status = TripStatus.CANCELLED
        assert trip.can_modify() is False

        # Past trip in planning status
        past_data = valid_trip_data.copy()
        past_data["start_date"] = date.today() - timedelta(days=10)
        past_data["end_date"] = date.today() - timedelta(days=5)
        past_trip = Trip(**past_data)
        assert past_trip.can_modify() is False

    def test_trip_update_status(self, valid_trip_data):
        """Test update_status method."""
        trip = Trip(**valid_trip_data)

        # Valid transitions from PLANNING
        assert trip.update_status(TripStatus.BOOKED) is True
        assert trip.status == TripStatus.BOOKED

        # Valid transition from BOOKED
        assert trip.update_status(TripStatus.COMPLETED) is True
        assert trip.status == TripStatus.COMPLETED

        # Invalid transition from COMPLETED
        assert trip.update_status(TripStatus.PLANNING) is False
        assert trip.status == TripStatus.COMPLETED

        # Test CANCELLED state
        trip2 = Trip(**valid_trip_data)
        assert trip2.update_status(TripStatus.CANCELLED) is True
        assert trip2.status == TripStatus.CANCELLED
        # Cannot change from CANCELLED
        assert trip2.update_status(TripStatus.PLANNING) is False

    def test_trip_add_tag(self, valid_trip_data):
        """Test add_tag method."""
        trip = Trip(**valid_trip_data)
        initial_tags = len(trip.tags)

        # Add new tag
        assert trip.add_tag("beach") is True
        assert "beach" in trip.tags
        assert len(trip.tags) == initial_tags + 1

        # Try to add duplicate
        assert trip.add_tag("beach") is False
        assert len(trip.tags) == initial_tags + 1

        # Add tag with whitespace
        assert trip.add_tag("  mountain  ") is True
        assert "mountain" in trip.tags

        # Try to add empty tag
        assert trip.add_tag("") is False
        assert trip.add_tag("   ") is False

        # Test max tags limit
        trip.tags = [f"tag{i}" for i in range(20)]
        assert trip.add_tag("overflow") is False
        assert len(trip.tags) == 20

    def test_trip_remove_tag(self, valid_trip_data):
        """Test remove_tag method."""
        trip = Trip(**valid_trip_data)
        initial_tags = trip.tags.copy()

        # Remove existing tag
        assert trip.remove_tag("europe") is True
        assert "europe" not in trip.tags
        assert len(trip.tags) == len(initial_tags) - 1

        # Try to remove non-existent tag
        assert trip.remove_tag("nonexistent") is False
        assert len(trip.tags) == len(initial_tags) - 1

        # Remove tag with whitespace
        assert trip.remove_tag("  adventure  ") is True
        assert "adventure" not in trip.tags

    def test_trip_budget_edge_cases(self, valid_trip_data):
        """Test budget calculation edge cases."""
        # Zero budget
        data = valid_trip_data.copy()
        data["budget_breakdown"] = EnhancedBudget(total=0.0)
        trip = Trip(**data)
        assert trip.budget_per_day == 0.0
        assert trip.budget_per_person == 0.0
        assert trip.budget_utilization == 0.0

        # Overspent budget
        trip.budget_breakdown.spent = 100.0
        assert trip.budget_utilization == 0.0  # Still 0 because total is 0
        assert trip.remaining_budget == 0.0

        # Normal budget overspent
        trip.budget_breakdown.total = 1000.0
        trip.budget_breakdown.spent = 1500.0
        assert trip.budget_utilization == 100.0  # Capped at 100%
        assert trip.remaining_budget == 0.0  # Can't be negative

    def test_trip_json_serialization(self, valid_trip_data):
        """Test Trip JSON serialization."""
        trip = Trip(**valid_trip_data)

        # Convert to dict
        trip_dict = trip.model_dump()
        assert isinstance(trip_dict["id"], UUID)
        assert trip_dict["title"] == "European Adventure"
        assert isinstance(trip_dict["created_at"], datetime)

        # Convert to JSON
        trip_json = trip.model_dump_json()
        assert isinstance(trip_json, str)
        assert "European Adventure" in trip_json

    def test_trip_model_validation_errors(self, valid_trip_data):
        """Test various validation error scenarios."""
        # Missing required field
        incomplete_data = valid_trip_data.copy()
        del incomplete_data["title"]
        with pytest.raises(ValidationError) as exc_info:
            Trip(**incomplete_data)
        assert "title" in str(exc_info.value)

        # Invalid enum value
        invalid_data = valid_trip_data.copy()
        invalid_data["trip_type"] = "invalid_type"
        with pytest.raises(ValidationError):
            Trip(**invalid_data)

        # Invalid UUID
        invalid_data = valid_trip_data.copy()
        invalid_data["user_id"] = "not-a-uuid"
        with pytest.raises(ValidationError):
            Trip(**invalid_data)


class TestTripIntegration:
    """Integration tests for Trip model with related models."""

    def test_trip_with_complex_preferences(self):
        """Test Trip with complex preferences setup."""
        preferences = TripPreferences(
            budget_flexibility=0.25,
            date_flexibility=5,
            destination_flexibility=True,
            accommodation_preferences={
                "type": "hotel",
                "rating": 4,
                "amenities": ["wifi", "breakfast", "gym"],
            },
            transportation_preferences={
                "mode": ["flight", "train"],
                "class": "business",
                "direct_only": True,
            },
            activity_preferences=["cultural", "adventure", "relaxation"],
            dietary_restrictions=["vegetarian", "nut-free"],
            accessibility_needs=["step-free access", "hearing loop"],
        )

        budget = EnhancedBudget(
            total=10000.0,
            currency="USD",
            spent=3500.0,
            breakdown=BudgetBreakdown(
                accommodation=4000.0,
                transportation=3000.0,
                food=1500.0,
                activities=1000.0,
                miscellaneous=500.0,
            ),
        )

        trip = Trip(
            user_id=uuid4(),
            title="Accessible Cultural Journey",
            description="A carefully planned trip with accessibility considerations",
            start_date=date.today() + timedelta(days=60),
            end_date=date.today() + timedelta(days=75),
            destination="Japan",
            budget_breakdown=budget,
            travelers=3,
            trip_type=TripType.LEISURE,
            visibility=TripVisibility.SHARED,
            tags=["accessible", "cultural", "japan", "family"],
            preferences_extended=preferences,
            notes=[
                {"content": "Check accessibility at each venue", "priority": "high"},
                {"content": "Book dietary-friendly restaurants", "priority": "medium"},
            ],
        )

        # Verify complex setup
        assert trip.preferences_extended.accommodation_preferences["rating"] == 4
        assert (
            "wifi" in trip.preferences_extended.accommodation_preferences["amenities"]
        )
        assert trip.budget_utilization == 35.0
        assert trip.remaining_budget == 6500.0
        assert len(trip.notes) == 2
        assert trip.is_shared is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
