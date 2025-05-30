"""
Unit tests for the API auth service.

Tests the thin wrapper functionality and model adaptation between
API and core services.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from api.schemas.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)
from api.schemas.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserResponse,
)
from api.services.auth_service import AuthService
from tripsage_core.exceptions.exceptions import CoreAuthenticationError
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.services.business.auth_service import (
    TokenResponse as CoreTokenResponse,
)
from tripsage_core.services.business.user_service import (
    UserResponse as CoreUserResponse,
)
from tripsage_core.services.business.user_service import (
    UserService,
)


class TestAuthService:
    """Test cases for AuthService."""

    @pytest.fixture
    def mock_core_auth_service(self):
        """Mock core authentication service."""
        return AsyncMock(spec=CoreAuthService)

    @pytest.fixture
    def mock_user_service(self):
        """Mock user service."""
        return AsyncMock(spec=UserService)

    @pytest.fixture
    def auth_service(self, mock_core_auth_service, mock_user_service):
        """Create auth service with mocked dependencies."""
        return AuthService(
            core_auth_service=mock_core_auth_service,
            user_service=mock_user_service,
        )

    @pytest.fixture
    def sample_user_response(self):
        """Sample core user response."""
        return CoreUserResponse(
            id="user_123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            preferences={"theme": "dark"},
        )

    @pytest.fixture
    def sample_token_response(self, sample_user_response):
        """Sample core token response."""
        return CoreTokenResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            token_type="bearer",
            expires_in=3600,
            user=sample_user_response,
        )

    async def test_register_user_success(
        self,
        auth_service,
        mock_user_service,
        mock_core_auth_service,
        sample_token_response,
    ):
        """Test successful user registration."""
        # Arrange
        request = RegisterUserRequest(
            username="testuser",
            email="test@example.com",
            password="Password123!",
            password_confirm="Password123!",
            full_name="Test User",
        )

        mock_user_service.create_user.return_value = sample_token_response.user
        mock_core_auth_service.authenticate_user.return_value = sample_token_response

        # Act
        result = await auth_service.register_user(request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token_123"
        assert result.refresh_token == "refresh_token_123"
        assert result.token_type == "bearer"
        assert result.expires_in == 3600

        # Verify core services were called correctly
        mock_user_service.create_user.assert_called_once()
        mock_core_auth_service.authenticate_user.assert_called_once()

    async def test_register_user_failure(self, auth_service, mock_user_service):
        """Test user registration failure."""
        # Arrange
        request = RegisterUserRequest(
            username="testuser",
            email="test@example.com",
            password="Password123!",
            password_confirm="Password123!",
            full_name="Test User",
        )

        mock_user_service.create_user.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(CoreAuthenticationError, match="Registration failed"):
            await auth_service.register_user(request)

    async def test_login_user_success(
        self, auth_service, mock_core_auth_service, sample_token_response
    ):
        """Test successful user login."""
        # Arrange
        request = LoginRequest(username="testuser", password="password123")
        mock_core_auth_service.authenticate_user.return_value = sample_token_response

        # Act
        result = await auth_service.login_user(request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token_123"
        mock_core_auth_service.authenticate_user.assert_called_once()

    async def test_login_user_failure(self, auth_service, mock_core_auth_service):
        """Test user login failure."""
        # Arrange
        request = LoginRequest(username="testuser", password="wrongpassword")
        mock_core_auth_service.authenticate_user.side_effect = CoreAuthenticationError(
            "Invalid credentials"
        )

        # Act & Assert
        with pytest.raises(CoreAuthenticationError):
            await auth_service.login_user(request)

    async def test_refresh_token_success(
        self, auth_service, mock_core_auth_service, sample_token_response
    ):
        """Test successful token refresh."""
        # Arrange
        request = RefreshTokenRequest(refresh_token="refresh_token_123")
        mock_core_auth_service.refresh_token.return_value = sample_token_response

        # Act
        result = await auth_service.refresh_token(request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token_123"
        mock_core_auth_service.refresh_token.assert_called_once()

    async def test_get_current_user_success(
        self, auth_service, mock_core_auth_service, sample_user_response
    ):
        """Test successful current user retrieval."""
        # Arrange
        token = "access_token_123"
        mock_core_auth_service.get_current_user.return_value = sample_user_response

        # Act
        result = await auth_service.get_current_user(token)

        # Assert
        assert isinstance(result, UserResponse)
        assert result.id == "user_123"
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        mock_core_auth_service.get_current_user.assert_called_once_with(token)

    async def test_change_password_success(self, auth_service, mock_user_service):
        """Test successful password change."""
        # Arrange
        user_id = "user_123"
        request = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        mock_user_service.change_password.return_value = True

        # Act
        result = await auth_service.change_password(user_id, request)

        # Assert
        assert isinstance(result, MessageResponse)
        assert result.success is True
        assert "successfully" in result.message
        mock_user_service.change_password.assert_called_once()

    async def test_change_password_failure(self, auth_service, mock_user_service):
        """Test password change failure."""
        # Arrange
        user_id = "user_123"
        request = ChangePasswordRequest(
            current_password="WrongPassword123!",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        mock_user_service.change_password.return_value = False

        # Act & Assert
        with pytest.raises(CoreAuthenticationError, match="Password change failed"):
            await auth_service.change_password(user_id, request)

    async def test_forgot_password_success(self, auth_service, mock_core_auth_service):
        """Test successful forgot password initiation."""
        # Arrange
        request = ForgotPasswordRequest(email="test@example.com")
        mock_core_auth_service.initiate_password_reset.return_value = True

        # Act
        result = await auth_service.forgot_password(request)

        # Assert
        assert isinstance(result, PasswordResetResponse)
        assert result.success is True
        assert result.email == "test@example.com"
        mock_core_auth_service.initiate_password_reset.assert_called_once()

    async def test_forgot_password_always_returns_success(
        self, auth_service, mock_core_auth_service
    ):
        """Test that forgot password always returns success for security."""
        # Arrange
        request = ForgotPasswordRequest(email="nonexistent@example.com")
        mock_core_auth_service.initiate_password_reset.side_effect = Exception(
            "User not found"
        )

        # Act
        result = await auth_service.forgot_password(request)

        # Assert - Should still return success for security
        assert isinstance(result, PasswordResetResponse)
        assert result.success is True
        assert result.email == "nonexistent@example.com"

    async def test_reset_password_success(self, auth_service, mock_core_auth_service):
        """Test successful password reset."""
        # Arrange
        request = ResetPasswordRequest(
            token="reset_token_123",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        mock_core_auth_service.confirm_password_reset.return_value = True

        # Act
        result = await auth_service.reset_password(request)

        # Assert
        assert isinstance(result, MessageResponse)
        assert result.success is True
        assert "successfully" in result.message
        mock_core_auth_service.confirm_password_reset.assert_called_once()

    async def test_reset_password_failure(self, auth_service, mock_core_auth_service):
        """Test password reset failure."""
        # Arrange
        request = ResetPasswordRequest(
            token="invalid_token",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        mock_core_auth_service.confirm_password_reset.return_value = False

        # Act & Assert
        with pytest.raises(CoreAuthenticationError, match="Password reset failed"):
            await auth_service.reset_password(request)

    async def test_logout_user_success(self, auth_service, mock_core_auth_service):
        """Test successful user logout."""
        # Arrange
        token = "access_token_123"
        mock_core_auth_service.logout_user.return_value = True

        # Act
        result = await auth_service.logout_user(token)

        # Assert
        assert isinstance(result, MessageResponse)
        assert result.success is True
        mock_core_auth_service.logout_user.assert_called_once_with(token)

    async def test_logout_user_always_returns_success(
        self, auth_service, mock_core_auth_service
    ):
        """Test that logout always returns success even on failure."""
        # Arrange
        token = "invalid_token"
        mock_core_auth_service.logout_user.side_effect = Exception("Invalid token")

        # Act
        result = await auth_service.logout_user(token)

        # Assert - Should still return success
        assert isinstance(result, MessageResponse)
        assert result.success is True

    async def test_model_adaptation(self, auth_service, sample_user_response):
        """Test model adaptation between core and API models."""
        # Test user response adaptation
        api_user = auth_service._adapt_user_response(sample_user_response)

        assert isinstance(api_user, UserResponse)
        assert api_user.id == sample_user_response.id
        assert api_user.username == sample_user_response.username
        assert api_user.email == sample_user_response.email
        assert api_user.full_name == sample_user_response.full_name
        assert api_user.is_active == sample_user_response.is_active
        assert api_user.is_verified == sample_user_response.is_verified
        assert api_user.preferences == sample_user_response.preferences

    async def test_lazy_service_initialization(self):
        """Test that services are initialized lazily."""
        # Arrange
        auth_service = AuthService()

        # Assert - Services should be None initially
        assert auth_service.core_auth_service is None
        assert auth_service.user_service is None

        # Act - Access services (would initialize them in real scenario)
        # Note: In real scenario, these would call get_core_auth_service() etc.
        # Here we just verify the lazy initialization pattern is in place
        assert hasattr(auth_service, "_get_core_auth_service")
        assert hasattr(auth_service, "_get_user_service")
