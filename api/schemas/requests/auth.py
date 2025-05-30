"""
Request schemas for authentication endpoints.

This module defines Pydantic models for validating incoming authentication requests
from the Next.js frontend. Uses shared validators from tripsage_core for consistency.
"""

from pydantic import BaseModel, EmailStr, Field, model_validator

from tripsage_core.models.schemas_common.validators import (
    validate_password_strength,
    validate_passwords_different,
    validate_passwords_match,
)


class RegisterUserRequest(BaseModel):
    """Request schema for user registration."""

    username: str = Field(
        ...,
        description="Username",
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(
        ...,
        description="Password",
        min_length=8,
        max_length=100,
    )
    password_confirm: str = Field(..., description="Password confirmation")
    full_name: str = Field(
        ...,
        description="Full name",
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "RegisterUserRequest":
        """Validate that password and password_confirm match."""
        validate_passwords_match(self.password, self.password_confirm)
        return self

    @model_validator(mode="after")
    def validate_password_strength(self) -> "RegisterUserRequest":
        """Validate password strength using shared validator."""
        validate_password_strength(self.password)
        return self


class LoginRequest(BaseModel):
    """Request schema for user login."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember me")


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=100,
    )
    new_password_confirm: str = Field(..., description="New password confirmation")

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "ChangePasswordRequest":
        """Validate that new_password and new_password_confirm match."""
        validate_passwords_match(self.new_password, self.new_password_confirm)
        return self

    @model_validator(mode="after")
    def validate_passwords_different(self) -> "ChangePasswordRequest":
        """Validate that current_password and new_password are different."""
        validate_passwords_different(self.current_password, self.new_password)
        return self

    @model_validator(mode="after")
    def validate_password_strength(self) -> "ChangePasswordRequest":
        """Validate new password strength using shared validator."""
        validate_password_strength(self.new_password)
        return self


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""

    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(BaseModel):
    """Request schema for resetting password."""

    token: str = Field(..., description="Reset token")
    new_password: str = Field(
        ...,
        description="New password",
        min_length=8,
        max_length=100,
    )
    new_password_confirm: str = Field(..., description="New password confirmation")

    @model_validator(mode="after")
    def validate_passwords_match(self) -> "ResetPasswordRequest":
        """Validate that new_password and new_password_confirm match."""
        validate_passwords_match(self.new_password, self.new_password_confirm)
        return self

    @model_validator(mode="after")
    def validate_password_strength(self) -> "ResetPasswordRequest":
        """Validate new password strength using shared validator."""
        validate_password_strength(self.new_password)
        return self
