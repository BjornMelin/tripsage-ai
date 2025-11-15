"""API schemas for TripSage.

This package contains consolidated Pydantic V2 schemas organized by domain:

- auth.py          : Authentication schemas
- dashboard.py     : Dashboard monitoring and analytics schemas
- users.py         : User management schemas

Trip and itinerary schemas now live in
``tripsage_core.models.api`` as the canonical definitions.

Chat, search, and destination schemas removed; handled via frontend AI SDK v6 agents.

Import directly from the consolidated schema files:

    from tripsage.api.schemas.auth import LoginRequest, UserResponse

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
