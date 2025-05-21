"""Response models for the TripSage API.

This package contains Pydantic V2 models for response validation.
"""

# Auth response models
from tripsage.api.models.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)

# Trip response models
from tripsage.api.models.responses.trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)

__all__ = [
    # Auth responses
    "MessageResponse",
    "PasswordResetResponse",
    "TokenResponse",
    "UserPreferencesResponse",
    "UserResponse",
    # Trip responses
    "TripListItem",
    "TripListResponse",
    "TripResponse",
    "TripSummaryResponse",
]
