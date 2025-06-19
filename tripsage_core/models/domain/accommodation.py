"""
Core accommodation domain models for TripSage.

This module contains the core business domain models for accommodation-related
entities. These models represent the essential accommodation data structures
independent of storage implementation or API specifics.
"""

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageDomainModel
from tripsage_core.models.schemas_common.enums import AccommodationType as PropertyType


class AccommodationAmenity(TripSageDomainModel):
    """Amenity offered by an accommodation."""

    name: str = Field(..., description="Amenity name")
    category: str | None = Field(None, description="Amenity category")
    description: str | None = Field(None, description="Amenity description")


class AccommodationImage(TripSageDomainModel):
    """Image of an accommodation."""

    url: str = Field(..., description="Image URL")
    caption: str | None = Field(None, description="Image caption")
    is_primary: bool = Field(False, description="Whether this is the primary image")


class AccommodationLocation(TripSageDomainModel):
    """Location information for an accommodation."""

    address: str | None = Field(None, description="Full address")
    city: str = Field(..., description="City")
    state: str | None = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    postal_code: str | None = Field(None, description="Postal/zip code")
    latitude: float | None = Field(None, description="Latitude coordinate")
    longitude: float | None = Field(None, description="Longitude coordinate")
    neighborhood: str | None = Field(None, description="Neighborhood name")


class AccommodationListing(TripSageDomainModel):
    """Core accommodation listing business entity.

    This represents the canonical accommodation listing model used throughout
    the TripSage system. It contains all essential information about an
    accommodation property independent of the source or storage mechanism.
    """

    id: str = Field(..., description="Listing ID")
    name: str = Field(..., description="Listing name")
    description: str | None = Field(None, description="Listing description")
    property_type: PropertyType = Field(..., description="Property type")
    location: AccommodationLocation = Field(..., description="Location information")
    price_per_night: float = Field(..., description="Price per night")
    currency: str = Field(..., description="Currency code")
    rating: float | None = Field(None, description="Guest rating (0-5)")
    review_count: int | None = Field(None, description="Number of reviews")
    amenities: list[AccommodationAmenity] = Field([], description="Available amenities")
    images: list[AccommodationImage] = Field([], description="Property images")
    max_guests: int = Field(..., description="Maximum number of guests")
    bedrooms: int | None = Field(None, description="Number of bedrooms")
    beds: int | None = Field(None, description="Number of beds")
    bathrooms: float | None = Field(None, description="Number of bathrooms")
    check_in_time: str | None = Field(None, description="Check-in time")
    check_out_time: str | None = Field(None, description="Check-out time")
    cancellation_policy: str | None = Field(None, description="Cancellation policy")
    host_id: str | None = Field(None, description="Host ID")
    host_name: str | None = Field(None, description="Host name")
    host_rating: float | None = Field(None, description="Host rating")
    total_price: float | None = Field(
        None, description="Total price for the stay (if dates provided)"
    )
    url: str | None = Field(None, description="URL to the listing")
    source: str | None = Field(
        None, description="Source of the listing (e.g., 'airbnb', 'booking')"
    )
