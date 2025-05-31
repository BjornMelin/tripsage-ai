"""Destination request models using Pydantic V2.

This module defines Pydantic models for destination-related requests.
"""

from datetime import date
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..common.destinations import DestinationCategory, DestinationVisitSchedule


class DestinationSearchRequest(BaseModel):
    """Request model for searching destinations."""

    query: str = Field(
        description="Search query (e.g., country, city, or general description)",
        min_length=1,
        max_length=100,
    )
    categories: Optional[List[DestinationCategory]] = Field(
        default=None, description="Categories to filter by"
    )
    min_safety_rating: Optional[float] = Field(
        default=None, ge=0, le=5, description="Minimum safety rating (0-5)"
    )
    travel_month: Optional[str] = Field(
        default=None, description="Month of travel (for weather filtering)"
    )
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of results to return"
    )
    include_weather: bool = Field(
        default=False, description="Whether to include weather information"
    )
    include_attractions: bool = Field(
        default=False, description="Whether to include points of interest"
    )


class DestinationDetailsRequest(BaseModel):
    """Request model for retrieving destination details."""

    destination_id: str = Field(description="Destination ID")
    include_weather: bool = Field(
        default=True, description="Whether to include weather information"
    )
    include_attractions: bool = Field(
        default=True, description="Whether to include points of interest"
    )
    travel_date: Optional[date] = Field(
        default=None, description="Travel date for seasonal information"
    )


class SavedDestinationRequest(BaseModel):
    """Request model for saving a destination to a trip."""

    destination_id: str = Field(description="Destination ID")
    trip_id: UUID = Field(description="Trip ID to save the destination for")
    notes: Optional[str] = Field(
        default=None, description="Notes about this destination"
    )
    visit_schedule: Optional[DestinationVisitSchedule] = Field(
        default=None, description="Visit schedule details"
    )
    priority: int = Field(1, ge=1, le=5, description="Priority (1=highest, 5=lowest)")


class DestinationSuggestionRequest(BaseModel):
    """Request model for getting destination suggestions."""

    interests: List[str] = Field(
        description="User interests (e.g., 'beaches', 'hiking', 'history')"
    )
    travel_dates: Optional[List[date]] = Field(
        default=None, description="Potential travel dates"
    )
    budget_range: Optional[Dict[str, float]] = Field(
        default=None,
        description="Budget range in USD (e.g., {'min': 500, 'max': 2000})",
    )
    trip_duration_days: Optional[int] = Field(
        default=None, ge=1, description="Trip duration in days"
    )
    preferred_continents: Optional[List[str]] = Field(
        default=None, description="Preferred continents"
    )
    preferred_climate: Optional[str] = Field(
        default=None, description="Preferred climate"
    )
    limit: int = Field(
        5, ge=1, le=20, description="Maximum number of suggestions to return"
    )


class PointOfInterestSearchRequest(BaseModel):
    """Request model for searching points of interest."""

    destination_id: str = Field(description="Destination ID to search POIs for")
    category: Optional[str] = Field(default=None, description="POI category filter")
    query: Optional[str] = Field(default=None, description="Search query for POIs")
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of results to return"
    )
    offset: int = Field(0, ge=0, description="Number of results to skip")
