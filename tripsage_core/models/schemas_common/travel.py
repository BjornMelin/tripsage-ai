"""Travel-related shared models for TripSage AI.

This module contains trip, destination, and preference models
that are shared across different parts of the application.
"""

from datetime import date
from typing import Any

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageModel

from .common_validators import PositiveInt, Rating
from .enums import AccommodationType, TripStatus
from .financial import Budget, Price
from .geographic import Coordinates


class TripDestination(TripSageModel):
    """Shared model for a trip destination with enhanced geographic support."""

    name: str = Field(..., description="Destination name")
    country: str | None = Field(None, description="Country")
    city: str | None = Field(None, description="City")
    coordinates: Coordinates | None = Field(
        None,
        description="Geographic coordinates",
    )
    arrival_date: date | None = Field(None, description="Date of arrival")
    departure_date: date | None = Field(None, description="Date of departure")
    duration_days: PositiveInt = Field(None, description="Duration in days")


class AccommodationPreferences(TripSageModel):
    """Accommodation preferences for trips."""

    type: AccommodationType | None = Field(
        None, description="Preferred accommodation type"
    )
    min_rating: Rating = Field(None, description="Minimum rating")
    max_price_per_night: Price | None = Field(
        None, description="Maximum price per night"
    )
    amenities: list[str] | None = Field(None, description="Required amenities")
    location_preference: str | None = Field(
        None, description="Location preference (e.g., city_center, beach)"
    )


class TransportationPreferences(TripSageModel):
    """Transportation preferences for trips."""

    flight_preferences: dict[str, Any] | None = Field(
        None,
        description="Flight preferences",
        json_schema_extra={
            "example": {
                "seat_class": "economy",
                "max_stops": 1,
                "preferred_airlines": [],
                "time_window": "flexible",
            }
        },
    )
    local_transportation: list[str] | None = Field(
        None,
        description="Preferred local transportation methods",
        json_schema_extra={"example": ["public_transport", "walking"]},
    )
    max_travel_time_hours: PositiveInt = Field(
        None, description="Maximum acceptable travel time in hours"
    )


class TripPreferences(TripSageModel):
    """Trip preferences using shared financial and accommodation models."""

    budget: Budget | None = Field(None, description="Trip budget")
    accommodation: AccommodationPreferences | None = Field(
        None, description="Accommodation preferences"
    )
    transportation: TransportationPreferences | None = Field(
        None, description="Transportation preferences"
    )
    activities: list[str] | None = Field(
        None,
        description="Preferred activities",
        json_schema_extra={"example": ["sightseeing", "museums", "outdoor_activities"]},
    )
    dietary_restrictions: list[str] | None = Field(
        None,
        description="Dietary restrictions",
        json_schema_extra={"example": ["vegetarian", "gluten_free"]},
    )
    accessibility_needs: list[str] | None = Field(
        None,
        description="Accessibility needs",
        json_schema_extra={"example": ["wheelchair_accessible", "elevator_access"]},
    )
    group_size: PositiveInt = Field(None, description="Number of travelers")
    trip_style: str | None = Field(
        None,
        description="Trip style",
        json_schema_extra={"example": "relaxed"},
    )


class TripSummary(TripSageModel):
    """Summary information for a trip."""

    title: str = Field(..., description="Trip title")
    date_range: str = Field(..., description="Trip date range")
    duration_days: int = Field(..., description="Trip duration in days", ge=1)
    destinations: list[str] = Field(..., description="Trip destination names")
    status: TripStatus = Field(..., description="Trip status")
    total_budget: Price | None = Field(None, description="Total trip budget")
    estimated_cost: Price | None = Field(None, description="Estimated total cost")
