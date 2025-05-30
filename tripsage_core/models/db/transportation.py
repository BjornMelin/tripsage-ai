"""Transportation model for TripSage.

This module provides the Transportation model with business logic validation,
used across different storage backends.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageModel


class TransportationType(str, Enum):
    """Enum for transportation type values."""

    CAR_RENTAL = "car_rental"
    PUBLIC_TRANSIT = "public_transit"
    TAXI = "taxi"
    SHUTTLE = "shuttle"
    FERRY = "ferry"
    TRAIN = "train"
    BUS = "bus"
    OTHER = "other"


class BookingStatus(str, Enum):
    """Enum for booking status values."""

    VIEWED = "viewed"
    SAVED = "saved"
    BOOKED = "booked"
    CANCELED = "canceled"


class Transportation(TripSageModel):
    """Transportation model for TripSage.

    Attributes:
        id: Unique identifier for the transportation
        trip_id: Reference to the associated trip
        transportation_type: Type of transportation
        provider: Name of the transportation provider
        pickup_date: Pickup date and time
        dropoff_date: Dropoff date and time
        price: Price in default currency
        notes: Additional notes or information
        booking_status: Status of the transportation booking
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    transportation_type: TransportationType = Field(
        ..., description="Type of transportation"
    )
    provider: Optional[str] = Field(
        None, description="Name of the transportation provider"
    )
    pickup_date: datetime = Field(..., description="Pickup date and time")
    dropoff_date: datetime = Field(..., description="Dropoff date and time")
    price: float = Field(..., description="Price in default currency")
    notes: Optional[str] = Field(None, description="Additional notes or information")
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the transportation booking"
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is a positive number."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "Transportation":
        """Validate that dropoff_date is not before pickup_date."""
        if self.dropoff_date < self.pickup_date:
            raise ValueError("Dropoff date must not be before pickup date")
        return self

    @property
    def duration_hours(self) -> float:
        """Get the duration of the transportation in hours."""
        delta = self.dropoff_date - self.pickup_date
        return delta.total_seconds() / 3600

    @property
    def is_booked(self) -> bool:
        """Check if the transportation is booked."""
        return self.booking_status == BookingStatus.BOOKED

    @property
    def is_canceled(self) -> bool:
        """Check if the transportation is canceled."""
        return self.booking_status == BookingStatus.CANCELED

    @property
    def is_active(self) -> bool:
        """Check if the transportation is in an active state."""
        return self.booking_status in [
            BookingStatus.VIEWED,
            BookingStatus.SAVED,
            BookingStatus.BOOKED,
        ]

    def can_cancel(self) -> bool:
        """Check if the transportation can be canceled."""
        # Can only cancel if booked and the pickup date hasn't passed
        if self.booking_status != BookingStatus.BOOKED:
            return False
        from datetime import datetime as datetime_type

        return datetime_type.now() < self.pickup_date

    def update_status(self, new_status: BookingStatus) -> bool:
        """Update the transportation status with validation.

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
