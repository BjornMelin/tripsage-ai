"""Flight model classes for TripSage.

This module provides the flight-related model classes used throughout the
TripSage application for representing flight search requests, offers, and bookings.
"""

from typing import Any

from pydantic import Field

from tripsage.models.mcp import MCPRequestBase, MCPResponseBase


# CabinClass consolidated to tripsage_core.models.schemas_common.enums


# FlightSearchRequest moved to tripsage_core.models.schemas_common.flight_schemas
# Import it from there if needed for MCP operations


# FlightSegment moved to tripsage_core.models.domain.flight


# MultiCityFlightSearchRequest moved to schemas_common.flight_schemas
# Import it from there if needed for MCP operations


# FlightOffer moved to tripsage_core.models.domain.flight


# FlightSearchResponse moved to tripsage_core.models.schemas_common.flight_schemas
# Import it from there if needed for MCP operations


# Airport moved to tripsage_core.models.domain.flight


# AirportSearchRequest moved to tripsage_core.models.schemas_common.flight_schemas
# Import it from there if needed for MCP operations


# AirportSearchResponse moved to tripsage_core.models.schemas_common.flight_schemas
# Import it from there if needed for MCP operations


class FlightBookingRequest(MCPRequestBase):
    """Parameters for flight booking."""

    offer_id: str = Field(..., description="Flight offer ID")
    passengers: list[dict[str, Any]] = Field(
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
    itinerary: list[dict[str, Any]] = Field(..., description="Flight itinerary")
