"""Canonical itinerary request and response models used by API routers."""

from datetime import date, time
from enum import Enum
from typing import Any, cast

from pydantic import ConfigDict, Field, ValidationInfo, field_validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.base_models import PaginatedResponse


def _empty_str_list() -> list[str]:
    """Return an empty list of strings."""
    return []


def _empty_item_list() -> list["ItineraryItemResponse"]:  # forward ref
    """Return an empty list of itinerary item responses."""
    return []


def _empty_dict_any_list() -> list[dict[str, Any]]:
    """Return an empty list of dictionaries."""
    return []


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


class Location(TripSageModel):
    """Location information for itinerary items."""

    latitude: float = Field(description="Latitude coordinate", ge=-90, le=90)
    longitude: float = Field(description="Longitude coordinate", ge=-180, le=180)
    name: str | None = Field(None, description="Name of the location")


class TimeSlot(TripSageModel):
    """Time slot for itinerary items."""

    start_time: time = Field(description="Start time")
    end_time: time = Field(description="End time")

    @field_validator("end_time")
    @classmethod
    def validate_end_time(cls, value: time, info: ValidationInfo) -> time:
        """Validate that end_time is after start_time."""
        data_any: Any = info.data
        if isinstance(data_any, dict):
            d = cast(dict[str, Any], data_any)
            start = cast(time | None, d.get("start_time"))
        else:
            start = None
        if start and value <= start:
            raise ValueError("End time must be after start time")
        return value


class ItineraryCreateRequest(TripSageModel):
    """Request model for creating a new itinerary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Tokyo Adventure",
                "description": "5-day itinerary across Tokyo",
                "start_date": "2025-05-01",
                "end_date": "2025-05-05",
                "destinations": ["Tokyo"],
                "total_budget": 4500.0,
                "currency": "USD",
                "tags": ["culture", "food"],
            }
        }
    )

    title: str = Field(
        description="Title of the itinerary",
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        None,
        description="Description of the itinerary",
    )
    start_date: date = Field(description="Start date of the itinerary")
    end_date: date = Field(description="End date of the itinerary")
    destinations: list[str] = Field(
        default_factory=list,
        description="List of destination IDs to include in this itinerary",
    )
    total_budget: float | None = Field(
        None,
        description="Total budget for the trip",
        ge=0,
    )
    currency: str | None = Field(
        None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="List of tags to associate with this itinerary",
    )

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, value: date, info: ValidationInfo) -> date:
        """Validate that end_date is after or equal to start_date."""
        data_any: Any = info.data
        if isinstance(data_any, dict):
            d = cast(dict[str, Any], data_any)
            start = cast(date | None, d.get("start_date"))
        else:
            start = None
        if start and value < start:
            raise ValueError("End date must be after or equal to start date")
        return value


class ItineraryUpdateRequest(TripSageModel):
    """Request model for updating an existing itinerary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Tokyo Adventure",
                "status": "active",
                "tags": ["culture", "nightlife"],
            }
        }
    )

    title: str | None = Field(
        None,
        description="Title of the itinerary",
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        None,
        description="Description of the itinerary",
    )
    status: ItineraryStatus | None = Field(
        None,
        description="Current status of the itinerary",
    )
    start_date: date | None = Field(
        None,
        description="Start date of the itinerary",
    )
    end_date: date | None = Field(
        None,
        description="End date of the itinerary",
    )
    destinations: list[str] | None = Field(
        None,
        description="List of destination IDs to include in this itinerary",
    )
    total_budget: float | None = Field(
        None,
        description="Total budget for the trip",
        ge=0,
    )
    currency: str | None = Field(
        None,
        description="Currency code for budget amounts (e.g., 'USD')",
    )
    tags: list[str] | None = Field(
        None,
        description="List of tags to associate with this itinerary",
    )
    share_settings: ItineraryShareSettings | None = Field(
        None,
        description="Sharing settings for the itinerary",
    )


class ItineraryItemCreateRequest(TripSageModel):
    """Request model for adding an item to an itinerary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_type": "activity",
                "title": "Visit Tokyo Tower",
                "description": "Iconic landmark with city views",
                "item_date": "2025-05-02",
                "time_slot": {
                    "start_time": "10:00",
                    "end_time": "12:00",
                },
                "cost": 100.0,
                "currency": "USD",
            }
        }
    )

    item_type: ItineraryItemType = Field(description="Type of itinerary item")
    title: str = Field(
        description="Title or name of the item",
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        None,
        description="Description of the item",
    )
    item_date: date = Field(description="Date of the itinerary item")
    time_slot: TimeSlot | None = Field(
        None,
        description="Time slot for the item, if applicable",
    )
    location: Location | None = Field(
        None,
        description="Location of the item, if applicable",
    )
    cost: float | None = Field(
        None,
        description="Cost of the item in the trip's currency",
        ge=0,
    )
    currency: str | None = Field(
        None,
        description="Currency code for the cost (e.g., 'USD')",
    )
    booking_reference: str | None = Field(
        None,
        description="Booking reference or confirmation number",
    )
    notes: str | None = Field(
        None,
        description="Additional notes about the item",
    )
    is_flexible: bool = Field(
        False,
        description="Whether this item's time is flexible",
    )
    flight_details: dict[str, Any] | None = Field(
        None,
        description="Flight-specific details if type is TRANSPORT",
    )
    accommodation_details: dict[str, Any] | None = Field(
        None,
        description="Accommodation-specific details if type is ACCOMMODATION",
    )
    activity_details: dict[str, Any] | None = Field(
        None,
        description="Activity-specific details if type is ACTIVITY",
    )
    transportation_details: dict[str, Any] | None = Field(
        None,
        description="Transportation-specific details if type is TRANSPORT",
    )


class ItineraryItemUpdateRequest(TripSageModel):
    """Request model for updating an itinerary item."""

    title: str | None = Field(
        None,
        description="Title or name of the item",
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        None,
        description="Description of the item",
    )
    item_date: date | None = Field(
        None,
        description="Date of the itinerary item",
    )
    time_slot: TimeSlot | None = Field(
        None,
        description="Time slot for the item, if applicable",
    )
    location: Location | None = Field(
        None,
        description="Location of the item, if applicable",
    )
    cost: float | None = Field(
        None,
        description="Cost of the item in the trip's currency",
        ge=0,
    )
    currency: str | None = Field(
        None,
        description="Currency code for the cost (e.g., 'USD')",
    )
    booking_reference: str | None = Field(
        None,
        description="Booking reference or confirmation number",
    )
    notes: str | None = Field(
        None,
        description="Additional notes about the item",
    )
    is_flexible: bool | None = Field(
        None,
        description="Whether this item's time is flexible",
    )
    flight_details: dict[str, Any] | None = Field(
        None,
        description="Flight-specific details if type is TRANSPORT",
    )
    accommodation_details: dict[str, Any] | None = Field(
        None,
        description="Accommodation-specific details if type is ACCOMMODATION",
    )
    activity_details: dict[str, Any] | None = Field(
        None,
        description="Activity-specific details if type is ACTIVITY",
    )
    transportation_details: dict[str, Any] | None = Field(
        None,
        description="Transportation-specific details if type is TRANSPORT",
    )


class ItinerarySearchRequest(TripSageModel):
    """Request model for searching itineraries."""

    query: str | None = Field(
        None,
        description="Search query for finding itineraries",
    )
    start_date_from: date | None = Field(
        None,
        description="Filter for itineraries starting from this date",
    )
    start_date_to: date | None = Field(
        None,
        description="Filter for itineraries starting before this date",
    )
    end_date_from: date | None = Field(
        None,
        description="Filter for itineraries ending from this date",
    )
    end_date_to: date | None = Field(
        None,
        description="Filter for itineraries ending before this date",
    )
    destinations: list[str] | None = Field(
        None,
        description="Filter by destination IDs included in the itinerary",
    )
    status: ItineraryStatus | None = Field(
        None,
        description="Filter by itinerary status",
    )
    tags: list[str] | None = Field(
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


class ItineraryOptimizeRequest(TripSageModel):
    """Request model for optimizing an itinerary."""

    itinerary_id: str = Field(
        description="ID of the itinerary to optimize",
    )
    settings: OptimizationSetting = Field(
        description="Optimization settings",
    )


class ItineraryItemResponse(TripSageModel):
    """Response model for itinerary item."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "item-123",
                "item_type": "activity",
                "title": "Visit Tokyo Tower",
                "description": "Iconic landmark with city views",
                "item_date": "2025-05-02",
                "start_time": "10:00",
                "end_time": "12:00",
                "cost": 100.0,
                "currency": "USD",
                "booking_reference": "ABC123",
                "notes": "Wear comfortable shoes",
                "is_flexible": False,
                "created_at": "2025-04-01T09:00:00Z",
                "updated_at": "2025-04-01T09:00:00Z",
            }
        }
    )

    id: str = Field(description="Unique identifier for the itinerary item")
    item_type: str = Field(description="Type of itinerary item")
    title: str = Field(description="Title or name of the item")
    description: str | None = Field(None, description="Description of the item")
    item_date: date = Field(description="Date of the itinerary item")
    start_time: str | None = Field(
        None, description="Start time (HH:MM) for the itinerary item"
    )
    end_time: str | None = Field(
        None, description="End time (HH:MM) for the itinerary item"
    )
    cost: float | None = Field(None, description="Cost of the item")
    currency: str | None = Field(None, description="Currency code for the cost")
    booking_reference: str | None = Field(None, description="Booking reference")
    notes: str | None = Field(None, description="Additional notes")
    is_flexible: bool = Field(False, description="Whether item time is flexible")
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")


class ItineraryResponse(TripSageModel):
    """Response model for itinerary."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "itinerary-123",
                "title": "Tokyo Adventure",
                "description": "5-day itinerary",
                "start_date": "2025-05-01",
                "end_date": "2025-05-05",
                "status": "active",
                "total_budget": 4500.0,
                "currency": "USD",
                "tags": ["culture", "food"],
                "items": [
                    {
                        "id": "item-123",
                        "item_type": "activity",
                        "title": "Visit Tokyo Tower",
                        "item_date": "2025-05-02",
                        "start_time": "10:00",
                        "end_time": "12:00",
                    }
                ],
                "created_at": "2025-04-01T09:00:00Z",
                "updated_at": "2025-04-01T09:00:00Z",
            }
        }
    )

    id: str = Field(description="Itinerary identifier")
    title: str = Field(description="Itinerary title")
    description: str | None = Field(None, description="Itinerary description")
    start_date: date = Field(description="Itinerary start date")
    end_date: date = Field(description="Itinerary end date")
    status: str = Field(description="Current status of the itinerary")
    total_budget: float | None = Field(None, description="Total budget for the trip")
    currency: str | None = Field(None, description="Currency code for budget")
    tags: list[str] = Field(
        default_factory=_empty_str_list, description="Associated tags"
    )
    items: list[ItineraryItemResponse] = Field(
        default_factory=_empty_item_list, description="Itinerary items"
    )
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")


class ItinerarySearchResponse(PaginatedResponse[ItineraryResponse]):
    """Paginated itinerary search response following canonical pagination schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": None,
                "timestamp": "2025-04-01T09:00:00Z",
                "data": [
                    {
                        "id": "itinerary-123",
                        "title": "Tokyo Adventure",
                        "description": "5-day itinerary",
                        "start_date": "2025-05-01",
                        "end_date": "2025-05-05",
                        "status": "active",
                        "total_budget": 4500.0,
                        "currency": "USD",
                        "tags": ["culture"],
                        "items": [],
                        "created_at": "2025-04-01T09:00:00Z",
                        "updated_at": "2025-04-01T09:00:00Z",
                    }
                ],
                "pagination": {
                    "page": 1,
                    "per_page": 25,
                    "total_items": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False,
                },
            }
        }
    )


class ItineraryConflictCheckResponse(TripSageModel):
    """Response model for checking conflicting items in an itinerary."""

    has_conflicts: bool = Field(
        description="Whether there are any conflicts",
    )
    conflicts: list[dict[str, Any]] = Field(
        default_factory=_empty_dict_any_list,
        description="List of conflicts found",
    )


class ItineraryOptimizeResponse(TripSageModel):
    """Response model for optimized itinerary."""

    original_itinerary: ItineraryResponse = Field(
        description="Original itinerary before optimization",
    )
    optimized_itinerary: ItineraryResponse = Field(
        description="Optimized itinerary",
    )
    changes: list[dict[str, Any]] = Field(
        default_factory=_empty_dict_any_list,
        description="List of changes made during optimization",
    )
    optimization_score: float = Field(
        description="Score representing the optimization improvement (0-1)",
        ge=0,
        le=1,
    )


__all__ = [
    "ItineraryConflictCheckResponse",
    "ItineraryCreateRequest",
    "ItineraryItemCreateRequest",
    "ItineraryItemResponse",
    "ItineraryItemType",
    "ItineraryItemUpdateRequest",
    "ItineraryOptimizeRequest",
    "ItineraryOptimizeResponse",
    "ItineraryResponse",
    "ItinerarySearchRequest",
    "ItinerarySearchResponse",
    "ItineraryShareSettings",
    "ItineraryStatus",
    "ItineraryUpdateRequest",
    "Location",
    "OptimizationSetting",
    "TimeSlot",
]
