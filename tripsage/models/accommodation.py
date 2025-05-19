"""
Accommodation model classes for TripSage.

This module provides the accommodation-related model classes used throughout the
TripSage application for representing accommodation search
requests, listings, and bookings.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator, model_validator

from tripsage.models.base import TripSageModel
from tripsage.models.mcp import MCPRequestBase, MCPResponseBase


class PropertyType(str, Enum):
    """Property type options for accommodations."""

    HOTEL = "hotel"
    APARTMENT = "apartment"
    HOUSE = "house"
    VILLA = "villa"
    RESORT = "resort"
    HOSTEL = "hostel"
    BED_AND_BREAKFAST = "bed_and_breakfast"
    GUEST_HOUSE = "guest_house"
    OTHER = "other"


class AccommodationSearchRequest(MCPRequestBase):
    """Parameters for accommodation search."""

    location: str = Field(..., description="Location (city, address, etc.)")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, le=16, description="Number of adults")
    children: int = Field(0, ge=0, le=10, description="Number of children")
    rooms: int = Field(1, ge=1, le=8, description="Number of rooms")
    property_type: Optional[PropertyType] = Field(None, description="Type of property")
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

    @field_validator("check_in", "check_out")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @model_validator(mode="after")
    def validate_check_out_after_check_in(self) -> "AccommodationSearchRequest":
        """Validate that check-out date is after check-in date."""
        if self.check_in and self.check_out:
            check_in_date = datetime.strptime(self.check_in, "%Y-%m-%d")
            check_out_date = datetime.strptime(self.check_out, "%Y-%m-%d")
            if check_out_date <= check_in_date:
                raise ValueError("Check-out date must be after check-in date")
        return self

    @model_validator(mode="after")
    def validate_price_range(self) -> "AccommodationSearchRequest":
        """Validate that max price is greater than min price if both are provided."""
        if self.min_price is not None and self.max_price is not None:
            if self.max_price < self.min_price:
                raise ValueError("Maximum price must be greater than minimum price")
        return self


class AccommodationAmenity(TripSageModel):
    """Amenity offered by an accommodation."""

    name: str = Field(..., description="Amenity name")
    category: Optional[str] = Field(None, description="Amenity category")
    description: Optional[str] = Field(None, description="Amenity description")


class AccommodationImage(TripSageModel):
    """Image of an accommodation."""

    url: str = Field(..., description="Image URL")
    caption: Optional[str] = Field(None, description="Image caption")
    is_primary: bool = Field(False, description="Whether this is the primary image")


class AccommodationLocation(TripSageModel):
    """Location information for an accommodation."""

    address: Optional[str] = Field(None, description="Full address")
    city: str = Field(..., description="City")
    state: Optional[str] = Field(None, description="State/province")
    country: str = Field(..., description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/zip code")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    neighborhood: Optional[str] = Field(None, description="Neighborhood name")


class AccommodationListing(TripSageModel):
    """Accommodation listing information."""

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


class AccommodationSearchResponse(MCPResponseBase):
    """Response for accommodation search."""

    listings: List[AccommodationListing] = Field(
        [], description="List of accommodation listings"
    )
    listing_count: int = Field(0, description="Number of listings found")
    currency: str = Field("USD", description="Currency code")
    search_id: Optional[str] = Field(None, description="Search ID for tracking")
    cheapest_price: Optional[float] = Field(None, description="Cheapest price found")
    average_price: Optional[float] = Field(None, description="Average price found")


class AccommodationDetailsRequest(MCPRequestBase):
    """Parameters for retrieving accommodation details."""

    listing_id: str = Field(..., description="Listing ID")
    check_in: Optional[str] = Field(None, description="Check-in date (YYYY-MM-DD)")
    check_out: Optional[str] = Field(None, description="Check-out date (YYYY-MM-DD)")
    adults: Optional[int] = Field(None, description="Number of adults")
    children: Optional[int] = Field(None, description="Number of children")
    source: Optional[str] = Field(
        None, description="Source of the listing (e.g., 'airbnb', 'booking')"
    )


class AccommodationDetailsResponse(MCPResponseBase):
    """Response for accommodation details."""

    listing: AccommodationListing = Field(..., description="Accommodation listing")
    availability: bool = Field(
        ..., description="Whether the accommodation is available for the dates"
    )
    total_price: Optional[float] = Field(
        None, description="Total price for the stay (if dates provided)"
    )


class AccommodationBookingRequest(MCPRequestBase):
    """Parameters for accommodation booking."""

    listing_id: str = Field(..., description="Listing ID")
    check_in: str = Field(..., description="Check-in date (YYYY-MM-DD)")
    check_out: str = Field(..., description="Check-out date (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, description="Number of adults")
    children: int = Field(0, ge=0, description="Number of children")
    guest_name: str = Field(..., description="Guest name")
    guest_email: str = Field(..., description="Guest email")
    guest_phone: str = Field(..., description="Guest phone number")
    special_requests: Optional[str] = Field(None, description="Special requests")
    payment_method: str = Field(..., description="Payment method")


class AccommodationBookingResponse(MCPResponseBase):
    """Response for accommodation booking."""

    booking_id: str = Field(..., description="Booking ID")
    confirmation_code: str = Field(..., description="Confirmation code")
    listing_id: str = Field(..., description="Listing ID")
    listing_name: str = Field(..., description="Listing name")
    check_in: str = Field(..., description="Check-in date")
    check_out: str = Field(..., description="Check-out date")
    total_price: float = Field(..., description="Total price")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Booking status")
    payment_status: str = Field(..., description="Payment status")
    cancellation_policy: Optional[str] = Field(None, description="Cancellation policy")
    host_instructions: Optional[str] = Field(
        None, description="Instructions from the host"
    )
