"""Accommodation request models using Pydantic V2.

This module defines Pydantic models for accommodation-related API requests.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from tripsage_core.models.schemas_common import (
    AccommodationType as PropertyType,  # Alias for API compatibility
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
