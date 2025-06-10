"""
Request schemas for itinerary endpoints.

This module defines Pydantic V2 models for validating incoming itinerary-related
requests.
"""

from datetime import date, time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ItineraryItemType(str, Enum):
    """Types of items that can be in an itinerary."""

    ACTIVITY = "activity"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"
    MEAL = "meal"


class ItineraryStatus(str, Enum):
    """Status of an itinerary."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class ItineraryShareSettings(str, Enum):
    """Sharing settings for an itinerary."""

    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"


class OptimizationSetting(str, Enum):
    """Optimization settings for itinerary planning."""

    TIME = "time"
    COST = "cost"
    CONVENIENCE = "convenience"


class Location(BaseModel):
    """Location information for itinerary items."""

    latitude: float = Field(description="Latitude coordinate", ge=-90, le=90)
    longitude: float = Field(description="Longitude coordinate", ge=-180, le=180)
    name: Optional[str] = Field(None, description="Name of the location")


class TimeSlot(BaseModel):
    """Time slot for itinerary items."""

    start_time: time = Field(description="Start time")
    end_time: time = Field(description="End time")

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, v: time, info) -> time:
        """Validate that end_time is after start_time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            raise ValueError("End time must be after start time")
        return v


class ItineraryCreateRequest(BaseModel):
    """Request model for creating a new itinerary."""

    title: str = Field(
        description="Title of the itinerary",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Description of the itinerary",
    )
    start_date: date = Field(description="Start date of the itinerary")
    end_date: date = Field(description="End date of the itinerary")
    destinations: List[str] = Field(
        default_factory=list,
        description="List of destination IDs to include in this itinerary",
    )
    total_budget: Optional[float] = Field(
        None,
        description="Total budget for the trip",
        ge=0,
    )
    currency: Optional[str] = Field(
        None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags to associate with this itinerary",
    )

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate that end_date is after or equal to start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("End date must be after or equal to start date")
        return v


class ItineraryUpdateRequest(BaseModel):
    """Request model for updating an existing itinerary."""

    title: Optional[str] = Field(
        None,
        description="Title of the itinerary",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Description of the itinerary",
    )
    status: Optional[ItineraryStatus] = Field(
        None,
        description="Current status of the itinerary",
    )
    start_date: Optional[date] = Field(
        None,
        description="Start date of the itinerary",
    )
    end_date: Optional[date] = Field(
        None,
        description="End date of the itinerary",
    )
    destinations: Optional[List[str]] = Field(
        None,
        description="List of destination IDs to include in this itinerary",
    )
    total_budget: Optional[float] = Field(
        None,
        description="Total budget for the trip",
        ge=0,
    )
    currency: Optional[str] = Field(
        None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    tags: Optional[List[str]] = Field(
        None,
        description="List of tags to associate with this itinerary",
    )
    share_settings: Optional[ItineraryShareSettings] = Field(
        None,
        description="Sharing settings for the itinerary",
    )


class ItineraryItemCreateRequest(BaseModel):
    """Request model for adding an item to an itinerary."""

    item_type: ItineraryItemType = Field(description="Type of itinerary item")
    title: str = Field(
        description="Title or name of the item",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Description of the item",
    )
    item_date: date = Field(description="Date of the itinerary item")
    time_slot: Optional[TimeSlot] = Field(
        None,
        description="Time slot for the item, if applicable",
    )
    location: Optional[Location] = Field(
        None,
        description="Location of the item, if applicable",
    )
    cost: Optional[float] = Field(
        None,
        description="Cost of the item in the trip's currency",
        ge=0,
    )
    currency: Optional[str] = Field(
        None,
        description="Currency code for the cost (e.g., 'USD')",
    )
    booking_reference: Optional[str] = Field(
        None,
        description="Booking reference or confirmation number",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the item",
    )
    is_flexible: bool = Field(
        False,
        description="Whether this item's time is flexible",
    )
    # Type-specific fields as they are conditionally needed
    flight_details: Optional[Dict] = Field(
        None,
        description="Flight-specific details if type is TRANSPORT",
    )
    accommodation_details: Optional[Dict] = Field(
        None,
        description="Accommodation-specific details if type is ACCOMMODATION",
    )
    activity_details: Optional[Dict] = Field(
        None,
        description="Activity-specific details if type is ACTIVITY",
    )
    transportation_details: Optional[Dict] = Field(
        None,
        description="Transportation-specific details if type is TRANSPORT",
    )


class ItineraryItemUpdateRequest(BaseModel):
    """Request model for updating an itinerary item."""

    title: Optional[str] = Field(
        None,
        description="Title or name of the item",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        None,
        description="Description of the item",
    )
    item_date: Optional[date] = Field(
        None,
        description="Date of the itinerary item",
    )
    time_slot: Optional[TimeSlot] = Field(
        None,
        description="Time slot for the item, if applicable",
    )
    location: Optional[Location] = Field(
        None,
        description="Location of the item, if applicable",
    )
    cost: Optional[float] = Field(
        None,
        description="Cost of the item in the trip's currency",
        ge=0,
    )
    currency: Optional[str] = Field(
        None,
        description="Currency code for the cost (e.g., 'USD')",
    )
    booking_reference: Optional[str] = Field(
        None,
        description="Booking reference or confirmation number",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the item",
    )
    is_flexible: Optional[bool] = Field(
        None,
        description="Whether this item's time is flexible",
    )
    # Type-specific details as they are conditionally needed
    flight_details: Optional[Dict] = Field(
        None,
        description="Flight-specific details if type is TRANSPORT",
    )
    accommodation_details: Optional[Dict] = Field(
        None,
        description="Accommodation-specific details if type is ACCOMMODATION",
    )
    activity_details: Optional[Dict] = Field(
        None,
        description="Activity-specific details if type is ACTIVITY",
    )
    transportation_details: Optional[Dict] = Field(
        None,
        description="Transportation-specific details if type is TRANSPORT",
    )


class ItinerarySearchRequest(BaseModel):
    """Request model for searching itineraries."""

    query: Optional[str] = Field(
        None,
        description="Search query for finding itineraries",
    )
    start_date_from: Optional[date] = Field(
        None,
        description="Filter for itineraries starting from this date",
    )
    start_date_to: Optional[date] = Field(
        None,
        description="Filter for itineraries starting before this date",
    )
    end_date_from: Optional[date] = Field(
        None,
        description="Filter for itineraries ending from this date",
    )
    end_date_to: Optional[date] = Field(
        None,
        description="Filter for itineraries ending before this date",
    )
    destinations: Optional[List[str]] = Field(
        None,
        description="Filter by destination IDs included in the itinerary",
    )
    status: Optional[ItineraryStatus] = Field(
        None,
        description="Filter by itinerary status",
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Filter by tags associated with the itinerary",
    )
    page: int = Field(
        1,
        description="Page number for pagination",
        ge=1,
    )
    page_size: int = Field(
        10,
        description="Number of results per page",
        ge=1,
        le=100,
    )


class ItineraryOptimizeRequest(BaseModel):
    """Request model for optimizing an itinerary."""

    itinerary_id: str = Field(
        description="ID of the itinerary to optimize",
    )
    settings: OptimizationSetting = Field(
        description="Optimization settings",
    )
