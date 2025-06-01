"""Flight response models using Pydantic V2.

This module defines Pydantic models for flight-related responses.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from tripsage_core.models.domain.flight import CabinClass

from ..requests.flights import FlightSearchRequest, MultiCityFlightSearchRequest


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
