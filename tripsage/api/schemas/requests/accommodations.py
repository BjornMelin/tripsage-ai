"""Accommodation request schemas using Pydantic V2.

This module defines Pydantic models for accommodation-related API requests.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from tripsage_core.models.schemas_common import AccommodationType


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
