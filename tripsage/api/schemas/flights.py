"""Flight API schemas using Pydantic V2.

This module defines Pydantic models for flight-related API requests and responses.
Consolidates both request and response schemas for flight operations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from tripsage_core.models.domain.flight import CabinClass

# ===== Request Schemas =====


class FlightSearchRequest(BaseModel):
    """Request model for flight search."""

    origin: str = Field(
        description="Origin airport IATA code",
        min_length=3,
        max_length=3,
    )
    destination: str = Field(
        description="Destination airport IATA code",
        min_length=3,
        max_length=3,
    )
    departure_date: date = Field(description="Departure date")
    return_date: Optional[date] = Field(
        default=None, description="Return date for round trips"
    )
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=4, description="Number of infant passengers")
    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")
    max_stops: Optional[int] = Field(
        None, ge=0, le=3, description="Maximum number of stops"
    )
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    preferred_airlines: Optional[List[str]] = Field(
        default=None, description="List of preferred airline codes"
    )
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v):
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()

    @model_validator(mode="after")
    def validate_return_date(self) -> "FlightSearchRequest":
        """Validate that return date is after departure date if provided."""
        if (
            self.return_date
            and self.departure_date
            and self.return_date < self.departure_date
        ):
            raise ValueError("Return date must be after departure date")
        return self


class MultiCityFlightSegment(BaseModel):
    """Model for a multi-city flight segment."""

    origin: str = Field(
        description="Origin airport IATA code",
        min_length=3,
        max_length=3,
    )
    destination: str = Field(
        description="Destination airport IATA code",
        min_length=3,
        max_length=3,
    )
    departure_date: date = Field(description="Departure date")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v):
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class MultiCityFlightSearchRequest(BaseModel):
    """Request model for multi-city flight search."""

    segments: List[MultiCityFlightSegment] = Field(
        description="List of flight segments",
        min_length=2,
    )
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=4, description="Number of infant passengers")
    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")
    max_stops: Optional[int] = Field(
        None, ge=0, le=3, description="Maximum number of stops"
    )
    max_price: Optional[float] = Field(None, gt=0, description="Maximum price in USD")
    preferred_airlines: Optional[List[str]] = Field(
        default=None, description="List of preferred airline codes"
    )
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")

    @model_validator(mode="after")
    def validate_segments(self) -> "MultiCityFlightSearchRequest":
        """Validate that there are at least two segments and dates are sequential."""
        if len(self.segments) < 2:
            raise ValueError("At least two segments are required for multi-city search")

        # Check that dates are sequential
        for i in range(len(self.segments) - 1):
            if self.segments[i + 1].departure_date < self.segments[i].departure_date:
                raise ValueError(
                    f"Segment {i + 2} departure date must be on or after segment "
                    f"{i + 1} departure date"
                )

        return self


class AirportSearchRequest(BaseModel):
    """Request model for airport search."""

    query: str = Field(
        description="Search query (airport name, city, or IATA code)",
        min_length=1,
        max_length=100,
    )
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of results to return"
    )


class SavedFlightRequest(BaseModel):
    """Request model for saving a flight offer."""

    offer_id: str = Field(description="Flight offer ID")
    trip_id: UUID = Field(description="Trip ID to save the flight for")
    notes: Optional[str] = Field(
        default=None, description="Notes about this flight offer"
    )


# ===== Response Schemas =====


class FlightOffer(BaseModel):
    """Response model for a flight offer."""

    id: str = Field(description="Offer ID")
    origin: str = Field(description="Origin airport code")
    destination: str = Field(description="Destination airport code")
    departure_date: date = Field(description="Departure date")
    return_date: Optional[date] = Field(default=None, description="Return date")
    airline: str = Field(description="Airline code")
    airline_name: str = Field(description="Airline name")
    price: float = Field(description="Total price")
    currency: str = Field(description="Currency code")
    cabin_class: CabinClass = Field(description="Cabin class")
    stops: int = Field(description="Number of stops")
    duration_minutes: int = Field(description="Flight duration in minutes")
    segments: List[Dict[str, Any]] = Field(description="Flight segments")
    booking_link: Optional[str] = Field(default=None, description="Booking link")


class FlightSearchResponse(BaseModel):
    """Response model for flight search results."""

    results: List[FlightOffer] = Field(description="Flight offers")
    count: int = Field(description="Number of results")
    currency: str = Field(description="Currency code for prices", default="USD")
    search_id: str = Field(description="Search ID for reference")
    trip_id: Optional[UUID] = Field(default=None, description="Associated trip ID")
    min_price: Optional[float] = Field(default=None, description="Minimum price found")
    max_price: Optional[float] = Field(default=None, description="Maximum price found")
    search_request: Union[FlightSearchRequest, MultiCityFlightSearchRequest] = Field(
        description="Original search request"
    )


class Airport(BaseModel):
    """Response model for airport information."""

    code: str = Field(description="IATA code")
    name: str = Field(description="Airport name")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    country_code: str = Field(description="Country code")
    latitude: float = Field(description="Latitude")
    longitude: float = Field(description="Longitude")


class AirportSearchResponse(BaseModel):
    """Response model for airport search results."""

    results: List[Airport] = Field(description="Airport results")
    count: int = Field(description="Number of results")


class SavedFlightResponse(BaseModel):
    """Response model for a saved flight offer."""

    id: UUID = Field(description="Saved flight ID")
    user_id: str = Field(description="User ID")
    trip_id: UUID = Field(description="Trip ID")
    offer: FlightOffer = Field(description="Flight offer details")
    saved_at: datetime = Field(description="Timestamp when flight was saved")
    notes: Optional[str] = Field(
        default=None, description="Notes about this flight offer"
    )


class UpcomingFlightResponse(BaseModel):
    """Response model for upcoming flights with real-time status."""

    id: str = Field(description="Flight ID")
    trip_id: Optional[str] = Field(default=None, description="Associated trip ID")
    trip_title: Optional[str] = Field(default=None, description="Trip title")
    airline: str = Field(description="Airline code")
    airline_name: str = Field(description="Airline name")
    flight_number: str = Field(description="Flight number")
    origin: str = Field(description="Origin airport code")
    destination: str = Field(description="Destination airport code")
    departure_time: datetime = Field(description="Departure time")
    arrival_time: datetime = Field(description="Arrival time")
    duration: int = Field(description="Flight duration in minutes")
    stops: int = Field(description="Number of stops")
    price: float = Field(description="Flight price")
    currency: str = Field(description="Currency code", default="USD")
    cabin_class: str = Field(description="Cabin class")
    seats_available: Optional[int] = Field(default=None, description="Available seats")
    status: str = Field(
        description="Flight status", default="upcoming"
    )  # upcoming, boarding, delayed, cancelled
    terminal: Optional[str] = Field(default=None, description="Terminal")
    gate: Optional[str] = Field(default=None, description="Gate")
    # Enhanced trip context fields
    is_shared_trip: Optional[bool] = Field(
        default=False, description="Whether the trip is shared"
    )
    collaborator_count: Optional[int] = Field(
        default=0, description="Number of trip collaborators"
    )
