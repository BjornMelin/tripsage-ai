"""Shared schemas and models for TripSage AI.

This module contains common Pydantic models, enums, and schemas that are used
across multiple parts of the TripSage application, including API layers,
services, and core business logic.
"""

from .base_models import (
    BaseResponse,
    ErrorResponse,
    PaginatedResponse,
    PaginationMeta,
    SuccessResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from .chat import (
    ChatContext,
    ChatMessage,
    ChatSession,
    ToolCall,
)
from .enums import (
    AccommodationType,
    BookingStatus,
    CabinClass,
    CancellationPolicy,
    CurrencyCode,
    PaymentType,
    TransportationType,
    TripStatus,
    TripType,
    TripVisibility,
    UserRole,
)
from .financial import (
    Budget,
    Currency,
    ExchangeRate,
    Price,
    PriceBreakdown,
    PriceRange,
)
from .flight_schemas import (
    AirportSearchRequest,
    AirportSearchResponse,
    FlightPassenger,
    FlightSearchRequest,
    FlightSearchResponse,
    MultiCityFlightSearchRequest,
    MultiCityFlightSegment,
    SavedFlightRequest,
    SavedFlightResponse,
    UpcomingFlightResponse,
)
from .geographic import (
    Address,
    Airport,
    BoundingBox,
    Coordinates,
    Place,
    Region,
    Route,
)
from .temporal import (
    Availability,
    BusinessHours,
    DateRange,
    DateTimeRange,
    Duration,
    TimeRange,
)
from .travel import (
    AccommodationPreferences,
    TransportationPreferences,
    TripDestination,
    TripPreferences,
    TripSummary,
)


__all__ = [
    # Travel
    "AccommodationPreferences",
    # Enums
    "AccommodationType",
    # Geographic
    "Address",
    "Airport",
    # Flight schemas
    "AirportSearchRequest",
    "AirportSearchResponse",
    # Temporal
    "Availability",
    # Base models
    "BaseResponse",
    "BookingStatus",
    "BoundingBox",
    # Financial
    "Budget",
    "BusinessHours",
    "CabinClass",
    "CancellationPolicy",
    # Chat models
    "ChatContext",
    "ChatMessage",
    "ChatSession",
    # Validators
    "Coordinates",
    "Currency",
    "CurrencyCode",
    "DateRange",
    "DateTimeRange",
    "Duration",
    "ErrorResponse",
    "ExchangeRate",
    "FlightPassenger",
    "FlightSearchRequest",
    "FlightSearchResponse",
    "MultiCityFlightSearchRequest",
    "MultiCityFlightSegment",
    "PaginatedResponse",
    "PaginationMeta",
    "PaymentType",
    "Place",
    "Price",
    "PriceBreakdown",
    "PriceRange",
    "Region",
    "Route",
    "SavedFlightRequest",
    "SavedFlightResponse",
    "SuccessResponse",
    "TimeRange",
    "ToolCall",
    "TransportationPreferences",
    "TransportationType",
    "TripDestination",
    "TripPreferences",
    "TripStatus",
    "TripSummary",
    "TripType",
    "TripVisibility",
    "UpcomingFlightResponse",
    "UserRole",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
]
