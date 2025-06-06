"""Trip API schemas using Pydantic V2.

This module defines Pydantic models for trip-related API requests and responses.
Consolidates both request and response schemas for trip operations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from tripsage_core.models.schemas_common.travel import TripDestination, TripPreferences

# ===== Request Schemas =====


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


# ===== Response Schemas =====


class TripResponse(BaseModel):
    """Response model for trip details."""

    model_config = ConfigDict(
        json_schema_extra={
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
    )

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

    model_config = ConfigDict(
        json_schema_extra={
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
    )

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


class TripSuggestionResponse(BaseModel):
    """Response model for trip suggestions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "suggestion-1",
                "title": "Tokyo Cherry Blossom Adventure",
                "destination": "Tokyo, Japan",
                "description": "Experience the magic of cherry blossom season in Japan's vibrant capital city.",
                "image_url": "https://example.com/tokyo-cherry-blossom.jpg",
                "estimated_price": 2800,
                "currency": "USD",
                "duration": 7,
                "rating": 4.8,
                "category": "culture",
                "best_time_to_visit": "March - May",
                "highlights": [
                    "Cherry Blossoms",
                    "Temples",
                    "Street Food",
                    "Modern Culture",
                ],
                "difficulty": "moderate",
                "trending": True,
                "seasonal": True,
                "relevance_score": 0.95,
                "metadata": {
                    "weather": "Mild spring weather",
                    "visa_required": False,
                    "language": "Japanese",
                    "personalization_reasons": [
                        "Based on your interest in cultural experiences",
                        "Previous trips to Asia",
                    ],
                },
            }
        }
    )

    id: str = Field(description="Suggestion ID")
    title: str = Field(description="Trip title")
    destination: str = Field(description="Primary destination")
    description: str = Field(description="Trip description")
    image_url: Optional[str] = Field(default=None, description="Cover image URL")
    estimated_price: float = Field(description="Estimated total price")
    currency: str = Field(description="Price currency")
    duration: int = Field(description="Trip duration in days")
    rating: float = Field(description="Average rating", ge=0, le=5)
    category: str = Field(
        description="Trip category (adventure, relaxation, culture, nature, city, beach)"
    )
    best_time_to_visit: str = Field(description="Recommended time period")
    highlights: List[str] = Field(description="Key highlights", max_length=10)
    difficulty: Optional[str] = Field(
        default=None, description="Trip difficulty (easy, moderate, challenging)"
    )
    trending: bool = Field(
        default=False, description="Whether this is a trending destination"
    )
    seasonal: bool = Field(
        default=False, description="Whether this is seasonal/time-sensitive"
    )
    relevance_score: Optional[float] = Field(
        default=None, description="Personalization relevance score", ge=0, le=1
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )
