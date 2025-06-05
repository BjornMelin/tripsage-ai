"""
API schemas for TripSage.

This package contains organized Pydantic V2 schemas with clear separation:

- requests/   : API request schemas and validation models
- responses/  : API response schemas and output models

Import directly from the appropriate subdirectory:

    from tripsage.api.schemas.requests.auth import LoginRequest
    from tripsage.api.schemas.responses.auth import UserResponse

For shared types from tripsage_core:
    from tripsage_core.models.schemas_common import BookingStatus
"""

# Re-export commonly used shared types for convenience
from tripsage_core.models.schemas_common import (
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

__all__ = [
    "AccommodationType",
    "BookingStatus",
    "CabinClass",
    "CancellationPolicy",
    "CurrencyCode",
    "PaymentType",
    "TransportationType",
    "TripStatus",
    "TripType",
    "TripVisibility",
    "UserRole",
]
