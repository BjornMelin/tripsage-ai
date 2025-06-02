"""
Travel-related shared models for TripSage AI.

This module contains trip, destination, and preference models
that are shared across different parts of the application.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel

from .enums import AccommodationType, TripStatus
from .financial import Budget, Price
from .geographic import Coordinates


class TripDestination(TripSageModel):
    """Shared model for a trip destination with enhanced geographic support."""

    name: str = Field(..., description="Destination name")
    country: Optional[str] = Field(None, description="Country")
    city: Optional[str] = Field(None, description="City")
    coordinates: Optional[Coordinates] = Field(
        None,
        description="Geographic coordinates",
    )
    arrival_date: Optional[date] = Field(None, description="Date of arrival")
    departure_date: Optional[date] = Field(None, description="Date of departure")
    duration_days: Optional[int] = Field(None, description="Duration in days", ge=1)

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Validate duration is positive."""
        if v is not None and v < 1:
            raise ValueError("Duration must be at least 1 day")
        return v


class AccommodationPreferences(TripSageModel):
    """Accommodation preferences for trips."""

    type: Optional[AccommodationType] = Field(
        None, description="Preferred accommodation type"
    )
    min_rating: Optional[float] = Field(
        None, description="Minimum rating", ge=0.0, le=5.0
    )
    max_price_per_night: Optional[Price] = Field(
        None, description="Maximum price per night"
    )
    amenities: Optional[List[str]] = Field(None, description="Required amenities")
    location_preference: Optional[str] = Field(
        None, description="Location preference (e.g., city_center, beach)"
    )

    @field_validator("min_rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate rating is between 0 and 5."""
        if v is not None and not 0.0 <= v <= 5.0:
            raise ValueError("Rating must be between 0.0 and 5.0")
        return v


class TransportationPreferences(TripSageModel):
    """Transportation preferences for trips."""

    flight_preferences: Optional[Dict[str, Any]] = Field(
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
    local_transportation: Optional[List[str]] = Field(
        None,
        description="Preferred local transportation methods",
        json_schema_extra={"example": ["public_transport", "walking"]},
    )
    max_travel_time_hours: Optional[int] = Field(
        None, description="Maximum acceptable travel time in hours", ge=1
    )

    @field_validator("max_travel_time_hours")
    @classmethod
    def validate_travel_time(cls, v: Optional[int]) -> Optional[int]:
        """Validate travel time is reasonable."""
        if v is not None and v < 1:
            raise ValueError("Travel time must be at least 1 hour")
        return v


class TripPreferences(TripSageModel):
    """Enhanced trip preferences using shared financial and accommodation models."""

    budget: Optional[Budget] = Field(None, description="Trip budget")
    accommodation: Optional[AccommodationPreferences] = Field(
        None, description="Accommodation preferences"
    )
    transportation: Optional[TransportationPreferences] = Field(
        None, description="Transportation preferences"
    )
    activities: Optional[List[str]] = Field(
        None,
        description="Preferred activities",
        json_schema_extra={"example": ["sightseeing", "museums", "outdoor_activities"]},
    )
    dietary_restrictions: Optional[List[str]] = Field(
        None,
        description="Dietary restrictions",
        json_schema_extra={"example": ["vegetarian", "gluten_free"]},
    )
    accessibility_needs: Optional[List[str]] = Field(
        None,
        description="Accessibility needs",
        json_schema_extra={"example": ["wheelchair_accessible", "elevator_access"]},
    )
    group_size: Optional[int] = Field(None, description="Number of travelers", ge=1)
    trip_style: Optional[str] = Field(
        None,
        description="Trip style",
        json_schema_extra={"example": "relaxed"},
    )

    @field_validator("group_size")
    @classmethod
    def validate_group_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate group size is positive."""
        if v is not None and v < 1:
            raise ValueError("Group size must be at least 1")
        return v


class TripSummary(TripSageModel):
    """Summary information for a trip."""

    title: str = Field(..., description="Trip title")
    date_range: str = Field(..., description="Trip date range")
    duration_days: int = Field(..., description="Trip duration in days", ge=1)
    destinations: List[str] = Field(..., description="Trip destination names")
    status: TripStatus = Field(..., description="Trip status")
    total_budget: Optional[Price] = Field(None, description="Total trip budget")
    estimated_cost: Optional[Price] = Field(None, description="Estimated total cost")

    @field_validator("duration_days")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Validate duration is positive."""
        if v < 1:
            raise ValueError("Duration must be at least 1 day")
        return v
