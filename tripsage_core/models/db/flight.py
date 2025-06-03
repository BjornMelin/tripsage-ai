"""Flight model for TripSage.

This module provides the Flight model with business logic validation,
used across different storage backends.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import (
    AirlineProvider,
    BookingStatus,
    DataSource,
)


class Flight(TripSageModel):
    """Flight model for TripSage.

    Attributes:
        id: Unique identifier for the flight
        trip_id: Reference to the associated trip
        origin: Origin airport code (IATA 3-letter code)
        destination: Destination airport code (IATA 3-letter code)
        airline: Airline provider
        departure_time: Departure date and time
        arrival_time: Arrival date and time
        price: Price in default currency
        booking_link: URL for booking this flight
        segment_number: For multi-segment flights, the order of this segment (1-based)
        search_timestamp: When this flight data was fetched
        booking_status: Status of the flight booking
        data_source: Source of the flight data
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    origin: str = Field(..., description="Origin airport code (IATA 3-letter code)")
    destination: str = Field(
        ..., description="Destination airport code (IATA 3-letter code)"
    )
    airline: AirlineProvider = Field(..., description="Airline provider")
    departure_time: datetime = Field(..., description="Departure date and time")
    arrival_time: datetime = Field(..., description="Arrival date and time")
    price: float = Field(..., description="Price in default currency")
    booking_link: Optional[str] = Field(None, description="URL for booking this flight")
    segment_number: int = Field(
        1, description="For multi-segment flights, the order of this segment (1-based)"
    )
    search_timestamp: datetime = Field(
        ..., description="When this flight data was fetched"
    )
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the flight booking"
    )
    data_source: DataSource = Field(..., description="Source of the flight data")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format (IATA 3-letter code)."""
        if not isinstance(v, str) or len(v) != 3 or not v.isalpha():
            raise ValueError("Airport code must be a 3-letter IATA code")
        return v.upper()

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is a positive number."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("segment_number")
    @classmethod
    def validate_segment_number(cls, v: int) -> int:
        """Validate that segment number is positive."""
        if v <= 0:
            raise ValueError("Segment number must be positive")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "Flight":
        """Validate that arrival_time is not before departure_time."""
        if self.arrival_time < self.departure_time:
            raise ValueError("Arrival time must not be before departure time")
        return self

    @model_validator(mode="after")
    def validate_different_airports(self) -> "Flight":
        """Validate that origin and destination are different."""
        if self.origin == self.destination:
            raise ValueError("Origin and destination must be different")
        return self

    @property
    def duration_minutes(self) -> float:
        """Get the flight duration in minutes."""
        delta = self.arrival_time - self.departure_time
        return delta.total_seconds() / 60

    @property
    def duration_hours(self) -> float:
        """Get the flight duration in hours."""
        return self.duration_minutes / 60

    @property
    def is_domestic(self) -> bool:
        """Check if the flight is domestic (origin and destination in the same country).

        Note: This is a simplistic implementation. In a production system,
        this would likely involve looking up the country for each airport code.
        """
        # For now, assuming US domestic if both codes start with 'K'
        # This is simplified - in production you would use a proper airport database
        return self.origin[0] == self.destination[0] == "K"

    @property
    def is_booked(self) -> bool:
        """Check if the flight is booked."""
        return self.booking_status == BookingStatus.BOOKED

    @property
    def is_canceled(self) -> bool:
        """Check if the flight is cancelled."""
        return self.booking_status == BookingStatus.CANCELLED

    @property
    def is_active(self) -> bool:
        """Check if the flight is in an active state."""
        return self.booking_status in [
            BookingStatus.VIEWED,
            BookingStatus.SAVED,
            BookingStatus.BOOKED,
        ]

    def book(self) -> None:
        """Book this flight."""
        self.booking_status = BookingStatus.BOOKED

    def cancel(self) -> None:
        """Cancel this flight booking."""
        if self.booking_status != BookingStatus.BOOKED:
            raise ValueError("Only booked flights can be cancelled")
        self.booking_status = BookingStatus.CANCELLED

    def can_cancel(self) -> bool:
        """Check if the flight can be canceled."""
        # Can only cancel if booked and the departure date hasn't passed
        if self.booking_status != BookingStatus.BOOKED:
            return False
        from datetime import datetime as datetime_type

        return datetime_type.now() < self.departure_time

    def update_status(self, new_status: BookingStatus) -> bool:
        """Update the flight status with validation.

        Args:
            new_status: The new status to set

        Returns:
            True if the status was updated, False if invalid transition
        """
        # Define valid status transitions
        valid_transitions = {
            BookingStatus.VIEWED: [
                BookingStatus.SAVED,
                BookingStatus.BOOKED,
                BookingStatus.CANCELLED,
            ],
            BookingStatus.SAVED: [
                BookingStatus.BOOKED,
                BookingStatus.CANCELLED,
                BookingStatus.VIEWED,
            ],
            BookingStatus.BOOKED: [BookingStatus.CANCELLED],
            BookingStatus.CANCELLED: [],  # Cannot change from cancelled
        }

        if new_status in valid_transitions.get(self.booking_status, []):
            self.booking_status = new_status
            return True
        return False
