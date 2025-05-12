"""
Flight MCP Initialization module.

This module provides initialization functions for the Flight MCP module.
"""

from .client import FlightService, FlightsMCPClient, get_client, get_service
from .models import (
    Airport,
    AirportSearchParams,
    AirportSearchResponse,
    BookingParams,
    BookingResponse,
    ContactDetails,
    FlightOffer,
    FlightPriceParams,
    FlightPriceResponse,
    FlightSearchParams,
    FlightSearchResponse,
    MultiCitySearchParams,
    OfferDetailsParams,
    OfferDetailsResponse,
    OrderDetailsParams,
    OrderDetailsResponse,
    Passenger,
    PaymentDetails,
    PriceTrackingParams,
    PriceTrackingResponse,
)

__all__ = [
    # Clients and services
    "get_client",
    "get_service",
    "FlightsMCPClient",
    "FlightService",
    # Parameter models
    "FlightSearchParams",
    "MultiCitySearchParams",
    "AirportSearchParams",
    "OfferDetailsParams",
    "FlightPriceParams",
    "PriceTrackingParams",
    "Passenger",
    "PaymentDetails",
    "ContactDetails",
    "BookingParams",
    "OrderDetailsParams",
    # Response models
    "FlightOffer",
    "FlightSearchResponse",
    "Airport",
    "AirportSearchResponse",
    "OfferDetailsResponse",
    "FlightPriceResponse",
    "PriceTrackingResponse",
    "BookingResponse",
    "OrderDetailsResponse",
]
