"""
Tests for trip request schemas.

This module tests the Pydantic models used for validating
trip-related requests from the Next.js frontend.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tripsage.api.models.requests.trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    TripSearchRequest,
    UpdateTripRequest,
)
from tripsage_core.models.schemas_common.enums import AccommodationType, CurrencyCode
from tripsage_core.models.schemas_common.financial import Budget, Price
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import (
    AccommodationPreferences,
    TransportationPreferences,
    TripDestination,
    TripPreferences,
)


class TestCreateTripRequest:
    """Test CreateTripRequest schema."""

    def test_valid_trip_creation(self):
        """Test valid trip creation request."""
        destinations = [
            TripDestination(
                name="Paris",
                country="France",
                city="Paris",
                coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
                arrival_date=date(2025, 6, 1),
                departure_date=date(2025, 6, 5),
                duration_days=4,
            ),
            TripDestination(
                name="Rome",
                country="Italy",
                city="Rome",
                arrival_date=date(2025, 6, 5),
                departure_date=date(2025, 6, 10),
                duration_days=5,
            ),
        ]

        data = {
            "title": "Summer European Tour",
            "description": "A wonderful summer vacation across Europe",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 15),
            "destinations": destinations,
        }

        request = CreateTripRequest(**data)
        assert request.title == "Summer European Tour"
        assert len(request.destinations) == 2
        assert request.start_date == date(2025, 6, 1)

    def test_minimal_trip_creation(self):
        """Test trip creation with minimal required fields."""
        destinations = [TripDestination(name="Boston")]

        data = {
            "title": "Weekend Trip",
            "start_date": date(2025, 3, 1),
            "end_date": date(2025, 3, 3),
            "destinations": destinations,
        }

        request = CreateTripRequest(**data)
        assert request.title == "Weekend Trip"
        assert request.description is None
        assert request.preferences is None

    def test_trip_with_preferences(self):
        """Test trip creation with preferences."""
        destinations = [TripDestination(name="Tokyo")]

        budget = Budget(
            total_budget=Price(amount=Decimal("3000.00"), currency=CurrencyCode.USD)
        )
        accommodation = AccommodationPreferences(
            type=AccommodationType.HOTEL,
            min_rating=4.0,
        )
        preferences = TripPreferences(
            budget=budget,
            accommodation=accommodation,
            activities=["sightseeing", "food_tours"],
        )

        data = {
            "title": "Tokyo Adventure",
            "start_date": date(2025, 4, 1),
            "end_date": date(2025, 4, 10),
            "destinations": destinations,
            "preferences": preferences,
        }

        request = CreateTripRequest(**data)
        assert request.preferences.budget.total_budget.amount == Decimal("3000.00")
        assert request.preferences.accommodation.min_rating == 4.0

    def test_title_validation(self):
        """Test title validation rules."""
        base_data = {
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 5),
            "destinations": [TripDestination(name="Paris")],
        }

        # Empty title
        with pytest.raises(ValidationError):
            CreateTripRequest(**{**base_data, "title": ""})

        # Too long title
        with pytest.raises(ValidationError):
            CreateTripRequest(**{**base_data, "title": "A" * 101})

        # Valid boundary titles
        request = CreateTripRequest(**{**base_data, "title": "A"})
        assert request.title == "A"

        request = CreateTripRequest(**{**base_data, "title": "A" * 100})
        assert len(request.title) == 100

    def test_description_validation(self):
        """Test description validation rules."""
        base_data = {
            "title": "Test Trip",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 5),
            "destinations": [TripDestination(name="Paris")],
        }

        # Too long description
        with pytest.raises(ValidationError):
            CreateTripRequest(**{**base_data, "description": "A" * 501})

        # Valid description
        request = CreateTripRequest(**{**base_data, "description": "A" * 500})
        assert len(request.description) == 500

    def test_date_validation(self):
        """Test date validation rules."""
        base_data = {
            "title": "Test Trip",
            "destinations": [TripDestination(name="Paris")],
        }

        # End date before start date
        with pytest.raises(ValidationError, match="End date must be after start date"):
            CreateTripRequest(
                **{
                    **base_data,
                    "start_date": date(2025, 6, 10),
                    "end_date": date(2025, 6, 5),
                }
            )

        # Same start and end date (should fail)
        with pytest.raises(ValidationError, match="End date must be after start date"):
            CreateTripRequest(
                **{
                    **base_data,
                    "start_date": date(2025, 6, 5),
                    "end_date": date(2025, 6, 5),
                }
            )

        # Valid dates
        request = CreateTripRequest(
            **{
                **base_data,
                "start_date": date(2025, 6, 1),
                "end_date": date(2025, 6, 5),
            }
        )
        assert request.end_date > request.start_date

    def test_destinations_validation(self):
        """Test destinations validation rules."""
        base_data = {
            "title": "Test Trip",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 5),
        }

        # Empty destinations list
        with pytest.raises(ValidationError):
            CreateTripRequest(**{**base_data, "destinations": []})

        # Valid single destination
        destinations = [TripDestination(name="Paris")]
        request = CreateTripRequest(**{**base_data, "destinations": destinations})
        assert len(request.destinations) == 1

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Missing title
        with pytest.raises(ValidationError):
            CreateTripRequest(
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 5),
                destinations=[TripDestination(name="Paris")],
            )

        # Missing dates
        with pytest.raises(ValidationError):
            CreateTripRequest(
                title="Trip",
                destinations=[TripDestination(name="Paris")],
            )

        # Missing destinations
        with pytest.raises(ValidationError):
            CreateTripRequest(
                title="Trip",
                start_date=date(2025, 6, 1),
                end_date=date(2025, 6, 5),
            )


class TestUpdateTripRequest:
    """Test UpdateTripRequest schema."""

    def test_valid_trip_update(self):
        """Test valid trip update request."""
        destinations = [TripDestination(name="Barcelona")]

        data = {
            "title": "Updated Trip Title",
            "description": "Updated description",
            "start_date": date(2025, 7, 1),
            "end_date": date(2025, 7, 10),
            "destinations": destinations,
        }

        request = UpdateTripRequest(**data)
        assert request.title == "Updated Trip Title"
        assert len(request.destinations) == 1

    def test_partial_update(self):
        """Test partial trip update with only some fields."""
        # Update only title
        request = UpdateTripRequest(title="New Title")
        assert request.title == "New Title"
        assert request.description is None

        # Update only dates
        request = UpdateTripRequest(
            start_date=date(2025, 8, 1),
            end_date=date(2025, 8, 10),
        )
        assert request.start_date == date(2025, 8, 1)
        assert request.title is None

    def test_empty_update(self):
        """Test empty update request (all fields None)."""
        request = UpdateTripRequest()
        assert request.title is None
        assert request.description is None
        assert request.start_date is None
        assert request.end_date is None
        assert request.destinations is None

    def test_date_validation_update(self):
        """Test date validation for updates."""
        # End date before start date
        with pytest.raises(ValidationError, match="End date must be after start date"):
            UpdateTripRequest(
                start_date=date(2025, 6, 10),
                end_date=date(2025, 6, 5),
            )

        # Only start date provided (should be valid)
        request = UpdateTripRequest(start_date=date(2025, 6, 1))
        assert request.start_date == date(2025, 6, 1)

        # Only end date provided (should be valid)
        request = UpdateTripRequest(end_date=date(2025, 6, 10))
        assert request.end_date == date(2025, 6, 10)

    def test_title_validation_update(self):
        """Test title validation for updates."""
        # Empty title should fail
        with pytest.raises(ValidationError):
            UpdateTripRequest(title="")

        # Too long title should fail
        with pytest.raises(ValidationError):
            UpdateTripRequest(title="A" * 101)

        # Valid title
        request = UpdateTripRequest(title="Valid Title")
        assert request.title == "Valid Title"


class TestTripPreferencesRequest:
    """Test TripPreferencesRequest schema."""

    def test_valid_preferences_request(self):
        """Test valid trip preferences request."""
        budget = Budget(
            total_budget=Price(amount=Decimal("5000.00"), currency=CurrencyCode.USD)
        )
        accommodation = AccommodationPreferences(
            type=AccommodationType.APARTMENT,
            min_rating=3.5,
        )
        transportation = TransportationPreferences(
            max_travel_time_hours=10,
        )

        data = {
            "budget": budget,
            "accommodation": accommodation,
            "transportation": transportation,
            "activities": ["museums", "hiking"],
            "dietary_restrictions": ["vegetarian"],
            "group_size": 3,
        }

        request = TripPreferencesRequest(**data)
        assert request.budget.total_budget.amount == Decimal("5000.00")
        assert request.accommodation.type == AccommodationType.APARTMENT
        assert request.group_size == 3

    def test_empty_preferences_request(self):
        """Test empty preferences request."""
        request = TripPreferencesRequest()
        assert request.budget is None
        assert request.accommodation is None
        assert request.activities is None

    def test_preferences_inheritance(self):
        """Test that TripPreferencesRequest inherits from TripPreferences."""
        # Should have all the same validation as TripPreferences
        with pytest.raises(ValidationError, match="Group size must be at least 1"):
            TripPreferencesRequest(group_size=0)


class TestTripSearchRequest:
    """Test TripSearchRequest schema."""

    def test_valid_search_request(self):
        """Test valid trip search request."""
        data = {
            "query": "European vacation",
            "destination": "Europe",
            "start_date_from": date(2025, 6, 1),
            "start_date_to": date(2025, 8, 31),
            "min_duration": 7,
            "max_duration": 21,
            "status": "planning",
        }

        request = TripSearchRequest(**data)
        assert request.query == "European vacation"
        assert request.destination == "Europe"
        assert request.min_duration == 7

    def test_minimal_search_request(self):
        """Test minimal search request with no filters."""
        request = TripSearchRequest()
        assert request.query is None
        assert request.destination is None
        assert request.min_duration is None

    def test_query_only_search(self):
        """Test search with only query parameter."""
        request = TripSearchRequest(query="beach vacation")
        assert request.query == "beach vacation"
        assert request.destination is None

    def test_duration_range_validation(self):
        """Test duration range validation."""
        # Min duration greater than max duration
        with pytest.raises(
            ValidationError,
            match="Minimum duration cannot be greater than maximum duration",
        ):
            TripSearchRequest(min_duration=14, max_duration=7)

        # Valid duration range
        request = TripSearchRequest(min_duration=7, max_duration=14)
        assert request.min_duration == 7
        assert request.max_duration == 14

        # Equal min and max duration (should be valid)
        request = TripSearchRequest(min_duration=7, max_duration=7)
        assert request.min_duration == 7
        assert request.max_duration == 7

    def test_date_range_validation(self):
        """Test start date range validation."""
        # Start date from after start date to
        with pytest.raises(
            ValidationError, match="Start date from cannot be after start date to"
        ):
            TripSearchRequest(
                start_date_from=date(2025, 8, 1),
                start_date_to=date(2025, 6, 1),
            )

        # Valid date range
        request = TripSearchRequest(
            start_date_from=date(2025, 6, 1),
            start_date_to=date(2025, 8, 31),
        )
        assert request.start_date_from == date(2025, 6, 1)
        assert request.start_date_to == date(2025, 8, 31)

        # Same start dates (should be valid)
        request = TripSearchRequest(
            start_date_from=date(2025, 6, 1),
            start_date_to=date(2025, 6, 1),
        )
        assert request.start_date_from == request.start_date_to

    def test_duration_field_validation(self):
        """Test individual duration field validation."""
        # Negative min duration
        with pytest.raises(ValidationError):
            TripSearchRequest(min_duration=0)

        # Negative max duration
        with pytest.raises(ValidationError):
            TripSearchRequest(max_duration=0)

        # Valid boundary values
        request = TripSearchRequest(min_duration=1, max_duration=1)
        assert request.min_duration == 1
        assert request.max_duration == 1

    def test_partial_filters(self):
        """Test search with partial filter combinations."""
        # Only destination filter
        request = TripSearchRequest(destination="Asia")
        assert request.destination == "Asia"
        assert request.query is None

        # Only date filters
        request = TripSearchRequest(
            start_date_from=date(2025, 6, 1),
            start_date_to=date(2025, 12, 31),
        )
        assert request.start_date_from == date(2025, 6, 1)
        assert request.destination is None

        # Only duration filters
        request = TripSearchRequest(min_duration=3, max_duration=10)
        assert request.min_duration == 3
        assert request.max_duration == 10


class TestTripRequestIntegration:
    """Test integration scenarios for trip requests."""

    def test_create_then_update_flow(self):
        """Test creating a trip then updating it."""
        # Initial creation
        destinations = [TripDestination(name="London")]
        create_data = {
            "title": "London Trip",
            "start_date": date(2025, 5, 1),
            "end_date": date(2025, 5, 7),
            "destinations": destinations,
        }
        create_request = CreateTripRequest(**create_data)
        assert create_request.title == "London Trip"

        # Update title and extend trip
        update_data = {
            "title": "Extended UK Tour",
            "end_date": date(2025, 5, 14),
            "destinations": [
                TripDestination(name="London"),
                TripDestination(name="Edinburgh"),
            ],
        }
        update_request = UpdateTripRequest(**update_data)
        assert update_request.title == "Extended UK Tour"
        assert len(update_request.destinations) == 2

    def test_search_to_create_flow(self):
        """Test searching for trips then creating a new one."""
        # Search for similar trips
        search_request = TripSearchRequest(
            query="European cities",
            destination="Europe",
            min_duration=10,
            max_duration=21,
        )
        assert search_request.query == "European cities"

        # Create trip based on search insights
        destinations = [
            TripDestination(name="Paris"),
            TripDestination(name="Amsterdam"),
            TripDestination(name="Berlin"),
        ]
        create_data = {
            "title": "European Cities Tour",
            "description": "Inspired by search results",
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 6, 15),
            "destinations": destinations,
        }
        create_request = CreateTripRequest(**create_data)
        assert len(create_request.destinations) == 3
        assert create_request.description == "Inspired by search results"

    def test_preferences_update_flow(self):
        """Test updating trip preferences."""
        # Initial preferences
        initial_budget = Budget(
            total_budget=Price(amount=Decimal("3000.00"), currency=CurrencyCode.USD)
        )
        initial_prefs = TripPreferencesRequest(
            budget=initial_budget,
            activities=["sightseeing"],
            group_size=2,
        )
        assert initial_prefs.budget.total_budget.amount == Decimal("3000.00")

        # Updated preferences with more budget and activities
        updated_budget = Budget(
            total_budget=Price(amount=Decimal("5000.00"), currency=CurrencyCode.USD)
        )
        accommodation = AccommodationPreferences(
            type=AccommodationType.HOTEL,
            min_rating=4.5,
        )
        updated_prefs = TripPreferencesRequest(
            budget=updated_budget,
            accommodation=accommodation,
            activities=["sightseeing", "museums", "food_tours"],
            group_size=4,
        )
        assert updated_prefs.budget.total_budget.amount == Decimal("5000.00")
        assert len(updated_prefs.activities) == 3
        assert updated_prefs.group_size == 4
