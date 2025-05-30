"""
Response schemas for authentication endpoints.

This module defines Pydantic models for API responses related to authentication
from the backend to the Next.js frontend.
"""

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """Response schema for user information."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(..., description="Whether the user is active")
    is_verified: bool = Field(..., description="Whether the user's email is verified")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    preferences: Optional[Dict] = Field(None, description="User preferences")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "user_123",
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "is_verified": True,
                "created_at": "2025-01-15T14:30:00Z",
                "updated_at": "2025-01-16T09:45:00Z",
                "preferences": {
                    "theme": "dark",
                    "language": "en",
                    "notifications": True,
                },
            }
        }
    }


class UserPreferencesResponse(BaseModel):
    """Response schema for user preferences."""

    id: str = Field(..., description="User ID")
    preferences: Dict = Field({}, description="User preferences")


class MessageResponse(BaseModel):
    """Response schema for simple messages."""

    message: str = Field(..., description="Message")
    success: bool = Field(True, description="Whether the operation was successful")

    model_config = {
        "json_schema_extra": {
            "example": {"message": "Operation completed successfully", "success": True}
        }
    }


class PasswordResetResponse(BaseModel):
    """Response schema for password reset."""

    message: str = Field(..., description="Message")
    email: EmailStr = Field(..., description="Email address")
    success: bool = Field(True, description="Whether the operation was successful")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Password reset email sent successfully",
                "email": "user@example.com",
                "success": True,
            }
        }
    }
