"""
Core transportation domain models for TripSage.

This module contains the core business domain models for transportation-related
entities. These models represent the essential transportation data structures
independent of storage implementation or API specifics.
"""

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageDomainModel
from tripsage_core.models.schemas_common.enums import TransportationType


class TransportationProvider(TripSageDomainModel):
    """Transportation provider information."""

    name: str = Field(..., description="Provider name")
    code: str | None = Field(None, description="Provider code")
    contact_info: str | None = Field(None, description="Contact information")
    rating: float | None = Field(None, description="Provider rating")


class TransportationVehicle(TripSageDomainModel):
    """Vehicle information for transportation."""

    type: str = Field(..., description="Vehicle type")
    make: str | None = Field(None, description="Vehicle make")
    model: str | None = Field(None, description="Vehicle model")
    license_plate: str | None = Field(None, description="License plate")
    capacity: int | None = Field(None, description="Passenger capacity")
    amenities: list[str] = Field([], description="Available amenities")

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: int | None) -> int | None:
        """Validate that capacity is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Capacity must be positive")
        return v


class TransportationLocation(TripSageDomainModel):
    """Location information for transportation."""

    address: str | None = Field(None, description="Full address")
    name: str | None = Field(None, description="Location name")
    city: str = Field(..., description="City")
    state: str | None = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    postal_code: str | None = Field(None, description="Postal/zip code")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")


class TransportationOffer(TripSageDomainModel):
    """Core transportation offer business entity.

    This represents the canonical transportation offer model used throughout
    the TripSage system. It contains all essential information about a
    transportation option independent of the source or storage mechanism.
    """

    id: str = Field(..., description="Offer ID")
    transportation_type: TransportationType = Field(
        ..., description="Type of transportation"
    )
    provider: TransportationProvider | None = Field(
        None, description="Transportation provider"
    )
    pickup_location: TransportationLocation = Field(..., description="Pickup location")
    dropoff_location: TransportationLocation = Field(
        ..., description="Dropoff location"
    )
    pickup_datetime: str = Field(..., description="Pickup date and time (ISO format)")
    dropoff_datetime: str = Field(..., description="Dropoff date and time (ISO format)")
    price: float = Field(..., description="Price for the transportation")
    currency: str = Field(..., description="Currency code")
    vehicle: TransportationVehicle | None = Field(
        None, description="Vehicle information"
    )
    distance_km: float | None = Field(None, description="Distance in kilometers")
    duration_minutes: int | None = Field(None, description="Duration in minutes")
    booking_url: str | None = Field(None, description="URL for booking")
    cancellation_policy: str | None = Field(None, description="Cancellation policy")

    # Source and tracking information
    source: str | None = Field(
        None, description="Source of the offer (e.g., 'uber', 'lyft', 'rental_cars')"
    )
    search_id: str | None = Field(None, description="Associated search ID")
    expires_at: str | None = Field(
        None, description="Offer expiration timestamp (ISO format)"
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate that price is positive."""
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("distance_km")
    @classmethod
    def validate_distance(cls, v: float | None) -> float | None:
        """Validate that distance is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Distance must be non-negative")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: int | None) -> int | None:
        """Validate that duration is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v
