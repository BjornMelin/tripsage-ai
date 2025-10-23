"""API schemas for TripSage.

This package contains consolidated Pydantic V2 schemas organized by domain:

- api_keys.py      : API key management schemas
- auth.py          : Authentication schemas
- chat.py          : Chat interaction schemas
- config.py        : Configuration management schemas
- dashboard.py     : Dashboard monitoring and analytics schemas
- destinations.py  : Destination search and info schemas
- flights.py       : Flight search and booking schemas
- users.py         : User management schemas
- websocket.py     : WebSocket communication schemas

Trip, itinerary, and accommodation schemas now live in
``tripsage_core.models.api`` as the canonical definitions.

Import directly from the consolidated schema files:

    from tripsage.api.schemas.auth import LoginRequest, UserResponse
    from tripsage.api.schemas.chat import ChatRequest, ChatResponse

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
