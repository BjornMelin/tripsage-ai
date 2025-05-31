"""Accommodation response models using Pydantic V2.

This module defines Pydantic models for accommodation-related API responses.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common import BookingStatus

# Create AccommodationListing model here
from tripsage_core.models.schemas_common.enums import AccommodationType

from ..requests.accommodations import AccommodationSearchRequest


class AccommodationLocation(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float
    neighborhood: Optional[str] = None
    distance_to_center: Optional[float] = None


class AccommodationAmenity(BaseModel):
    name: str


class AccommodationImage(BaseModel):
    url: str
    caption: Optional[str] = None
    is_primary: bool = False


class AccommodationListing(BaseModel):
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
