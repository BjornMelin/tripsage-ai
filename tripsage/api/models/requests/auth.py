"""Authentication request models using Pydantic V2.

This module defines Pydantic models for authentication-related requests.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from tripsage_core.models.schemas_common.validators import (
    validate_password_strength,
    validate_passwords_different,
    validate_passwords_match,
)


class RegisterUserRequest(BaseModel):
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
    def validate_passwords_match_check(self) -> "RegisterUserRequest":
        """Validate that password and password_confirm match."""
        validate_passwords_match(self.password, self.password_confirm)
        return self


class LoginRequest(BaseModel):
    """User login request model."""

    username: str = Field(description="Username or email address")
    password: str = Field(description="User password")
    remember_me: bool = Field(default=False, description="Remember user session")


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
        validate_passwords_match(self.new_password, self.new_password_confirm)
        # Check that new password is different from current
        validate_passwords_different(self.current_password, self.new_password)
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
        validate_passwords_match(self.new_password, self.new_password_confirm)
        return self


# Legacy models for backward compatibility
class UserCreate(BaseModel):
    """User creation request model (legacy)."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request model (legacy)."""

    email: EmailStr
    password: str


class RefreshToken(BaseModel):
    """Refresh token request model (legacy)."""

    refresh_token: str
