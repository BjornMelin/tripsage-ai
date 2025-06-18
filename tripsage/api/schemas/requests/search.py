"""Search request schemas using Pydantic V2.

This module defines Pydantic models for search-related API requests.
"""

from datetime import date
from typing import Optional, Union

from pydantic import BaseModel, Field

class SearchFilters(BaseModel):
    """Common search filters across all types."""

    price_min: float | None = Field(None, ge=0, description="Minimum price")
    price_max: float | None = Field(None, ge=0, description="Maximum price")
    rating_min: float | None = Field(None, ge=0, le=5, description="Minimum rating")

    # Location filters
    latitude: float | None = Field(
        None, ge=-90, le=90, description="Center latitude"
    )
    longitude: float | None = Field(
        None, ge=-180, le=180, description="Center longitude"
    )
    radius_km: float | None = Field(
        None, ge=0, le=100, description="Search radius in kilometers"
    )

    # Additional filters as key-value pairs
    custom_filters: dict[str, str | int | float | bool | list[str]] | None = (
        Field(None, description="Additional type-specific filters")
    )

class UnifiedSearchRequest(BaseModel):
    """Unified search request across multiple resource types."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string",
    )

    types: list[str] | None = Field(
        None,
        description=(
            "Resource types to search (destination, flight, accommodation, activity)"
        ),
    )

    # Common parameters
    destination: str | None = Field(
        None,
        description="Destination for location-based searches",
    )
    start_date: date | None = Field(
        None,
        description="Start date for date-based searches",
    )
    end_date: date | None = Field(
        None,
        description="End date for date-based searches",
    )

    # Flight-specific (optional)
    origin: str | None = Field(
        None,
        description="Origin location for flight searches",
    )

    # Traveler counts
    adults: int | None = Field(1, ge=1, le=20, description="Number of adults")
    children: int | None = Field(0, ge=0, le=20, description="Number of children")
    infants: int | None = Field(0, ge=0, le=10, description="Number of infants")

    # Filters
    filters: SearchFilters | None = Field(
        None,
        description="Search filters to apply",
    )

    # Search preferences
    sort_by: str | None = Field(
        None,
        description="Sort field (relevance, price, rating, distance)",
    )
    sort_order: str | None = Field(
        "desc",
        pattern="^(asc|desc)$",
        description="Sort order",
    )

    # User context (for personalization)
    user_preferences: dict[str, str | int | float | bool] | None = Field(
        None,
        description="User preferences for result personalization",
    )
