"""
Comprehensive tests for AuthenticationService.

This module provides full test coverage for authentication operations
including JWT token management, token validation, and refresh mechanisms.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import jwt
import pytest

from tripsage_core.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshTokenRequest,
    TokenData,
    TokenResponse,
    get_auth_service,
)
from tripsage_core.services.business.user_service import UserResponse


class TestAuthenticationService:
    """Test suite for AuthenticationService."""

    @pytest.fixture
    def mock_user_service(self):
        """Mock user service."""
        user_service = AsyncMock()
        return user_service

    @pytest.fixture
    def auth_service(self, mock_user_service):
        """Create AuthenticationService instance with mocked dependencies."""
        return AuthenticationService(
            user_service=mock_user_service,
            secret_key=os.getenv(
                "TEST_JWT_SECRET_KEY", "dummy_test_secret_for_unit_tests"
            ),
            access_token_expire_minutes=30,
            refresh_token_expire_days=7,
        )

    @pytest.fixture
    def sample_user_response(self):
        """Sample user response for testing."""
        user_id = str(uuid4())
        now = datetime.now(timezone.utc)

        return UserResponse(
            id=user_id,
            email="test@example.com",
            full_name="Test User",
            username="testuser",
            is_active=True,
            is_verified=True,
            created_at=now,
            updated_at=now,
            preferences={},
        )

    @pytest.fixture
    def sample_login_request(self):
        """Sample login request."""
        return LoginRequest(identifier="test@example.com", password="testpassword123")

    async def test_authenticate_user_success(
        self,
        auth_service,
        mock_user_service,
        sample_user_response,
        sample_login_request,
    ):
        """Test successful user authentication."""
        # Mock user service responses
        mock_user_service.verify_user_credentials.return_value = sample_user_response

        result = await auth_service.authenticate_user(sample_login_request)

        # Assertions
        assert isinstance(result, TokenResponse)
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.token_type == "bearer"
        assert result.expires_in == auth_service.access_token_expire_minutes * 60
        assert result.user == sample_user_response

        # Verify service calls
        mock_user_service.verify_user_credentials.assert_called_once_with(
            sample_login_request.identifier, sample_login_request.password
        )

    async def test_authenticate_user_invalid_credentials(
        self, auth_service, mock_user_service, sample_login_request
    ):
        """Test authentication with invalid credentials."""
        # Mock user service to return None (invalid credentials)
        mock_user_service.verify_user_credentials.return_value = None

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await auth_service.authenticate_user(sample_login_request)

    async def test_refresh_token_success(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test successful token refresh."""
        # Create a valid refresh token first
        refresh_token = await auth_service._create_refresh_token(sample_user_response)

        # Mock user service
        mock_user_service.get_user_by_id.return_value = sample_user_response

        refresh_request = RefreshTokenRequest(refresh_token=refresh_token)
        result = await auth_service.refresh_token(refresh_request)

        # Assertions
        assert isinstance(result, TokenResponse)
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.user == sample_user_response

        # Verify service calls
        mock_user_service.get_user_by_id.assert_called_once_with(
            sample_user_response.id
        )

    async def test_refresh_token_invalid(self, auth_service):
        """Test refresh with invalid token."""
        refresh_request = RefreshTokenRequest(refresh_token="invalid_token")

        with pytest.raises(AuthenticationError, match="Invalid token"):
            await auth_service.refresh_token(refresh_request)

    async def test_refresh_token_user_not_found(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test refresh when user not found."""
        # Create a valid refresh token
        refresh_token = await auth_service._create_refresh_token(sample_user_response)

        # Mock user service to return None
        mock_user_service.get_user_by_id.return_value = None

        refresh_request = RefreshTokenRequest(refresh_token=refresh_token)

        with pytest.raises(AuthenticationError, match="User not found or inactive"):
            await auth_service.refresh_token(refresh_request)

    async def test_refresh_token_user_inactive(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test refresh when user is inactive."""
        # Create a valid refresh token
        refresh_token = await auth_service._create_refresh_token(sample_user_response)

        # Create inactive user
        inactive_user = sample_user_response.model_copy()
        inactive_user.is_active = False

        # Mock user service to return inactive user
        mock_user_service.get_user_by_id.return_value = inactive_user

        refresh_request = RefreshTokenRequest(refresh_token=refresh_token)

        with pytest.raises(AuthenticationError, match="User not found or inactive"):
            await auth_service.refresh_token(refresh_request)

    async def test_validate_access_token_success(
        self, auth_service, sample_user_response
    ):
        """Test successful access token validation."""
        # Create a valid access token
        access_token = await auth_service._create_access_token(sample_user_response)

        # Validate the token
        token_data = await auth_service.validate_access_token(access_token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == sample_user_response.id
        assert token_data.email == sample_user_response.email
        assert token_data.token_type == "access"

    async def test_validate_access_token_expired(self, auth_service):
        """Test validation of expired token."""
        # Create an expired token
        token = jwt.encode(
            {
                "sub": "test-user-id",
                "user_id": "test-user-id",
                "email": "test@example.com",
                "token_type": "access",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int(
                    (datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()
                ),
            },
            auth_service.secret_key,
            algorithm=auth_service.algorithm,
        )

        with pytest.raises(AuthenticationError, match="Token has expired"):
            await auth_service.validate_access_token(token)

    async def test_validate_access_token_wrong_type(
        self, auth_service, sample_user_response
    ):
        """Test validation with wrong token type."""
        # Create a refresh token
        refresh_token = await auth_service._create_refresh_token(sample_user_response)

        # Try to validate it as an access token
        with pytest.raises(AuthenticationError, match="Invalid token type"):
            await auth_service.validate_access_token(refresh_token)

    async def test_validate_access_token_invalid_signature(self, auth_service):
        """Test validation with invalid signature."""
        # Create token with different secret
        token = jwt.encode(
            {
                "sub": "test-user-id",
                "user_id": "test-user-id",
                "email": "test@example.com",
                "token_type": "access",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int(
                    (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()
                ),
            },
            "wrong_secret_key",
            algorithm="HS256",
        )

        with pytest.raises(AuthenticationError, match="Invalid token"):
            await auth_service.validate_access_token(token)

    async def test_get_current_user_success(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test successful current user retrieval."""
        # Create a valid access token
        access_token = await auth_service._create_access_token(sample_user_response)

        # Mock user service
        mock_user_service.get_user_by_id.return_value = sample_user_response

        result = await auth_service.get_current_user(access_token)

        assert result == sample_user_response
        mock_user_service.get_user_by_id.assert_called_once_with(
            sample_user_response.id
        )

    async def test_get_current_user_invalid_token(self, auth_service):
        """Test current user retrieval with invalid token."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await auth_service.get_current_user("invalid_token")

    async def test_get_current_user_not_found(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test current user retrieval when user not found."""
        # Create a valid access token
        access_token = await auth_service._create_access_token(sample_user_response)

        # Mock user service to return None
        mock_user_service.get_user_by_id.return_value = None

        with pytest.raises(AuthenticationError, match="User not found or inactive"):
            await auth_service.get_current_user(access_token)

    async def test_initiate_password_reset_success(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test successful password reset initiation."""
        # Mock user service
        mock_user_service.get_user_by_email.return_value = sample_user_response

        reset_request = PasswordResetRequest(email="test@example.com")
        result = await auth_service.initiate_password_reset(reset_request)

        assert result is True
        mock_user_service.get_user_by_email.assert_called_once_with("test@example.com")

    async def test_initiate_password_reset_user_not_found(
        self, auth_service, mock_user_service
    ):
        """Test password reset initiation for non-existent user."""
        # Mock user service to return None
        mock_user_service.get_user_by_email.return_value = None

        reset_request = PasswordResetRequest(email="nonexistent@example.com")
        result = await auth_service.initiate_password_reset(reset_request)

        # Should still return True for security
        assert result is True

    async def test_confirm_password_reset_success(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test successful password reset confirmation."""
        # Create a password reset token
        reset_token = await auth_service._create_password_reset_token(
            sample_user_response
        )

        # Mock user service
        mock_user_service.get_user_by_id.return_value = sample_user_response

        # Mock the password reset
        with patch.object(auth_service, "_reset_user_password", return_value=True):
            confirm_request = PasswordResetConfirmRequest(
                token=reset_token, new_password="newpassword123"
            )
            result = await auth_service.confirm_password_reset(confirm_request)

        assert result is True
        mock_user_service.get_user_by_id.assert_called_once_with(
            sample_user_response.id
        )

    async def test_confirm_password_reset_invalid_token(self, auth_service):
        """Test password reset confirmation with invalid token."""
        confirm_request = PasswordResetConfirmRequest(
            token="invalid_token", new_password="newpassword123"
        )

        with pytest.raises(AuthenticationError, match="Invalid token"):
            await auth_service.confirm_password_reset(confirm_request)

    async def test_confirm_password_reset_expired_token(self, auth_service):
        """Test password reset confirmation with expired token."""
        # Create an expired reset token
        token = jwt.encode(
            {
                "sub": "test-user-id",
                "user_id": "test-user-id",
                "email": "test@example.com",
                "token_type": "password_reset",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int(
                    (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
                ),
            },
            auth_service.secret_key,
            algorithm=auth_service.algorithm,
        )

        confirm_request = PasswordResetConfirmRequest(
            token=token, new_password="newpassword123"
        )

        with pytest.raises(AuthenticationError, match="Token has expired"):
            await auth_service.confirm_password_reset(confirm_request)

    async def test_logout_user_success(self, auth_service, sample_user_response):
        """Test successful user logout."""
        # Create a valid access token
        access_token = await auth_service._create_access_token(sample_user_response)

        result = await auth_service.logout_user(access_token)

        assert result is True

    async def test_logout_user_invalid_token(self, auth_service):
        """Test logout with invalid token."""
        result = await auth_service.logout_user("invalid_token")

        # Should return False for invalid token
        assert result is False

    async def test_create_access_token_structure(
        self, auth_service, sample_user_response
    ):
        """Test access token structure."""
        token = await auth_service._create_access_token(sample_user_response)

        # Decode and verify structure
        decoded = jwt.decode(
            token, auth_service.secret_key, algorithms=[auth_service.algorithm]
        )

        assert decoded["sub"] == sample_user_response.id
        assert decoded["user_id"] == sample_user_response.id
        assert decoded["email"] == sample_user_response.email
        assert decoded["token_type"] == "access"
        assert "iat" in decoded
        assert "exp" in decoded

        # Verify expiration time
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        assert (
            exp_time - iat_time
        ).total_seconds() == auth_service.access_token_expire_minutes * 60

    async def test_create_refresh_token_structure(
        self, auth_service, sample_user_response
    ):
        """Test refresh token structure."""
        token = await auth_service._create_refresh_token(sample_user_response)

        # Decode and verify structure
        decoded = jwt.decode(
            token, auth_service.secret_key, algorithms=[auth_service.algorithm]
        )

        assert decoded["sub"] == sample_user_response.id
        assert decoded["user_id"] == sample_user_response.id
        assert decoded["email"] == sample_user_response.email
        assert decoded["token_type"] == "refresh"
        assert "iat" in decoded
        assert "exp" in decoded

        # Verify expiration time
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        assert (
            exp_time - iat_time
        ).total_seconds() == auth_service.refresh_token_expire_days * 24 * 60 * 60

    async def test_create_password_reset_token_structure(
        self, auth_service, sample_user_response
    ):
        """Test password reset token structure."""
        token = await auth_service._create_password_reset_token(sample_user_response)

        # Decode and verify structure
        decoded = jwt.decode(
            token, auth_service.secret_key, algorithms=[auth_service.algorithm]
        )

        assert decoded["sub"] == sample_user_response.id
        assert decoded["user_id"] == sample_user_response.id
        assert decoded["email"] == sample_user_response.email
        assert decoded["token_type"] == "password_reset"
        assert "iat" in decoded
        assert "exp" in decoded

        # Verify expiration time (1 hour)
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        assert (exp_time - iat_time).total_seconds() == 3600  # 1 hour

    async def test_get_auth_service_dependency(self):
        """Test the dependency injection function."""
        service = await get_auth_service()
        assert isinstance(service, AuthenticationService)

    async def test_authenticate_user_exception_handling(
        self, auth_service, mock_user_service, sample_login_request
    ):
        """Test exception handling in authenticate_user."""
        # Mock user service to raise an exception
        mock_user_service.verify_user_credentials.side_effect = Exception(
            "Database error"
        )

        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await auth_service.authenticate_user(sample_login_request)

    async def test_refresh_token_exception_handling(
        self, auth_service, mock_user_service, sample_user_response
    ):
        """Test exception handling in refresh_token."""
        # Create a valid refresh token
        refresh_token = await auth_service._create_refresh_token(sample_user_response)

        # Mock user service to raise an exception
        mock_user_service.get_user_by_id.side_effect = Exception("Database error")

        refresh_request = RefreshTokenRequest(refresh_token=refresh_token)

        with pytest.raises(AuthenticationError, match="Token refresh failed"):
            await auth_service.refresh_token(refresh_request)
