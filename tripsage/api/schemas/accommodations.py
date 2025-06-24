"""Accommodation API schemas using Pydantic V2.

This module defines Pydantic models for accommodation-related API requests
and responses.
Consolidates both request and response schemas for accommodation operations.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from tripsage_core.models.schemas_common import AccommodationType, BookingStatus

# ===== Request Schemas =====


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
    property_type: Optional[AccommodationType] = Field(
        None, description="Type of property"
    )
    min_price: Optional[float] = Field(
        None, ge=0, description="Minimum price per night"
    )
    max_price: Optional[float] = Field(
        None, ge=0, description="Maximum price per night"
    )
    amenities: Optional[List[str]] = Field(
        None, description="Required amenities (e.g., wifi, pool)"
    )
    min_rating: Optional[float] = Field(
        None, ge=0, le=5, description="Minimum guest rating (0-5)"
    )
    latitude: Optional[float] = Field(
        None, ge=-90, le=90, description="Latitude coordinate"
    )
    longitude: Optional[float] = Field(
        None, ge=-180, le=180, description="Longitude coordinate"
    )
    trip_id: Optional[UUID] = Field(None, description="Associated trip ID")

    @field_validator("check_out")
    @classmethod
    def validate_check_out_after_check_in(cls, v: date, info) -> date:
        """Validate that check-out date is after check-in date."""
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("Check-out date must be after check-in date")
        return v

    @field_validator("max_price")
    @classmethod
    def validate_price_range(cls, v: Optional[float], info) -> Optional[float]:
        """Validate that max price is greater than min price if both are provided."""
        if (
            v is not None
            and "min_price" in info.data
            and info.data["min_price"] is not None
        ):
            if v < info.data["min_price"]:
                raise ValueError("Maximum price must be greater than minimum price")
        return v


class AccommodationDetailsRequest(BaseModel):
    """Request model for retrieving accommodation details."""

    listing_id: str = Field(description="Listing ID")
    check_in: Optional[date] = Field(None, description="Check-in date")
    check_out: Optional[date] = Field(None, description="Check-out date")
    adults: Optional[int] = Field(None, ge=1, le=16, description="Number of adults")
    children: Optional[int] = Field(None, ge=0, le=10, description="Number of children")
    source: Optional[str] = Field(
        None,
        description="Source of the listing (e.g., 'airbnb', 'booking')",
    )

    @field_validator("check_out")
    @classmethod
    def validate_dates(cls, v: Optional[date], info) -> Optional[date]:
        """Validate that check-out date is after check-in date if both are provided."""
        if (
            v is not None
            and "check_in" in info.data
            and info.data["check_in"] is not None
        ):
            if v <= info.data["check_in"]:
                raise ValueError("Check-out date must be after check-in date")
        return v


class SavedAccommodationRequest(BaseModel):
    """Request model for saving an accommodation listing."""

    listing_id: str = Field(description="Accommodation listing ID")
    trip_id: UUID = Field(description="Trip ID to save the accommodation for")
    check_in: date = Field(description="Check-in date")
    check_out: date = Field(description="Check-out date")
    notes: Optional[str] = Field(None, description="Notes about this accommodation")

    @field_validator("check_out")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate that check-out date is after check-in date."""
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("Check-out date must be after check-in date")
        return v


# ===== Response Schemas =====


class AccommodationLocation(BaseModel):
    """Location details for an accommodation."""

    city: str
    country: str
    latitude: float
    longitude: float
    neighborhood: Optional[str] = None
    distance_to_center: Optional[float] = None


class AccommodationAmenity(BaseModel):
    """Amenity information."""

    name: str


class AccommodationImage(BaseModel):
    """Image information for an accommodation."""

    url: str
    caption: Optional[str] = None
    is_primary: bool = False


class AccommodationListing(BaseModel):
    """Complete accommodation listing information."""

    id: str
    name: str
    description: str
    property_type: AccommodationType
    location: AccommodationLocation
    price_per_night: float
    currency: str = "USD"
    rating: Optional[float] = None
    review_count: Optional[int] = None
    amenities: List[AccommodationAmenity] = []
    images: List[AccommodationImage] = []
    max_guests: int = 2
    bedrooms: int = 1
    beds: int = 1
    bathrooms: float = 1.0
    check_in_time: str = "15:00"
    check_out_time: str = "11:00"
    url: Optional[str] = None
    source: Optional[str] = None
    total_price: Optional[float] = None


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


class AccommodationDetailsResponse(BaseModel):
    """Response model for accommodation details."""

    listing: AccommodationListing = Field(description="Accommodation listing")
    availability: bool = Field(
        description="Whether the accommodation is available for the dates"
    )
    total_price: Optional[float] = Field(
        default=None, description="Total price for the stay (if dates provided)"
    )


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
