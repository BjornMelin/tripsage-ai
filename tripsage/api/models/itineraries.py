"""
Models related to itineraries in the TripSage API.

This module defines Pydantic V2 models for itinerary-related requests and responses.
"""

from datetime import date as Date, datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ItineraryItemType(str, Enum):
    """Types of items that can be included in an itinerary."""

    FLIGHT = "flight"
    ACCOMMODATION = "accommodation"
    ACTIVITY = "activity"
    TRANSPORTATION = "transportation"
    MEAL = "meal"
    REST = "rest"
    OTHER = "other"


class ItineraryStatus(str, Enum):
    """Status of an itinerary."""

    DRAFT = "draft"
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ItineraryVisibility(str, Enum):
    """Visibility settings for an itinerary."""

    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class ItineraryShareSettings(BaseModel):
    """Model for itinerary sharing settings."""

    visibility: ItineraryVisibility = Field(
        default=ItineraryVisibility.PRIVATE,
        description="Visibility level of the itinerary",
    )
    shared_with: List[str] = Field(
        default=[],
        description="List of user IDs the itinerary is shared with",
    )
    editable_by: List[str] = Field(
        default=[],
        description="List of user IDs that can edit the itinerary",
    )
    share_link: Optional[str] = Field(
        default=None,
        description="Shareable link to the itinerary (if shared)",
    )
    password_protected: bool = Field(
        default=False,
        description="Whether the shared link is password protected",
    )


class TimeSlot(BaseModel):
    """Model for a time slot within a day."""

    start_time: str = Field(
        description="Start time in 24-hour format (HH:MM)",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )
    end_time: str = Field(
        description="End time in 24-hour format (HH:MM)",
        pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$",
    )
    duration_minutes: int = Field(
        description="Duration in minutes",
        ge=0,
    )

    @model_validator(mode="after")
    def validate_time_slot(self) -> "TimeSlot":
        """Validate time slot start/end times and duration."""
        # Convert to minutes since midnight for easy comparison
        start_hour, start_minute = map(int, self.start_time.split(":"))
        end_hour, end_minute = map(int, self.end_time.split(":"))

        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute

        # Handle overnight slots
        if end_minutes < start_minutes:
            end_minutes += 24 * 60  # Add 24 hours

        calculated_duration = end_minutes - start_minutes

        if self.duration_minutes != calculated_duration:
            self.duration_minutes = calculated_duration

        return self


class Location(BaseModel):
    """Model for a location."""

    name: str = Field(description="Name of the location")
    address: Optional[str] = Field(
        default=None,
        description="Full address of the location",
    )
    coordinates: Optional[Dict[str, float]] = Field(
        default=None,
        description="Geographic coordinates (latitude/longitude)",
    )
    country: Optional[str] = Field(
        default=None,
        description="Country of the location",
    )
    city: Optional[str] = Field(
        default=None,
        description="City of the location",
    )


class ItineraryItem(BaseModel):
    """Base model for an item in an itinerary."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique identifier for the itinerary item")
    item_item_type: ItineraryItemType = Field(description="Type of itinerary item")
    title: str = Field(description="Title or name of the item")
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


class FlightItineraryItem(ItineraryItem):
    """Model for a flight item in an itinerary."""

    item_type: Literal[ItineraryItemType.FLIGHT] = Field(
        default=ItineraryItemType.FLIGHT,
        description="Type is always 'flight' for this model",
    )
    flight_number: str = Field(description="Flight number")
    airline: str = Field(description="Airline name")
    departure_airport: str = Field(description="Departure airport code")
    arrival_airport: str = Field(description="Arrival airport code")
    departure_time: str = Field(
        description="Departure time (ISO 8601 format with timezone)"
    )
    arrival_time: str = Field(
        description="Arrival time (ISO 8601 format with timezone)"
    )
    duration_minutes: int = Field(
        description="Flight duration in minutes",
        ge=0,
    )
    layovers: Optional[List[Dict]] = Field(
        default=None,
        description="List of layover details",
    )
    seat_assignment: Optional[str] = Field(
        default=None,
        description="Seat assignment if available",
    )
    terminal_info: Optional[Dict] = Field(
        default=None,
        description="Terminal information for departure and arrival",
    )


class AccommodationItineraryItem(ItineraryItem):
    """Model for an accommodation item in an itinerary."""

    item_type: Literal[ItineraryItemType.ACCOMMODATION] = Field(
        default=ItineraryItemType.ACCOMMODATION,
        description="Type is always 'accommodation' for this model",
    )
    check_in_date: Date = Field(description="Check-in date")
    check_out_date: Date = Field(description="Check-out date")
    accommodation_type: str = Field(
        description="Type of accommodation (hotel, apartment, etc.)"
    )
    provider: Optional[str] = Field(
        default=None,
        description="Accommodation provider or brand",
    )
    amenities: Optional[List[str]] = Field(
        default=None,
        description="List of available amenities",
    )
    room_type: Optional[str] = Field(
        default=None,
        description="Type of room booked",
    )
    booking_platform: Optional[str] = Field(
        default=None,
        description="Platform used for booking",
    )


class ActivityItineraryItem(ItineraryItem):
    """Model for an activity item in an itinerary."""

    item_type: Literal[ItineraryItemType.ACTIVITY] = Field(
        default=ItineraryItemType.ACTIVITY,
        description="Type is always 'activity' for this model",
    )
    activity_type: str = Field(description="Type of activity (tour, attraction, etc.)")
    duration_minutes: int = Field(
        description="Duration of the activity in minutes",
        ge=0,
    )
    booking_required: bool = Field(
        default=False,
        description="Whether booking is required",
    )
    guided: Optional[bool] = Field(
        default=None,
        description="Whether the activity is guided",
    )
    weather_dependent: Optional[bool] = Field(
        default=None,
        description="Whether the activity is weather dependent",
    )


class TransportationItineraryItem(ItineraryItem):
    """Model for a transportation item in an itinerary."""

    item_type: Literal[ItineraryItemType.TRANSPORTATION] = Field(
        default=ItineraryItemType.TRANSPORTATION,
        description="Type is always 'transportation' for this model",
    )
    transportation_type: str = Field(
        description="Type of transportation (train, bus, car, etc.)"
    )
    departure_location: Location = Field(description="Departure location details")
    arrival_location: Location = Field(description="Arrival location details")
    departure_time: str = Field(description="Departure time in ISO 8601 format")
    arrival_time: str = Field(description="Arrival time in ISO 8601 format")
    duration_minutes: int = Field(
        description="Duration in minutes",
        ge=0,
    )
    provider: Optional[str] = Field(
        default=None,
        description="Transportation provider",
    )
    booking_platform: Optional[str] = Field(
        default=None,
        description="Platform used for booking",
    )


class ItineraryDay(BaseModel):
    """Model for a day in an itinerary."""

    date: Date = Field(description="Date of this itinerary day")
    items: List[ItineraryItem] = Field(
        default=[],
        description="List of items scheduled for this day",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Notes for this day",
    )

    @property
    def sorted_items(self) -> List[ItineraryItem]:
        """Return items sorted by time slot start time."""

        def get_sort_key(item):
            if not item.time_slot:
                return "24:00"  # Put items without time at the end
            return item.time_slot.start_time

        return sorted(self.items, key=get_sort_key)


class Itinerary(BaseModel):
    """Model for a complete itinerary."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Unique identifier for the itinerary")
    user_id: str = Field(description="ID of the user who owns the itinerary")
    title: str = Field(description="Title of the itinerary")
    description: Optional[str] = Field(
        default=None,
        description="Description of the itinerary",
    )
    status: ItineraryStatus = Field(
        default=ItineraryStatus.DRAFT,
        description="Current status of the itinerary",
    )
    start_date: Date = Field(description="Start date of the itinerary")
    end_date: Date = Field(description="End date of the itinerary")
    days: List[ItineraryDay] = Field(
        default=[],
        description="List of days in the itinerary",
    )
    destinations: List[str] = Field(
        default=[],
        description="List of destination IDs included in this itinerary",
    )
    total_budget: Optional[float] = Field(
        default=None,
        description="Total budget for the trip",
    )
    budget_spent: Optional[float] = Field(
        default=None,
        description="Amount of budget already spent or allocated",
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    share_settings: ItineraryShareSettings = Field(
        default_factory=ItineraryShareSettings,
        description="Sharing settings for the itinerary",
    )
    created_at: datetime = Field(
        description="Timestamp when the itinerary was created",
    )
    updated_at: datetime = Field(
        description="Timestamp when the itinerary was last updated",
    )
    tags: List[str] = Field(
        default=[],
        description="List of tags associated with this itinerary",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "Itinerary":
        """Validate that end_date is after or equal to start_date."""
        if self.end_date < self.start_date:
            raise ValueError("End date must be after or equal to start date")
        return self

    @property
    def duration_days(self) -> int:
        """Calculate the duration of the itinerary in days."""
        return (self.end_date - self.start_date).days + 1


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
        if self.type == ItineraryItemType.FLIGHT and not self.flight_details:
            raise ValueError("Flight details must be provided for flight items")
        if (
            self.type == ItineraryItemType.ACCOMMODATION
            and not self.accommodation_details
        ):
            raise ValueError("Accommodation details required for accommodation items")
        if self.type == ItineraryItemType.ACTIVITY and not self.activity_details:
            raise ValueError("Activity details must be provided for activity items")
        if (
            self.type == ItineraryItemType.TRANSPORTATION
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


class ItinerarySearchResponse(BaseModel):
    """Response model for itinerary search results."""

    results: List[Itinerary] = Field(
        description="List of itineraries matching the search criteria",
    )
    total: int = Field(
        description="Total number of itineraries matching the search criteria",
    )
    page: int = Field(
        description="Current page number",
    )
    page_size: int = Field(
        description="Number of results per page",
    )
    pages: int = Field(
        description="Total number of pages available",
    )


class ItineraryConflictCheckResponse(BaseModel):
    """Response model for checking conflicting items in an itinerary."""

    has_conflicts: bool = Field(
        description="Whether there are any conflicts",
    )
    conflicts: List[Dict] = Field(
        description="List of conflicts found",
        default=[],
    )


class OptimizationSetting(BaseModel):
    """Settings for itinerary optimization."""

    prioritize: List[str] = Field(
        description="Features to prioritize (e.g., 'cost', 'time', 'convenience')",
    )
    minimize_travel_time: bool = Field(
        default=True,
        description="Whether to minimize travel time between items",
    )
    include_breaks: bool = Field(
        default=True,
        description="Whether to include breaks between activities",
    )
    break_duration_minutes: Optional[int] = Field(
        default=None,
        description="Default duration for breaks in minutes",
    )
    start_day_time: Optional[str] = Field(
        default=None,
        description="Preferred start time for each day (HH:MM)",
    )
    end_day_time: Optional[str] = Field(
        default=None,
        description="Preferred end time for each day (HH:MM)",
    )
    meal_times: Optional[Dict[str, str]] = Field(
        default=None,
        description="Preferred times for meals (e.g., {'breakfast': '08:00'})",
    )


class ItineraryOptimizeRequest(BaseModel):
    """Request model for optimizing an itinerary."""

    itinerary_id: str = Field(
        description="ID of the itinerary to optimize",
    )
    settings: OptimizationSetting = Field(
        description="Optimization settings",
    )


class ItineraryOptimizeResponse(BaseModel):
    """Response model for optimized itinerary."""

    original_itinerary: Itinerary = Field(
        description="Original itinerary before optimization",
    )
    optimized_itinerary: Itinerary = Field(
        description="Optimized itinerary",
    )
    changes: List[Dict] = Field(
        description="List of changes made during optimization",
    )
    optimization_score: float = Field(
        description="Score representing the optimization improvement (0-1)",
        ge=0,
        le=1,
    )
