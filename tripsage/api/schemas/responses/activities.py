"""Activity response schemas using Pydantic V2.

This module defines Pydantic models for activity-related API responses.
"""

from typing import Any

from pydantic import BaseModel, Field


class ActivityCoordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class ActivityResponse(BaseModel):
    """Activity response model."""

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
    cancellation_policy: str | None = Field(None, description="Cancellation policy")
    included: list[str] | None = Field(None, description="What's included")
    excluded: list[str] | None = Field(None, description="What's not included")
    meeting_point: str | None = Field(None, description="Meeting point details")
    languages: list[str] | None = Field(None, description="Available languages")
    max_participants: int | None = Field(None, description="Maximum participants")
    min_participants: int | None = Field(None, description="Minimum participants")
    wheelchair_accessible: bool | None = Field(
        None, description="Wheelchair accessibility"
    )
    instant_confirmation: bool | None = Field(
        None, description="Instant confirmation available"
    )


class ActivitySearchResponse(BaseModel):
    """Activity search response model."""

    activities: list[ActivityResponse] = Field(
        default_factory=list, description="List of activities"
    )
    total: int = Field(0, ge=0, description="Total number of results")
    skip: int = Field(0, ge=0, description="Number of results skipped")
    limit: int = Field(20, ge=1, description="Results per page")
    filters_applied: dict[str, Any] | None = Field(
        None, description="Applied search filters"
    )

    # Search metadata
    search_id: str | None = Field(None, description="Search session ID")
    cached: bool | None = Field(None, description="Whether results are from cache")
    provider_responses: dict[str, int] | None = Field(
        None, description="Number of results from each provider"
    )


class SavedActivityResponse(BaseModel):
    """Saved activity response model."""

    activity_id: str = Field(..., description="Activity ID")
    trip_id: str | None = Field(None, description="Associated trip ID")
    user_id: str = Field(..., description="User ID who saved the activity")
    saved_at: str = Field(..., description="When activity was saved (ISO format)")
    notes: str | None = Field(None, description="User notes about the activity")

    # Optional activity details (for list views)
    activity: ActivityResponse | None = Field(None, description="Full activity details")
