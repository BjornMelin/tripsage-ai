"""Pydantic models for the TripSage API.

This package contains Pydantic V2 models for request and response validation.
"""

# Auth models
from tripsage.api.models.api_key import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyRotateRequest,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from tripsage.api.models.auth import (
    RefreshToken,
    Token,
    TokenData,
    UserCreate,
    UserLogin,
    UserResponse,
)

# Request models
from tripsage.api.models.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)
from tripsage.api.models.requests.trips import (
    CreateTripRequest,
    TripDestination,
    TripPreferences,
    TripPreferencesRequest,
    UpdateTripRequest,
)

# Response models
from tripsage.api.models.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserPreferencesResponse,
)
from tripsage.api.models.responses.auth import UserResponse as UserResponseExtended
from tripsage.api.models.responses.trips import (
    TripListItem,
    TripListResponse,
    TripResponse,
    TripSummaryResponse,
)

__all__ = [
    # Auth models
    "Token", "TokenData", "UserCreate", "UserLogin", "UserResponse", "RefreshToken",
    "ApiKeyCreate", "ApiKeyResponse", "ApiKeyValidateRequest", 
    "ApiKeyValidateResponse", "ApiKeyRotateRequest",
    
    # Request models
    "RegisterUserRequest", "LoginRequest", "RefreshTokenRequest", 
    "ChangePasswordRequest", "ForgotPasswordRequest", "ResetPasswordRequest", 
    "TripDestination", "TripPreferences", "CreateTripRequest", "UpdateTripRequest", 
    "TripPreferencesRequest",
    
    # Response models
    "TokenResponse", "UserResponseExtended", "UserPreferencesResponse", 
    "MessageResponse", "PasswordResetResponse", "TripResponse", "TripListItem", 
    "TripListResponse", "TripSummaryResponse"
]