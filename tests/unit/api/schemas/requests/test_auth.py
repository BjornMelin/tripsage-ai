"""
Tests for authentication request schemas.

This module tests the Pydantic models used for validating
authentication requests from the Next.js frontend.
"""

import pytest
from pydantic import ValidationError

from api.schemas.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)


class TestRegisterUserRequest:
    """Test RegisterUserRequest schema."""

    def test_valid_registration(self):
        """Test valid user registration request."""
        data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "full_name": "John Doe",
        }
        request = RegisterUserRequest(**data)
        assert request.username == "john_doe"
        assert request.email == "john@example.com"
        assert request.full_name == "John Doe"

    def test_username_validation(self):
        """Test username validation rules."""
        base_data = {
            "email": "john@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "full_name": "John Doe",
        }

        # Valid usernames
        valid_usernames = ["john_doe", "user123", "test-user", "a_b_c"]
        for username in valid_usernames:
            data = {**base_data, "username": username}
            request = RegisterUserRequest(**data)
            assert request.username == username

        # Invalid usernames
        invalid_usernames = ["ab", "a" * 51, "user space", "user@domain"]
        for username in invalid_usernames:
            data = {**base_data, "username": username}
            with pytest.raises(ValidationError):
                RegisterUserRequest(**data)

    def test_email_validation(self):
        """Test email validation."""
        base_data = {
            "username": "john_doe",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "full_name": "John Doe",
        }

        # Valid emails
        valid_emails = [
            "user@example.com",
            "test+tag@domain.co.uk",
            "user.name@sub.domain.com",
        ]
        for email in valid_emails:
            data = {**base_data, "email": email}
            request = RegisterUserRequest(**data)
            assert request.email == email

        # Invalid emails
        invalid_emails = [
            "invalid-email",
            "@domain.com",
            "user@",
            "user space@domain.com",
        ]
        for email in invalid_emails:
            data = {**base_data, "email": email}
            with pytest.raises(ValidationError):
                RegisterUserRequest(**data)

    def test_password_length_validation(self):
        """Test password length validation."""
        base_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password_confirm": "SecurePassword123!",
            "full_name": "John Doe",
        }

        # Too short password
        with pytest.raises(ValidationError):
            RegisterUserRequest(
                **{**base_data, "password": "Short1!", "password_confirm": "Short1!"}
            )

        # Too long password
        long_password = "A" * 95 + "1b!"
        with pytest.raises(ValidationError):
            RegisterUserRequest(
                **{
                    **base_data,
                    "password": long_password,
                    "password_confirm": long_password,
                }
            )

    def test_password_strength_validation(self):
        """Test password strength requirements."""
        base_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "full_name": "John Doe",
        }

        # Missing uppercase
        with pytest.raises(ValidationError, match="at least one uppercase letter"):
            RegisterUserRequest(
                **{
                    **base_data,
                    "password": "mysecure123!",
                    "password_confirm": "mysecure123!",
                }
            )

        # Missing lowercase
        with pytest.raises(ValidationError, match="at least one lowercase letter"):
            RegisterUserRequest(
                **{
                    **base_data,
                    "password": "MYSECURE123!",
                    "password_confirm": "MYSECURE123!",
                }
            )

        # Missing digit
        with pytest.raises(ValidationError, match="at least one number"):
            RegisterUserRequest(
                **{
                    **base_data,
                    "password": "MySecurePass!",
                    "password_confirm": "MySecurePass!",
                }
            )

        # Missing special character
        with pytest.raises(ValidationError, match="at least one special character"):
            RegisterUserRequest(
                **{
                    **base_data,
                    "password": "MySecure123",
                    "password_confirm": "MySecure123",
                }
            )

    def test_password_confirmation_validation(self):
        """Test password confirmation matching."""
        base_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePassword123!",
            "full_name": "John Doe",
        }

        # Passwords don't match
        with pytest.raises(ValidationError, match="Passwords do not match"):
            RegisterUserRequest(
                **{
                    **base_data,
                    "password_confirm": "DifferentPassword456#",
                }
            )

    def test_full_name_validation(self):
        """Test full name validation."""
        base_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

        # Too short full name
        with pytest.raises(ValidationError):
            RegisterUserRequest(**{**base_data, "full_name": ""})

        # Too long full name
        with pytest.raises(ValidationError):
            RegisterUserRequest(**{**base_data, "full_name": "A" * 101})

        # Valid full names
        valid_names = ["John Doe", "María García", "李小明", "A"]
        for name in valid_names:
            request = RegisterUserRequest(**{**base_data, "full_name": name})
            assert request.full_name == name


class TestLoginRequest:
    """Test LoginRequest schema."""

    def test_valid_login(self):
        """Test valid login request."""
        data = {
            "username": "john_doe",
            "password": "password123",
            "remember_me": True,
        }
        request = LoginRequest(**data)
        assert request.username == "john_doe"
        assert request.password == "password123"
        assert request.remember_me is True

    def test_login_with_email(self):
        """Test login with email as username."""
        data = {
            "username": "john@example.com",
            "password": "password123",
        }
        request = LoginRequest(**data)
        assert request.username == "john@example.com"
        assert request.remember_me is False  # Default value

    def test_required_fields(self):
        """Test that required fields are enforced."""
        # Missing username
        with pytest.raises(ValidationError):
            LoginRequest(password="password123")

        # Missing password
        with pytest.raises(ValidationError):
            LoginRequest(username="john_doe")


class TestRefreshTokenRequest:
    """Test RefreshTokenRequest schema."""

    def test_valid_refresh_token(self):
        """Test valid refresh token request."""
        token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        request = RefreshTokenRequest(refresh_token=token)
        assert request.refresh_token == token

    def test_required_field(self):
        """Test that refresh token is required."""
        with pytest.raises(ValidationError):
            RefreshTokenRequest()


class TestChangePasswordRequest:
    """Test ChangePasswordRequest schema."""

    def test_valid_password_change(self):
        """Test valid password change request."""
        data = {
            "current_password": "OldPassword123!",
            "new_password": "NewSecurePass456#",
            "new_password_confirm": "NewSecurePass456#",
        }
        request = ChangePasswordRequest(**data)
        assert request.current_password == "OldPassword123!"
        assert request.new_password == "NewSecurePass456#"

    def test_new_password_strength_validation(self):
        """Test new password strength validation."""
        base_data = {
            "current_password": "OldPassword123!",
            "new_password_confirm": "WeakPassword",
        }

        # Weak new password
        with pytest.raises(ValidationError, match="at least one special character"):
            ChangePasswordRequest(
                **{
                    **base_data,
                    "new_password": "WeakPassword",
                }
            )

    def test_new_password_confirmation_validation(self):
        """Test new password confirmation matching."""
        data = {
            "current_password": "OldPassword123!",
            "new_password": "NewSecurePass456#",
            "new_password_confirm": "DifferentPassword789$",
        }
        with pytest.raises(ValidationError, match="Passwords do not match"):
            ChangePasswordRequest(**data)

    def test_password_difference_validation(self):
        """Test that new password must be different from current."""
        password = "SamePassword123!"
        data = {
            "current_password": password,
            "new_password": password,
            "new_password_confirm": password,
        }
        with pytest.raises(ValidationError, match="New password must be different"):
            ChangePasswordRequest(**data)

    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            ChangePasswordRequest()

        with pytest.raises(ValidationError):
            ChangePasswordRequest(current_password="password")


class TestForgotPasswordRequest:
    """Test ForgotPasswordRequest schema."""

    def test_valid_forgot_password(self):
        """Test valid forgot password request."""
        email = "john@example.com"
        request = ForgotPasswordRequest(email=email)
        assert request.email == email

    def test_email_validation(self):
        """Test email validation for forgot password."""
        # Invalid email
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="invalid-email")

    def test_required_field(self):
        """Test that email is required."""
        with pytest.raises(ValidationError):
            ForgotPasswordRequest()


class TestResetPasswordRequest:
    """Test ResetPasswordRequest schema."""

    def test_valid_password_reset(self):
        """Test valid password reset request."""
        data = {
            "token": "reset-token-123",
            "new_password": "NewSecurePass456#",
            "new_password_confirm": "NewSecurePass456#",
        }
        request = ResetPasswordRequest(**data)
        assert request.token == "reset-token-123"
        assert request.new_password == "NewSecurePass456#"

    def test_password_strength_validation(self):
        """Test password strength validation for reset."""
        base_data = {
            "token": "reset-token-123",
            "new_password_confirm": "weakpassword",
        }

        with pytest.raises(ValidationError, match="at least one uppercase letter"):
            ResetPasswordRequest(
                **{
                    **base_data,
                    "new_password": "weakpassword",
                }
            )

    def test_password_confirmation_validation(self):
        """Test password confirmation for reset."""
        data = {
            "token": "reset-token-123",
            "new_password": "NewSecurePass456#",
            "new_password_confirm": "DifferentPassword789$",
        }
        with pytest.raises(ValidationError, match="Passwords do not match"):
            ResetPasswordRequest(**data)

    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest()

        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="token")


class TestAuthRequestIntegration:
    """Test integration scenarios for auth requests."""

    def test_registration_to_login_flow(self):
        """Test a complete registration to login flow."""
        # Registration data
        reg_data = {
            "username": "newuser123",
            "email": "newuser@example.com",
            "password": "MySecurePass123!",
            "password_confirm": "MySecurePass123!",
            "full_name": "New User",
        }

        # Valid registration
        reg_request = RegisterUserRequest(**reg_data)
        assert reg_request.username == "newuser123"

        # Subsequent login with username
        login_data = {
            "username": "newuser123",
            "password": "MySecurePass123!",
            "remember_me": True,
        }
        login_request = LoginRequest(**login_data)
        assert login_request.username == "newuser123"

        # Subsequent login with email
        login_email_data = {
            "username": "newuser@example.com",
            "password": "MySecurePass123!",
        }
        login_email_request = LoginRequest(**login_email_data)
        assert login_email_request.username == "newuser@example.com"

    def test_password_change_flow(self):
        """Test a complete password change flow."""
        # Initial password change
        change_data = {
            "current_password": "OldPassword123!",
            "new_password": "NewSecurePass456#",
            "new_password_confirm": "NewSecurePass456#",
        }
        change_request = ChangePasswordRequest(**change_data)
        assert change_request.new_password == "NewSecurePass456#"

        # Subsequent login with new password
        login_data = {
            "username": "user",
            "password": "NewSecurePass456#",
        }
        login_request = LoginRequest(**login_data)
        assert login_request.password == "NewSecurePass456#"

    def test_password_reset_flow(self):
        """Test a complete password reset flow."""
        # Forgot password request
        forgot_request = ForgotPasswordRequest(email="user@example.com")
        assert forgot_request.email == "user@example.com"

        # Password reset with token
        reset_data = {
            "token": "reset-token-abc123",
            "new_password": "ResetPassword789$",
            "new_password_confirm": "ResetPassword789$",
        }
        reset_request = ResetPasswordRequest(**reset_data)
        assert reset_request.token == "reset-token-abc123"

        # Login with reset password
        login_data = {
            "username": "user@example.com",
            "password": "ResetPassword789$",
        }
        login_request = LoginRequest(**login_data)
        assert login_request.password == "ResetPassword789$"
