"""
Flight MCP Initialization module.

This module provides initialization functions for the Flight MCP module.
"""

from .client import FlightsMCPClient, get_client
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
from .service import FlightService, get_service

__all__ = [
    # Clients and services
    "get_client",
    "FlightsMCPClient",
    "get_service",
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
