"""Accommodation API schemas.

Final-only consolidation: re-export canonical service/domain models from
``tripsage_core`` and keep only API-specific compositions.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Canonical request/response and entities from the business service layer
from tripsage_core.services.business.accommodation_service import (
    AccommodationListing,
    BookingStatus,
)


class AccommodationDetailsRequest(BaseModel):
    """Request model for retrieving accommodation details."""

    listing_id: str = Field(description="Listing ID")
    check_in: date | None = Field(None, description="Check-in date")
    check_out: date | None = Field(None, description="Check-out date")
    adults: int | None = Field(None, ge=1, le=16, description="Number of adults")
    children: int | None = Field(None, ge=0, le=10, description="Number of children")
    source: str | None = Field(
        None,
        description="Source of the listing (e.g., 'airbnb', 'booking')",
    )

    @field_validator("check_out")
    @classmethod
    def validate_dates(cls, v: date | None, info) -> date | None:
        """Validate that check-out date is after check-in when both provided."""
        if (
            v is not None
            and "check_in" in info.data
            and info.data["check_in"] is not None
            and v <= info.data["check_in"]
        ):
            raise ValueError("Check-out date must be after check-in date")
        return v


class SavedAccommodationRequest(BaseModel):
    """Request model for saving an accommodation listing."""

    listing_id: str = Field(description="Accommodation listing ID")
    trip_id: UUID = Field(description="Trip ID to save the accommodation for")
    check_in: date = Field(description="Check-in date")
    check_out: date = Field(description="Check-out date")
    notes: str | None = Field(None, description="Notes about this accommodation")

    @field_validator("check_out")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        """Validate that check-out date is after check-in date."""
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("Check-out date must be after check-in date")
        return v


class AccommodationDetailsResponse(BaseModel):
    """API response for accommodation details.

    Kept API-local since the service exposes listing retrieval directly.
    """

    listing: AccommodationListing = Field(description="Accommodation listing")
    availability: bool = Field(
        description="Whether the accommodation is available for the dates"
    )
    total_price: float | None = Field(
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
    notes: str | None = Field(
        default=None, description="Notes about this accommodation"
    )
    status: BookingStatus = Field(
        default=BookingStatus.SAVED, description="Booking status"
    )
