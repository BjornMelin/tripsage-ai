"""Canonical flights domain models used across API, services, and orchestration.

These models are the single source of truth for flight-related entities in
TripSage. They consolidate previously duplicated DTOs into one place.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from tripsage_core.models.base_core_model import TripSageModel
from tripsage_core.models.schemas_common.enums import BookingStatus, CabinClass
from tripsage_core.models.schemas_common.flight_schemas import FlightPassenger


class FlightSegment(TripSageModel):
    """Flight segment information."""

    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: datetime = Field(..., description="Departure date and time")
    arrival_date: datetime = Field(..., description="Arrival date and time")
    airline: str | None = Field(None, description="Airline code")
    flight_number: str | None = Field(None, description="Flight number")
    aircraft_type: str | None = Field(None, description="Aircraft type")
    duration_minutes: int | None = Field(None, description="Flight duration in minutes")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate airport code format."""
        if len(v) != 3 or not v.isalpha():
            raise ValueError("Airport code must be 3 letters")
        return v.upper()


class FlightOffer(TripSageModel):
    """Flight offer response model."""

    id: str = Field(..., description="Offer ID")
    search_id: str | None = Field(None, description="Associated search ID")
    outbound_segments: list[FlightSegment] = Field(
        ..., description="Outbound flight segments"
    )
    return_segments: list[FlightSegment] | None = Field(
        None, description="Return flight segments"
    )

    total_price: float = Field(..., description="Total price")
    base_price: float | None = Field(None, description="Base fare price")
    taxes: float | None = Field(None, description="Taxes and fees")
    currency: str = Field(..., description="Price currency")

    cabin_class: CabinClass = Field(..., description="Cabin class")
    booking_class: str | None = Field(None, description="Booking class code")

    total_duration: int | None = Field(None, description="Total travel time in minutes")
    stops_count: int = Field(default=0, description="Number of stops")
    airlines: list[str] = Field(default_factory=list, description="Airlines involved")

    expires_at: datetime | None = Field(None, description="Offer expiration time")
    bookable: bool = Field(default=True, description="Whether offer can be booked")

    source: str | None = Field(None, description="Source API (duffel, amadeus, etc.)")
    source_offer_id: str | None = Field(
        None, description="Original offer ID from source"
    )

    # Scoring and ranking
    score: float | None = Field(None, ge=0, le=1, description="Quality score")
    price_score: float | None = Field(
        None, ge=0, le=1, description="Price competitiveness"
    )
    convenience_score: float | None = Field(
        None, ge=0, le=1, description="Convenience score"
    )


class FlightBooking(TripSageModel):
    """Flight booking response model."""

    id: str = Field(..., description="Booking ID")
    trip_id: str | None = Field(None, description="Associated trip ID")
    user_id: str = Field(..., description="User ID")

    offer_id: str = Field(..., description="Booked offer ID")
    confirmation_number: str | None = Field(
        None, description="Airline confirmation number"
    )

    passengers: list[FlightPassenger] = Field(..., description="Passenger details")
    outbound_segments: list[FlightSegment] = Field(..., description="Outbound segments")
    return_segments: list[FlightSegment] | None = Field(
        None, description="Return segments"
    )

    total_price: float = Field(..., description="Total booking price")
    currency: str = Field(..., description="Price currency")

    status: BookingStatus = Field(..., description="Booking status")
    booked_at: datetime = Field(..., description="Booking timestamp")
    expires_at: datetime | None = Field(None, description="Booking expiration")

    cancellable: bool = Field(
        default=False, description="Whether booking can be cancelled"
    )
    refundable: bool = Field(default=False, description="Whether booking is refundable")

    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class FlightSearchResponse(TripSageModel):
    """Flight search response model."""

    search_id: str = Field(..., description="Search ID")
    offers: list[FlightOffer] = Field(..., description="Flight offers")
    search_parameters: Any = Field(..., description="Original search parameters")
    total_results: int = Field(..., description="Total number of results")
    search_duration_ms: int | None = Field(
        None, description="Search duration in milliseconds"
    )
    cached: bool = Field(default=False, description="Whether results were cached")


class FlightBookingRequest(TripSageModel):
    """Request model for flight booking."""

    offer_id: str = Field(..., description="Offer ID to book")
    passengers: list[FlightPassenger] = Field(
        ..., description="Complete passenger information"
    )
    trip_id: str | None = Field(None, description="Associated trip ID")
    hold_only: bool = Field(default=False, description="Hold booking without payment")
    metadata: dict[str, Any] | None = Field(
        None, description="Additional booking metadata"
    )

    @field_validator("passengers")
    @classmethod
    def validate_passengers(cls, v: list[FlightPassenger]) -> list[FlightPassenger]:
        """Validate passenger information is complete for booking."""
        for passenger in v:
            if not passenger.given_name or not passenger.family_name:
                raise ValueError("Given name and family name are required for booking")
        return v
