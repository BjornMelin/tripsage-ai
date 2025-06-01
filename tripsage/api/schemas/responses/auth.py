"""Authentication response models using Pydantic V2.

This module defines Pydantic models for authentication-related responses.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response model."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: datetime = Field(description="Token expiration timestamp")


class TokenResponse(BaseModel):
    """Enhanced token response model."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user: "UserResponse" = Field(description="User information")


class UserResponse(BaseModel):
    """User response model."""

    id: str = Field(description="User ID")
    email: EmailStr = Field(description="User email address")
    full_name: Optional[str] = Field(default=None, description="User's full name")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether user account is active")
    preferences: Optional[Dict] = Field(default=None, description="User preferences")


class UserPreferencesResponse(BaseModel):
    """User preferences response model."""

    user_id: str = Field(description="User ID")
    preferences: Dict = Field(description="User preferences dictionary")
    updated_at: datetime = Field(description="Last update timestamp")


class MessageResponse(BaseModel):
    """Generic message response model."""

    message: str = Field(description="Response message")
    success: bool = Field(default=True, description="Whether operation was successful")
    details: Optional[Dict] = Field(default=None, description="Additional details")


class PasswordResetResponse(BaseModel):
    """Password reset response model."""

    message: str = Field(description="Reset status message")
    email: EmailStr = Field(description="Email where reset link was sent")
    reset_token_expires_at: Optional[datetime] = Field(
        default=None, description="When reset token expires"
    )
