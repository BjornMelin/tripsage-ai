"""Activity request schemas using Pydantic V2.

This module defines Pydantic models for activity-related API requests.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class PriceRange(BaseModel):
    """Price range filter."""

    min: float = Field(ge=0, description="Minimum price")
    max: float = Field(ge=0, description="Maximum price")


class ActivitySearchRequest(BaseModel):
    """Activity search request model."""

    destination: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Destination to search activities",
    )
    start_date: date = Field(..., description="Activity date or start date")
    end_date: Optional[date] = Field(
        None, description="End date for date range searches"
    )
    adults: int = Field(1, ge=1, le=20, description="Number of adults")
    children: int = Field(0, ge=0, le=20, description="Number of children")
    infants: int = Field(0, ge=0, le=10, description="Number of infants")

    # Filters
    categories: Optional[List[str]] = Field(
        None,
        description="Activity categories (tour, museum, adventure, entertainment, etc.)",
    )
    duration: Optional[int] = Field(
        None,
        ge=1,
        le=1440,
        description="Maximum duration in minutes",
    )
    price_range: Optional[PriceRange] = Field(None, description="Price range filter")
    rating: Optional[float] = Field(
        None,
        ge=0,
        le=5,
        description="Minimum rating filter",
    )

    # Additional preferences
    wheelchair_accessible: Optional[bool] = Field(
        None, description="Filter for wheelchair accessible activities"
    )
    instant_confirmation: Optional[bool] = Field(
        None, description="Filter for instant confirmation activities"
    )
    free_cancellation: Optional[bool] = Field(
        None, description="Filter for free cancellation activities"
    )


class SaveActivityRequest(BaseModel):
    """Save activity to trip request model."""

    activity_id: str = Field(..., description="Activity ID to save")
    trip_id: Optional[str] = Field(None, description="Trip ID to add activity to")
    notes: Optional[str] = Field(
        None, max_length=1000, description="Personal notes about the activity"
    )
