"""
Tests for shared travel models in tripsage_core.

This module tests the travel-related models used across
the application including trip destinations and preferences.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    CurrencyCode,
    TripStatus,
)
from tripsage_core.models.schemas_common.financial import Budget, Price
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import (
    AccommodationPreferences,
    TransportationPreferences,
    TripDestination,
    TripPreferences,
    TripSummary,
)


class TestTripDestination:
    """Test TripDestination model."""

    def test_valid_destination(self):
        """Test creating a valid destination."""
        destination = TripDestination(
            name="Paris",
            country="France",
            city="Paris",
            coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
            arrival_date=date(2025, 6, 1),
            departure_date=date(2025, 6, 5),
            duration_days=4,
        )
        assert destination.name == "Paris"
        assert destination.country == "France"
        assert destination.duration_days == 4

    def test_minimal_destination(self):
        """Test creating destination with minimal required fields."""
        destination = TripDestination(name="Tokyo")
        assert destination.name == "Tokyo"
        assert destination.country is None
        assert destination.coordinates is None

    def test_invalid_duration_zero(self):
        """Test that zero duration fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TripDestination(name="Paris", duration_days=0)
        assert "Duration must be at least 1 day" in str(exc_info.value)

    def test_invalid_duration_negative(self):
        """Test that negative duration fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TripDestination(name="Paris", duration_days=-1)
        assert "Duration must be at least 1 day" in str(exc_info.value)

    def test_valid_duration_one(self):
        """Test that duration of 1 is valid."""
        destination = TripDestination(name="Paris", duration_days=1)
        assert destination.duration_days == 1

    def test_coordinates_validation(self):
        """Test that coordinates are properly validated."""
        # Valid coordinates
        destination = TripDestination(
            name="Paris",
            coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
        )
        assert destination.coordinates.latitude == 48.8566

        # Invalid coordinates should be caught by Coordinates model
        with pytest.raises(ValidationError):
            TripDestination(
                name="Invalid",
                coordinates=Coordinates(
                    latitude=91.0, longitude=2.3522
                ),  # Invalid latitude
            )


class TestAccommodationPreferences:
    """Test AccommodationPreferences model."""

    def test_valid_preferences(self):
        """Test creating valid accommodation preferences."""
        price = Price(amount=Decimal("150.00"), currency=CurrencyCode.USD)
        prefs = AccommodationPreferences(
            type=AccommodationType.HOTEL,
            min_rating=4.0,
            max_price_per_night=price,
            amenities=["wifi", "breakfast"],
            location_preference="city_center",
        )
        assert prefs.type == AccommodationType.HOTEL
        assert prefs.min_rating == 4.0
        assert len(prefs.amenities) == 2

    def test_empty_preferences(self):
        """Test creating empty accommodation preferences."""
        prefs = AccommodationPreferences()
        assert prefs.type is None
        assert prefs.min_rating is None
        assert prefs.amenities is None

    def test_invalid_rating_too_high(self):
        """Test that rating above 5 fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            AccommodationPreferences(min_rating=5.5)
        assert "Rating must be between 0.0 and 5.0" in str(exc_info.value)

    def test_invalid_rating_negative(self):
        """Test that negative rating fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            AccommodationPreferences(min_rating=-1.0)
        assert "Rating must be between 0.0 and 5.0" in str(exc_info.value)

    def test_valid_rating_boundaries(self):
        """Test that boundary ratings are valid."""
        # Rating of 0.0 should be valid
        prefs = AccommodationPreferences(min_rating=0.0)
        assert prefs.min_rating == 0.0

        # Rating of 5.0 should be valid
        prefs = AccommodationPreferences(min_rating=5.0)
        assert prefs.min_rating == 5.0


class TestTransportationPreferences:
    """Test TransportationPreferences model."""

    def test_valid_preferences(self):
        """Test creating valid transportation preferences."""
        prefs = TransportationPreferences(
            flight_preferences={
                "seat_class": "economy",
                "max_stops": 1,
                "preferred_airlines": ["Delta", "United"],
            },
            local_transportation=["public_transport", "walking"],
            max_travel_time_hours=8,
        )
        assert prefs.max_travel_time_hours == 8
        assert len(prefs.local_transportation) == 2

    def test_empty_preferences(self):
        """Test creating empty transportation preferences."""
        prefs = TransportationPreferences()
        assert prefs.flight_preferences is None
        assert prefs.local_transportation is None
        assert prefs.max_travel_time_hours is None

    def test_invalid_travel_time_zero(self):
        """Test that zero travel time fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TransportationPreferences(max_travel_time_hours=0)
        assert "Travel time must be at least 1 hour" in str(exc_info.value)

    def test_invalid_travel_time_negative(self):
        """Test that negative travel time fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TransportationPreferences(max_travel_time_hours=-1)
        assert "Travel time must be at least 1 hour" in str(exc_info.value)

    def test_valid_travel_time_one(self):
        """Test that travel time of 1 hour is valid."""
        prefs = TransportationPreferences(max_travel_time_hours=1)
        assert prefs.max_travel_time_hours == 1


class TestTripPreferences:
    """Test TripPreferences model."""

    def test_valid_preferences(self):
        """Test creating valid trip preferences."""
        budget = Budget(
            total_budget=Price(amount=Decimal("5000.00"), currency=CurrencyCode.USD)
        )
        accommodation = AccommodationPreferences(
            type=AccommodationType.HOTEL,
            min_rating=4.0,
        )
        transportation = TransportationPreferences(
            max_travel_time_hours=8,
        )

        prefs = TripPreferences(
            budget=budget,
            accommodation=accommodation,
            transportation=transportation,
            activities=["sightseeing", "museums"],
            dietary_restrictions=["vegetarian"],
            accessibility_needs=["wheelchair_accessible"],
            group_size=2,
            trip_style="relaxed",
        )
        assert prefs.group_size == 2
        assert len(prefs.activities) == 2
        assert prefs.trip_style == "relaxed"

    def test_empty_preferences(self):
        """Test creating empty trip preferences."""
        prefs = TripPreferences()
        assert prefs.budget is None
        assert prefs.accommodation is None
        assert prefs.activities is None

    def test_invalid_group_size_zero(self):
        """Test that zero group size fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TripPreferences(group_size=0)
        assert "Group size must be at least 1" in str(exc_info.value)

    def test_invalid_group_size_negative(self):
        """Test that negative group size fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TripPreferences(group_size=-1)
        assert "Group size must be at least 1" in str(exc_info.value)

    def test_valid_group_size_one(self):
        """Test that group size of 1 is valid."""
        prefs = TripPreferences(group_size=1)
        assert prefs.group_size == 1


class TestTripSummary:
    """Test TripSummary model."""

    def test_valid_summary(self):
        """Test creating a valid trip summary."""
        total_budget = Price(amount=Decimal("5000.00"), currency=CurrencyCode.USD)
        estimated_cost = Price(amount=Decimal("4200.00"), currency=CurrencyCode.USD)

        summary = TripSummary(
            title="Summer Vacation",
            date_range="Jun 1-15, 2025",
            duration_days=14,
            destinations=["Paris", "Rome", "Barcelona"],
            status=TripStatus.PLANNING,
            total_budget=total_budget,
            estimated_cost=estimated_cost,
        )
        assert summary.title == "Summer Vacation"
        assert summary.duration_days == 14
        assert len(summary.destinations) == 3

    def test_minimal_summary(self):
        """Test creating summary with minimal required fields."""
        summary = TripSummary(
            title="Weekend Trip",
            date_range="Feb 1-3, 2025",
            duration_days=2,
            destinations=["Boston"],
            status=TripStatus.PLANNING,
        )
        assert summary.title == "Weekend Trip"
        assert summary.duration_days == 2
        assert summary.total_budget is None

    def test_invalid_duration_zero(self):
        """Test that zero duration fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TripSummary(
                title="Invalid Trip",
                date_range="Feb 1-1, 2025",
                duration_days=0,
                destinations=["Boston"],
                status=TripStatus.PLANNING,
            )
        assert "Duration must be at least 1 day" in str(exc_info.value)

    def test_invalid_duration_negative(self):
        """Test that negative duration fails validation."""
        with pytest.raises(ValidationError) as exc_info:
            TripSummary(
                title="Invalid Trip",
                date_range="Feb 1-1, 2025",
                duration_days=-1,
                destinations=["Boston"],
                status=TripStatus.PLANNING,
            )
        assert "Duration must be at least 1 day" in str(exc_info.value)

    def test_valid_duration_one(self):
        """Test that duration of 1 is valid."""
        summary = TripSummary(
            title="Day Trip",
            date_range="Feb 1, 2025",
            duration_days=1,
            destinations=["Boston"],
            status=TripStatus.PLANNING,
        )
        assert summary.duration_days == 1


class TestTravelModelsIntegration:
    """Test integration between travel models."""

    def test_complete_trip_preferences(self):
        """Test creating complete trip preferences with all components."""
        # Create budget
        budget = Budget(
            total_budget=Price(amount=Decimal("5000.00"), currency=CurrencyCode.USD),
            categories={
                "accommodation": Price(
                    amount=Decimal("2000.00"), currency=CurrencyCode.USD
                ),
                "transportation": Price(
                    amount=Decimal("1500.00"), currency=CurrencyCode.USD
                ),
                "food": Price(amount=Decimal("1000.00"), currency=CurrencyCode.USD),
                "activities": Price(
                    amount=Decimal("500.00"), currency=CurrencyCode.USD
                ),
            },
        )

        # Create accommodation preferences
        accommodation = AccommodationPreferences(
            type=AccommodationType.HOTEL,
            min_rating=4.0,
            max_price_per_night=Price(
                amount=Decimal("200.00"), currency=CurrencyCode.USD
            ),
            amenities=["wifi", "breakfast", "gym"],
            location_preference="city_center",
        )

        # Create transportation preferences
        transportation = TransportationPreferences(
            flight_preferences={
                "seat_class": "economy",
                "max_stops": 1,
                "preferred_airlines": ["Delta", "United"],
                "time_window": "flexible",
            },
            local_transportation=["public_transport", "walking", "taxi"],
            max_travel_time_hours=12,
        )

        # Create complete preferences
        preferences = TripPreferences(
            budget=budget,
            accommodation=accommodation,
            transportation=transportation,
            activities=["sightseeing", "museums", "food_tours", "shopping"],
            dietary_restrictions=["vegetarian"],
            accessibility_needs=["wheelchair_accessible"],
            group_size=2,
            trip_style="cultural",
        )

        # Verify all components are properly integrated
        assert preferences.budget.total_budget.amount == Decimal("5000.00")
        assert preferences.accommodation.min_rating == 4.0
        assert preferences.transportation.max_travel_time_hours == 12
        assert preferences.group_size == 2
        assert len(preferences.activities) == 4

    def test_trip_destination_with_coordinates(self):
        """Test trip destination with proper coordinate validation."""
        destination = TripDestination(
            name="Paris",
            country="France",
            city="Paris",
            coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
            arrival_date=date(2025, 6, 1),
            departure_date=date(2025, 6, 5),
            duration_days=4,
        )

        # Test coordinate access
        assert destination.coordinates.latitude == 48.8566
        assert destination.coordinates.longitude == 2.3522

        # Test model serialization
        data = destination.model_dump()
        assert data["coordinates"]["latitude"] == 48.8566
        assert data["name"] == "Paris"
