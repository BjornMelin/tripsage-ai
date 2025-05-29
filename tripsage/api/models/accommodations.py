"""Accommodation models using Pydantic V2.

This module defines Pydantic models for accommodation-related requests and responses.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from tripsage_core.models.schemas_common import (
    AccommodationType as PropertyType,  # Alias for API compatibility
)
from tripsage_core.models.schemas_common import (
    BookingStatus,
    CancellationPolicy,
)


class AccommodationSearchRequest(BaseModel):
    """Request model for searching accommodations."""

    location: str = Field(
        description="Location (city, address, etc.)",
        min_length=1,
        max_length=100,
    )
    check_in: date = Field(description="Check-in date")
    check_out: date = Field(description="Check-out date")
    adults: int = Field(1, ge=1, le=16, description="Number of adults")
    children: int = Field(0, ge=0, le=10, description="Number of children")
    rooms: int = Field(1, ge=1, le=8, description="Number of rooms")
    property_type: Optional[PropertyType] = Field(
        default=None, description="Type of property"
    )
    min_price: Optional[float] = Field(
        default=None, ge=0, description="Minimum price per night"
    )
    max_price: Optional[float] = Field(
        default=None, ge=0, description="Maximum price per night"
    )
    amenities: Optional[List[str]] = Field(
        default=None, description="Required amenities (e.g., wifi, pool)"
    )
    min_rating: Optional[float] = Field(
        default=None, ge=0, le=5, description="Minimum guest rating (0-5)"
    )
    latitude: Optional[float] = Field(
        default=None, ge=-90, le=90, description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Longitude coordinate"
    )
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")

    @model_validator(mode="after")
    def validate_check_out_after_check_in(self) -> "AccommodationSearchRequest":
        """Validate that check-out date is after check-in date."""
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError("Check-out date must be after check-in date")
        return self

    @model_validator(mode="after")
    def validate_price_range(self) -> "AccommodationSearchRequest":
        """Validate that max price is greater than min price if both are provided."""
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.max_price < self.min_price
        ):
            raise ValueError("Maximum price must be greater than minimum price")
        return self


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


class AccommodationSearchResponse(BaseModel):
    """Response model for accommodation search results."""

    listings: List[AccommodationListing] = Field(
        default=[], description="List of accommodation listings"
    )
    count: int = Field(description="Number of listings found")
    currency: str = Field(default="USD", description="Currency code")
    search_id: str = Field(description="Search ID for tracking")
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")
    min_price: Optional[float] = Field(default=None, description="Minimum price found")
    max_price: Optional[float] = Field(default=None, description="Maximum price found")
    avg_price: Optional[float] = Field(default=None, description="Average price found")
    search_request: AccommodationSearchRequest = Field(
        description="Original search request"
    )


class AccommodationDetailsRequest(BaseModel):
    """Request model for retrieving accommodation details."""

    listing_id: str = Field(description="Listing ID")
    check_in: Optional[date] = Field(default=None, description="Check-in date")
    check_out: Optional[date] = Field(default=None, description="Check-out date")
    adults: Optional[int] = Field(
        default=None, ge=1, le=16, description="Number of adults"
    )
    children: Optional[int] = Field(
        default=None, ge=0, le=10, description="Number of children"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source of the listing (e.g., 'airbnb', 'booking')",
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "AccommodationDetailsRequest":
        """Validate that check-out date is after check-in date if both are provided."""
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValueError("Check-out date must be after check-in date")
        return self


class AccommodationDetailsResponse(BaseModel):
    """Response model for accommodation details."""

    listing: AccommodationListing = Field(description="Accommodation listing")
    availability: bool = Field(
        description="Whether the accommodation is available for the dates"
    )
    total_price: Optional[float] = Field(
        default=None, description="Total price for the stay (if dates provided)"
    )


class SavedAccommodationRequest(BaseModel):
    """Request model for saving an accommodation listing."""

    listing_id: str = Field(description="Accommodation listing ID")
    trip_id: UUID = Field(description="Trip ID to save the accommodation for")
    check_in: date = Field(description="Check-in date")
    check_out: date = Field(description="Check-out date")
    notes: Optional[str] = Field(
        default=None, description="Notes about this accommodation"
    )

    @model_validator(mode="after")
    def validate_dates(self) -> "SavedAccommodationRequest":
        """Validate that check-out date is after check-in date."""
        if self.check_out <= self.check_in:
            raise ValueError("Check-out date must be after check-in date")
        return self


class SavedAccommodationResponse(BaseModel):
    """Response model for a saved accommodation listing."""

    id: UUID = Field(description="Saved accommodation ID")
    user_id: str = Field(description="User ID")
    trip_id: UUID = Field(description="Trip ID")
    listing: AccommodationListing = Field(description="Accommodation listing details")
    check_in: date = Field(description="Check-in date")
    check_out: date = Field(description="Check-out date")
    saved_at: date = Field(description="Date when the accommodation was saved")
    notes: Optional[str] = Field(
        default=None, description="Notes about this accommodation"
    )
    status: BookingStatus = Field(
        default=BookingStatus.SAVED, description="Booking status"
    )
