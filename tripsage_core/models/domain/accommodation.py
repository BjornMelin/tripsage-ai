"""
Core accommodation domain models for TripSage.

This module contains the core business domain models for accommodation-related
entities. These models represent the essential accommodation data structures
independent of storage implementation or API specifics.
"""

from typing import List, Optional

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageDomainModel
from tripsage_core.models.schemas_common.enums import AccommodationType as PropertyType


class AccommodationAmenity(TripSageDomainModel):
    """Amenity offered by an accommodation."""

    name: str = Field(..., description="Amenity name")
    category: Optional[str] = Field(None, description="Amenity category")
    description: Optional[str] = Field(None, description="Amenity description")


class AccommodationImage(TripSageDomainModel):
    """Image of an accommodation."""

    url: str = Field(..., description="Image URL")
    caption: Optional[str] = Field(None, description="Image caption")
    is_primary: bool = Field(False, description="Whether this is the primary image")


class AccommodationLocation(TripSageDomainModel):
    """Location information for an accommodation."""

    address: Optional[str] = Field(None, description="Full address")
    city: str = Field(..., description="City")
    state: Optional[str] = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/zip code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")


class AccommodationListing(TripSageDomainModel):
    """Core accommodation listing business entity.

    This represents the canonical accommodation listing model used throughout
    the TripSage system. It contains all essential information about an
    accommodation property independent of the source or storage mechanism.
    """

    id: str = Field(..., description="Listing ID")
    name: str = Field(..., description="Listing name")
    description: Optional[str] = Field(None, description="Listing description")
    property_type: PropertyType = Field(..., description="Property type")
    location: AccommodationLocation = Field(..., description="Location information")
    price_per_night: float = Field(..., description="Price per night")
    currency: str = Field(..., description="Currency code")
    rating: Optional[float] = Field(None, description="Guest rating (0-5)")
    review_count: Optional[int] = Field(None, description="Number of reviews")
    amenities: List[AccommodationAmenity] = Field([], description="Available amenities")
    images: List[AccommodationImage] = Field([], description="Property images")
    max_guests: int = Field(..., description="Maximum number of guests")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    beds: Optional[int] = Field(None, description="Number of beds")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    check_in_time: Optional[str] = Field(None, description="Check-in time")
    check_out_time: Optional[str] = Field(None, description="Check-out time")
    cancellation_policy: Optional[str] = Field(None, description="Cancellation policy")
    host_id: Optional[str] = Field(None, description="Host ID")
    host_name: Optional[str] = Field(None, description="Host name")
    host_rating: Optional[float] = Field(None, description="Host rating")
    total_price: Optional[float] = Field(
        None, description="Total price for the stay (if dates provided)"
    )
    url: Optional[str] = Field(None, description="URL to the listing")
    source: Optional[str] = Field(
        None, description="Source of the listing (e.g., 'airbnb', 'booking')"
    )
