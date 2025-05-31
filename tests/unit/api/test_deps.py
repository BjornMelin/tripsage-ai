"""
Comprehensive tests for the API dependencies module.

Tests dependency injection, authentication, session management,
and service integration patterns.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import Request
from fastapi.security import OAuth2PasswordBearer

import api.deps as deps
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.utils.session_utils import SessionMemory


class TestCoreDependencies:
    """Test core dependency functions."""

    async def test_get_core_auth_service_dep(self):
        """Test core auth service dependency creation."""
        # Mock the get_core_auth_service function
        mock_service = AsyncMock(spec=CoreAuthService)
        
        async def mock_get_core_auth_service():
            return mock_service
            
        # Replace the function
        original_fn = deps.get_core_auth_service
        deps.get_core_auth_service = mock_get_core_auth_service
        
        try:
            # Act
            result = await deps.get_core_auth_service_dep()
            
            # Assert
            assert result is mock_service
        finally:
            # Restore original function
            deps.get_core_auth_service = original_fn


class TestSessionMemory:
    """Test session memory dependency functions."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.cookies = {}
        return request

    async def test_get_session_memory_new_session(self, mock_request):
        """Test session memory creation for new session."""
        # Arrange
        mock_request.cookies = {}
        # Mock hasattr to return False initially
        def mock_hasattr(obj, name):
            return False if name == "session_memory" else hasattr(obj, name)
        
        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr
        
        try:
            # Act
            session_memory = await deps.get_session_memory(mock_request)
            
            # Assert
            assert isinstance(session_memory, SessionMemory)
            assert session_memory.session_id is not None
            assert mock_request.state.session_memory is session_memory
        finally:
            builtins.hasattr = original_hasattr

    async def test_get_session_memory_existing_session(self, mock_request):
        """Test session memory retrieval for existing session."""
        # Arrange
        existing_session_id = str(uuid4())
        mock_request.cookies = {"session_id": existing_session_id}
        # Mock hasattr to return False initially
        def mock_hasattr(obj, name):
            return False if name == "session_memory" else hasattr(obj, name)
        
        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr
        
        try:
            # Act
            session_memory = await deps.get_session_memory(mock_request)
            
            # Assert
            assert isinstance(session_memory, SessionMemory)
            assert session_memory.session_id == existing_session_id
            assert mock_request.state.session_memory is session_memory
        finally:
            builtins.hasattr = original_hasattr

    async def test_get_session_memory_reuse_existing_state(self, mock_request):
        """Test that existing session memory in state is reused."""
        # Arrange
        existing_session_memory = SessionMemory(session_id="existing_session")
        mock_request.state.session_memory = existing_session_memory
        
        # Act
        session_memory = await deps.get_session_memory(mock_request)
        
        # Assert
        assert session_memory is existing_session_memory


class TestAuthentication:
    """Test authentication dependency functions."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        return AsyncMock(spec=CoreAuthService)

    @pytest.fixture
    def sample_user_response(self):
        """Sample user response from auth service."""
        user = MagicMock()
        user.id = "user_123"
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.is_verified = True
        return user

    # Optional Authentication Tests
    async def test_get_current_user_optional_with_api_key_header(
        self, mock_auth_service
    ):
        """Test optional authentication with valid API key in header."""
        # Arrange
        api_key = "tripsage_abc123"
        
        # Act
        result = await deps.get_current_user_optional(
            token=None,
            api_key_header=api_key,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is not None
        assert result["id"] == "api_user"
        assert result["username"] == "api_user"
        assert result["is_api"] is True
        assert result["api_key"] == api_key

    async def test_get_current_user_optional_with_api_key_query(
        self, mock_auth_service
    ):
        """Test optional authentication with valid API key in query."""
        # Arrange
        api_key = "tripsage_xyz789"
        
        # Act
        result = await deps.get_current_user_optional(
            token=None,
            api_key_header=None,
            api_key_query=api_key,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is not None
        assert result["id"] == "api_user"
        assert result["username"] == "api_user"
        assert result["is_api"] is True
        assert result["api_key"] == api_key

    async def test_get_current_user_optional_prefers_header_over_query(
        self, mock_auth_service
    ):
        """Test that header API key is preferred over query API key."""
        # Arrange
        header_key = "tripsage_header123"
        query_key = "tripsage_query456"
        
        # Act
        result = await deps.get_current_user_optional(
            token=None,
            api_key_header=header_key,
            api_key_query=query_key,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is not None
        assert result["api_key"] == header_key

    async def test_get_current_user_optional_with_invalid_api_key(
        self, mock_auth_service
    ):
        """Test optional authentication with invalid API key."""
        # Arrange
        api_key = "invalid_key_format"
        
        # Act
        result = await deps.get_current_user_optional(
            token=None,
            api_key_header=api_key,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is None

    async def test_get_current_user_optional_with_valid_jwt_token(
        self, mock_auth_service, sample_user_response
    ):
        """Test optional authentication with valid JWT token."""
        # Arrange
        token = "valid_jwt_token"
        mock_auth_service.get_current_user.return_value = sample_user_response
        
        # Act
        result = await deps.get_current_user_optional(
            token=token,
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is not None
        assert result["id"] == "user_123"
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"
        assert result["is_api"] is False
        assert result["is_active"] is True
        assert result["is_verified"] is True
        
        mock_auth_service.get_current_user.assert_called_once_with(token)

    async def test_get_current_user_optional_with_invalid_jwt_token(
        self, mock_auth_service
    ):
        """Test optional authentication with invalid JWT token."""
        # Arrange
        token = "invalid_jwt_token"
        mock_auth_service.get_current_user.side_effect = Exception("Invalid token")
        
        # Act
        result = await deps.get_current_user_optional(
            token=token,
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is None

    async def test_get_current_user_optional_prefers_api_key_over_jwt(
        self, mock_auth_service, sample_user_response
    ):
        """Test that API key authentication is preferred over JWT."""
        # Arrange
        api_key = "tripsage_priority123"
        token = "valid_jwt_token"
        mock_auth_service.get_current_user.return_value = sample_user_response
        
        # Act
        result = await deps.get_current_user_optional(
            token=token,
            api_key_header=api_key,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is not None
        assert result["is_api"] is True
        assert result["api_key"] == api_key
        
        # JWT should not be called if API key is valid
        mock_auth_service.get_current_user.assert_not_called()

    async def test_get_current_user_optional_no_authentication(
        self, mock_auth_service
    ):
        """Test optional authentication with no credentials provided."""
        # Act
        result = await deps.get_current_user_optional(
            token=None,
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        
        # Assert
        assert result is None

    # Required Authentication Tests
    async def test_get_current_user_with_valid_authentication(
        self, mock_auth_service
    ):
        """Test required authentication with valid credentials."""
        # Arrange
        api_key = "tripsage_valid123"
        
        # Mock the optional function to return a user
        original_optional = deps.get_current_user_optional
        async def mock_optional(*args, **kwargs):
            return {
                "id": "api_user",
                "username": "api_user",
                "is_api": True,
                "api_key": api_key,
            }
        deps.get_current_user_optional = mock_optional
        
        try:
            # Act
            result = await deps.get_current_user(
                token=None,
                api_key_header=api_key,
                api_key_query=None,
                auth_service=mock_auth_service,
            )
            
            # Assert
            assert result is not None
            assert result["id"] == "api_user"
        finally:
            # Restore original function
            deps.get_current_user_optional = original_optional

    async def test_get_current_user_with_no_authentication(
        self, mock_auth_service
    ):
        """Test required authentication with no credentials."""
        # Arrange
        original_optional = deps.get_current_user_optional
        async def mock_optional(*args, **kwargs):
            return None
        deps.get_current_user_optional = mock_optional
        
        try:
            # Act & Assert
            with pytest.raises(AuthenticationError, match="Not authenticated"):
                await deps.get_current_user(
                    token=None,
                    api_key_header=None,
                    api_key_query=None,
                    auth_service=mock_auth_service,
                )
        finally:
            # Restore original function
            deps.get_current_user_optional = original_optional

    # API Key Verification Tests
    async def test_verify_api_key_success(self):
        """Test API key verification for authenticated user."""
        # Arrange
        current_user = {
            "id": "user_123",
            "username": "testuser",
            "is_api": False,
        }
        
        # Act
        result = await deps.verify_api_key(current_user)
        
        # Assert
        assert result is True

    async def test_verify_api_key_with_api_user(self):
        """Test API key verification for API user."""
        # Arrange
        current_user = {
            "id": "api_user",
            "username": "api_user",
            "is_api": True,
            "api_key": "tripsage_abc123",
        }
        
        # Act
        result = await deps.verify_api_key(current_user)
        
        # Assert
        assert result is True


class TestServiceDependencies:
    """Test service dependency functions."""

    async def test_get_auth_service_dep(self):
        """Test auth service dependency creation."""
        # Mock the service
        mock_service = AsyncMock()
        
        # Mock the import and function
        async def mock_get_auth_service():
            return mock_service
        
        # Patch the import in the dependency function
        import api.services.auth_service
        original_fn = api.services.auth_service.get_auth_service
        api.services.auth_service.get_auth_service = mock_get_auth_service
        
        try:
            # Act
            result = await deps.get_auth_service_dep()
            
            # Assert
            assert result is mock_service
        finally:
            # Restore original function
            api.services.auth_service.get_auth_service = original_fn

    async def test_get_key_service_dep(self):
        """Test key service dependency creation."""
        # Mock the service
        mock_service = AsyncMock()
        
        # Mock the import and function
        async def mock_get_key_service():
            return mock_service
        
        # Patch the import in the dependency function
        import api.services.key_service
        original_fn = api.services.key_service.get_key_service
        api.services.key_service.get_key_service = mock_get_key_service
        
        try:
            # Act
            result = await deps.get_key_service_dep()
            
            # Assert
            assert result is mock_service
        finally:
            # Restore original function
            api.services.key_service.get_key_service = original_fn

    async def test_get_trip_service_dep(self):
        """Test trip service dependency creation."""
        # Mock the service
        mock_service = AsyncMock()
        
        # Mock the import and function
        async def mock_get_trip_service():
            return mock_service
        
        # Patch the import in the dependency function
        import api.services.trip_service
        original_fn = api.services.trip_service.get_trip_service
        api.services.trip_service.get_trip_service = mock_get_trip_service
        
        try:
            # Act
            result = await deps.get_trip_service_dep()
            
            # Assert
            assert result is mock_service
        finally:
            # Restore original function
            api.services.trip_service.get_trip_service = original_fn

    async def test_get_cache_service_dep(self):
        """Test cache service dependency creation."""
        # Mock the service
        mock_service = AsyncMock()
        
        # Mock the get_cache_service function
        original_fn = deps.get_cache_service
        deps.get_cache_service = AsyncMock(return_value=mock_service)
        
        try:
            # Act
            result = await deps.get_cache_service_dep()
            
            # Assert
            assert result is mock_service
            deps.get_cache_service.assert_called_once()
        finally:
            # Restore original function
            deps.get_cache_service = original_fn


class TestDependencyConstants:
    """Test dependency constants and configurations."""

    def test_oauth2_scheme_configuration(self):
        """Test OAuth2 scheme configuration."""
        # Assert
        assert isinstance(deps.oauth2_scheme, OAuth2PasswordBearer)
        assert deps.oauth2_scheme.model.flows.password.tokenUrl == "api/v1/auth/token"
        assert deps.oauth2_scheme.auto_error is False

    def test_api_key_header_configuration(self):
        """Test API key header configuration."""
        # Assert
        assert deps.api_key_header.model.name == "X-API-Key"
        assert deps.api_key_header.auto_error is False

    def test_api_key_query_configuration(self):
        """Test API key query parameter configuration."""
        # Assert
        assert deps.api_key_query.model.name == "api_key"
        assert deps.api_key_query.auto_error is False

    def test_module_level_dependencies_exist(self):
        """Test that module-level dependency singletons exist."""
        # Assert that all singleton dependencies are defined
        assert hasattr(deps, '_core_auth_service_dep')
        assert hasattr(deps, 'get_current_user_dep')
        assert hasattr(deps, 'auth_service_dependency')
        assert hasattr(deps, 'key_service_dependency')
        assert hasattr(deps, 'trip_service_dependency')
        assert hasattr(deps, 'cache_service_dependency')


class TestIntegrationAndEdgeCases:
    """Test integration scenarios and edge cases."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        return AsyncMock(spec=CoreAuthService)

    async def test_authentication_precedence_chain(self, mock_auth_service):
        """Test the full authentication precedence chain."""
        # Test 1: API key in header takes precedence
        result1 = await deps.get_current_user_optional(
            token="jwt_token",
            api_key_header="tripsage_header123",
            api_key_query="tripsage_query456",
            auth_service=mock_auth_service,
        )
        assert result1["api_key"] == "tripsage_header123"
        
        # Test 2: API key in query used when no header
        result2 = await deps.get_current_user_optional(
            token="jwt_token",
            api_key_header=None,
            api_key_query="tripsage_query456",
            auth_service=mock_auth_service,
        )
        assert result2["api_key"] == "tripsage_query456"
        
        # Test 3: JWT used when no API keys
        sample_user = MagicMock()
        sample_user.id = "jwt_user"
        sample_user.username = "jwtuser"
        sample_user.email = "jwt@example.com"
        sample_user.is_active = True
        sample_user.is_verified = True
        mock_auth_service.get_current_user.return_value = sample_user
        
        result3 = await deps.get_current_user_optional(
            token="jwt_token",
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        assert result3["id"] == "jwt_user"
        assert result3["is_api"] is False

    async def test_session_memory_uuid_generation(self):
        """Test that session memory generates valid UUIDs for new sessions."""
        # Arrange
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.cookies = {}
        
        # Mock hasattr to return False initially
        def mock_hasattr(obj, name):
            return False if name == "session_memory" else hasattr(obj, name)
        
        import builtins
        original_hasattr = builtins.hasattr
        builtins.hasattr = mock_hasattr
        
        try:
            # Act
            session_memory = await deps.get_session_memory(mock_request)
            
            # Assert
            assert session_memory.session_id is not None
            # Verify it's a valid UUID format
            from uuid import UUID
            try:
                UUID(session_memory.session_id)
                uuid_valid = True
            except ValueError:
                uuid_valid = False
            assert uuid_valid is True
        finally:
            builtins.hasattr = original_hasattr

    async def test_error_handling_in_jwt_validation(self, mock_auth_service):
        """Test various error scenarios in JWT validation."""
        # Test different exception types
        error_scenarios = [
            AuthenticationError("Token expired"),
            ValueError("Invalid token format"),
            ConnectionError("Service unavailable"),
            Exception("Unexpected error"),
        ]
        
        for error in error_scenarios:
            mock_auth_service.get_current_user.side_effect = error
            
            result = await deps.get_current_user_optional(
                token="invalid_token",
                api_key_header=None,
                api_key_query=None,
                auth_service=mock_auth_service,
            )
            
            # All errors should result in None for optional auth
            assert result is None

    async def test_api_key_validation_edge_cases(self, mock_auth_service):
        """Test edge cases in API key validation."""
        # Test various invalid API key formats
        invalid_keys = [
            "invalid_prefix_key",
            "tripsage",  # Too short (missing underscore)
            "",  # Empty
            "   ",  # Whitespace only
        ]
        
        # Test keys that don't start with "tripsage_"
        for invalid_key in invalid_keys:
            result = await deps.get_current_user_optional(
                token=None,
                api_key_header=invalid_key,
                api_key_query=None,
                auth_service=mock_auth_service,
            )
            # All invalid keys should result in None
            assert result is None
        
        # Test key that starts with "tripsage_" but is minimal - should be valid
        result = await deps.get_current_user_optional(
            token=None,
            api_key_header="tripsage_",
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        # Should be valid because it starts with "tripsage_"
        assert result is not None
        assert result["api_key"] == "tripsage_"

    async def test_dependency_import_isolation(self):
        """Test that service dependency functions handle import properly."""
        # This test ensures that the dynamic imports in the dependency
        # functions work correctly and don't cause circular import issues
        
        # Test that the dependency functions can be called without errors
        # (They may fail due to missing core services, but imports should work)
        
        try:
            await deps.get_auth_service_dep()
        except Exception as e:
            # Expected to fail in test environment, but should not be ImportError
            assert not isinstance(e, ImportError)
        
        try:
            await deps.get_key_service_dep()
        except Exception as e:
            assert not isinstance(e, ImportError)
        
        try:
            await deps.get_trip_service_dep()
        except Exception as e:
            assert not isinstance(e, ImportError)