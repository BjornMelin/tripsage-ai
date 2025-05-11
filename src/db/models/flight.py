"""
Flight model for TripSage.

This module provides the Flight model for the TripSage database.
"""

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field, field_validator, model_validator

from src.db.models.base import BaseDBModel


class BookingStatus(str, Enum):
    """Enum for booking status values."""

    VIEWED = "viewed"
    SAVED = "saved"
    BOOKED = "booked"
    CANCELED = "canceled"


class Flight(BaseDBModel):
    """
    Flight model for TripSage.

    Attributes:
        id: Unique identifier for the flight
        trip_id: Reference to the associated trip
        origin: Origin airport or city
        destination: Destination airport or city
        airline: Name of the airline
        departure_time: Scheduled departure time with timezone
        arrival_time: Scheduled arrival time with timezone
        price: Price of the flight in default currency
        booking_link: URL for booking the flight
        segment_number: Segment number for multi-leg flights
        search_timestamp: When this flight option was found
        booking_status: Status of the flight booking (viewed, saved, booked, canceled)
        data_source: Source of the flight data (API provider)
    """

    __tablename__: ClassVar[str] = "flights"

    trip_id: int = Field(..., description="Reference to the associated trip")
    origin: str = Field(..., description="Origin airport or city")
    destination: str = Field(..., description="Destination airport or city")
    airline: Optional[str] = Field(None, description="Name of the airline")
    departure_time: datetime = Field(
        ..., description="Scheduled departure time with timezone"
    )
    arrival_time: datetime = Field(
        ..., description="Scheduled arrival time with timezone"
    )
    price: float = Field(..., description="Price of the flight in default currency")
    booking_link: Optional[str] = Field(None, description="URL for booking the flight")
    segment_number: Optional[int] = Field(
        None, description="Segment number for multi-leg flights"
    )
    search_timestamp: Optional[datetime] = Field(
        default_factory=datetime.now, description="When this flight option was found"
    )
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the flight booking"
    )
    data_source: Optional[str] = Field(
        None, description="Source of the flight data (API provider)"
    )

    @model_validator(mode="after")
    def validate_times(self) -> "Flight":
        """Validate that arrival_time is after departure_time."""
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be after departure time")
        return self

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is non-negative."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @property
    def duration_minutes(self) -> int:
        """Get the flight duration in minutes."""
        delta = self.arrival_time - self.departure_time
        return int(delta.total_seconds() / 60)

    @property
    def duration_formatted(self) -> str:
        """Get the flight duration formatted as HH:MM."""
        minutes = self.duration_minutes
        hours = minutes // 60
        remaining_minutes = minutes % 60
        return f"{hours}h {remaining_minutes}m"

    @property
    def is_international(self) -> bool:
        """
        Determine if the flight is likely international based on origin/destination.

        This is a simplistic implementation and would need to be improved with
        actual airport code mappings in a production system.
        """
        # Simple check - if origin and destination are 3-letter codes (IATA),
        # and they start with different characters, consider it international
        # This is obviously not accurate but serves as a placeholder
        if (
            len(self.origin) == 3
            and len(self.destination) == 3
            and self.origin[0] != self.destination[0]
        ):
            return True
        return False

    def to_dict(self, exclude_none: bool = True) -> Dict[str, Any]:
        """Convert the flight to a dictionary for database operations."""
        data = super().to_dict(exclude_none=exclude_none)

        # Convert enum values to strings for the database
        if "booking_status" in data and isinstance(
            data["booking_status"], BookingStatus
        ):
            data["booking_status"] = data["booking_status"].value

        return data

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "Flight":
        """Create a Flight instance from a database row."""
        # Convert string booking_status to enum value
        if "booking_status" in row and isinstance(row["booking_status"], str):
            try:
                row["booking_status"] = BookingStatus(row["booking_status"])
            except ValueError:
                # Handle invalid booking_status values
                row["booking_status"] = BookingStatus.VIEWED

        return super().from_row(row)
