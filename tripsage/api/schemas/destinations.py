"""Destination API schemas using Pydantic V2.

This module defines Pydantic models for destination-related API requests and responses.
Consolidates both request and response schemas for destination operations.
"""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common.geographic import Place as Destination

# ===== Enums =====

class DestinationCategory(str, Enum):
    CULTURE = "culture"
    NATURE = "nature"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    FOOD = "food"

class DestinationVisitSchedule(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    FULL_DAY = "full_day"

# ===== Request Schemas =====

class DestinationSearchRequest(BaseModel):
    """Request model for searching destinations."""

    query: str = Field(
        description="Search query (e.g., country, city, or general description)",
        min_length=1,
        max_length=100,
    )
    categories: list[DestinationCategory] | None = Field(
        default=None, description="Categories to filter by"
    )
    min_safety_rating: float | None = Field(
        default=None, ge=0, le=5, description="Minimum safety rating (0-5)"
    )
    travel_month: str | None = Field(
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
    travel_date: date | None = Field(
        default=None, description="Travel date for seasonal information"
    )

class SavedDestinationRequest(BaseModel):
    """Request model for saving a destination to a trip."""

    destination_id: str = Field(description="Destination ID")
    trip_id: UUID = Field(description="Trip ID to save the destination for")
    notes: str | None = Field(
        default=None, description="Notes about this destination"
    )
    visit_schedule: DestinationVisitSchedule | None = Field(
        default=None, description="Visit schedule details"
    )
    priority: int = Field(1, ge=1, le=5, description="Priority (1=highest, 5=lowest)")

class DestinationSuggestionRequest(BaseModel):
    """Request model for getting destination suggestions."""

    interests: list[str] = Field(
        description="User interests (e.g., 'beaches', 'hiking', 'history')"
    )
    travel_dates: list[date] | None = Field(
        default=None, description="Potential travel dates"
    )
    budget_range: dict[str, float] | None = Field(
        default=None,
        description="Budget range in USD (e.g., {'min': 500, 'max': 2000})",
    )
    trip_duration_days: int | None = Field(
        default=None, ge=1, description="Trip duration in days"
    )
    preferred_continents: list[str] | None = Field(
        default=None, description="Preferred continents"
    )
    preferred_climate: str | None = Field(
        default=None, description="Preferred climate"
    )
    limit: int = Field(
        5, ge=1, le=20, description="Maximum number of suggestions to return"
    )

class PointOfInterestSearchRequest(BaseModel):
    """Request model for searching points of interest."""

    destination_id: str = Field(description="Destination ID to search POIs for")
    category: str | None = Field(default=None, description="POI category filter")
    query: str | None = Field(default=None, description="Search query for POIs")
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of results to return"
    )
    offset: int = Field(0, ge=0, description="Number of results to skip")

# ===== Response Schemas =====

class DestinationSearchResponse(BaseModel):
    """Response model for destination search results."""

    destinations: list[Destination] = Field(description="List of destinations")
    count: int = Field(description="Number of destinations found")
    query: str = Field(description="Original search query")

class DestinationDetailsResponse(BaseModel):
    """Response model for destination details."""

    destination: Destination = Field(description="Destination details")

class SavedDestinationResponse(BaseModel):
    """Response model for a saved destination."""

    id: UUID = Field(description="Saved destination ID")
    user_id: str = Field(description="User ID")
    trip_id: UUID = Field(description="Trip ID")
    destination: Destination = Field(description="Destination details")
    saved_at: date = Field(description="Date when the destination was saved")
    notes: str | None = Field(
        default=None, description="Notes about this destination"
    )
    visit_schedule: DestinationVisitSchedule | None = Field(
        default=None, description="Visit schedule details"
    )
    priority: int = Field(description="Priority (1=highest, 5=lowest)")

class DestinationSuggestionResponse(BaseModel):
    """Response model for destination suggestions."""

    suggestions: list[Destination] = Field(description="Destination suggestions")
    count: int = Field(description="Number of suggestions")
    reasoning: dict[str, str] | None = Field(
        default=None,
        description="Reasoning for each suggestion (destination_id -> explanation)",
    )

# Keep these aliases as they represent different semantic concepts
DestinationRecommendation = DestinationSuggestionResponse
