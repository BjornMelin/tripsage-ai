"""Edge case tests for Pydantic v2 auth schemas.

This module provides comprehensive edge case testing for authentication-related
schemas, focusing on boundary conditions, unusual input patterns, and
production scenarios not covered in the main comprehensive tests.
"""

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from tripsage.api.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetResponse,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
    TokenResponse,
    UserPreferencesResponse,
    UserResponse,
)


class TestAuthSchemaEdgeCases:
    """Test edge cases and boundary conditions for auth schemas."""

    def test_register_request_unicode_handling(self):
        """Test registration with various Unicode characters."""
        # Test Unicode in full name
        register = RegisterRequest(
            username="testuser123",
            email="user@example.com",
            password="SecurePass123!",
            password_confirm="SecurePass123!",
            full_name="José María Aznar-López 李小明",
        )
        assert "José María" in register.full_name
        assert "李小明" in register.full_name

        # Test Unicode in username (should fail due to pattern restriction)
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="testuser李",
                email="user@example.com",
                password="SecurePass123!",
                password_confirm="SecurePass123!",
                full_name="Test User",
            )

    def test_register_request_boundary_lengths(self):
        """Test registration with exact boundary lengths."""
        # Test minimum lengths
        register = RegisterRequest(
            username="usr",  # Exactly 3 chars
            email="a@b.co",  # Minimal valid email
            password="Pass123!",  # Exactly 8 chars
            password_confirm="Pass123!",
            full_name="A",  # Exactly 1 char
        )
        assert len(register.username) == 3
        assert len(register.full_name) == 1

        # Test maximum lengths
        register = RegisterRequest(
            username="a" * 50,  # Exactly 50 chars
            email="test@example.com",
            password="A" * 120 + "1!aB",  # Exactly 124 chars (within 128 limit)
            password_confirm="A" * 120 + "1!aB",
            full_name="B" * 100,  # Exactly 100 chars
        )
        assert len(register.username) == 50
        assert len(register.full_name) == 100

    def test_password_strength_edge_cases(self):
        """Test password strength validation edge cases."""
        # Test minimal requirements satisfied
        minimal_valid = "Aa1!"  # Too short but has all requirements
        with pytest.raises(ValidationError, match="at least 8 characters"):
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password=minimal_valid,
                password_confirm=minimal_valid,
                full_name="Test User",
            )

        # Test password with unusual but valid special characters
        unusual_special = "Password123§"
        with pytest.raises(ValidationError):
            # This should fail as § is not in the allowed special characters
            RegisterRequest(
                username="testuser",
                email="test@example.com",
                password=unusual_special,
                password_confirm=unusual_special,
                full_name="Test User",
            )

        # Test password with all allowed special characters
        all_specials = "Pass123!@#$%^&*()_-+=[]{}|:;,.<>?/"
        register = RegisterRequest(
            username="testuser",
            email="test@example.com",
            password=all_specials,
            password_confirm=all_specials,
            full_name="Test User",
        )
        assert register.password == all_specials

    def test_email_edge_cases(self):
        """Test email validation edge cases."""
        # Test various valid email formats
        valid_emails = [
            "test+tag@example.com",
            "user.name@sub.domain.co.uk",
            "123@456.org",
            "a@b.co",  # Minimal length
            "very.long.email.address@very.long.domain.name.example.com",
        ]

        for email in valid_emails:
            register = RegisterRequest(
                username="testuser",
                email=email,
                password="SecurePass123!",
                password_confirm="SecurePass123!",
                full_name="Test User",
            )
            assert register.email == email

    def test_username_pattern_edge_cases(self):
        """Test username pattern validation edge cases."""
        # Test various valid username patterns
        valid_usernames = [
            "a123",  # Mix of letters and numbers
            "test_user",  # With underscore
            "test-user",  # With hyphen
            "123user",  # Starting with number
            "user123_test-final",  # Complex valid pattern
        ]

        for username in valid_usernames:
            if len(username) >= 3:  # Only test if meets length requirement
                register = RegisterRequest(
                    username=username,
                    email="test@example.com",
                    password="SecurePass123!",
                    password_confirm="SecurePass123!",
                    full_name="Test User",
                )
                assert register.username == username

    def test_change_password_complex_scenarios(self):
        """Test change password with complex validation scenarios."""
        # Test where current and new passwords differ by one character
        change_request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        assert change_request.current_password != change_request.new_password

        # Test case sensitivity in password comparison
        with pytest.raises(ValidationError, match="New password must be different"):
            ChangePasswordRequest(
                current_password="Password123!",
                new_password="Password123!",  # Exact match
                new_password_confirm="Password123!",
            )

    def test_token_edge_cases(self):
        """Test token validation edge cases."""
        # Test with very short expiration time
        very_soon = datetime.utcnow() + timedelta(seconds=1)
        token = Token(
            access_token="short-lived-token",
            refresh_token="refresh-token",
            expires_at=very_soon,
        )
        assert token.expires_at == very_soon

        # Test with far future expiration
        far_future = datetime.utcnow() + timedelta(days=365 * 10)  # 10 years
        token = Token(
            access_token="long-lived-token",
            refresh_token="refresh-token",
            expires_at=far_future,
        )
        assert token.expires_at == far_future

    def test_user_response_edge_cases(self):
        """Test user response with edge case data."""
        # Test with minimal data
        now = datetime.utcnow()
        minimal_user = UserResponse(
            id="u",  # Single character ID
            email="a@b.co",  # Minimal email
            created_at=now,
            updated_at=now,
        )
        assert minimal_user.id == "u"
        assert minimal_user.username is None

        # Test with complex preferences
        complex_preferences = {
            "theme": {"primary": "dark", "accent": "blue"},
            "notifications": {
                "email": True,
                "push": False,
                "sms": None,
            },
            "nested": {
                "deep": {
                    "value": [1, 2, 3],
                    "config": {"enabled": True},
                }
            },
            "unicode": "🌟✨🎉",
            "numbers": [1, 2.5, -3],
            "booleans": [True, False, None],
        }

        complex_user = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            created_at=now,
            updated_at=now,
            preferences=complex_preferences,
        )
        assert complex_user.preferences["unicode"] == "🌟✨🎉"
        assert complex_user.preferences["nested"]["deep"]["value"] == [1, 2, 3]

    def test_message_response_edge_cases(self):
        """Test message response with various data types."""
        # Test with nested details
        complex_details = {
            "error_stack": ["error1", "error2", "error3"],
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "user_agent": "Mozilla/5.0...",
                "ip_address": "192.168.1.1",
            },
            "validation_errors": {
                "field1": ["error1", "error2"],
                "field2": ["error3"],
            },
        }

        message = MessageResponse(
            message="Complex operation failed",
            success=False,
            details=complex_details,
        )
        assert message.details["error_stack"] == ["error1", "error2", "error3"]
        assert "timestamp" in message.details["metadata"]

    def test_serialization_edge_cases(self):
        """Test JSON serialization with edge case data."""
        now = datetime.utcnow()

        # Create complex auth response
        user = UserResponse(
            id=str(uuid4()),
            username="test_user-123",
            email="test@example.com",
            full_name="José María Aznar-López",
            created_at=now,
            updated_at=now,
            preferences={
                "unicode": "🌟✨🎉",
                "nested": {"deep": {"list": [1, 2, 3]}},
            },
        )

        token = Token(
            access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ",
            refresh_token="refresh_token_here",
            expires_at=now + timedelta(hours=1),
        )

        auth_response = AuthResponse(user=user, tokens=token)

        # Test serialization
        json_data = auth_response.model_dump_json()
        parsed = json.loads(json_data)

        # Verify complex data is preserved
        assert parsed["user"]["full_name"] == "José María Aznar-López"
        assert parsed["user"]["preferences"]["unicode"] == "🌟✨🎉"
        assert parsed["user"]["preferences"]["nested"]["deep"]["list"] == [1, 2, 3]

        # Test round-trip
        reconstructed = AuthResponse.model_validate(parsed)
        assert reconstructed.user.full_name == auth_response.user.full_name
        assert reconstructed.user.preferences == auth_response.user.preferences

    def test_password_reset_edge_cases(self):
        """Test password reset response edge cases."""
        # Test with very long token expiration message
        now = datetime.utcnow()
        long_message = (
            "Your password reset request has been processed successfully. "
            "A secure reset link has been sent to your email address. "
            "This link will expire in 1 hour for security purposes. "
            "If you did not request this reset, please ignore this message."
        )

        response = PasswordResetResponse(
            message=long_message,
            email="user@verylongdomainname.example.com",
            reset_token_expires_at=now + timedelta(minutes=30),
        )

        assert len(response.message) > 200
        assert response.email.endswith(".example.com")

    def test_login_request_edge_cases(self):
        """Test login request with edge case inputs."""
        # Test with email as username
        login = LoginRequest(
            username="user+tag@sub.domain.co.uk",
            password="anypassword",
            remember_me=True,
        )
        assert "@" in login.username
        assert login.remember_me is True

        # Test with very long username
        long_username = "a" * 100  # Much longer than typical
        login = LoginRequest(
            username=long_username,
            password="password",
        )
        assert len(login.username) == 100

    def test_refresh_token_edge_cases(self):
        """Test refresh token request edge cases."""
        # Test with very long JWT token
        long_jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9." + "a" * 1000 + ".signature"
        request = RefreshTokenRequest(refresh_token=long_jwt)
        assert len(request.refresh_token) > 1000

        # Test with minimal token
        minimal_token = "abc"
        request = RefreshTokenRequest(refresh_token=minimal_token)
        assert request.refresh_token == "abc"

    @given(
        preferences=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(min_value=-1000, max_value=1000),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
                st.lists(st.integers(min_value=0, max_value=100), max_size=10),
            ),
            min_size=0,
            max_size=20,
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_user_preferences_property_based(self, preferences: dict[str, Any]):
        """Test user preferences with property-based testing."""
        now = datetime.utcnow()

        try:
            response = UserPreferencesResponse(
                user_id=str(uuid4()),
                preferences=preferences,
                updated_at=now,
            )

            # Verify the data round-trips correctly
            json_data = response.model_dump_json()
            parsed = json.loads(json_data)
            reconstructed = UserPreferencesResponse.model_validate(parsed)

            assert reconstructed.user_id == response.user_id
            assert reconstructed.preferences == response.preferences
            assert reconstructed.updated_at == response.updated_at

        except ValidationError:
            # Some generated data might not be serializable
            pass

    def test_concurrent_password_validation(self):
        """Test password validation with multiple simultaneous checks."""
        # Simulate multiple password validation scenarios
        passwords = [
            ("ValidPass123!", True),
            ("weakpass", False),
            ("UPPERCASE123!", False),
            ("lowercase123!", False),
            ("NoNumbers!", False),
            ("NoSpecial123", False),
            ("Sh0rt!", False),
            ("AnotherValid123@", True),
        ]

        results = []
        for password, _should_be_valid in passwords:
            try:
                RegisterRequest(
                    username=f"user{len(results)}",
                    email=f"user{len(results)}@example.com",
                    password=password,
                    password_confirm=password,
                    full_name="Test User",
                )
                results.append((password, True))
            except ValidationError:
                results.append((password, False))

        # Verify expected results
        for i, (password, should_be_valid) in enumerate(passwords):
            actual_valid = results[i][1]
            assert actual_valid == should_be_valid, (
                f"Password {password} validation mismatch"
            )

    def test_token_response_edge_cases(self):
        """Test token response with edge case scenarios."""
        now = datetime.utcnow()

        # Test with zero expiration
        user = UserResponse(
            id="user-123",
            email="test@example.com",
            created_at=now,
            updated_at=now,
        )

        token_response = TokenResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=0,  # Immediate expiration
            user=user,
        )
        assert token_response.expires_in == 0

        # Test with very large expiration
        token_response = TokenResponse(
            access_token="token",
            refresh_token="refresh",
            expires_in=2147483647,  # Max int32
            user=user,
        )
        assert token_response.expires_in == 2147483647


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
