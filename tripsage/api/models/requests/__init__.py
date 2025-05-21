"""Request models for the TripSage API.

This package contains Pydantic V2 models for request validation.
"""

# Auth request models
from tripsage.api.models.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)

# Trip request models
from tripsage.api.models.requests.trips import (
    CreateTripRequest,
    TripDestination,
    TripPreferences,
    TripPreferencesRequest,
    UpdateTripRequest,
)

__all__ = [
    # Auth requests
    "ChangePasswordRequest",
    "ForgotPasswordRequest",
    "LoginRequest",
    "RefreshTokenRequest",
    "RegisterUserRequest",
    "ResetPasswordRequest",
    # Trip requests
    "CreateTripRequest",
    "TripDestination",
    "TripPreferences",
    "TripPreferencesRequest",
    "UpdateTripRequest",
]
