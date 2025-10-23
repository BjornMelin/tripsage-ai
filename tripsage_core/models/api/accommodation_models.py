"""Canonical accommodation request and response models for the API layer."""

from datetime import date
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.services.business.accommodation_service import (
    AccommodationListing,
    AccommodationSearchRequest as ServiceAccommodationSearchRequest,
    AccommodationSearchResponse as ServiceAccommodationSearchResponse,
    BookingStatus,
    PropertyType,
)


class AccommodationDetailsRequest(TripSageModel):
    """Request model for retrieving accommodation details."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "listing_id": "listing-123",
                "check_in": "2025-07-12",
                "check_out": "2025-07-15",
                "adults": 2,
                "children": 1,
                "source": "booking",
            }
        }
    )

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
    def validate_dates(cls, value: date | None, info) -> date | None:
        """Ensure check-out is after check-in when both provided."""
        check_in = info.data.get("check_in")
        if value is not None and check_in and value <= check_in:
            raise ValueError("Check-out date must be after check-in date")
        return value


class SavedAccommodationRequest(TripSageModel):
    """Request model for saving an accommodation listing."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "listing_id": "listing-123",
                "trip_id": "8c808086-7a9f-4a4a-8212-1c0857f0fa4f",
                "check_in": "2025-07-12",
                "check_out": "2025-07-15",
                "notes": "Great location for conference",
            }
        }
    )

    listing_id: str = Field(description="Accommodation listing ID")
    trip_id: UUID = Field(description="Trip ID to save the accommodation for")
    check_in: date = Field(description="Check-in date")
    check_out: date = Field(description="Check-out date")
    notes: str | None = Field(None, description="Notes about this accommodation")

    @field_validator("check_out")
    @classmethod
    def validate_dates(cls, value: date, info) -> date:
        """Validate that check-out date is after check-in date."""
        check_in = info.data.get("check_in")
        if check_in and value <= check_in:
            raise ValueError("Check-out date must be after check-in date")
        return value


class AccommodationDetailsResponse(TripSageModel):
    """API response for accommodation details."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "listing": {
                    "id": "listing-123",
                    "name": "Central City Loft",
                    "description": "Modern loft near downtown",
                    "property_type": "apartment",
                    "location": {
                        "address": "123 Main St",
                        "city": "New York",
                        "country": "USA",
                    },
                    "price_per_night": 245.0,
                    "currency": "USD",
                    "max_guests": 2,
                },
                "availability": True,
                "total_price": 985.0,
            }
        }
    )

    listing: AccommodationListing = Field(description="Accommodation listing")
    availability: bool = Field(
        description="Whether the accommodation is available for the dates"
    )
    total_price: float | None = Field(
        default=None, description="Total price for the stay (if dates provided)"
    )


class SavedAccommodationResponse(TripSageModel):
    """Response model for a saved accommodation listing."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "7b991b2c-6ce5-49e1-9960-1ef5a06979cd",
                "user_id": "user-42",
                "trip_id": "8c808086-7a9f-4a4a-8212-1c0857f0fa4f",
                "listing": {
                    "id": "listing-123",
                    "name": "Central City Loft",
                    "property_type": "apartment",
                    "location": {
                        "address": "123 Main St",
                        "city": "New York",
                        "country": "USA",
                    },
                    "price_per_night": 245.0,
                    "currency": "USD",
                    "max_guests": 2,
                },
                "check_in": "2025-07-12",
                "check_out": "2025-07-15",
                "saved_at": "2025-05-01",
                "notes": "Request late checkout",
                "status": "saved",
            }
        }
    )

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


class AccommodationSearchRequest(ServiceAccommodationSearchRequest):
    """Canonical API request model for accommodation search queries."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "user-42",
                "trip_id": "8c808086-7a9f-4a4a-8212-1c0857f0fa4f",
                "location": "San Francisco",
                "check_in": "2025-08-10",
                "check_out": "2025-08-14",
                "guests": 2,
                "property_types": [PropertyType.APARTMENT.value],
                "max_price": 350.0,
                "currency": "USD",
                "amenities": ["wifi", "washer"],
                "sort_by": "price",
                "sort_order": "asc",
            }
        }
    )


class AccommodationSearchResponse(ServiceAccommodationSearchResponse):
    """Canonical API response model for accommodation search results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "search_id": "search-abc123",
                "user_id": "user-42",
                "trip_id": "8c808086-7a9f-4a4a-8212-1c0857f0fa4f",
                "listings": [
                    {
                        "id": "listing-123",
                        "name": "Central City Loft",
                        "property_type": "apartment",
                        "price_per_night": 245.0,
                        "currency": "USD",
                        "max_guests": 2,
                    }
                ],
                "search_parameters": {
                    "location": "San Francisco",
                    "check_in": "2025-08-10",
                    "check_out": "2025-08-14",
                    "guests": 2,
                },
                "total_results": 42,
                "results_returned": 10,
                "min_price": 180.0,
                "max_price": 410.0,
                "avg_price": 265.0,
                "search_duration_ms": 320,
                "cached": False,
            }
        }
    )


__all__ = [
    "AccommodationDetailsRequest",
    "AccommodationDetailsResponse",
    "AccommodationSearchRequest",
    "AccommodationSearchResponse",
    "SavedAccommodationRequest",
    "SavedAccommodationResponse",
]
