"""
Response schemas for the Frontend API.

This module contains Pydantic models for API responses sent to
the Next.js frontend application.
"""

from .auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)
from .trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSearchResponse,
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
    "TripSearchResponse",
    "TripSummaryResponse",
]
