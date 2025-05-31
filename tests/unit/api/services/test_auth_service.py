"""
Comprehensive tests for the refactored API auth service.

Tests the thin wrapper functionality, model adaptation, error handling,
and dependency injection patterns of the AuthService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from api.services.auth_service import AuthService
from tripsage.api.models.requests.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterUserRequest,
    ResetPasswordRequest,
)
from tripsage.api.models.responses.auth import (
    MessageResponse,
    PasswordResetResponse,
    TokenResponse,
    UserResponse,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
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
    """Comprehensive test cases for AuthService thin wrapper."""

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
    def sample_core_user_response(self):
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
            preferences={"theme": "dark", "notifications": True},
        )

    @pytest.fixture
    def sample_core_token_response(self, sample_core_user_response):
        """Sample core token response."""
        return CoreTokenResponse(
            access_token="access_token_abc123",
            refresh_token="refresh_token_xyz789",
            token_type="bearer",
            expires_in=3600,
            user=sample_core_user_response,
        )

    # Registration Tests
    async def test_register_user_success(
        self,
        auth_service,
        mock_user_service,
        mock_core_auth_service,
        sample_core_token_response,
    ):
        """Test successful user registration with proper model adaptation."""
        # Arrange
        request = RegisterUserRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="Test User",
        )

        mock_user_service.create_user.return_value = sample_core_token_response.user
        mock_core_auth_service.authenticate_user.return_value = (
            sample_core_token_response
        )

        # Act
        result = await auth_service.register_user(request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token_abc123"
        assert result.refresh_token == "refresh_token_xyz789"
        assert result.token_type == "bearer"
        assert result.expires_in == 3600

        # Verify core services were called with correct data
        user_create_call = mock_user_service.create_user.call_args[0][0]
        assert user_create_call.username == request.username
        assert user_create_call.email == request.email
        assert user_create_call.password == request.password
        assert user_create_call.full_name == request.full_name

        auth_call = mock_core_auth_service.authenticate_user.call_args[0][0]
        assert auth_call.identifier == request.username
        assert auth_call.password == request.password

    async def test_register_user_user_creation_failure(
        self, auth_service, mock_user_service
    ):
        """Test registration failure during user creation."""
        # Arrange
        request = RegisterUserRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="Test User",
        )

        mock_user_service.create_user.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Registration failed"):
            await auth_service.register_user(request)

    async def test_register_user_authentication_failure(
        self,
        auth_service,
        mock_user_service,
        mock_core_auth_service,
        sample_core_user_response,
    ):
        """Test registration failure during authentication after user creation."""
        # Arrange
        request = RegisterUserRequest(
            username="testuser",
            email="test@example.com",
            password="SecurePassword123!",
            password_confirm="SecurePassword123!",
            full_name="Test User",
        )

        mock_user_service.create_user.return_value = sample_core_user_response
        mock_core_auth_service.authenticate_user.side_effect = AuthenticationError(
            "Authentication failed"
        )

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Registration failed"):
            await auth_service.register_user(request)

    # Login Tests
    async def test_login_user_success(
        self, auth_service, mock_core_auth_service, sample_core_token_response
    ):
        """Test successful user login."""
        # Arrange
        request = LoginRequest(username="testuser", password="password123")
        mock_core_auth_service.authenticate_user.return_value = (
            sample_core_token_response
        )

        # Act
        result = await auth_service.login_user(request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token_abc123"
        assert result.refresh_token == "refresh_token_xyz789"

        # Verify core service was called correctly
        auth_call = mock_core_auth_service.authenticate_user.call_args[0][0]
        assert auth_call.identifier == request.username
        assert auth_call.password == request.password

    async def test_login_user_invalid_credentials(
        self, auth_service, mock_core_auth_service
    ):
        """Test login with invalid credentials."""
        # Arrange
        request = LoginRequest(username="testuser", password="wrongpassword")
        mock_core_auth_service.authenticate_user.side_effect = AuthenticationError(
            "Invalid credentials"
        )

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Authentication failed"):
            await auth_service.login_user(request)

    # Token Refresh Tests
    async def test_refresh_token_success(
        self, auth_service, mock_core_auth_service, sample_core_token_response
    ):
        """Test successful token refresh."""
        # Arrange
        request = RefreshTokenRequest(refresh_token="refresh_token_xyz789")
        mock_core_auth_service.refresh_token.return_value = sample_core_token_response

        # Act
        result = await auth_service.refresh_token(request)

        # Assert
        assert isinstance(result, TokenResponse)
        assert result.access_token == "access_token_abc123"

        # Verify core service was called correctly
        refresh_call = mock_core_auth_service.refresh_token.call_args[0][0]
        assert refresh_call.refresh_token == request.refresh_token

    async def test_refresh_token_invalid_token(
        self, auth_service, mock_core_auth_service
    ):
        """Test token refresh with invalid token."""
        # Arrange
        request = RefreshTokenRequest(refresh_token="invalid_token")
        mock_core_auth_service.refresh_token.side_effect = AuthenticationError(
            "Invalid refresh token"
        )

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Token refresh failed"):
            await auth_service.refresh_token(request)

    # Current User Tests
    async def test_get_current_user_success(
        self, auth_service, mock_core_auth_service, sample_core_user_response
    ):
        """Test successful current user retrieval."""
        # Arrange
        token = "access_token_abc123"
        mock_core_auth_service.get_current_user.return_value = sample_core_user_response

        # Act
        result = await auth_service.get_current_user(token)

        # Assert
        assert isinstance(result, UserResponse)
        assert result.id == "user_123"
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.full_name == "Test User"
        assert result.is_active is True
        assert result.is_verified is True
        assert result.preferences == {"theme": "dark", "notifications": True}

        mock_core_auth_service.get_current_user.assert_called_once_with(token)

    async def test_get_current_user_invalid_token(
        self, auth_service, mock_core_auth_service
    ):
        """Test current user retrieval with invalid token."""
        # Arrange
        token = "invalid_token"
        mock_core_auth_service.get_current_user.side_effect = AuthenticationError(
            "Invalid token"
        )

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await auth_service.get_current_user(token)

    # Password Change Tests
    async def test_change_password_success(self, auth_service, mock_user_service):
        """Test successful password change."""
        # Arrange
        user_id = "user_123"
        request = ChangePasswordRequest(
            current_password="CurrentPassword123!",
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

        mock_user_service.change_password.assert_called_once_with(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
        )

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
        with pytest.raises(AuthenticationError, match="Password change failed"):
            await auth_service.change_password(user_id, request)

    async def test_change_password_service_error(self, auth_service, mock_user_service):
        """Test password change with service error."""
        # Arrange
        user_id = "user_123"
        request = ChangePasswordRequest(
            current_password="CurrentPassword123!",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        mock_user_service.change_password.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Password change failed"):
            await auth_service.change_password(user_id, request)

    # Password Reset Tests
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
        assert "sent" in result.message

        # Verify core service was called correctly
        reset_call = mock_core_auth_service.initiate_password_reset.call_args[0][0]
        assert reset_call.email == request.email

    async def test_forgot_password_always_returns_success_for_security(
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
            token="reset_token_abc123",
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

        # Verify core service was called correctly
        confirm_call = mock_core_auth_service.confirm_password_reset.call_args[0][0]
        assert confirm_call.token == request.token
        assert confirm_call.new_password == request.new_password

    async def test_reset_password_invalid_token(
        self, auth_service, mock_core_auth_service
    ):
        """Test password reset with invalid token."""
        # Arrange
        request = ResetPasswordRequest(
            token="invalid_token",
            new_password="NewPassword123!",
            new_password_confirm="NewPassword123!",
        )
        mock_core_auth_service.confirm_password_reset.return_value = False

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Password reset failed"):
            await auth_service.reset_password(request)

    # Logout Tests
    async def test_logout_user_success(self, auth_service, mock_core_auth_service):
        """Test successful user logout."""
        # Arrange
        token = "access_token_abc123"
        mock_core_auth_service.logout_user.return_value = True

        # Act
        result = await auth_service.logout_user(token)

        # Assert
        assert isinstance(result, MessageResponse)
        assert result.success is True
        assert "successfully" in result.message

        mock_core_auth_service.logout_user.assert_called_once_with(token)

    async def test_logout_user_always_returns_success(
        self, auth_service, mock_core_auth_service
    ):
        """Test that logout always returns success even on failure for UX."""
        # Arrange
        token = "invalid_token"
        mock_core_auth_service.logout_user.side_effect = Exception("Token error")

        # Act
        result = await auth_service.logout_user(token)

        # Assert - Should still return success
        assert isinstance(result, MessageResponse)
        assert result.success is True

    # Model Adaptation Tests
    async def test_adapt_token_response(self, auth_service, sample_core_token_response):
        """Test token response model adaptation."""
        # Act
        api_token = auth_service._adapt_token_response(sample_core_token_response)

        # Assert
        assert isinstance(api_token, TokenResponse)
        assert api_token.access_token == sample_core_token_response.access_token
        assert api_token.refresh_token == sample_core_token_response.refresh_token
        assert api_token.token_type == sample_core_token_response.token_type
        assert api_token.expires_in == sample_core_token_response.expires_in

    async def test_adapt_user_response(self, auth_service, sample_core_user_response):
        """Test user response model adaptation."""
        # Act
        api_user = auth_service._adapt_user_response(sample_core_user_response)

        # Assert
        assert isinstance(api_user, UserResponse)
        assert api_user.id == sample_core_user_response.id
        assert api_user.username == sample_core_user_response.username
        assert api_user.email == sample_core_user_response.email
        assert api_user.full_name == sample_core_user_response.full_name
        assert api_user.is_active == sample_core_user_response.is_active
        assert api_user.is_verified == sample_core_user_response.is_verified
        assert api_user.created_at == sample_core_user_response.created_at
        assert api_user.updated_at == sample_core_user_response.updated_at
        assert api_user.preferences == sample_core_user_response.preferences

    # Lazy Initialization Tests
    async def test_lazy_service_initialization(self):
        """Test that services are initialized lazily."""
        # Arrange
        auth_service = AuthService()

        # Assert - Services should be None initially
        assert auth_service.core_auth_service is None
        assert auth_service.user_service is None

        # Verify lazy initialization methods exist
        assert hasattr(auth_service, "_get_core_auth_service")
        assert hasattr(auth_service, "_get_user_service")

    async def test_get_core_auth_service_lazy_initialization(self):
        """Test core auth service lazy initialization."""
        # Arrange
        auth_service = AuthService()

        # Mock the lazy initialization
        mock_service = AsyncMock(spec=CoreAuthService)

        # Mock the get_core_auth_service function
        async def mock_get_core_auth_service():
            return mock_service

        # Replace the function
        import api.services.auth_service

        original_fn = api.services.auth_service.get_core_auth_service
        api.services.auth_service.get_core_auth_service = mock_get_core_auth_service

        try:
            # Act
            result = await auth_service._get_core_auth_service()

            # Assert
            assert result is mock_service
            assert auth_service.core_auth_service is mock_service
        finally:
            # Restore original function
            api.services.auth_service.get_core_auth_service = original_fn

    # Integration and Edge Case Tests
    async def test_multiple_service_calls_use_same_instances(self, auth_service):
        """Test that multiple calls use the same service instances."""
        # Arrange
        mock_core_auth = AsyncMock(spec=CoreAuthService)
        mock_user = AsyncMock(spec=UserService)

        auth_service.core_auth_service = mock_core_auth
        auth_service.user_service = mock_user

        # Act
        service1 = await auth_service._get_core_auth_service()
        service2 = await auth_service._get_core_auth_service()

        user_service1 = await auth_service._get_user_service()
        user_service2 = await auth_service._get_user_service()

        # Assert - Same instances should be returned
        assert service1 is service2
        assert user_service1 is user_service2

    async def test_error_handling_preserves_original_errors(
        self, auth_service, mock_core_auth_service
    ):
        """Test that error handling preserves original error types when appropriate."""
        # Arrange
        request = LoginRequest(username="testuser", password="password")

        # Create a specific authentication error
        original_error = AuthenticationError("Invalid credentials")
        mock_core_auth_service.authenticate_user.side_effect = original_error

        # Act & Assert
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.login_user(request)

        # The exception should preserve the original error message
        assert "Authentication failed" in str(exc_info.value)

    async def test_comprehensive_error_logging(
        self, auth_service, mock_core_auth_service, caplog
    ):
        """Test that errors are properly logged."""
        # Arrange
        request = LoginRequest(username="testuser", password="password")
        mock_core_auth_service.authenticate_user.side_effect = Exception(
            "Database error"
        )

        # Act
        with pytest.raises(AuthenticationError):
            await auth_service.login_user(request)

        # Assert - Check that error was logged
        assert "User login failed" in caplog.text
        assert "Database error" in caplog.text
