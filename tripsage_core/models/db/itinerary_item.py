"""ItineraryItem model for TripSage.

This module provides the ItineraryItem model with business logic validation,
used across different storage backends.
"""

from datetime import date as Date
from datetime import time as dt_time
from enum import Enum

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel


class ItemType(str, Enum):
    """Enum for itinerary item type values."""

    ACTIVITY = "activity"
    MEAL = "meal"
    TRANSPORT = "transport"
    ACCOMMODATION = "accommodation"
    OTHER = "other"


class ItineraryItem(TripSageModel):
    """ItineraryItem model for TripSage.

    Attributes:
        id: Unique identifier for the itinerary item
        trip_id: Reference to the associated trip
        item_type: Type of itinerary item
        date: Date of the itinerary item
        scheduled_time: Time of the itinerary item
        description: Description of the itinerary item
        cost: Cost of the itinerary item in default currency
        notes: Additional notes or information
    """

    id: int | None = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    item_type: ItemType = Field(..., description="Type of itinerary item")
    date: Date = Field(..., description="Date of the itinerary item")
    scheduled_time: dt_time | None = Field(
        None, description="Time of the itinerary item"
    )
    description: str = Field(..., description="Description of the itinerary item")
    cost: float | None = Field(None, description="Cost in default currency")
    notes: str | None = Field(None, description="Additional notes or information")

    @field_validator("cost")
    @classmethod
    def validate_cost(cls, v: float | None) -> float | None:
        """Validate that cost is a non-negative number if provided."""
        if v is not None and v < 0:
            raise ValueError("Cost must be non-negative")
        return v

    @property
    def has_time(self) -> bool:
        """Check if the itinerary item has a specific time."""
        return self.scheduled_time is not None

    @property
    def is_activity(self) -> bool:
        """Check if the itinerary item is an activity."""
        return self.item_type == ItemType.ACTIVITY

    @property
    def is_meal(self) -> bool:
        """Check if the itinerary item is a meal."""
        return self.item_type == ItemType.MEAL

    @property
    def is_transport(self) -> bool:
        """Check if the itinerary item is transportation."""
        return self.item_type == ItemType.TRANSPORT

    @property
    def is_accommodation(self) -> bool:
        """Check if the itinerary item is accommodation."""
        return self.item_type == ItemType.ACCOMMODATION

    @property
    def formatted_time(self) -> str:
        """Get the formatted time for the itinerary item."""
        if self.scheduled_time:
            return self.scheduled_time.strftime("%H:%M")
        return "All day"

    @property
    def formatted_cost(self) -> str:
        """Get the formatted cost with currency symbol."""
        if self.cost is None:
            return "N/A"
        return f"${self.cost:.2f}"
