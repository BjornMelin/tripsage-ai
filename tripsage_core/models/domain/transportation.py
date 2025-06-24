"""
Core transportation domain models for TripSage.

This module contains the core business domain models for transportation-related
entities. These models represent the essential transportation data structures
independent of storage implementation or API specifics.
"""

from typing import List, Optional

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageDomainModel
from tripsage_core.models.schemas_common.enums import TransportationType


class TransportationProvider(TripSageDomainModel):
    """Transportation provider information."""

    name: str = Field(..., description="Provider name")
    code: Optional[str] = Field(None, description="Provider code")
    contact_info: Optional[str] = Field(None, description="Contact information")
    rating: Optional[float] = Field(None, description="Provider rating")


class TransportationVehicle(TripSageDomainModel):
    """Vehicle information for transportation."""

    type: str = Field(..., description="Vehicle type")
    make: Optional[str] = Field(None, description="Vehicle make")
    model: Optional[str] = Field(None, description="Vehicle model")
    license_plate: Optional[str] = Field(None, description="License plate")
    capacity: Optional[int] = Field(None, description="Passenger capacity")
    amenities: List[str] = Field([], description="Available amenities")

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: Optional[int]) -> Optional[int]:
        """Validate that capacity is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Capacity must be positive")
        return v


class TransportationLocation(TripSageDomainModel):
    """Location information for transportation."""

    address: Optional[str] = Field(None, description="Full address")
    name: Optional[str] = Field(None, description="Location name")
    city: str = Field(..., description="City")
    state: Optional[str] = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/zip code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


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
    provider: Optional[TransportationProvider] = Field(
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
    vehicle: Optional[TransportationVehicle] = Field(
        None, description="Vehicle information"
    )
    distance_km: Optional[float] = Field(None, description="Distance in kilometers")
    duration_minutes: Optional[int] = Field(None, description="Duration in minutes")
    booking_url: Optional[str] = Field(None, description="URL for booking")
    cancellation_policy: Optional[str] = Field(None, description="Cancellation policy")

    # Source and tracking information
    source: Optional[str] = Field(
        None, description="Source of the offer (e.g., 'uber', 'lyft', 'rental_cars')"
    )
    search_id: Optional[str] = Field(None, description="Associated search ID")
    expires_at: Optional[str] = Field(
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
    def validate_distance(cls, v: Optional[float]) -> Optional[float]:
        """Validate that distance is non-negative if provided."""
        if v is not None and v < 0:
            raise ValueError("Distance must be non-negative")
        return v

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Validate that duration is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v
