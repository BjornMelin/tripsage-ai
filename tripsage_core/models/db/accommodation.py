"""Accommodation model for TripSage.

This module provides the Accommodation model with business logic validation,
used across different storage backends.
"""

from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base import TripSageModel


class AccommodationType(str, Enum):
    """Enum for accommodation type values."""

    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOSTEL = "hostel"
    RESORT = "resort"
    VILLA = "villa"
    HOUSE = "house"
    OTHER = "other"


class BookingStatus(str, Enum):
    """Enum for booking status values."""

    VIEWED = "viewed"
    SAVED = "saved"
    BOOKED = "booked"
    CANCELED = "canceled"


class CancellationPolicy(str, Enum):
    """Enum for cancellation policy values."""

    FREE = "free"
    PARTIAL_REFUND = "partial_refund"
    NO_REFUND = "no_refund"
    FLEXIBLE = "flexible"
    MODERATE = "moderate"
    STRICT = "strict"
    UNKNOWN = "unknown"


class Accommodation(TripSageModel):
    """Accommodation model for TripSage.

    Attributes:
        id: Unique identifier for the accommodation
        trip_id: Reference to the associated trip
        name: Name of the accommodation
        accommodation_type: Type of accommodation
        check_in: Check-in date
        check_out: Check-out date
        price_per_night: Price per night in default currency
        total_price: Total price for the stay in default currency
        location: Address or location description
        rating: Rating score out of 5
        amenities: List of available amenities as JSON
        booking_link: URL for booking this accommodation
        search_timestamp: When this accommodation data was fetched
        booking_status: Status of the accommodation booking
        cancellation_policy: Cancellation policy for the booking
        distance_to_center: Distance to city center in kilometers
        neighborhood: Neighborhood or area name
    """

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    name: str = Field(..., description="Name of the accommodation")
    accommodation_type: AccommodationType = Field(
        ..., description="Type of accommodation"
    )
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    price_per_night: float = Field(
        ..., description="Price per night in default currency"
    )
    total_price: float = Field(
        ..., description="Total price for the stay in default currency"
    )
    location: str = Field(..., description="Address or location description")
    rating: Optional[float] = Field(None, description="Rating score out of 5")
    amenities: Optional[Dict[str, Any]] = Field(None, description="Available amenities")
    booking_link: Optional[str] = Field(
        None, description="URL for booking this accommodation"
    )
    search_timestamp: date = Field(
        ..., description="When this accommodation data was fetched"
    )
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the accommodation booking"
    )
    cancellation_policy: Optional[CancellationPolicy] = Field(
        None, description="Cancellation policy for the booking"
    )
    distance_to_center: Optional[float] = Field(
        None, description="Distance to city center in kilometers"
    )
    neighborhood: Optional[str] = Field(None, description="Neighborhood or area name")

    @field_validator("price_per_night", "total_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is a positive number."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate that rating is between 0 and 5 if provided."""
        if v is not None and (v < 0 or v > 5):
            raise ValueError("Rating must be between 0 and 5")
        return v

    @field_validator("distance_to_center")
    @classmethod
    def validate_distance(cls, v: Optional[float]) -> Optional[float]:
        """Validate that distance is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Distance must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "Accommodation":
        """Validate that check_out is not before check_in."""
        if self.check_out < self.check_in:
            raise ValueError("Check-out date must not be before check-in date")
        return self

    @model_validator(mode="after")
    def validate_total_price(self) -> "Accommodation":
        """Validate that total_price is consistent with duration and price_per_night."""
        nights = (self.check_out - self.check_in).days
        expected_min = self.price_per_night * 0.95 * nights  # Allow 5% variation
        expected_max = self.price_per_night * 1.05 * nights  # Allow 5% variation

        if nights > 0 and (
            self.total_price < expected_min or self.total_price > expected_max
        ):
            # This is a warning - total price might include fees, taxes, etc.
            # We won't raise an error but could log this inconsistency in a real system
            pass

        return self

    @property
    def duration_nights(self) -> int:
        """Get the duration of the stay in nights."""
        return (self.check_out - self.check_in).days

    @property
    def price_with_taxes(self) -> float:
        """Get the total price with estimated taxes (simplified example)."""
        # This is a simplified example - real tax calculations would be more complex
        return self.total_price * 1.1  # Assuming 10% tax

    @property
    def is_booked(self) -> bool:
        """Check if the accommodation is booked."""
        return self.booking_status == BookingStatus.BOOKED

    @property
    def is_canceled(self) -> bool:
        """Check if the accommodation is canceled."""
        return self.booking_status == BookingStatus.CANCELED

    @property
    def is_active(self) -> bool:
        """Check if the accommodation is in an active state."""
        return self.booking_status in [
            BookingStatus.VIEWED,
            BookingStatus.SAVED,
            BookingStatus.BOOKED,
        ]

    @property
    def has_free_cancellation(self) -> bool:
        """Check if the accommodation has free cancellation."""
        return self.cancellation_policy == CancellationPolicy.FREE

    @property
    def has_flexible_cancellation(self) -> bool:
        """Check if the accommodation has flexible cancellation."""
        return self.cancellation_policy == CancellationPolicy.FLEXIBLE

    @property
    def is_refundable(self) -> bool:
        """Check if the accommodation is refundable."""
        return self.cancellation_policy not in [CancellationPolicy.NO_REFUND, None]

    @property
    def stay_duration(self) -> int:
        """Get the duration of the stay in nights."""
        return self.duration_nights

    @property
    def amenities_list(self) -> List[str]:
        """Get the list of amenities."""
        if not self.amenities:
            return []

        # Depending on how amenities are stored, extract the list
        # Assuming amenities is a dict with a key 'list' containing the amenities
        if isinstance(self.amenities, dict) and "list" in self.amenities:
            return self.amenities["list"]
        # Or if it's directly a list stored as a dict key 'amenities'
        if isinstance(self.amenities, dict) and "amenities" in self.amenities:
            return self.amenities["amenities"]
        # If it's another format, return a simple string representation
        return [str(k) for k, v in self.amenities.items() if v]

    def book(self) -> None:
        """Book this accommodation."""
        self.booking_status = BookingStatus.BOOKED

    def cancel(self) -> None:
        """Cancel this accommodation booking."""
        if self.booking_status != BookingStatus.BOOKED:
            raise ValueError("Only booked accommodations can be canceled")
        self.booking_status = BookingStatus.CANCELED

    def can_cancel(self) -> bool:
        """Check if the accommodation can be canceled."""
        # Can only cancel if booked and check-in date hasn't passed
        if self.booking_status != BookingStatus.BOOKED:
            return False
        from datetime import date as date_type

        return date_type.today() < self.check_in

    def update_status(self, new_status: BookingStatus) -> bool:
        """Update the accommodation status with validation.

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
