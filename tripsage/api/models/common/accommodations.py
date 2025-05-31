"""Accommodation common models using Pydantic V2.

This module defines shared Pydantic models for accommodation-related data structures.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from tripsage_core.models.schemas_common import (
    AccommodationType as PropertyType,
)
from tripsage_core.models.schemas_common import (
    CancellationPolicy,
)


class AccommodationAmenity(BaseModel):
    """Model for an accommodation amenity."""

    name: str = Field(description="Amenity name")
    category: Optional[str] = Field(default=None, description="Amenity category")
    description: Optional[str] = Field(default=None, description="Amenity description")


class AccommodationImage(BaseModel):
    """Model for an accommodation image."""

    url: str = Field(description="Image URL")
    caption: Optional[str] = Field(default=None, description="Image caption")
    is_primary: bool = Field(
        default=False, description="Whether this is the primary image"
    )


class AccommodationLocation(BaseModel):
    """Model for an accommodation location."""

    address: Optional[str] = Field(default=None, description="Full address")
    city: str = Field(description="City")
    state: Optional[str] = Field(default=None, description="State/province")
    country: str = Field(description="Country")
    postal_code: Optional[str] = Field(default=None, description="Postal/zip code")
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    neighborhood: Optional[str] = Field(default=None, description="Neighborhood name")
    distance_to_center: Optional[float] = Field(
        default=None, description="Distance to city center in kilometers"
    )


class AccommodationListing(BaseModel):
    """Model for an accommodation listing."""

    id: str = Field(description="Listing ID")
    name: str = Field(description="Listing name")
    description: Optional[str] = Field(default=None, description="Listing description")
    property_type: PropertyType = Field(description="Property type")
    location: AccommodationLocation = Field(description="Location information")
    price_per_night: float = Field(description="Price per night")
    currency: str = Field(description="Currency code")
    rating: Optional[float] = Field(default=None, description="Guest rating (0-5)")
    review_count: Optional[int] = Field(default=None, description="Number of reviews")
    amenities: List[AccommodationAmenity] = Field(
        default=[], description="Available amenities"
    )
    images: List[AccommodationImage] = Field(default=[], description="Property images")
    max_guests: int = Field(description="Maximum number of guests")
    bedrooms: Optional[int] = Field(default=None, description="Number of bedrooms")
    beds: Optional[int] = Field(default=None, description="Number of beds")
    bathrooms: Optional[float] = Field(default=None, description="Number of bathrooms")
    check_in_time: Optional[str] = Field(default=None, description="Check-in time")
    check_out_time: Optional[str] = Field(default=None, description="Check-out time")
    cancellation_policy: Optional[CancellationPolicy] = Field(
        default=None, description="Cancellation policy"
    )
    host_id: Optional[str] = Field(default=None, description="Host ID")
    host_name: Optional[str] = Field(default=None, description="Host name")
    host_rating: Optional[float] = Field(default=None, description="Host rating")
    total_price: Optional[float] = Field(
        default=None, description="Total price for the stay (if dates provided)"
    )
    url: Optional[str] = Field(default=None, description="URL to the listing")
    source: Optional[str] = Field(
        default=None, description="Source of the listing (e.g., 'airbnb', 'booking')"
    )

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Validate that rating is between 0 and 5 if provided."""
        if v is not None and (v < 0 or v > 5):
            raise ValueError("Rating must be between 0 and 5")
        return v
