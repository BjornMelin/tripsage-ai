"""Accommodation response models using Pydantic V2.

This module defines Pydantic models for accommodation-related API responses.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage_core.models.schemas_common import BookingStatus

from ..common.accommodations import AccommodationListing
from ..requests.accommodations import AccommodationSearchRequest


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
