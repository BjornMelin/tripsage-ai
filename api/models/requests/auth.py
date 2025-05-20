"""
Request models for authentication endpoints.

This module defines Pydantic models for validating incoming authentication requests.
"""

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterUserRequest(BaseModel):
    """Request model for user registration."""

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
        if self.password != self.password_confirm:
            raise ValueError("Passwords do not match")
        return self

    @model_validator(mode="after")
    def validate_password_strength(self) -> "RegisterUserRequest":
        """Validate password strength."""
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in self.password):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not any(c.islower() for c in self.password):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not any(c.isdigit() for c in self.password):
            raise ValueError("Password must contain at least one number")

        # Check for at least one special character
        special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
        if not any(c in special_chars for c in self.password):
            raise ValueError("Password must contain at least one special character")

        return self


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(False, description="Remember me")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")


class ChangePasswordRequest(BaseModel):
    """Request model for changing password."""

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
        if self.new_password != self.new_password_confirm:
            raise ValueError("New passwords do not match")
        return self

    @model_validator(mode="after")
    def validate_passwords_different(self) -> "ChangePasswordRequest":
        """Validate that current_password and new_password are different."""
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")
        return self

    @model_validator(mode="after")
    def validate_password_strength(self) -> "ChangePasswordRequest":
        """Validate password strength."""
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in self.new_password):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not any(c.islower() for c in self.new_password):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not any(c.isdigit() for c in self.new_password):
            raise ValueError("Password must contain at least one number")

        # Check for at least one special character
        special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
        if not any(c in special_chars for c in self.new_password):
            raise ValueError("Password must contain at least one special character")

        return self


class ForgotPasswordRequest(BaseModel):
    """Request model for forgot password."""

    email: EmailStr = Field(..., description="Email address")


class ResetPasswordRequest(BaseModel):
    """Request model for resetting password."""

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
        if self.new_password != self.new_password_confirm:
            raise ValueError("Passwords do not match")
        return self

    @model_validator(mode="after")
    def validate_password_strength(self) -> "ResetPasswordRequest":
        """Validate password strength."""
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in self.new_password):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one lowercase letter
        if not any(c.islower() for c in self.new_password):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one digit
        if not any(c.isdigit() for c in self.new_password):
            raise ValueError("Password must contain at least one number")

        # Check for at least one special character
        special_chars = "!@#$%^&*()_-+=[]{}|:;,.<>?/"
        if not any(c in special_chars for c in self.new_password):
            raise ValueError("Password must contain at least one special character")

        return self
