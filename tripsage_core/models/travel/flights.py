"""Flight domain models.

This module consolidates all flight-related models including domain logic
and database representations following Pydantic v2 best practices.
"""

from datetime import datetime, timedelta
from typing import Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageDomainModel, TripSageModel
from tripsage_core.models.schemas_common.enums import (
    AirlineProvider,
    BookingStatus,
    CabinClass,
    DataSource,
    FareType,
)


class FlightOffer(TripSageDomainModel):
    """Domain model for flight offers with business logic."""

    origin: str = Field(..., description="Origin airport code (IATA)")
    destination: str = Field(..., description="Destination airport code (IATA)")
    airline: AirlineProvider = Field(..., description="Airline provider")
    departure_time: datetime = Field(..., description="Departure date and time")
    arrival_time: datetime = Field(..., description="Arrival date and time")
    price: float = Field(..., description="Flight price")
    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")
    fare_type: FareType = Field(FareType.ECONOMY_STANDARD, description="Fare type")
    available_seats: Optional[int] = Field(None, description="Available seats")
    flight_number: Optional[str] = Field(None, description="Flight number")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_codes(cls, v: str) -> str:
        """Validate airport codes are 3 characters."""
        if len(v) != 3:
            raise ValueError("Airport codes must be 3 characters")
        return v.upper()

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is positive."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_flight_times(self) -> "FlightOffer":
        """Validate that arrival is after departure."""
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be after departure time")
        return self

    @property
    def duration(self) -> timedelta:
        """Get flight duration."""
        return self.arrival_time - self.departure_time

    @property
    def duration_hours(self) -> float:
        """Get flight duration in hours."""
        return self.duration.total_seconds() / 3600


class Flight(TripSageModel):
    """Database model for flight bookings and search results."""

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
    search_timestamp: Optional[datetime] = Field(
        None, description="When this flight data was fetched"
    )
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the flight booking"
    )
    data_source: DataSource = Field(..., description="Source of the flight data")
    flight_number: Optional[str] = Field(None, description="Flight number")
    cabin_class: Optional[str] = Field(None, description="Cabin class")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_codes(cls, v: str) -> str:
        """Validate that airport codes are 3 characters and uppercase."""
        if len(v) != 3:
            raise ValueError("Airport codes must be 3 characters")
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
        if v < 1:
            raise ValueError("Segment number must be at least 1")
        return v

    @model_validator(mode="after")
    def validate_flight_times(self) -> "Flight":
        """Validate that arrival time is after departure time."""
        if self.arrival_time <= self.departure_time:
            raise ValueError("Arrival time must be after departure time")
        return self

    @property
    def duration(self) -> timedelta:
        """Get the flight duration."""
        return self.arrival_time - self.departure_time

    @property
    def formatted_duration(self) -> str:
        """Get a human-readable duration string."""
        total_seconds = int(self.duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours}h {minutes}m"

    @property
    def is_booked(self) -> bool:
        """Check if the flight is booked."""
        return self.booking_status == BookingStatus.BOOKED

    @property
    def is_canceled(self) -> bool:
        """Check if the flight is canceled."""
        return self.booking_status == BookingStatus.CANCELED

    @property
    def route(self) -> str:
        """Get the flight route as a string."""
        return f"{self.origin} → {self.destination}"

    def book(self) -> None:
        """Book this flight."""
        self.booking_status = BookingStatus.BOOKED

    def cancel(self) -> None:
        """Cancel this flight booking."""
        if self.booking_status != BookingStatus.BOOKED:
            raise ValueError("Only booked flights can be canceled")
        self.booking_status = BookingStatus.CANCELED

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
                BookingStatus.CANCELED,
            ],
            BookingStatus.SAVED: [
                BookingStatus.BOOKED,
                BookingStatus.CANCELED,
                BookingStatus.VIEWED,
            ],
            BookingStatus.BOOKED: [BookingStatus.CANCELED],
            BookingStatus.CANCELED: [],  # Cannot change from canceled
        }

        if new_status in valid_transitions.get(self.booking_status, []):
            self.booking_status = new_status
            return True
        return False
