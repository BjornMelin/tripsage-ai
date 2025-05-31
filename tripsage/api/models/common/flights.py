"""Flight common models using Pydantic V2.

This module defines shared Pydantic models for flight-related data structures.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Airport(BaseModel):
    """Model for an airport."""

    code: str = Field(description="Airport IATA code")
    name: str = Field(description="Airport name")
    city: str = Field(description="City name")
    country: str = Field(description="Country name")
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    timezone: Optional[str] = Field(default=None, description="Airport timezone")


class FlightOffer(BaseModel):
    """Model for a flight offer."""

    id: str = Field(description="Offer ID")
    price: float = Field(description="Total price")
    currency: str = Field(description="Currency code")
    departure_airport: str = Field(description="Departure airport code")
    arrival_airport: str = Field(description="Arrival airport code")
    departure_time: datetime = Field(description="Departure time")
    arrival_time: datetime = Field(description="Arrival time")
    duration_minutes: int = Field(description="Flight duration in minutes")
    airline: str = Field(description="Airline name")
    flight_number: str = Field(description="Flight number")
    aircraft_type: Optional[str] = Field(default=None, description="Aircraft type")
    booking_class: Optional[str] = Field(default=None, description="Booking class")
    baggage_allowance: Optional[str] = Field(
        default=None, description="Baggage allowance"
    )
    is_refundable: bool = Field(
        default=False, description="Whether the ticket is refundable"
    )
    stops: int = Field(default=0, description="Number of stops")
    layovers: List[dict] = Field(default=[], description="Layover information")


class MultiCityFlightSegment(BaseModel):
    """Model for a multi-city flight segment."""

    from_airport: str = Field(description="Departure airport code")
    to_airport: str = Field(description="Arrival airport code")
    departure_date: str = Field(description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(
        default=None, description="Return date in YYYY-MM-DD format (if round trip)"
    )
