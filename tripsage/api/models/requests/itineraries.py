"""
Request models for itinerary endpoints.

This module defines Pydantic models for validating incoming itinerary-related requests.
"""

from datetime import date as Date
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from ..common.itineraries import (
    ItineraryItemType,
    ItineraryShareSettings,
    ItineraryStatus,
    Location,
    OptimizationSetting,
    TimeSlot,
)


class ItineraryCreateRequest(BaseModel):
    """Request model for creating a new itinerary."""

    title: str = Field(
        description="Title of the itinerary",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the itinerary",
    )
    start_date: Date = Field(description="Start date of the itinerary")
    end_date: Date = Field(description="End date of the itinerary")
    destinations: List[str] = Field(
        default=[],
        description="List of destination IDs to include in this itinerary",
    )
    total_budget: Optional[float] = Field(
        default=None,
        description="Total budget for the trip",
        ge=0,
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    tags: List[str] = Field(
        default=[],
        description="List of tags to associate with this itinerary",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "ItineraryCreateRequest":
        """Validate that end_date is after or equal to start_date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must be after or equal to start date")
        return self


class ItineraryUpdateRequest(BaseModel):
    """Request model for updating an existing itinerary."""

    title: Optional[str] = Field(
        default=None,
        description="Title of the itinerary",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the itinerary",
    )
    status: Optional[ItineraryStatus] = Field(
        default=None,
        description="Current status of the itinerary",
    )
    start_date: Optional[Date] = Field(
        default=None,
        description="Start date of the itinerary",
    )
    end_date: Optional[Date] = Field(
        default=None,
        description="End date of the itinerary",
    )
    destinations: Optional[List[str]] = Field(
        default=None,
        description="List of destination IDs to include in this itinerary",
    )
    total_budget: Optional[float] = Field(
        default=None,
        description="Total budget for the trip",
        ge=0,
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="List of tags to associate with this itinerary",
    )
    share_settings: Optional[ItineraryShareSettings] = Field(
        default=None,
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
        default=None,
        description="Description of the item",
    )
    item_date: Date = Field(description="Date of the itinerary item")
    time_slot: Optional[TimeSlot] = Field(
        default=None,
        description="Time slot for the item, if applicable",
    )
    location: Optional[Location] = Field(
        default=None,
        description="Location of the item, if applicable",
    )
    cost: Optional[float] = Field(
        default=None,
        description="Cost of the item in the trip's currency",
        ge=0,
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code for the cost (e.g., 'USD')",
    )
    booking_reference: Optional[str] = Field(
        default=None,
        description="Booking reference or confirmation number",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the item",
    )
    is_flexible: bool = Field(
        default=False,
        description="Whether this item's time is flexible",
    )
    # Type-specific fields as they are conditionally needed
    flight_details: Optional[Dict] = Field(
        default=None,
        description="Flight-specific details if type is FLIGHT",
    )
    accommodation_details: Optional[Dict] = Field(
        default=None,
        description="Accommodation-specific details if type is ACCOMMODATION",
    )
    activity_details: Optional[Dict] = Field(
        default=None,
        description="Activity-specific details if type is ACTIVITY",
    )
    transportation_details: Optional[Dict] = Field(
        default=None,
        description="Transportation-specific details if type is TRANSPORTATION",
    )

    @model_validator(mode="after")
    def validate_type_specific_details(self) -> "ItineraryItemCreateRequest":
        """Validate that type-specific details are provided when required."""
        if self.item_type == ItineraryItemType.FLIGHT and not self.flight_details:
            raise ValueError("Flight details must be provided for flight items")
        if (
            self.item_type == ItineraryItemType.ACCOMMODATION
            and not self.accommodation_details
        ):
            raise ValueError("Accommodation details required for accommodation items")
        if self.item_type == ItineraryItemType.ACTIVITY and not self.activity_details:
            raise ValueError("Activity details must be provided for activity items")
        if (
            self.item_type == ItineraryItemType.TRANSPORTATION
            and not self.transportation_details
        ):
            raise ValueError("Transportation details required for transportation items")
        return self


class ItineraryItemUpdateRequest(BaseModel):
    """Request model for updating an itinerary item."""

    title: Optional[str] = Field(
        default=None,
        description="Title or name of the item",
        min_length=1,
        max_length=100,
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of the item",
    )
    date: Optional[Date] = Field(
        default=None,
        description="Date of the itinerary item",
    )
    time_slot: Optional[TimeSlot] = Field(
        default=None,
        description="Time slot for the item, if applicable",
    )
    location: Optional[Location] = Field(
        default=None,
        description="Location of the item, if applicable",
    )
    cost: Optional[float] = Field(
        default=None,
        description="Cost of the item in the trip's currency",
        ge=0,
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code for the cost (e.g., 'USD')",
    )
    booking_reference: Optional[str] = Field(
        default=None,
        description="Booking reference or confirmation number",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the item",
    )
    is_flexible: Optional[bool] = Field(
        default=None,
        description="Whether this item's time is flexible",
    )
    # Type-specific details as they are conditionally needed
    flight_details: Optional[Dict] = Field(
        default=None,
        description="Flight-specific details if type is FLIGHT",
    )
    accommodation_details: Optional[Dict] = Field(
        default=None,
        description="Accommodation-specific details if type is ACCOMMODATION",
    )
    activity_details: Optional[Dict] = Field(
        default=None,
        description="Activity-specific details if type is ACTIVITY",
    )
    transportation_details: Optional[Dict] = Field(
        default=None,
        description="Transportation-specific details if type is TRANSPORTATION",
    )


class ItinerarySearchRequest(BaseModel):
    """Request model for searching itineraries."""

    query: Optional[str] = Field(
        default=None,
        description="Search query for finding itineraries",
    )
    start_date_from: Optional[Date] = Field(
        default=None,
        description="Filter for itineraries starting from this date",
    )
    start_date_to: Optional[Date] = Field(
        default=None,
        description="Filter for itineraries starting before this date",
    )
    end_date_from: Optional[Date] = Field(
        default=None,
        description="Filter for itineraries ending from this date",
    )
    end_date_to: Optional[Date] = Field(
        default=None,
        description="Filter for itineraries ending before this date",
    )
    destinations: Optional[List[str]] = Field(
        default=None,
        description="Filter by destination IDs included in the itinerary",
    )
    status: Optional[ItineraryStatus] = Field(
        default=None,
        description="Filter by itinerary status",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Filter by tags associated with the itinerary",
    )
    page: int = Field(
        default=1,
        description="Page number for pagination",
        ge=1,
    )
    page_size: int = Field(
        default=10,
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
