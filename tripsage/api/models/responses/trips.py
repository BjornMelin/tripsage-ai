"""
Response models for trip endpoints.

This module defines Pydantic models for API responses related to trips.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage.api.models.requests.trips import TripDestination, TripPreferences


class TripResponse(BaseModel):
    """Response model for trip details."""

    id: UUID = Field(..., description="Trip ID")
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Trip title")
    description: Optional[str] = Field(None, description="Trip description")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    duration_days: int = Field(..., description="Trip duration in days")
    destinations: List[TripDestination] = Field(..., description="Trip destinations")
    preferences: Optional[TripPreferences] = Field(None, description="Trip preferences")
    itinerary_id: Optional[UUID] = Field(None, description="Associated itinerary ID")
    status: str = Field(..., description="Trip status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

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

    id: UUID = Field(..., description="Trip ID")
    title: str = Field(..., description="Trip title")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    duration_days: int = Field(..., description="Trip duration in days")
    destinations: List[str] = Field(..., description="Trip destination names")
    status: str = Field(..., description="Trip status")
    created_at: datetime = Field(..., description="Creation timestamp")


class TripListResponse(BaseModel):
    """Response model for a list of trips."""

    items: List[TripListItem] = Field(..., description="List of trips")
    total: int = Field(..., description="Total number of trips")
    skip: int = Field(..., description="Number of trips skipped")
    limit: int = Field(..., description="Maximum number of trips returned")


class TripSummaryResponse(BaseModel):
    """Response model for trip summary."""

    id: UUID = Field(..., description="Trip ID")
    title: str = Field(..., description="Trip title")
    date_range: str = Field(..., description="Trip date range")
    duration_days: int = Field(..., description="Trip duration in days")
    destinations: List[str] = Field(..., description="Trip destination names")
    accommodation_summary: Optional[str] = Field(
        None, description="Accommodation summary"
    )
    transportation_summary: Optional[str] = Field(
        None, description="Transportation summary"
    )
    budget_summary: Optional[Dict[str, Any]] = Field(None, description="Budget summary")
    has_itinerary: bool = Field(..., description="Whether trip has an itinerary")
    completion_percentage: int = Field(
        ...,
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
