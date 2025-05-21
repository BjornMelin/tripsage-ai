"""Destination models using Pydantic V2.

This module defines Pydantic models for destination-related requests and responses.
"""

from datetime import date
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class DestinationCategory(str, Enum):
    """Destination category options."""

    CITY = "city"
    BEACH = "beach"
    MOUNTAIN = "mountain"
    COUNTRYSIDE = "countryside"
    HISTORICAL = "historical"
    CULTURAL = "cultural"
    ADVENTURE = "adventure"
    RELAXATION = "relaxation"
    OTHER = "other"


class DestinationImage(BaseModel):
    """Model for a destination image."""

    url: str = Field(description="Image URL")
    caption: Optional[str] = Field(default=None, description="Image caption")
    is_primary: bool = Field(
        default=False, description="Whether this is the primary image"
    )
    attribution: Optional[str] = Field(default=None, description="Image attribution")


class PointOfInterest(BaseModel):
    """Model for a point of interest."""

    name: str = Field(description="Point of interest name")
    category: str = Field(description="Point of interest category")
    description: Optional[str] = Field(
        default=None, description="Point of interest description"
    )
    address: Optional[str] = Field(default=None, description="Address")
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    rating: Optional[float] = Field(default=None, description="Rating (0-5)")
    images: List[DestinationImage] = Field(
        default=[], description="Point of interest images"
    )
    website: Optional[str] = Field(default=None, description="Website URL")
    opening_hours: Optional[Dict[str, str]] = Field(
        default=None, description="Opening hours by day of week"
    )

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate that rating is between 0 and 5 if provided."""
        if v is not None and (v < 0 or v > 5):
            raise ValueError("Rating must be between 0 and 5")
        return v


class DestinationWeather(BaseModel):
    """Model for destination weather information."""

    season: str = Field(description="Current season")
    temperature_high_celsius: float = Field(
        description="Average high temperature in Celsius"
    )
    temperature_low_celsius: float = Field(
        description="Average low temperature in Celsius"
    )
    precipitation_mm: float = Field(description="Average precipitation in mm")
    humidity_percent: float = Field(description="Average humidity percentage")
    conditions: str = Field(description="Typical weather conditions")
    best_time_to_visit: List[str] = Field(
        default=[], description="Best months to visit"
    )


class Destination(BaseModel):
    """Model for a destination."""

    id: str = Field(description="Destination ID")
    name: str = Field(description="Destination name")
    country: str = Field(description="Country")
    region: Optional[str] = Field(default=None, description="Region/state/province")
    city: Optional[str] = Field(default=None, description="City")
    description: Optional[str] = Field(default=None, description="Description")
    categories: List[DestinationCategory] = Field(
        default=[], description="Destination categories"
    )
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    timezone: Optional[str] = Field(default=None, description="Timezone")
    currency: Optional[str] = Field(default=None, description="Local currency code")
    language: Optional[str] = Field(default=None, description="Primary language")
    images: List[DestinationImage] = Field(default=[], description="Destination images")
    points_of_interest: List[PointOfInterest] = Field(
        default=[], description="Points of interest"
    )
    weather: Optional[DestinationWeather] = Field(
        default=None, description="Weather information"
    )
    best_time_to_visit: List[str] = Field(
        default=[], description="Best months to visit"
    )
    travel_advisory: Optional[str] = Field(
        default=None, description="Travel advisory information"
    )
    visa_requirements: Optional[str] = Field(
        default=None, description="Visa requirements"
    )
    local_transportation: Optional[str] = Field(
        default=None, description="Local transportation options"
    )
    popular_activities: List[str] = Field(default=[], description="Popular activities")
    safety_rating: Optional[float] = Field(
        default=None, description="Safety rating (0-5)"
    )

    @field_validator("safety_rating")
    @classmethod
    def validate_safety_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate that safety rating is between 0 and 5 if provided."""
        if v is not None and (v < 0 or v > 5):
            raise ValueError("Safety rating must be between 0 and 5")
        return v


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


class DestinationSearchResponse(BaseModel):
    """Response model for destination search results."""

    destinations: List[Destination] = Field(description="List of destinations")
    count: int = Field(description="Number of destinations found")
    query: str = Field(description="Original search query")


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


class DestinationDetailsResponse(BaseModel):
    """Response model for destination details."""

    destination: Destination = Field(description="Destination details")


class DestinationVisitSchedule(BaseModel):
    """Model for a scheduled destination visit."""

    destination_id: str = Field(description="Destination ID")
    destination_name: str = Field(description="Destination name")
    arrival_date: date = Field(description="Arrival date")
    departure_date: date = Field(description="Departure date")
    stay_duration_days: int = Field(description="Duration of stay in days")

    @model_validator(mode="after")
    def validate_dates(self) -> "DestinationVisitSchedule":
        """Validate that departure date is after arrival date."""
        if self.departure_date <= self.arrival_date:
            raise ValueError("Departure date must be after arrival date")

        # Check duration matches dates
        duration = (self.departure_date - self.arrival_date).days
        if duration != self.stay_duration_days:
            self.stay_duration_days = duration

        return self


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


class SavedDestinationResponse(BaseModel):
    """Response model for a saved destination."""

    id: UUID = Field(description="Saved destination ID")
    user_id: str = Field(description="User ID")
    trip_id: UUID = Field(description="Trip ID")
    destination: Destination = Field(description="Destination details")
    saved_at: date = Field(description="Date when the destination was saved")
    notes: Optional[str] = Field(
        default=None, description="Notes about this destination"
    )
    visit_schedule: Optional[DestinationVisitSchedule] = Field(
        default=None, description="Visit schedule details"
    )
    priority: int = Field(description="Priority (1=highest, 5=lowest)")


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


class DestinationSuggestionResponse(BaseModel):
    """Response model for destination suggestions."""

    suggestions: List[Destination] = Field(description="Destination suggestions")
    count: int = Field(description="Number of suggestions")
    reasoning: Optional[Dict[str, str]] = Field(
        default=None,
        description="Reasoning for each suggestion (destination_id -> explanation)",
    )
