"""Tests for the enhanced authentication middleware."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from starlette.types import ASGIApp

from tripsage.api.middlewares.authentication import (
    AuthenticationMiddleware,
    Principal,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.services.business.auth_service import TokenData
from tripsage_core.services.business.user_service import UserResponse


@pytest.fixture
def mock_app():
    """Create a mock ASGI app."""
    app = MagicMock(spec=ASGIApp)
    return app


@pytest.fixture
def mock_auth_service():
    """Create a mock authentication service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_key_service():
    """Create a mock key management service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.secret_key = "test-secret-key"
    return settings


@pytest.fixture
def middleware(mock_app, mock_auth_service, mock_key_service, mock_settings):
    """Create middleware instance with mocked dependencies."""
    return AuthenticationMiddleware(
        app=mock_app,
        settings=mock_settings,
        auth_service=mock_auth_service,
        key_service=mock_key_service,
    )


@pytest.fixture
def mock_request():
    """Create a mock request."""
    request = MagicMock(spec=Request)

    # Create a state object that doesn't have principal attribute by default
    class State:
        pass

    request.state = State()
    request.headers = {}
    request.url.path = "/api/test"
    return request


@pytest.fixture
def mock_call_next():
    """Create a mock call_next function."""

    async def call_next(request):
        response = MagicMock(spec=Response)
        response.status_code = 200
        return response

    return call_next


@pytest.fixture
def valid_token_data():
    """Create valid token data."""
    now = datetime.now(timezone.utc)
    return TokenData(
        sub="user123",
        user_id="user123",
        email="test@example.com",
        token_type="access",
        iat=int(now.timestamp()),
        exp=int((now + timedelta(hours=1)).timestamp()),
    )


@pytest.fixture
def valid_user():
    """Create a valid user response."""
    return UserResponse(
        id="user123",
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestAuthenticationMiddleware:
    """Test cases for AuthenticationMiddleware."""

    async def test_skip_auth_for_public_endpoints(
        self, middleware, mock_request, mock_call_next
    ):
        """Test that authentication is skipped for public endpoints."""
        # Test various public endpoints
        public_paths = [
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json",
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/reset-password",
        ]

        for path in public_paths:
            mock_request.url.path = path
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should not set principal for public endpoints
            assert (
                not hasattr(mock_request.state, "principal")
                or mock_request.state.principal is None
            )
            assert response.status_code == 200

    async def test_successful_jwt_authentication(
        self,
        middleware,
        mock_request,
        mock_call_next,
        mock_auth_service,
        valid_token_data,
        valid_user,
    ):
        """Test successful JWT authentication."""
        # Set up request with bearer token
        mock_request.headers = {"Authorization": "Bearer valid-jwt-token"}

        # Mock auth service responses
        mock_auth_service.validate_access_token.return_value = valid_token_data
        mock_auth_service.get_current_user.return_value = valid_user

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify authentication
        assert hasattr(mock_request.state, "principal")
        principal = mock_request.state.principal
        assert isinstance(principal, Principal)
        assert principal.id == "user123"
        assert principal.type == "user"
        assert principal.email == "test@example.com"
        assert principal.auth_method == "jwt"
        assert response.status_code == 200

        # Verify service calls
        mock_auth_service.validate_access_token.assert_called_once_with(
            "valid-jwt-token"
        )
        mock_auth_service.get_current_user.assert_called_once_with("valid-jwt-token")

    async def test_failed_jwt_authentication(
        self, middleware, mock_request, mock_call_next, mock_auth_service
    ):
        """Test failed JWT authentication."""
        # Set up request with invalid bearer token
        mock_request.headers = {"Authorization": "Bearer invalid-jwt-token"}

        # Mock auth service to raise error
        mock_auth_service.validate_access_token.side_effect = AuthenticationError(
            "Invalid token"
        )

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 401
        assert response.status_code == 401
        assert (
            not hasattr(mock_request.state, "principal")
            or mock_request.state.principal is None
        )

    async def test_successful_api_key_authentication(
        self, middleware, mock_request, mock_call_next
    ):
        """Test successful API key authentication."""
        # Set up request with API key
        mock_request.headers = {"X-API-Key": "sk_openai_key123_verylongsecretkey123456"}

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Verify authentication
        assert hasattr(mock_request.state, "principal")
        principal = mock_request.state.principal
        assert isinstance(principal, Principal)
        assert principal.id == "agent_openai_key123"
        assert principal.type == "agent"
        assert principal.service == "openai"
        assert principal.auth_method == "api_key"
        assert "openai:*" in principal.scopes
        assert response.status_code == 200

    async def test_failed_api_key_authentication_invalid_format(
        self, middleware, mock_request, mock_call_next
    ):
        """Test failed API key authentication with invalid format."""
        # Set up request with invalid API key format
        mock_request.headers = {"X-API-Key": "invalid-key-format"}

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 401
        assert response.status_code == 401
        assert (
            not hasattr(mock_request.state, "principal")
            or mock_request.state.principal is None
        )

    async def test_failed_api_key_authentication_short_secret(
        self, middleware, mock_request, mock_call_next
    ):
        """Test failed API key authentication with short secret."""
        # Set up request with API key with short secret
        mock_request.headers = {"X-API-Key": "sk_openai_key123_short"}

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 401
        assert response.status_code == 401
        assert (
            not hasattr(mock_request.state, "principal")
            or mock_request.state.principal is None
        )

    async def test_no_authentication_provided(
        self, middleware, mock_request, mock_call_next
    ):
        """Test request with no authentication."""
        # No auth headers
        mock_request.headers = {}

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 401
        assert response.status_code == 401
        assert (
            not hasattr(mock_request.state, "principal")
            or mock_request.state.principal is None
        )
        # Check response content (starlette Response object uses content, not body)
        assert (
            hasattr(response, "body")
            and b"Authentication required" in response.body
            or hasattr(response, "content")
            and b"Authentication required" in response.content
        )

    async def test_jwt_takes_precedence_over_api_key(
        self,
        middleware,
        mock_request,
        mock_call_next,
        mock_auth_service,
        valid_token_data,
        valid_user,
    ):
        """Test that JWT authentication takes precedence when both are provided."""
        # Set up request with both JWT and API key
        mock_request.headers = {
            "Authorization": "Bearer valid-jwt-token",
            "X-API-Key": "sk_openai_key123_verylongsecretkey123456",
        }

        # Mock auth service responses
        mock_auth_service.validate_access_token.return_value = valid_token_data
        mock_auth_service.get_current_user.return_value = valid_user

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should authenticate with JWT
        assert hasattr(mock_request.state, "principal")
        principal = mock_request.state.principal
        assert principal.type == "user"
        assert principal.auth_method == "jwt"
        assert response.status_code == 200

    async def test_api_key_fallback_when_jwt_fails(
        self, middleware, mock_request, mock_call_next, mock_auth_service
    ):
        """Test API key authentication when JWT fails."""
        # Set up request with both JWT and API key
        mock_request.headers = {
            "Authorization": "Bearer invalid-jwt-token",
            "X-API-Key": "sk_openai_key123_verylongsecretkey123456",
        }

        # Mock auth service to fail JWT validation
        mock_auth_service.validate_access_token.side_effect = AuthenticationError(
            "Invalid token"
        )

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should authenticate with API key
        assert hasattr(mock_request.state, "principal")
        principal = mock_request.state.principal
        assert principal.type == "agent"
        assert principal.auth_method == "api_key"
        assert response.status_code == 200

    async def test_principal_metadata(
        self,
        middleware,
        mock_request,
        mock_call_next,
        mock_auth_service,
        valid_token_data,
        valid_user,
    ):
        """Test that principal metadata is properly set."""
        # Set up request with bearer token
        mock_request.headers = {"Authorization": "Bearer valid-jwt-token"}

        # Mock auth service responses
        mock_auth_service.validate_access_token.return_value = valid_token_data
        mock_auth_service.get_current_user.return_value = valid_user

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check metadata
        principal = mock_request.state.principal
        assert "token_issued_at" in principal.metadata
        assert "token_expires_at" in principal.metadata
        assert response.status_code == 200

    async def test_service_initialization(
        self, mock_app, mock_settings, mock_request, mock_call_next
    ):
        """Test lazy initialization of services."""
        # Create middleware without services
        middleware = AuthenticationMiddleware(app=mock_app, settings=mock_settings)

        # Set up request that requires auth
        mock_request.headers = {}

        # Mock the service getters - they're imported inside the method
        with patch(
            "tripsage_core.services.business.auth_service.get_auth_service"
        ) as mock_get_auth:
            with patch(
                "tripsage_core.services.business.key_management_service.get_key_management_service"
            ) as mock_get_key:
                mock_get_auth.return_value = AsyncMock()
                mock_get_key.return_value = AsyncMock()

                # Dispatch request
                await middleware.dispatch(mock_request, mock_call_next)

                # Services should be initialized
                assert middleware._services_initialized
                mock_get_auth.assert_called_once()
                mock_get_key.assert_called_once()

    async def test_error_response_for_key_validation_error(
        self, middleware, mock_request, mock_call_next
    ):
        """Test error response for key validation errors."""
        # Set up request with API key that will fail validation
        mock_request.headers = {"X-API-Key": "invalid"}

        # Dispatch request
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should return 401 with appropriate message
        assert response.status_code == 401
        # Check response content (starlette Response object uses content, not body)
        if hasattr(response, "body"):
            content = response.body
        else:
            content = response.content
        assert b"API key validation failed" in content or b"Invalid API key" in content
