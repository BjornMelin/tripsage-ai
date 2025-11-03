"""Activities API schemas (feature-first)."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class PriceRange(BaseModel):
    """Price range filter."""

    min: float = Field(ge=0, description="Minimum price")
    max: float = Field(ge=0, description="Maximum price")


class ActivitySearchRequest(BaseModel):
    """Activity search request parameters."""

    destination: str
    start_date: date
    end_date: date | None = None
    adults: int = Field(1, ge=1, le=20)
    children: int = Field(0, ge=0, le=20)
    infants: int = Field(0, ge=0, le=10)
    categories: list[str] | None = None
    duration: int | None = Field(None, ge=1, le=1440)
    price_range: PriceRange | None = None
    rating: float | None = Field(None, ge=0, le=5)
    wheelchair_accessible: bool | None = None
    instant_confirmation: bool | None = None
    free_cancellation: bool | None = None


class ActivityResponse(BaseModel):
    """Activity response model (matches API shape)."""

    id: str = Field(..., description="Activity ID")
    name: str = Field(..., description="Activity name")
    type: str = Field(..., description="Activity type (tour, museum, adventure, etc.)")
    location: str = Field(..., description="Activity location")
    date: str = Field(..., description="Activity date (ISO format)")
    duration: int = Field(..., ge=0, description="Duration in minutes")
    price: float = Field(..., ge=0, description="Price per person")
    rating: float = Field(..., ge=0, le=5, description="Average rating")
    description: str = Field(..., description="Activity description")
    images: list[str] = Field(default_factory=list, description="Activity images")
    coordinates: ActivityCoordinates | None = Field(
        None, description="Geographic coordinates"
    )

    # Additional details
    provider: str | None = Field(None, description="Activity provider name")
    availability: str | None = Field(None, description="Availability status")
    wheelchair_accessible: bool | None = Field(
        None, description="Wheelchair accessibility"
    )
    instant_confirmation: bool | None = Field(
        None, description="Instant confirmation available"
    )
    cancellation_policy: str | None = Field(None, description="Cancellation policy")
    included: list[str] | None = Field(None, description="What's included")
    excluded: list[str] | None = Field(None, description="What's not included")
    meeting_point: str | None = Field(None, description="Meeting point details")
    languages: list[str] | None = Field(None, description="Available languages")
    max_participants: int | None = Field(None, description="Maximum participants")
    min_participants: int | None = Field(None, description="Minimum participants")


class SavedActivityResponse(BaseModel):
    """Saved activity entry in a user's trip context."""

    activity_id: str = Field(..., description="Activity ID")
    trip_id: str | None = Field(None, description="Associated trip ID")
    user_id: str = Field(..., description="User ID who saved the activity")
    saved_at: str = Field(..., description="When activity was saved (ISO format)")
    notes: str | None = Field(None, description="User notes about the activity")
    activity: ActivityResponse | None = Field(None, description="Full activity details")


def _empty_activities() -> list[ActivityResponse]:
    """Return an empty list of activities for default factory."""
    return []


class ActivitySearchResponse(BaseModel):
    """Aggregate search results with metadata."""

    activities: list[ActivityResponse] = Field(default_factory=_empty_activities)
    total: int = Field(0, ge=0)
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1)
    filters_applied: dict[str, Any] | None = None
    search_id: str | None = None
    cached: bool | None = None
    provider_responses: dict[str, int] | None = None


class ActivityCoordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class SaveActivityRequest(BaseModel):
    """Request body to save an activity to a trip."""

    activity_id: str
    trip_id: str | None = None
    notes: str | None = Field(None, max_length=1000)
