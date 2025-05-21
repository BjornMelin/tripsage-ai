"""
Response models for authentication endpoints.

This module defines Pydantic models for API responses related to authentication.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """Response model for user information."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(..., description="Whether the user is active")
    is_verified: bool = Field(..., description="Whether the user's email is verified")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    preferences: Optional[Dict] = Field(None, description="User preferences")


class UserPreferencesResponse(BaseModel):
    """Response model for user preferences."""

    id: str = Field(..., description="User ID")
    preferences: Dict = Field({}, description="User preferences")


class MessageResponse(BaseModel):
    """Response model for simple messages."""

    message: str = Field(..., description="Message")


class PasswordResetResponse(BaseModel):
    """Response model for password reset."""

    message: str = Field(..., description="Message")
    email: EmailStr = Field(..., description="Email address")
