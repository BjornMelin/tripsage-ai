"""Authentication API schemas using Pydantic V2.

This module defines Pydantic models for authentication-related API requests
and responses.
Consolidates both request and response schemas for authentication operations.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from tripsage_core.models.schemas_common.common_validators import (
    passwords_different,
    passwords_match,
    validate_password_strength,
)


# ===== Request Schemas =====


class RegisterRequest(BaseModel):
    """User registration request model."""

    username: str = Field(
        min_length=3,
        max_length=50,
        description="Username (3-50 characters, alphanumeric, underscore, hyphen)",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    email: EmailStr = Field(description="Valid email address")
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Password (8-128 characters with strength requirements)",
    )
    password_confirm: str = Field(
        min_length=8,
        max_length=128,
        description="Password confirmation (must match password)",
    )
    full_name: str = Field(
        min_length=1,
        max_length=100,
        description="Full name (1-100 characters)",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength_check(cls, v: str) -> str:
        """Validate password meets strength requirements."""
        return validate_password_strength(v)

    @model_validator(mode="after")
    def validate_passwords_match_check(self) -> "RegisterRequest":
        """Validate that password and password_confirm match."""
        passwords_match(self.password, self.password_confirm)
        return self


class LoginRequest(BaseModel):
    """User login request model."""

    username: str = Field(description="Username or email address")
    password: str = Field(description="User password")
    remember_me: bool = Field(False, description="Remember user session")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""

    refresh_token: str = Field(description="JWT refresh token")


class ChangePasswordRequest(BaseModel):
    """Change password request model."""

    current_password: str = Field(description="Current user password")
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password (8-128 characters with strength requirements)",
    )
    new_password_confirm: str = Field(
        min_length=8,
        max_length=128,
        description="New password confirmation (must match new_password)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        """Validate new password meets strength requirements."""
        return validate_password_strength(v)

    @model_validator(mode="after")
    def validate_password_requirements(self) -> "ChangePasswordRequest":
        """Validate password requirements."""
        # Check that passwords match
        passwords_match(self.new_password, self.new_password_confirm)
        # Check that new password is different from current
        passwords_different(self.current_password, self.new_password)
        return self


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model."""

    email: EmailStr = Field(description="Email address for password reset")


class ResetPasswordRequest(BaseModel):
    """Reset password request model."""

    token: str = Field(description="Password reset token")
    new_password: str = Field(
        min_length=8,
        max_length=128,
        description="New password (8-128 characters with strength requirements)",
    )
    new_password_confirm: str = Field(
        min_length=8,
        max_length=128,
        description="New password confirmation (must match new_password)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        """Validate new password meets strength requirements."""
        return validate_password_strength(v)

    @model_validator(mode="after")
    def validate_passwords_match_check(self) -> "ResetPasswordRequest":
        """Validate that password and password_confirm match."""
        passwords_match(self.new_password, self.new_password_confirm)
        return self


# ===== Response Schemas =====


class Token(BaseModel):
    """Token response model."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: datetime = Field(description="Token expiration timestamp")


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str = Field(description="JWT access token")
    refresh_token: str = Field(description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration in seconds")
    user: "UserResponse" = Field(description="User information")


class UserResponse(BaseModel):
    """User response model."""

    id: str = Field(description="User ID")
    username: str | None = Field(default=None, description="Username")
    email: EmailStr = Field(description="User email address")
    full_name: str | None = Field(default=None, description="User's full name")
    created_at: datetime = Field(description="Account creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether user account is active")
    is_verified: bool = Field(
        default=False, description="Whether user account is verified"
    )
    preferences: dict[str, object] | None = Field(
        default=None, description="User preferences"
    )


class UserPreferencesResponse(BaseModel):
    """User preferences response model."""

    user_id: str = Field(description="User ID")
    preferences: dict[str, object] = Field(description="User preferences dictionary")
    updated_at: datetime = Field(description="Last update timestamp")


class MessageResponse(BaseModel):
    """Generic message response model."""

    message: str = Field(description="Response message")
    success: bool = Field(default=True, description="Whether operation was successful")
    details: dict[str, object] | None = Field(
        default=None, description="Additional details"
    )


class AuthResponse(BaseModel):
    """Authentication response with user and tokens."""

    user: UserResponse = Field(description="User information")
    tokens: Token = Field(description="Authentication tokens")


class PasswordResetResponse(BaseModel):
    """Password reset response model."""

    message: str = Field(description="Reset status message")
    email: EmailStr = Field(description="Email where reset link was sent")
    reset_token_expires_at: datetime | None = Field(
        default=None, description="When reset token expires"
    )
