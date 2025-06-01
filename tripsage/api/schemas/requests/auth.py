"""Authentication request schemas using Pydantic V2.

This module defines Pydantic models for authentication-related requests.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator

from tripsage_core.models.schemas_common.validators import (
    validate_password_strength,
    validate_passwords_different,
    validate_passwords_match,
)


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

    @field_validator("password_confirm")
    @classmethod
    def validate_passwords_match_check(cls, v: str, info) -> str:
        """Validate that password and password_confirm match."""
        if "password" in info.data:
            validate_passwords_match(info.data["password"], v)
        return v


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

    @field_validator("new_password_confirm")
    @classmethod
    def validate_password_requirements(cls, v: str, info) -> str:
        """Validate password requirements."""
        if "new_password" in info.data:
            # Check that passwords match
            validate_passwords_match(info.data["new_password"], v)
        if "current_password" in info.data and "new_password" in info.data:
            # Check that new password is different from current
            validate_passwords_different(
                info.data["current_password"], info.data["new_password"]
            )
        return v


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

    @field_validator("new_password_confirm")
    @classmethod
    def validate_passwords_match_check(cls, v: str, info) -> str:
        """Validate that password and password_confirm match."""
        if "new_password" in info.data:
            validate_passwords_match(info.data["new_password"], v)
        return v
