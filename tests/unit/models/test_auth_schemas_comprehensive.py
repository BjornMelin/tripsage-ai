"""Comprehensive tests for Pydantic v2 auth schemas.

This module provides comprehensive test coverage for authentication-related
schemas including request validation, password requirements, and API responses.
"""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from tripsage.api.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    Token,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)


class TestRegisterRequestValidation:
    """Test RegisterRequest model validation."""

    def test_valid_registration(self):
        """Test valid registration data."""
        register = RegisterRequest(
            username="validuser123",
            email="user@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="John Doe",
        )

        assert register.username == "validuser123"
        assert register.email == "user@example.com"
        assert register.full_name == "John Doe"

    def test_username_validation(self):
        """Test username validation rules."""
        # Valid usernames
        valid_usernames = ["user123", "test_user", "user-name", "a" * 50]
        for username in valid_usernames:
            register = RegisterRequest(
                username=username,
                email="user@example.com",
                password="SecurePassword123!",
                password_confirm="SecurePassword123!",
                full_name="John Doe",
            )
            assert register.username == username

    def test_username_invalid_patterns(self):
        """Test invalid username patterns."""
        invalid_usernames = [
            "us",  # Too short
            "a" * 51,  # Too long
            "user@name",  # Invalid character
            "user name",  # Space not allowed
            "user!name",  # Special character not allowed
        ]

        for username in invalid_usernames:
            with pytest.raises(ValidationError):
                RegisterRequest(
                    username=username,
                    email="user@example.com",
                    password="SecurePassword123!",
                    password_confirm="SecurePassword123!",
                    full_name="John Doe",
                )

    def test_email_validation(self):
        """Test email validation."""
        # Valid emails
        valid_emails = [
            "user@example.com",
            "test.user+tag@domain.co.uk",
            "user123@sub.domain.org",
        ]

        for email in valid_emails:
            register = RegisterRequest(
                username="testuser",
                email=email,
                password="SecurePassword123!",
                password_confirm="SecurePassword123!",
                full_name="John Doe",
            )
            assert register.email == email

    def test_email_invalid_formats(self):
        """Test invalid email formats."""
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user@@domain.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError):
                RegisterRequest(
                    username="testuser",
                    email=email,
                    password="SecurePassword123!",
                    password_confirm="SecurePassword123!",
                    full_name="John Doe",
                )

    def test_password_strength_validation(self):
        """Test password strength requirements."""
        # Test weak passwords that should fail
        weak_passwords = [
            (
                "password",
                "Password must contain",
            ),  # No uppercase, numbers, or special chars
            (
                "PASSWORD",
                "Password must contain",
            ),  # No lowercase, numbers, or special chars
            ("Password", "Password must contain"),  # No numbers or special chars
            ("Pass123", "String should have at least 8 characters"),  # Too short
            ("password123", "Password must contain"),  # No uppercase or special chars
            ("PASSWORD123", "Password must contain"),  # No lowercase or special chars
        ]

        for password, expected_error in weak_passwords:
            with pytest.raises(ValidationError, match=expected_error):
                RegisterRequest(
                    username="testuser",
                    email="user@example.com",
                    password=password,
                    password_confirm=password,
                    full_name="John Doe",
                )

    def test_password_match_validation(self):
        """Test password confirmation matching."""
        with pytest.raises(ValidationError, match="Passwords do not match"):
            RegisterRequest(
                username="testuser",
                email="user@example.com",
                password="SecurePassword123!",
                password_confirm="DifferentPassword123!",
                full_name="John Doe",
            )

    def test_full_name_validation(self):
        """Test full name validation."""
        # Valid full names
        valid_names = ["John Doe", "María García", "李小明", "A", "A" * 100]

        for name in valid_names:
            register = RegisterRequest(
                username="testuser",
                email="user@example.com",
                password="SecurePassword123!",
                password_confirm="SecurePassword123!",
                full_name=name,
            )
            assert register.full_name == name

    def test_full_name_invalid_length(self):
        """Test invalid full name lengths."""
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                email="user@example.com",
                password="SecurePassword123!",
                password_confirm="SecurePassword123!",
                full_name="",  # Empty string
            )

        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser",
                email="user@example.com",
                password="SecurePassword123!",
                password_confirm="SecurePassword123!",
                full_name="A" * 101,  # Too long
            )

    @given(
        username=st.text(
            min_size=3,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=["Lu", "Ll", "Nd"], whitelist_characters="_-"
            ),
        ),
        full_name=st.text(min_size=1, max_size=100),
    )
    def test_register_request_property_validation(self, username: str, full_name: str):
        """Test registration with property-based testing."""
        try:
            register = RegisterRequest(
                username=username,
                email="test@example.com",
                password="SecurePassword123!",
                password_confirm="SecurePassword123!",
                full_name=full_name,
            )

            assert len(register.username) >= 3
            assert len(register.username) <= 50
            assert len(register.full_name) >= 1
            assert len(register.full_name) <= 100
            assert register.email == "test@example.com"
        except ValidationError:
            # Some generated strings might not match the pattern
            pass


class TestLoginRequestValidation:
    """Test LoginRequest model validation."""

    def test_valid_login(self):
        """Test valid login data."""
        login = LoginRequest(
            username="testuser",
            password="password123",
            remember_me=True,
        )

        assert login.username == "testuser"
        assert login.password == "password123"
        assert login.remember_me is True

    def test_login_defaults(self):
        """Test login default values."""
        login = LoginRequest(
            username="testuser",
            password="password123",
        )

        assert login.remember_me is False

    def test_email_as_username(self):
        """Test using email as username."""
        login = LoginRequest(
            username="user@example.com",
            password="password123",
        )

        assert login.username == "user@example.com"


class TestChangePasswordRequestValidation:
    """Test ChangePasswordRequest model validation."""

    def test_valid_password_change(self):
        """Test valid password change."""
        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
            new_password_confirm="NewPassword456!",
        )

        assert request.current_password == "OldPassword123!"
        assert request.new_password == "NewPassword456!"
        assert request.new_password_confirm == "NewPassword456!"

    def test_new_password_strength_validation(self):
        """Test new password strength requirements."""
        with pytest.raises(ValidationError, match="Password must contain"):
            ChangePasswordRequest(
                current_password="OldPassword123!",
                new_password="weakpass",
                new_password_confirm="weakpass",
            )

    def test_new_password_mismatch(self):
        """Test new password confirmation mismatch."""
        with pytest.raises(ValidationError, match="Passwords do not match"):
            ChangePasswordRequest(
                current_password="OldPassword123!",
                new_password="NewPassword456!",
                new_password_confirm="DifferentPassword789!",
            )

    def test_same_current_and_new_password(self):
        """Test validation when new password is same as current."""
        with pytest.raises(ValidationError, match="New password must be different"):
            ChangePasswordRequest(
                current_password="SamePassword123!",
                new_password="SamePassword123!",
                new_password_confirm="SamePassword123!",
            )


class TestResetPasswordRequestValidation:
    """Test ResetPasswordRequest model validation."""

    def test_valid_password_reset(self):
        """Test valid password reset."""
        request = ResetPasswordRequest(
            token="reset-token-12345",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )

        assert request.token == "reset-token-12345"
        assert request.new_password == "NewPassword123!"

    def test_reset_password_strength_validation(self):
        """Test reset password strength requirements."""
        with pytest.raises(ValidationError, match="Password must contain"):
            ResetPasswordRequest(
                token="reset-token-12345",
                new_password="weakpass",
                new_password_confirm="weakpass",
            )

    def test_reset_password_mismatch(self):
        """Test reset password confirmation mismatch."""
        with pytest.raises(ValidationError, match="Passwords do not match"):
            ResetPasswordRequest(
                token="reset-token-12345",
                new_password="NewPassword123!",
                new_password_confirm="DifferentPassword456!",
            )


class TestRefreshTokenRequestValidation:
    """Test RefreshTokenRequest model validation."""

    def test_valid_refresh_token(self):
        """Test valid refresh token request."""
        request = RefreshTokenRequest(
            refresh_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        )

        assert request.refresh_token == "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."


class TestForgotPasswordRequestValidation:
    """Test ForgotPasswordRequest model validation."""

    def test_valid_forgot_password(self):
        """Test valid forgot password request."""
        request = ForgotPasswordRequest(email="user@example.com")
        assert request.email == "user@example.com"

    def test_invalid_forgot_password_email(self):
        """Test invalid email in forgot password request."""
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="invalid-email")


class TestTokenValidation:
    """Test Token model validation."""

    def test_valid_token(self):
        """Test valid token creation."""
        expires_at = datetime.utcnow() + timedelta(hours=1)
        token = Token(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            token_type="bearer",
            expires_at=expires_at,
        )

        assert token.access_token == "access-token-123"
        assert token.refresh_token == "refresh-token-456"
        assert token.token_type == "bearer"
        assert token.expires_at == expires_at

    def test_token_defaults(self):
        """Test token default values."""
        expires_at = datetime.utcnow() + timedelta(hours=1)
        token = Token(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            expires_at=expires_at,
        )

        assert token.token_type == "bearer"


class TestUserResponseValidation:
    """Test UserResponse model validation."""

    def test_valid_user_response(self):
        """Test valid user response."""
        now = datetime.utcnow()
        user = UserResponse(
            id="user-123",
            username="testuser",
            email="user@example.com",
            full_name="John Doe",
            created_at=now,
            updated_at=now,
            is_active=True,
            is_verified=True,
            preferences={"theme": "dark", "language": "en"},
        )

        assert user.id == "user-123"
        assert user.username == "testuser"
        assert user.email == "user@example.com"
        assert user.full_name == "John Doe"
        assert user.is_active is True
        assert user.is_verified is True
        assert user.preferences == {"theme": "dark", "language": "en"}

    def test_user_response_defaults(self):
        """Test user response default values."""
        now = datetime.utcnow()
        user = UserResponse(
            id="user-123",
            email="user@example.com",
            created_at=now,
            updated_at=now,
        )

        assert user.username is None
        assert user.full_name is None
        assert user.is_active is True
        assert user.is_verified is False
        assert user.preferences is None

    def test_user_response_optional_fields(self):
        """Test user response with optional fields."""
        now = datetime.utcnow()
        user = UserResponse(
            id="user-123",
            email="user@example.com",
            created_at=now,
            updated_at=now,
            full_name="Jane Smith",
            preferences=None,
        )

        assert user.full_name == "Jane Smith"
        assert user.preferences is None


class TestAuthResponseValidation:
    """Test AuthResponse model validation."""

    def test_valid_auth_response(self):
        """Test valid authentication response."""
        now = datetime.utcnow()

        user = UserResponse(
            id="user-123",
            username="testuser",
            email="user@example.com",
            created_at=now,
            updated_at=now,
        )

        token = Token(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            expires_at=now + timedelta(hours=1),
        )

        auth_response = AuthResponse(user=user, tokens=token)

        assert auth_response.user.id == "user-123"
        assert auth_response.tokens.access_token == "access-token-123"

    def test_auth_response_serialization(self):
        """Test auth response JSON serialization."""
        now = datetime.utcnow()

        user = UserResponse(
            id="user-123",
            username="testuser",
            email="user@example.com",
            created_at=now,
            updated_at=now,
        )

        token = Token(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            expires_at=now + timedelta(hours=1),
        )

        auth_response = AuthResponse(user=user, tokens=token)

        # Test JSON serialization
        json_data = auth_response.model_dump_json()
        parsed = json.loads(json_data)

        assert parsed["user"]["id"] == "user-123"
        assert parsed["tokens"]["access_token"] == "access-token-123"
        assert parsed["tokens"]["token_type"] == "bearer"


class TestTokenResponseValidation:
    """Test TokenResponse model validation."""

    def test_valid_token_response(self):
        """Test valid token response."""
        now = datetime.utcnow()

        user = UserResponse(
            id="user-123",
            username="testuser",
            email="user@example.com",
            created_at=now,
            updated_at=now,
        )

        token_response = TokenResponse(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            token_type="bearer",
            expires_in=3600,
            user=user,
        )

        assert token_response.access_token == "access-token-123"
        assert token_response.refresh_token == "refresh-token-456"
        assert token_response.expires_in == 3600
        assert token_response.user.id == "user-123"

    def test_token_response_defaults(self):
        """Test token response default values."""
        now = datetime.utcnow()

        user = UserResponse(
            id="user-123",
            email="user@example.com",
            created_at=now,
            updated_at=now,
        )

        token_response = TokenResponse(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            expires_in=3600,
            user=user,
        )

        assert token_response.token_type == "bearer"


class TestMessageResponseValidation:
    """Test MessageResponse model validation."""

    def test_valid_message_response(self):
        """Test valid message response."""
        message = MessageResponse(
            message="Operation completed successfully",
            success=True,
            details={"operation_id": "12345", "timestamp": "2024-01-01T00:00:00Z"},
        )

        assert message.message == "Operation completed successfully"
        assert message.success is True
        assert message.details["operation_id"] == "12345"

    def test_message_response_defaults(self):
        """Test message response default values."""
        message = MessageResponse(message="Test message")

        assert message.success is True
        assert message.details is None

    def test_error_message_response(self):
        """Test error message response."""
        message = MessageResponse(
            message="Operation failed",
            success=False,
            details={"error_code": "VALIDATION_ERROR", "field": "username"},
        )

        assert message.message == "Operation failed"
        assert message.success is False
        assert message.details["error_code"] == "VALIDATION_ERROR"


class TestPasswordResetResponseValidation:
    """Test PasswordResetResponse model validation."""

    def test_valid_password_reset_response(self):
        """Test valid password reset response."""
        expires_at = datetime.utcnow() + timedelta(hours=1)

        response = PasswordResetResponse(
            message="Password reset link sent",
            email="user@example.com",
            reset_token_expires_at=expires_at,
        )

        assert response.message == "Password reset link sent"
        assert response.email == "user@example.com"
        assert response.reset_token_expires_at == expires_at

    def test_password_reset_response_without_expiry(self):
        """Test password reset response without expiry."""
        response = PasswordResetResponse(
            message="Password reset link sent",
            email="user@example.com",
        )

        assert response.message == "Password reset link sent"
        assert response.email == "user@example.com"
        assert response.reset_token_expires_at is None


class TestUserPreferencesResponseValidation:
    """Test UserPreferencesResponse model validation."""

    def test_valid_preferences_response(self):
        """Test valid user preferences response."""
        now = datetime.utcnow()
        preferences = {
            "theme": "dark",
            "language": "en",
            "notifications": True,
            "currency": "USD",
        }

        response = UserPreferencesResponse(
            user_id="user-123",
            preferences=preferences,
            updated_at=now,
        )

        assert response.user_id == "user-123"
        assert response.preferences == preferences
        assert response.updated_at == now

    def test_empty_preferences(self):
        """Test user preferences with empty dictionary."""
        now = datetime.utcnow()

        response = UserPreferencesResponse(
            user_id="user-123",
            preferences={},
            updated_at=now,
        )

        assert response.preferences == {}


class TestAuthSchemaIntegration:
    """Test auth schema integration scenarios."""

    def test_complete_registration_flow(self):
        """Test complete registration to auth response flow."""
        # 1. Registration request
        register_request = RegisterRequest(
            username="newuser",
            email="newuser@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="New User",
        )

        # 2. Create user response (simulating successful registration)
        now = datetime.utcnow()
        user_response = UserResponse(
            id=str(uuid4()),
            username=register_request.username,
            email=register_request.email,
            full_name=register_request.full_name,
            created_at=now,
            updated_at=now,
            is_active=True,
            is_verified=False,
        )

        # 3. Create tokens
        token = Token(
            access_token="access-token-123",
            refresh_token="refresh-token-456",
            expires_at=now + timedelta(hours=1),
        )

        # 4. Create auth response
        auth_response = AuthResponse(user=user_response, tokens=token)

        # Verify flow
        assert auth_response.user.username == register_request.username
        assert auth_response.user.email == register_request.email
        assert auth_response.user.full_name == register_request.full_name
        assert auth_response.tokens.access_token == "access-token-123"

    def test_password_change_flow(self):
        """Test password change flow."""
        # 1. Change password request
        change_request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
            new_password_confirm="NewPassword456!",
        )

        # 2. Success response
        success_response = MessageResponse(
            message="Password changed successfully",
            success=True,
            details={"changed_at": datetime.utcnow().isoformat()},
        )

        assert change_request.new_password != change_request.current_password
        assert success_response.success is True

    def test_forgot_password_flow(self):
        """Test forgot password flow."""
        # 1. Forgot password request
        forgot_request = ForgotPasswordRequest(email="user@example.com")

        # 2. Reset response
        reset_response = PasswordResetResponse(
            message="Password reset link sent to your email",
            email=forgot_request.email,
            reset_token_expires_at=datetime.utcnow() + timedelta(hours=1),
        )

        assert reset_response.email == forgot_request.email
        assert "reset link sent" in reset_response.message.lower()

    def test_token_refresh_flow(self):
        """Test token refresh flow."""
        # 1. Refresh token request
        refresh_request = RefreshTokenRequest(refresh_token="refresh-token-456")

        # 2. New token response
        now = datetime.utcnow()
        user = UserResponse(
            id="user-123",
            email="user@example.com",
            created_at=now,
            updated_at=now,
        )

        new_token_response = TokenResponse(
            access_token="new-access-token-789",
            refresh_token=refresh_request.refresh_token,
            expires_in=3600,
            user=user,
        )

        assert new_token_response.access_token != refresh_request.refresh_token
        assert new_token_response.refresh_token == refresh_request.refresh_token

    @settings(max_examples=20, deadline=None)
    @given(
        username=st.text(
            min_size=3,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=["Lu", "Ll", "Nd"], whitelist_characters="_-"
            ),
        ),
        full_name=st.text(min_size=1, max_size=100),
        preferences=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.booleans(), st.integers()),
            min_size=0,
            max_size=10,
        ),
    )
    def test_user_response_property_validation(
        self, username: str, full_name: str, preferences: dict
    ):
        """Test user response with property-based testing."""
        try:
            now = datetime.utcnow()
            user = UserResponse(
                id=str(uuid4()),
                username=username,
                email="test@example.com",
                full_name=full_name,
                created_at=now,
                updated_at=now,
                preferences=preferences,
            )

            assert user.id is not None
            assert user.email == "test@example.com"
            assert len(user.username) >= 3 if user.username else True
            assert len(user.username) <= 50 if user.username else True
            assert len(user.full_name) >= 1 if user.full_name else True
            assert len(user.full_name) <= 100 if user.full_name else True
            assert isinstance(user.preferences, dict) if user.preferences else True
        except ValidationError:
            # Some generated data might not be valid
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
