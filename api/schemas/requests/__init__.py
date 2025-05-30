"""
Request schemas for the Frontend API.

This module contains Pydantic models for validating incoming requests
from the Next.js frontend application.
"""

from .auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)
from .trips import (
    CreateTripRequest,
    TripPreferencesRequest,
    TripSearchRequest,
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
    "TripPreferencesRequest",
    "TripSearchRequest",
    "UpdateTripRequest",
]
