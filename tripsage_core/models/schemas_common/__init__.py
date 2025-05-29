"""
Shared schemas and models for TripSage AI.

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
from .enums import (
    AccommodationType,
    BookingStatus,
    CabinClass,
    CancellationPolicy,
    CurrencyCode,
    PaymentType,
    TripStatus,
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

__all__ = [
    # Base models
    "BaseResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "SuccessResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    # Enums
    "AccommodationType",
    "BookingStatus",
    "CabinClass",
    "CancellationPolicy",
    "CurrencyCode",
    "PaymentType",
    "TripStatus",
    "UserRole",
    # Financial
    "Budget",
    "Currency",
    "ExchangeRate",
    "Price",
    "PriceBreakdown",
    "PriceRange",
    # Geographic
    "Address",
    "Airport",
    "BoundingBox",
    "Coordinates",
    "Place",
    "Region",
    "Route",
    # Temporal
    "Availability",
    "BusinessHours",
    "DateRange",
    "DateTimeRange",
    "Duration",
    "TimeRange",
]
