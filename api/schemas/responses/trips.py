"""
Response schemas for trip endpoints.

This module defines Pydantic models for API responses related to trips
from the backend to the Next.js frontend. Uses shared travel models.
"""

from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common.enums import TripStatus
from tripsage_core.models.schemas_common.financial import Budget
from tripsage_core.models.schemas_common.travel import (
    TripDestination,
    TripPreferences,
    TripSummary,
)


class TripResponse(BaseModel):
    """Response schema for trip details."""

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
    status: TripStatus = Field(..., description="Trip status")
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
                        "coordinates": {"latitude": 48.8566, "longitude": 2.3522},
                        "arrival_date": "2025-06-01",
                        "departure_date": "2025-06-05",
                        "duration_days": 4,
                    },
                    {
                        "name": "Rome",
                        "country": "Italy",
                        "city": "Rome",
                        "coordinates": {"latitude": 41.9028, "longitude": 12.4964},
                        "arrival_date": "2025-06-05",
                        "departure_date": "2025-06-10",
                        "duration_days": 5,
                    },
                ],
                "preferences": {
                    "budget": {
                        "total_budget": {"amount": 5000.00, "currency": "USD"},
                        "categories": {
                            "accommodation": {"amount": 2000.00, "currency": "USD"},
                            "transportation": {"amount": 1500.00, "currency": "USD"},
                            "food": {"amount": 1000.00, "currency": "USD"},
                            "activities": {"amount": 500.00, "currency": "USD"},
                        },
                    },
                    "accommodation": {
                        "type": "hotel",
                        "min_rating": 4.0,
                        "amenities": ["wifi", "breakfast", "air_conditioning"],
                        "location_preference": "city_center",
                    },
                    "activities": ["sightseeing", "museums", "food_tours"],
                },
                "itinerary_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "planning",
                "created_at": "2025-01-15T14:30:00Z",
                "updated_at": "2025-01-16T09:45:00Z",
            }
        }
    }


class TripListItem(BaseModel):
    """Response schema for trip list items."""

    id: UUID = Field(..., description="Trip ID")
    title: str = Field(..., description="Trip title")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    duration_days: int = Field(..., description="Trip duration in days")
    destinations: List[str] = Field(..., description="Trip destination names")
    status: TripStatus = Field(..., description="Trip status")
    created_at: datetime = Field(..., description="Creation timestamp")
    thumbnail_url: Optional[str] = Field(None, description="Trip thumbnail image URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Summer Vacation in Europe",
                "start_date": "2025-06-01",
                "end_date": "2025-06-15",
                "duration_days": 14,
                "destinations": ["Paris", "Rome", "Barcelona"],
                "status": "planning",
                "created_at": "2025-01-15T14:30:00Z",
                "thumbnail_url": "/images/trips/europe-summer.jpg",
            }
        }
    }


class TripListResponse(BaseModel):
    """Response schema for a list of trips."""

    items: List[TripListItem] = Field(..., description="List of trips")
    total: int = Field(..., description="Total number of trips")
    skip: int = Field(..., description="Number of trips skipped")
    limit: int = Field(..., description="Maximum number of trips returned")
    has_more: bool = Field(..., description="Whether there are more trips available")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Summer Vacation in Europe",
                        "start_date": "2025-06-01",
                        "end_date": "2025-06-15",
                        "duration_days": 14,
                        "destinations": ["Paris", "Rome", "Barcelona"],
                        "status": "planning",
                        "created_at": "2025-01-15T14:30:00Z",
                    }
                ],
                "total": 5,
                "skip": 0,
                "limit": 10,
                "has_more": False,
            }
        }
    }


class TripSummaryResponse(TripSummary):
    """Response schema for trip summary with additional frontend-specific fields."""

    id: UUID = Field(..., description="Trip ID")
    accommodation_summary: Optional[str] = Field(
        None, description="Accommodation summary"
    )
    transportation_summary: Optional[str] = Field(
        None, description="Transportation summary"
    )
    budget_summary: Optional[Budget] = Field(None, description="Budget summary")
    has_itinerary: bool = Field(..., description="Whether trip has an itinerary")
    completion_percentage: int = Field(
        ...,
        description="Trip planning completion percentage",
        ge=0,
        le=100,
    )
    next_action: Optional[str] = Field(
        None, description="Suggested next action for trip planning"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Summer Vacation in Europe",
                "date_range": "Jun 1-15, 2025",
                "duration_days": 14,
                "destinations": ["Paris", "Rome", "Barcelona"],
                "status": "planning",
                "total_budget": {"amount": 5000.00, "currency": "USD"},
                "estimated_cost": {"amount": 4200.00, "currency": "USD"},
                "accommodation_summary": "4-star hotels in city centers",
                "transportation_summary": (
                    "Economy flights with 1 connection, local transit"
                ),
                "budget_summary": {
                    "total_budget": {"amount": 5000.00, "currency": "USD"},
                    "allocated": {"amount": 3500.00, "currency": "USD"},
                    "spent": {"amount": 0.00, "currency": "USD"},
                    "remaining": {"amount": 5000.00, "currency": "USD"},
                },
                "has_itinerary": True,
                "completion_percentage": 60,
                "next_action": "Book accommodation in Paris",
            }
        }
    }


class TripSearchResponse(BaseModel):
    """Response schema for trip search results."""

    query: Optional[str] = Field(None, description="Search query used")
    filters_applied: dict = Field({}, description="Filters that were applied")
    results: TripListResponse = Field(..., description="Search results")
    suggestions: Optional[List[str]] = Field(None, description="Search suggestions")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Europe summer",
                "filters_applied": {
                    "destination": "Europe",
                    "start_date_from": "2025-06-01",
                    "min_duration": 7,
                },
                "results": {
                    "items": [],
                    "total": 0,
                    "skip": 0,
                    "limit": 10,
                    "has_more": False,
                },
                "suggestions": [
                    "European cities",
                    "Mediterranean cruise",
                    "UK Scotland",
                ],
            }
        }
    }
