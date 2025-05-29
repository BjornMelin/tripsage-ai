"""Trip models using Pydantic V2.

This module defines Pydantic models for trip-related requests and responses.
"""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

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


# Request Models


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


class CreateTripRequest(BaseModel):
    """Request model for creating a trip."""

    title: str = Field(
        description="Trip title",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Trip description",
        max_length=500,
    )
    start_date: date = Field(description="Trip start date")
    end_date: date = Field(description="Trip end date")
    destinations: List[TripDestination] = Field(
        description="Trip destinations",
        min_length=1,
    )
    preferences: Optional[TripPreferences] = Field(
        default=None,
        description="Trip preferences",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "CreateTripRequest":
        """Validate that end_date is after start_date."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class UpdateTripRequest(BaseModel):
    """Request model for updating a trip."""

    title: Optional[str] = Field(
        default=None,
        description="Trip title",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Trip description",
        max_length=500,
    )
    start_date: Optional[date] = Field(default=None, description="Trip start date")
    end_date: Optional[date] = Field(default=None, description="Trip end date")
    destinations: Optional[List[TripDestination]] = Field(
        default=None,
        description="Trip destinations",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "UpdateTripRequest":
        """Validate that end_date is after start_date if both are provided."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date must be after start date")
        return self


class TripPreferencesRequest(TripPreferences):
    """Request model for updating trip preferences."""

    pass


# Response Models


class TripResponse(BaseModel):
    """Response model for trip details."""

    id: UUID = Field(description="Trip ID")
    user_id: str = Field(description="User ID")
    title: str = Field(description="Trip title")
    description: Optional[str] = Field(default=None, description="Trip description")
    start_date: date = Field(description="Trip start date")
    end_date: date = Field(description="Trip end date")
    duration_days: int = Field(description="Trip duration in days")
    destinations: List[TripDestination] = Field(description="Trip destinations")
    preferences: Optional[TripPreferences] = Field(
        default=None, description="Trip preferences"
    )
    itinerary_id: Optional[UUID] = Field(
        default=None, description="Associated itinerary ID"
    )
    status: str = Field(description="Trip status")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "user123",
                "title": "Summer Vacation in Europe",
                "description": "A two-week tour of Western Europe",
                "start_date": "2025-06-01",
                "end_date": "2025-06-15",
                "duration_days": 14,
                "destinations": [
                    {
                        "name": "Paris",
                        "country": "France",
                        "city": "Paris",
                        "arrival_date": "2025-06-01",
                        "departure_date": "2025-06-05",
                        "duration_days": 4,
                    },
                    {
                        "name": "Rome",
                        "country": "Italy",
                        "city": "Rome",
                        "arrival_date": "2025-06-05",
                        "departure_date": "2025-06-10",
                        "duration_days": 5,
                    },
                    {
                        "name": "Barcelona",
                        "country": "Spain",
                        "city": "Barcelona",
                        "arrival_date": "2025-06-10",
                        "departure_date": "2025-06-15",
                        "duration_days": 5,
                    },
                ],
                "preferences": {
                    "budget": {
                        "total": 5000,
                        "currency": "USD",
                        "accommodation_budget": 2000,
                        "transportation_budget": 1500,
                        "food_budget": 1000,
                        "activities_budget": 500,
                    },
                    "accommodation": {
                        "type": "hotel",
                        "min_rating": 4.0,
                        "amenities": ["wifi", "breakfast", "air_conditioning"],
                        "location_preference": "city_center",
                    },
                    "transportation": {
                        "flight_preferences": {
                            "seat_class": "economy",
                            "max_stops": 1,
                            "preferred_airlines": [],
                            "time_window": "flexible",
                        },
                        "local_transportation": ["public_transport", "walking"],
                    },
                    "activities": ["sightseeing", "museums", "food_tours", "shopping"],
                    "dietary_restrictions": [],
                    "accessibility_needs": [],
                },
                "itinerary_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "planning",
                "created_at": "2025-01-15T14:30:00Z",
                "updated_at": "2025-01-16T09:45:00Z",
            }
        }
    }


class TripListItem(BaseModel):
    """Response model for trip list items."""

    id: UUID = Field(description="Trip ID")
    title: str = Field(description="Trip title")
    start_date: date = Field(description="Trip start date")
    end_date: date = Field(description="Trip end date")
    duration_days: int = Field(description="Trip duration in days")
    destinations: List[str] = Field(description="Trip destination names")
    status: str = Field(description="Trip status")
    created_at: datetime = Field(description="Creation timestamp")


class TripListResponse(BaseModel):
    """Response model for a list of trips."""

    items: List[TripListItem] = Field(description="List of trips")
    total: int = Field(description="Total number of trips")
    skip: int = Field(description="Number of trips skipped")
    limit: int = Field(description="Maximum number of trips returned")


class TripSummaryResponse(BaseModel):
    """Response model for trip summary."""

    id: UUID = Field(description="Trip ID")
    title: str = Field(description="Trip title")
    date_range: str = Field(description="Trip date range")
    duration_days: int = Field(description="Trip duration in days")
    destinations: List[str] = Field(description="Trip destination names")
    accommodation_summary: Optional[str] = Field(
        default=None, description="Accommodation summary"
    )
    transportation_summary: Optional[str] = Field(
        default=None, description="Transportation summary"
    )
    budget_summary: Optional[Dict[str, Any]] = Field(
        default=None, description="Budget summary"
    )
    has_itinerary: bool = Field(description="Whether trip has an itinerary")
    completion_percentage: int = Field(
        description="Trip planning completion percentage",
        ge=0,
        le=100,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Summer Vacation in Europe",
                "date_range": "Jun 1-15, 2025",
                "duration_days": 14,
                "destinations": ["Paris", "Rome", "Barcelona"],
                "accommodation_summary": "4-star hotels in city centers",
                "transportation_summary": (
                    "Economy flights with 1 connection, local transit"
                ),
                "budget_summary": {
                    "total": 5000,
                    "currency": "USD",
                    "spent": 0,
                    "remaining": 5000,
                    "breakdown": {
                        "accommodation": {"budget": 2000, "spent": 0},
                        "transportation": {"budget": 1500, "spent": 0},
                        "food": {"budget": 1000, "spent": 0},
                        "activities": {"budget": 500, "spent": 0},
                    },
                },
                "has_itinerary": True,
                "completion_percentage": 60,
            }
        }
    }
