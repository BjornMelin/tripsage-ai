"""
Core flight domain models for TripSage.

This module contains the core business domain models for flight-related
entities. These models represent the essential flight data structures
independent of storage implementation or API specifics.
"""

from typing import Any

from pydantic import Field

from tripsage_core.models.base_core_model import TripSageDomainModel
from tripsage_core.models.schemas_common.common_validators import (
    AirportCode,
    CurrencyCode,
    Latitude,
    Longitude,
    NonNegativeFloat,
    PositiveInt,
)
from tripsage_core.models.schemas_common.enums import CabinClass


class Airport(TripSageDomainModel):
    """Core airport information business entity.

    This represents the canonical airport model used throughout the TripSage system.
    """

    iata_code: AirportCode = Field(..., description="IATA code")
    name: str = Field(..., description="Airport name")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    latitude: Latitude = Field(None, description="Latitude coordinate")
    longitude: Longitude = Field(None, description="Longitude coordinate")
    timezone: str | None = Field(None, description="Timezone")


class FlightSegment(TripSageDomainModel):
    """A segment of a flight (one leg of the journey)."""

    origin: AirportCode = Field(..., description="Origin airport code")
    destination: AirportCode = Field(..., description="Destination airport code")
    departure_date: str = Field(..., description="Departure date (YYYY-MM-DD)")
    departure_time: str | None = Field(None, description="Departure time (HH:MM)")
    arrival_date: str | None = Field(None, description="Arrival date (YYYY-MM-DD)")
    arrival_time: str | None = Field(None, description="Arrival time (HH:MM)")
    carrier: str | None = Field(None, description="Carrier code")
    flight_number: str | None = Field(None, description="Flight number")
    duration_minutes: PositiveInt = Field(None, description="Duration in minutes")


class FlightOffer(TripSageDomainModel):
    """Core flight offer business entity.

    This represents the canonical flight offer model used throughout the TripSage
    system. It contains all essential information about a flight offer independent
    of the source or storage mechanism.
    """

    id: str = Field(..., description="Offer ID")
    total_amount: NonNegativeFloat = Field(..., description="Total price")
    total_currency: CurrencyCode = Field(..., description="Currency code")
    base_amount: NonNegativeFloat = Field(None, description="Base fare amount")
    tax_amount: NonNegativeFloat = Field(None, description="Tax amount")
    slices: list[dict[str, Any]] = Field(..., description="Flight slices (legs)")
    passenger_count: PositiveInt = Field(..., description="Number of passengers")
    cabin_class: CabinClass | None = Field(None, description="Cabin class")

    # Additional domain-specific fields for enhanced functionality
    segments: list[FlightSegment] | None = Field(
        None, description="Parsed flight segments"
    )
    origin_airport: Airport | None = Field(None, description="Origin airport details")
    destination_airport: Airport | None = Field(
        None, description="Destination airport details"
    )
    departure_datetime: str | None = Field(
        None, description="Combined departure date and time (ISO format)"
    )
    arrival_datetime: str | None = Field(
        None, description="Combined arrival date and time (ISO format)"
    )
    total_duration_minutes: PositiveInt = Field(
        None, description="Total travel duration in minutes"
    )
    stops_count: PositiveInt = Field(None, description="Number of stops")
    airlines: list[str] | None = Field(None, description="Airlines involved")
    booking_class: str | None = Field(None, description="Booking class code")
    fare_basis: str | None = Field(None, description="Fare basis code")

    # Source and tracking information
    source: str | None = Field(
        None, description="Source of the offer (e.g., 'duffel', 'amadeus')"
    )
    search_id: str | None = Field(None, description="Associated search ID")
    expires_at: str | None = Field(
        None, description="Offer expiration timestamp (ISO format)"
    )
