"""
Flight model classes for TripSage.

This module provides the flight-related model classes used throughout the
TripSage application for representing flight search requests, offers, and bookings.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator, model_validator

from tripsage_core.models.base import TripSageModel
from tripsage.models.mcp import MCPRequestBase, MCPResponseBase


class CabinClass(str, Enum):
    """Cabin class options for flights."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class FlightSearchRequest(MCPRequestBase):
    """Parameters for flight search queries."""

    origin: str = Field(..., description="Origin airport IATA code")
    destination: str = Field(..., description="Destination airport IATA code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    return_date: Optional[str] = Field(
        None, description="Return date for round trips (YYYY-MM-DD)"
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
        None, description="List of preferred airline codes"
    )

    @field_validator("departure_date", "return_date")
    @classmethod
    def validate_date_format(cls, v):
        """Validate that dates are in YYYY-MM-DD format."""
        if v:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Date must be in YYYY-MM-DD format") from e
        return v

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()

    @model_validator(mode="after")
    def validate_return_date_after_departure(self) -> "FlightSearchRequest":
        """Validate that return date is after departure date if provided."""
        if (
            self.return_date
            and self.departure_date
            and self.return_date < self.departure_date
        ):
            raise ValueError("Return date must be after departure date")
        return self


class FlightSegment(TripSageModel):
    """A segment of a flight (one leg of the journey)."""

    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    departure_time: Optional[str] = Field(None, description="Departure time (HH:MM)")
    arrival_date: Optional[str] = Field(None, description="Arrival date (YYYY-MM-DD)")
    arrival_time: Optional[str] = Field(None, description="Arrival time (HH:MM)")
    carrier: Optional[str] = Field(None, description="Carrier code")
    flight_number: Optional[str] = Field(None, description="Flight number")
    duration_minutes: Optional[int] = Field(None, description="Duration in minutes")

    @field_validator("origin", "destination")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class MultiCityFlightSearchRequest(MCPRequestBase):
    """Parameters for multi-city flight search."""

    segments: List[FlightSegment] = Field(..., description="List of flight segments")
    adults: int = Field(1, ge=1, le=9, description="Number of adult passengers")
    children: int = Field(0, ge=0, le=9, description="Number of child passengers")
    infants: int = Field(0, ge=0, le=4, description="Number of infant passengers")
    cabin_class: CabinClass = Field(CabinClass.ECONOMY, description="Cabin class")

    @model_validator(mode="after")
    def validate_segments(self) -> "MultiCityFlightSearchRequest":
        """Validate that there are at least two segments."""
        if len(self.segments) < 2:
            raise ValueError("At least two segments are required for multi-city search")
        return self


class FlightOffer(TripSageModel):
    """Flight offer information."""

    id: str = Field(..., description="Offer ID")
    total_amount: float = Field(..., description="Total price")
    total_currency: str = Field(..., description="Currency code")
    base_amount: Optional[float] = Field(None, description="Base fare amount")
    tax_amount: Optional[float] = Field(None, description="Tax amount")
    slices: List[Dict[str, Any]] = Field(..., description="Flight slices (legs)")
    passenger_count: int = Field(..., description="Number of passengers")


class FlightSearchResponse(MCPResponseBase):
    """Response for flight search."""

    offers: List[FlightOffer] = Field([], description="List of flight offers")
    offer_count: int = Field(0, description="Number of offers found")
    currency: str = Field("USD", description="Currency code")
    search_id: Optional[str] = Field(None, description="Search ID for tracking")
    cheapest_price: Optional[float] = Field(None, description="Cheapest price found")


class Airport(TripSageModel):
    """Airport information."""

    iata_code: str = Field(..., description="IATA code")
    name: str = Field(..., description="Airport name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    timezone: Optional[str] = Field(None, description="Timezone")

    @field_validator("iata_code")
    @classmethod
    def validate_airport_code(cls, v: str) -> str:
        """Validate and standardize airport codes."""
        if len(v) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")
        return v.upper()


class AirportSearchRequest(MCPRequestBase):
    """Parameters for airport search."""

    code: Optional[str] = Field(None, description="IATA airport code")
    search_term: Optional[str] = Field(
        None, description="Airport name or city to search for"
    )

    @model_validator(mode="after")
    def validate_params(self) -> "AirportSearchRequest":
        """Validate that either code or search_term is provided."""
        if not self.code and not self.search_term:
            raise ValueError("Either code or search_term must be provided")

        if self.code and len(self.code) != 3:
            raise ValueError("Airport code must be 3 characters (IATA code)")

        return self


class AirportSearchResponse(MCPResponseBase):
    """Response for airport search."""

    airports: List[Airport] = Field([], description="List of airports")
    count: int = Field(0, description="Number of airports found")


class FlightBookingRequest(MCPRequestBase):
    """Parameters for flight booking."""

    offer_id: str = Field(..., description="Flight offer ID")
    passengers: List[Dict[str, Any]] = Field(
        ..., min_length=1, description="List of passengers"
    )
    contact_email: str = Field(..., description="Contact email address")
    contact_phone: str = Field(..., description="Contact phone number")


class FlightBookingResponse(MCPResponseBase):
    """Response for flight booking."""

    booking_id: str = Field(..., description="Booking ID")
    booking_reference: str = Field(..., description="Booking reference (PNR)")
    total_amount: float = Field(..., description="Total amount paid")
    currency: str = Field(..., description="Currency code")
    status: str = Field(..., description="Booking status")
    passenger_count: int = Field(..., description="Number of passengers")
    itinerary: List[Dict[str, Any]] = Field(..., description="Flight itinerary")
