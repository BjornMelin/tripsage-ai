"""
Common trip models shared across the API.

This module contains domain models and common data structures for trips.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common import Coordinates, TripStatus


class TripVisibility(str, Enum):
    """Visibility options for trips."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class TripPreferenceData(BaseModel):
    """Model for detailed trip preferences."""

    key: str = Field(description="Preference key")
    value: Any = Field(description="Preference value")
    category: str = Field(description="Preference category")


class TripDestinationData(BaseModel):
    """Model for detailed trip destination data."""

    id: str = Field(description="Destination ID")
    name: str = Field(description="Destination name")
    details: Dict[str, Any] = Field(description="Destination details")


class TripMember(BaseModel):
    """Model for a trip member."""

    user_id: str = Field(description="User ID of the member")
    role: str = Field(description="Member role (owner, editor, viewer)")
    joined_at: datetime = Field(description="When the member joined")


class TripDay(BaseModel):
    """Model for a day in a trip."""

    day_date: date = Field(description="Date of this trip day")
    location: Optional[str] = Field(default=None, description="Location on this day")
    notes: Optional[str] = Field(default=None, description="Notes for this day")


class Trip(BaseModel):
    """Complete trip model."""

    id: UUID = Field(description="Trip ID")
    user_id: str = Field(description="Owner user ID")
    title: str = Field(description="Trip title")
    description: Optional[str] = Field(default=None, description="Trip description")
    start_date: date = Field(description="Trip start date")
    end_date: date = Field(description="Trip end date")
    status: TripStatus = Field(default=TripStatus.PLANNING, description="Trip status")
    visibility: TripVisibility = Field(
        default=TripVisibility.PRIVATE, description="Trip visibility"
    )
    destinations: List[TripDestinationData] = Field(
        default=[], description="Trip destinations"
    )
    preferences: Dict[str, Any] = Field(default={}, description="Trip preferences")
    members: List[TripMember] = Field(default=[], description="Trip members")
    days: List[TripDay] = Field(default=[], description="Trip days")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    @property
    def duration_days(self) -> int:
        """Calculate the duration of the trip in days."""
        return (self.end_date - self.start_date).days + 1


class TripDestination(BaseModel):
    """Model for a trip destination."""

    name: str = Field(description="Destination name")
    country: Optional[str] = Field(default=None, description="Country")
    city: Optional[str] = Field(default=None, description="City")
    coordinates: Optional[Coordinates] = Field(
        default=None,
        description="Geographic coordinates",
    )
    arrival_date: Optional[date] = Field(default=None, description="Date of arrival")
    departure_date: Optional[date] = Field(
        default=None, description="Date of departure"
    )
    duration_days: Optional[int] = Field(default=None, description="Duration in days")


class TripPreferences(BaseModel):
    """Model for trip preferences."""

    budget: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Budget information",
        examples=[
            {
                "total": 2000,
                "currency": "USD",
                "accommodation_budget": 1000,
                "transportation_budget": 600,
                "food_budget": 300,
                "activities_budget": 100,
            }
        ],
    )
    accommodation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Accommodation preferences",
        examples=[
            {
                "type": "hotel",
                "min_rating": 3.5,
                "amenities": ["wifi", "breakfast"],
                "location_preference": "city_center",
            }
        ],
    )
    transportation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Transportation preferences",
        examples=[
            {
                "flight_preferences": {
                    "seat_class": "economy",
                    "max_stops": 1,
                    "preferred_airlines": [],
                    "time_window": "flexible",
                },
                "local_transportation": ["public_transport", "walking"],
            }
        ],
    )
    activities: Optional[List[str]] = Field(
        default=None,
        description="Preferred activities",
        examples=[["sightseeing", "museums", "outdoor_activities"]],
    )
    dietary_restrictions: Optional[List[str]] = Field(
        default=None,
        description="Dietary restrictions",
        examples=[["vegetarian", "gluten_free"]],
    )
    accessibility_needs: Optional[List[str]] = Field(
        default=None,
        description="Accessibility needs",
        examples=[["wheelchair_accessible", "elevator_access"]],
    )
