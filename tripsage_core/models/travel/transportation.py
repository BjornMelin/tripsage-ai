"""Transportation domain models.

This module consolidates all transportation-related models including domain logic
and database representations following Pydantic v2 best practices.
"""

from datetime import datetime, timedelta
from typing import Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base_core_model import TripSageDomainModel, TripSageModel
from tripsage_core.models.schemas_common.enums import (
    BookingStatus,
    TransportationType,
)
from tripsage_core.models.schemas_common.geographic import Coordinates


class TransportationOffer(TripSageDomainModel):
    """Domain model for transportation offers with business logic."""

    transportation_type: TransportationType = Field(
        ..., description="Type of transportation"
    )
    provider: str = Field(..., description="Transportation provider")
    pickup_location: str = Field(..., description="Pickup location description")
    dropoff_location: str = Field(..., description="Dropoff location description")
    pickup_time: datetime = Field(..., description="Pickup date and time")
    dropoff_time: datetime = Field(..., description="Dropoff date and time")
    price: float = Field(..., description="Price for the transportation")
    capacity: Optional[int] = Field(None, description="Maximum passenger capacity")
    vehicle_type: Optional[str] = Field(None, description="Specific vehicle type")
    amenities: Optional[list[str]] = Field(None, description="Available amenities")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is positive."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: Optional[int]) -> Optional[int]:
        """Validate that capacity is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Capacity must be positive")
        return v

    @model_validator(mode="after")
    def validate_times(self) -> "TransportationOffer":
        """Validate that dropoff_time is after pickup_time."""
        if self.dropoff_time <= self.pickup_time:
            raise ValueError("Dropoff time must be after pickup time")
        return self

    @property
    def duration(self) -> timedelta:
        """Get transportation duration."""
        return self.dropoff_time - self.pickup_time

    @property
    def duration_hours(self) -> float:
        """Get transportation duration in hours."""
        return self.duration.total_seconds() / 3600

    @property
    def price_per_hour(self) -> float:
        """Get price per hour of transportation."""
        return self.price / self.duration_hours if self.duration_hours > 0 else 0


class Transportation(TripSageModel):
    """Database model for transportation bookings and search results."""

    id: Optional[int] = Field(None, description="Unique identifier")
    trip_id: int = Field(..., description="Reference to the associated trip")
    transportation_type: TransportationType = Field(
        ..., description="Type of transportation"
    )
    provider: Optional[str] = Field(
        None, description="Name of the transportation provider"
    )
    pickup_location: str = Field(..., description="Pickup location description")
    dropoff_location: str = Field(..., description="Dropoff location description")
    pickup_coordinates: Optional[Coordinates] = Field(
        None, description="Pickup location coordinates"
    )
    dropoff_coordinates: Optional[Coordinates] = Field(
        None, description="Dropoff location coordinates"
    )
    pickup_date: datetime = Field(..., description="Pickup date and time")
    dropoff_date: datetime = Field(..., description="Dropoff date and time")
    price: float = Field(..., description="Price in default currency")
    booking_link: Optional[str] = Field(
        None, description="URL for booking this transportation"
    )
    confirmation_number: Optional[str] = Field(
        None, description="Booking confirmation number"
    )
    vehicle_info: Optional[str] = Field(
        None, description="Vehicle information (make, model, license plate, etc.)"
    )
    driver_info: Optional[str] = Field(
        None, description="Driver information (name, contact, etc.)"
    )
    notes: Optional[str] = Field(None, description="Additional notes or information")
    booking_status: BookingStatus = Field(
        BookingStatus.VIEWED, description="Status of the transportation booking"
    )
    search_timestamp: Optional[datetime] = Field(
        None, description="When this transportation data was fetched"
    )
    amenities: Optional[list[str]] = Field(None, description="Available amenities")
    max_passengers: Optional[int] = Field(
        None, description="Maximum passenger capacity"
    )
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is a positive number."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("max_passengers")
    @classmethod
    def validate_max_passengers(cls, v: Optional[int]) -> Optional[int]:
        """Validate that max_passengers is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Max passengers must be positive")
        return v

    @field_validator("distance_km")
    @classmethod
    def validate_distance(cls, v: Optional[float]) -> Optional[float]:
        """Validate that distance is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Distance must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "Transportation":
        """Validate that dropoff_date is not before pickup_date."""
        if self.dropoff_date < self.pickup_date:
            raise ValueError("Dropoff date must not be before pickup date")
        return self

    @property
    def duration(self) -> timedelta:
        """Get the duration of the transportation."""
        return self.dropoff_date - self.pickup_date

    @property
    def duration_hours(self) -> float:
        """Get the duration of the transportation in hours."""
        return self.duration.total_seconds() / 3600

    @property
    def duration_minutes(self) -> int:
        """Get the duration of the transportation in minutes."""
        return int(self.duration.total_seconds() / 60)

    @property
    def formatted_duration(self) -> str:
        """Get a human-readable duration string."""
        total_seconds = int(self.duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

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

    @property
    def route(self) -> str:
        """Get the transportation route as a string."""
        return f"{self.pickup_location} → {self.dropoff_location}"

    @property
    def average_speed_kmh(self) -> Optional[float]:
        """Calculate average speed in km/h if distance is available."""
        if self.distance_km is None or self.duration_hours == 0:
            return None
        return self.distance_km / self.duration_hours

    @property
    def price_per_km(self) -> Optional[float]:
        """Calculate price per kilometer if distance is available."""
        if self.distance_km is None or self.distance_km == 0:
            return None
        return self.price / self.distance_km

    @property
    def price_per_hour(self) -> float:
        """Calculate price per hour."""
        if self.duration_hours == 0:
            return self.price
        return self.price / self.duration_hours

    @property
    def has_confirmation(self) -> bool:
        """Check if the transportation has a confirmation number."""
        return bool(self.confirmation_number)

    @property
    def is_rideshare(self) -> bool:
        """Check if this is a rideshare transportation."""
        return self.transportation_type == TransportationType.RIDESHARE

    @property
    def is_public_transit(self) -> bool:
        """Check if this is public transit."""
        return self.transportation_type == TransportationType.PUBLIC_TRANSIT

    @property
    def is_rental(self) -> bool:
        """Check if this is a rental (car, bike, etc.)."""
        return self.transportation_type in [
            TransportationType.CAR_RENTAL,
            TransportationType.BIKE_RENTAL,
        ]

    def can_cancel(self) -> bool:
        """Check if the transportation can be canceled."""
        # Can only cancel if booked and the pickup date hasn't passed
        if self.booking_status != BookingStatus.BOOKED:
            return False
        from datetime import datetime as datetime_type

        return datetime_type.now() < self.pickup_date

    def book(self) -> None:
        """Book this transportation."""
        self.booking_status = BookingStatus.BOOKED

    def cancel(self) -> None:
        """Cancel this transportation booking."""
        if self.booking_status != BookingStatus.BOOKED:
            raise ValueError("Only booked transportation can be canceled")
        self.booking_status = BookingStatus.CANCELED

    def save(self) -> None:
        """Save this transportation for later."""
        if self.booking_status == BookingStatus.VIEWED:
            self.booking_status = BookingStatus.SAVED

    def set_confirmation(self, confirmation_number: str) -> None:
        """Set the confirmation number for the booking."""
        if not self.is_booked:
            raise ValueError("Transportation must be booked to set confirmation")
        self.confirmation_number = confirmation_number

    def add_amenity(self, amenity: str) -> None:
        """Add an amenity to the transportation."""
        if self.amenities is None:
            self.amenities = []
        if amenity not in self.amenities:
            self.amenities.append(amenity)

    def remove_amenity(self, amenity: str) -> bool:
        """Remove an amenity from the transportation."""
        if self.amenities and amenity in self.amenities:
            self.amenities.remove(amenity)
            return True
        return False

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
