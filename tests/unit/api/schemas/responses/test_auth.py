"""
Tests for authentication response schemas.

This module tests the Pydantic models used for API responses
related to authentication sent to the Next.js frontend.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)


class TestTokenResponse:
    """Test TokenResponse schema."""

    def test_valid_token_response(self):
        """Test valid token response."""
        data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600,
        }
        response = TokenResponse(**data)
        assert response.access_token.startswith("eyJhbGciOiJIUzI1NiIs")
        assert response.token_type == "bearer"
        assert response.expires_in == 3600

    def test_default_token_type(self):
        """Test that token_type defaults to 'bearer'."""
        data = {
            "access_token": "access_token_123",
            "refresh_token": "refresh_token_456",
            "expires_in": 7200,
        }
        response = TokenResponse(**data)
        assert response.token_type == "bearer"

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Missing access_token
        with pytest.raises(ValidationError):
            TokenResponse(
                refresh_token="refresh_token",
                expires_in=3600,
            )

        # Missing refresh_token
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token="access_token",
                expires_in=3600,
            )

        # Missing expires_in
        with pytest.raises(ValidationError):
            TokenResponse(
                access_token="access_token",
                refresh_token="refresh_token",
            )


class TestUserResponse:
    """Test UserResponse schema."""

    def test_valid_user_response(self):
        """Test valid user response."""
        data = {
            "id": "user_123",
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime(2025, 1, 15, 14, 30),
            "updated_at": datetime(2025, 1, 16, 9, 45),
            "preferences": {
                "theme": "dark",
                "language": "en",
                "notifications": True,
            },
        }
        response = UserResponse(**data)
        assert response.id == "user_123"
        assert response.username == "john_doe"
        assert response.email == "john@example.com"
        assert response.preferences["theme"] == "dark"

    def test_minimal_user_response(self):
        """Test user response with minimal required fields."""
        data = {
            "id": "user_456",
            "username": "jane_smith",
            "email": "jane@example.com",
            "full_name": "Jane Smith",
            "is_active": True,
            "is_verified": False,
            "created_at": datetime(2025, 1, 10, 10, 0),
            "updated_at": datetime(2025, 1, 10, 10, 0),
        }
        response = UserResponse(**data)
        assert response.preferences is None
        assert response.is_verified is False

    def test_email_validation(self):
        """Test email validation in user response."""
        base_data = {
            "id": "user_123",
            "username": "john_doe",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime(2025, 1, 15, 14, 30),
            "updated_at": datetime(2025, 1, 16, 9, 45),
        }

        # Valid email
        response = UserResponse(**{**base_data, "email": "valid@example.com"})
        assert response.email == "valid@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            UserResponse(**{**base_data, "email": "invalid-email"})

    def test_required_fields(self):
        """Test that required fields are enforced."""
        base_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime(2025, 1, 15, 14, 30),
            "updated_at": datetime(2025, 1, 16, 9, 45),
        }

        # Missing id
        with pytest.raises(ValidationError):
            UserResponse(**base_data)

        # Missing username
        with pytest.raises(ValidationError):
            UserResponse(**{**base_data, "id": "user_123"})

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        # This tests that the model_config is properly set
        schema = UserResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert example["username"] == "john_doe"
        assert example["email"] == "john@example.com"


class TestUserPreferencesResponse:
    """Test UserPreferencesResponse schema."""

    def test_valid_preferences_response(self):
        """Test valid user preferences response."""
        data = {
            "id": "user_123",
            "preferences": {
                "theme": "dark",
                "language": "es",
                "notifications": False,
                "timezone": "America/New_York",
            },
        }
        response = UserPreferencesResponse(**data)
        assert response.id == "user_123"
        assert response.preferences["language"] == "es"
        assert response.preferences["notifications"] is False

    def test_empty_preferences(self):
        """Test preferences response with empty preferences."""
        data = {
            "id": "user_456",
            "preferences": {},
        }
        response = UserPreferencesResponse(**data)
        assert response.preferences == {}

    def test_default_preferences(self):
        """Test that preferences defaults to empty dict."""
        response = UserPreferencesResponse(id="user_789")
        assert response.preferences == {}

    def test_required_fields(self):
        """Test that id is required."""
        with pytest.raises(ValidationError):
            UserPreferencesResponse(preferences={"theme": "light"})


class TestMessageResponse:
    """Test MessageResponse schema."""

    def test_valid_message_response(self):
        """Test valid message response."""
        data = {
            "message": "Operation completed successfully",
            "success": True,
        }
        response = MessageResponse(**data)
        assert response.message == "Operation completed successfully"
        assert response.success is True

    def test_default_success_value(self):
        """Test that success defaults to True."""
        response = MessageResponse(message="Test message")
        assert response.success is True

    def test_failure_message(self):
        """Test message response for failure."""
        data = {
            "message": "Operation failed",
            "success": False,
        }
        response = MessageResponse(**data)
        assert response.message == "Operation failed"
        assert response.success is False

    def test_required_fields(self):
        """Test that message is required."""
        with pytest.raises(ValidationError):
            MessageResponse(success=True)

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = MessageResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert example["success"] is True


class TestPasswordResetResponse:
    """Test PasswordResetResponse schema."""

    def test_valid_password_reset_response(self):
        """Test valid password reset response."""
        data = {
            "message": "Password reset email sent successfully",
            "email": "user@example.com",
            "success": True,
        }
        response = PasswordResetResponse(**data)
        assert response.message == "Password reset email sent successfully"
        assert response.email == "user@example.com"
        assert response.success is True

    def test_default_success_value(self):
        """Test that success defaults to True."""
        data = {
            "message": "Reset email sent",
            "email": "test@example.com",
        }
        response = PasswordResetResponse(**data)
        assert response.success is True

    def test_email_validation(self):
        """Test email validation in password reset response."""
        base_data = {
            "message": "Reset email sent",
            "success": True,
        }

        # Valid email
        response = PasswordResetResponse(**{**base_data, "email": "valid@example.com"})
        assert response.email == "valid@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            PasswordResetResponse(**{**base_data, "email": "invalid-email"})

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Missing message
        with pytest.raises(ValidationError):
            PasswordResetResponse(
                email="user@example.com",
                success=True,
            )

        # Missing email
        with pytest.raises(ValidationError):
            PasswordResetResponse(
                message="Reset email sent",
                success=True,
            )

    def test_json_schema_example(self):
        """Test that the model includes proper JSON schema example."""
        schema = PasswordResetResponse.model_json_schema()
        assert "example" in schema
        example = schema["example"]
        assert example["email"] == "user@example.com"
        assert example["success"] is True


class TestAuthResponseIntegration:
    """Test integration scenarios for auth responses."""

    def test_login_success_flow(self):
        """Test successful login response flow."""
        # Token response for successful login
        token_data = {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
            "expires_in": 3600,
        }
        token_response = TokenResponse(**token_data)
        assert token_response.token_type == "bearer"

        # User response with user details
        user_data = {
            "id": "user_123",
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime(2025, 1, 15, 14, 30),
            "updated_at": datetime(2025, 1, 16, 9, 45),
            "preferences": {
                "theme": "dark",
                "language": "en",
            },
        }
        user_response = UserResponse(**user_data)
        assert user_response.username == "john_doe"

    def test_registration_success_flow(self):
        """Test successful registration response flow."""
        # User response for new user
        user_data = {
            "id": "user_new",
            "username": "new_user",
            "email": "new@example.com",
            "full_name": "New User",
            "is_active": True,
            "is_verified": False,  # Email not verified yet
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        user_response = UserResponse(**user_data)
        assert user_response.is_verified is False

        # Success message
        message_response = MessageResponse(
            message=(
                "Registration successful. Please check your email for verification."
            ),
        )
        assert message_response.success is True

    def test_password_reset_flow(self):
        """Test password reset response flow."""
        # Password reset initiation
        reset_response = PasswordResetResponse(
            message="Password reset instructions sent to your email",
            email="user@example.com",
        )
        assert reset_response.email == "user@example.com"

        # Password reset completion
        completion_response = MessageResponse(
            message="Password has been reset successfully",
        )
        assert completion_response.success is True

    def test_error_response_flow(self):
        """Test error response scenarios."""
        # Failed operation message
        error_response = MessageResponse(
            message="Authentication failed. Invalid credentials.",
            success=False,
        )
        assert error_response.success is False

        # Password reset for non-existent user
        reset_error = PasswordResetResponse(
            message=(
                "If an account with this email exists, "
                "you will receive reset instructions"
            ),
            email="nonexistent@example.com",
            success=True,  # Still return success for security
        )
        assert reset_error.success is True  # Don't reveal if email exists

    def test_user_preferences_flow(self):
        """Test user preferences response flow."""
        # Get current preferences
        current_prefs = UserPreferencesResponse(
            id="user_123",
            preferences={
                "theme": "light",
                "language": "en",
                "notifications": True,
            },
        )
        assert current_prefs.preferences["theme"] == "light"

        # Update preferences confirmation
        update_message = MessageResponse(
            message="Preferences updated successfully",
        )
        assert update_message.success is True

        # Get updated preferences
        updated_prefs = UserPreferencesResponse(
            id="user_123",
            preferences={
                "theme": "dark",
                "language": "es",
                "notifications": False,
            },
        )
        assert updated_prefs.preferences["theme"] == "dark"
        assert updated_prefs.preferences["language"] == "es"
