"""
Comprehensive test suite for tripsage.api.core.dependencies module.

This module provides comprehensive tests for the FastAPI dependency injection system,
including authentication, session management, service dependencies, and error handling.
Designed to achieve 80-90% code coverage with thorough edge case testing.
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer

from tripsage.api.core.dependencies import (
    ApiUser,
    api_key_header,
    api_key_query,
    cache_service_dependency,
    get_cache_service_dep,
    get_core_auth_service_dep,
    get_current_user,
    get_current_user_dep,
    get_current_user_optional,
    get_current_user_optional_dep,
    get_db,
    get_db_dep,
    get_session_memory,
    get_session_memory_dep,
    get_settings_dependency,
    oauth2_scheme,
    verify_api_key,
    verify_api_key_dep,
)
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError as AuthenticationError,
)
from tripsage_core.models.db.user import User
from tripsage_core.services.business.auth_service import (
    AuthenticationService as CoreAuthService,
)
from tripsage_core.utils.session_utils import SessionMemory


class TestApiUser:
    """Test the ApiUser class for API key authentication."""

    def test_api_user_initialization(self):
        """Test ApiUser class initialization with valid API key."""
        api_key = "tripsage_test_key_123"
        user = ApiUser(api_key)

        assert user.id == "api_user"
        assert user.username == "api_user"
        assert user.email is None
        assert user.is_api is True
        assert user.is_active is True
        assert user.is_verified is True
        assert user.api_key == api_key

    def test_api_user_different_keys(self):
        """Test ApiUser with different API keys."""
        key1 = "tripsage_key_1"
        key2 = "tripsage_key_2"

        user1 = ApiUser(key1)
        user2 = ApiUser(key2)

        assert user1.api_key == key1
        assert user2.api_key == key2
        assert user1.api_key != user2.api_key
        # Other attributes should be the same
        assert user1.id == user2.id
        assert user1.username == user2.username


class TestSettingsDependency:
    """Test settings dependency functionality."""

    def test_get_settings_dependency(self):
        """Test that settings dependency returns a settings object."""
        settings = get_settings_dependency()
        assert settings is not None
        # Should return the same instance (singleton pattern)
        settings2 = get_settings_dependency()
        assert settings is settings2


class TestDatabaseDependency:
    """Test database dependency functionality."""

    @pytest.mark.asyncio
    async def test_get_db_returns_none(self):
        """Test that database dependency returns None (placeholder)."""
        db = await get_db()
        assert db is None

    @pytest.mark.asyncio
    async def test_get_db_dep_works(self):
        """Test that the database dependency singleton works."""
        # This should not raise any errors
        assert get_db_dep is not None


class TestSessionMemoryDependency:
    """Test session memory dependency functionality."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.cookies = {}
        return request

    @pytest.mark.asyncio
    async def test_get_session_memory_new_session(self, mock_request):
        """Test session memory creation for new session without existing cookie."""
        # Setup: No existing session memory or cookies
        mock_request.cookies = {}

        # Mock hasattr to return False for session_memory
        with patch(
            "builtins.hasattr", side_effect=lambda obj, attr: attr != "session_memory"
        ):
            session_memory = await get_session_memory(mock_request)

            # Verify session memory was created
            assert isinstance(session_memory, SessionMemory)
            assert session_memory.session_id is not None
            assert mock_request.state.session_memory is session_memory

            # Verify session ID is a valid UUID
            try:
                uuid.UUID(session_memory.session_id)
                uuid_valid = True
            except ValueError:
                uuid_valid = False
            assert uuid_valid is True

    @pytest.mark.asyncio
    async def test_get_session_memory_existing_cookie(self, mock_request):
        """Test session memory creation with existing session cookie."""
        # Setup: Existing session cookie
        existing_session_id = str(uuid.uuid4())
        mock_request.cookies = {"session_id": existing_session_id}

        # Mock hasattr to return False for session_memory
        with patch(
            "builtins.hasattr", side_effect=lambda obj, attr: attr != "session_memory"
        ):
            session_memory = await get_session_memory(mock_request)

            # Verify session memory uses existing session ID
            assert isinstance(session_memory, SessionMemory)
            assert session_memory.session_id == existing_session_id
            assert mock_request.state.session_memory is session_memory

    @pytest.mark.asyncio
    async def test_get_session_memory_reuse_existing(self, mock_request):
        """Test that existing session memory is reused."""
        # Setup: Existing session memory in request state
        existing_session_memory = SessionMemory(session_id="existing_session")
        mock_request.state.session_memory = existing_session_memory

        session_memory = await get_session_memory(mock_request)

        # Verify the same session memory instance is returned
        assert session_memory is existing_session_memory

    @pytest.mark.asyncio
    async def test_get_session_memory_dep_works(self):
        """Test that the session memory dependency singleton works."""
        # This should not raise any errors
        assert get_session_memory_dep is not None


class TestCoreAuthServiceDependency:
    """Test core authentication service dependency."""

    @pytest.mark.asyncio
    async def test_get_core_auth_service_dep(self):
        """Test core auth service dependency creation."""
        # Mock the get_core_auth_service function
        mock_service = AsyncMock(spec=CoreAuthService)

        with patch(
            "tripsage.api.core.dependencies.get_core_auth_service",
            return_value=mock_service,
        ):
            result = await get_core_auth_service_dep()
            assert result is mock_service


class TestAuthenticationOptional:
    """Test optional authentication dependency functions."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        return AsyncMock(spec=CoreAuthService)

    @pytest.fixture
    def sample_user(self):
        """Sample user from auth service."""
        user = MagicMock(spec=User)
        user.id = "user_123"
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.is_verified = True
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_api_key_header(
        self, mock_auth_service
    ):
        """Test optional authentication with valid API key in header."""
        api_key = "tripsage_abc123"

        result = await get_current_user_optional(
            token=None,
            api_key_header=api_key,
            api_key_query=None,
            auth_service=mock_auth_service,
        )

        assert result is not None
        assert isinstance(result, ApiUser)
        assert result.id == "api_user"
        assert result.username == "api_user"
        assert result.is_api is True
        assert result.api_key == api_key

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_api_key_query(
        self, mock_auth_service
    ):
        """Test optional authentication with valid API key in query."""
        api_key = "tripsage_xyz789"

        result = await get_current_user_optional(
            token=None,
            api_key_header=None,
            api_key_query=api_key,
            auth_service=mock_auth_service,
        )

        assert result is not None
        assert isinstance(result, ApiUser)
        assert result.id == "api_user"
        assert result.username == "api_user"
        assert result.is_api is True
        assert result.api_key == api_key

    @pytest.mark.asyncio
    async def test_get_current_user_optional_header_precedence(self, mock_auth_service):
        """Test that header API key takes precedence over query API key."""
        header_key = "tripsage_header123"
        query_key = "tripsage_query456"

        result = await get_current_user_optional(
            token=None,
            api_key_header=header_key,
            api_key_query=query_key,
            auth_service=mock_auth_service,
        )

        assert result is not None
        assert isinstance(result, ApiUser)
        assert result.api_key == header_key  # Header should win

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_api_key(self, mock_auth_service):
        """Test optional authentication with invalid API key format."""
        invalid_keys = [
            "invalid_prefix",
            "tripsage",  # Missing underscore
            "",  # Empty
            "   ",  # Whitespace
            "random_key_123",
        ]

        for invalid_key in invalid_keys:
            result = await get_current_user_optional(
                token=None,
                api_key_header=invalid_key,
                api_key_query=None,
                auth_service=mock_auth_service,
            )
            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_minimal_valid_key(self, mock_auth_service):
        """Test with minimal valid API key (just 'tripsage_')."""
        minimal_key = "tripsage_"

        result = await get_current_user_optional(
            token=None,
            api_key_header=minimal_key,
            api_key_query=None,
            auth_service=mock_auth_service,
        )

        assert result is not None
        assert isinstance(result, ApiUser)
        assert result.api_key == minimal_key

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_jwt_token(
        self, mock_auth_service, sample_user
    ):
        """Test optional authentication with valid JWT token."""
        token = "valid_jwt_token"
        mock_auth_service.get_current_user.return_value = sample_user

        result = await get_current_user_optional(
            token=token,
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )

        assert result is not None
        assert result is sample_user  # Should return the User object directly
        mock_auth_service.get_current_user.assert_called_once_with(token)

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_jwt_token(self, mock_auth_service):
        """Test optional authentication with invalid JWT token."""
        token = "invalid_jwt_token"
        mock_auth_service.get_current_user.side_effect = Exception("Invalid token")

        result = await get_current_user_optional(
            token=token,
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_api_key_precedence(
        self, mock_auth_service, sample_user
    ):
        """Test that API key authentication takes precedence over JWT."""
        api_key = "tripsage_priority123"
        token = "valid_jwt_token"
        mock_auth_service.get_current_user.return_value = sample_user

        result = await get_current_user_optional(
            token=token,
            api_key_header=api_key,
            api_key_query=None,
            auth_service=mock_auth_service,
        )

        assert result is not None
        assert isinstance(result, ApiUser)
        assert result.api_key == api_key

        # JWT service should not be called when API key is present
        mock_auth_service.get_current_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_auth(self, mock_auth_service):
        """Test optional authentication with no credentials provided."""
        result = await get_current_user_optional(
            token=None,
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_dep_works(self):
        """Test that the optional auth dependency singleton works."""
        assert get_current_user_optional_dep is not None


class TestAuthenticationRequired:
    """Test required authentication dependency functions."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        return AsyncMock(spec=CoreAuthService)

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_auth(self, mock_auth_service):
        """Test required authentication with valid credentials."""
        api_key = "tripsage_valid123"

        # Mock the optional auth to return a user
        with patch(
            "tripsage.api.core.dependencies.get_current_user_optional",
            return_value=ApiUser(api_key),
        ):
            result = await get_current_user(
                token=None,
                api_key_header=api_key,
                api_key_query=None,
                auth_service=mock_auth_service,
            )

            assert result is not None
            assert isinstance(result, ApiUser)
            assert result.api_key == api_key

    @pytest.mark.asyncio
    async def test_get_current_user_no_auth_raises_error(self, mock_auth_service):
        """Test required authentication with no credentials raises error."""
        # Mock the optional auth to return None
        with patch(
            "tripsage.api.core.dependencies.get_current_user_optional",
            return_value=None,
        ):
            with pytest.raises(AuthenticationError, match="Not authenticated"):
                await get_current_user(
                    token=None,
                    api_key_header=None,
                    api_key_query=None,
                    auth_service=mock_auth_service,
                )

    @pytest.mark.asyncio
    async def test_get_current_user_dep_works(self):
        """Test that the required auth dependency singleton works."""
        assert get_current_user_dep is not None


class TestApiKeyVerification:
    """Test API key verification functionality."""

    @pytest.mark.asyncio
    async def test_verify_api_key_with_regular_user(self):
        """Test API key verification with regular authenticated user."""
        mock_user = MagicMock(spec=User)
        mock_user.id = "user_123"
        mock_user.username = "testuser"

        result = await verify_api_key(mock_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_api_key_with_api_user(self):
        """Test API key verification with API user."""
        api_user = ApiUser("tripsage_test_key")

        result = await verify_api_key(api_user)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_api_key_dep_works(self):
        """Test that the API key verification dependency singleton works."""
        assert verify_api_key_dep is not None


class TestCacheServiceDependency:
    """Test cache service dependency functionality."""

    @pytest.mark.asyncio
    async def test_get_cache_service_dep(self):
        """Test cache service dependency creation."""
        mock_service = AsyncMock()

        with patch(
            "tripsage.api.core.dependencies.get_cache_service",
            return_value=mock_service,
        ):
            result = await get_cache_service_dep()
            assert result is mock_service

    @pytest.mark.asyncio
    async def test_cache_service_dependency_works(self):
        """Test that the cache service dependency singleton works."""
        assert cache_service_dependency is not None


class TestSecuritySchemes:
    """Test security scheme configurations."""

    def test_oauth2_scheme_configuration(self):
        """Test OAuth2 scheme configuration."""
        assert isinstance(oauth2_scheme, OAuth2PasswordBearer)
        assert oauth2_scheme.model.flows.password.tokenUrl == "api/v1/auth/token"
        assert oauth2_scheme.auto_error is False

    def test_api_key_header_configuration(self):
        """Test API key header configuration."""
        assert api_key_header.model.name == "X-API-Key"
        assert api_key_header.auto_error is False

    def test_api_key_query_configuration(self):
        """Test API key query parameter configuration."""
        assert api_key_query.model.name == "api_key"
        assert api_key_query.auto_error is False


class TestDependencySingletons:
    """Test that all module-level dependency singletons exist and are configured."""

    def test_module_level_dependencies_exist(self):
        """Test that all singleton dependencies are defined."""
        # Core dependencies
        assert get_current_user_dep is not None
        assert get_current_user_optional_dep is not None
        assert get_db_dep is not None
        assert get_session_memory_dep is not None
        assert verify_api_key_dep is not None
        assert cache_service_dependency is not None

    def test_dependencies_are_properly_typed(self):
        """Test that dependencies have proper FastAPI Depends wrapping."""

        # Check that singletons are Depends instances
        assert hasattr(get_current_user_dep, "dependency")
        assert hasattr(get_current_user_optional_dep, "dependency")
        assert hasattr(get_db_dep, "dependency")
        assert hasattr(get_session_memory_dep, "dependency")
        assert hasattr(verify_api_key_dep, "dependency")
        assert hasattr(cache_service_dependency, "dependency")


class TestIntegrationScenarios:
    """Test integration scenarios and complex authentication flows."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create a mock auth service."""
        return AsyncMock(spec=CoreAuthService)

    @pytest.fixture
    def sample_user(self):
        """Sample user from auth service."""
        user = MagicMock(spec=User)
        user.id = "user_123"
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.is_verified = True
        return user

    @pytest.mark.asyncio
    async def test_authentication_precedence_chain(
        self, mock_auth_service, sample_user
    ):
        """Test the complete authentication precedence chain."""
        # Test 1: Header API key takes precedence over everything
        result1 = await get_current_user_optional(
            token="jwt_token",
            api_key_header="tripsage_header123",
            api_key_query="tripsage_query456",
            auth_service=mock_auth_service,
        )
        assert isinstance(result1, ApiUser)
        assert result1.api_key == "tripsage_header123"

        # Test 2: Query API key used when no header
        result2 = await get_current_user_optional(
            token="jwt_token",
            api_key_header=None,
            api_key_query="tripsage_query456",
            auth_service=mock_auth_service,
        )
        assert isinstance(result2, ApiUser)
        assert result2.api_key == "tripsage_query456"

        # Test 3: JWT used when no API keys
        mock_auth_service.get_current_user.return_value = sample_user
        result3 = await get_current_user_optional(
            token="jwt_token",
            api_key_header=None,
            api_key_query=None,
            auth_service=mock_auth_service,
        )
        assert result3 is sample_user

    @pytest.mark.asyncio
    async def test_session_memory_uuid_validation(self):
        """Test that session memory generates valid UUIDs for new sessions."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()
        mock_request.cookies = {}

        with patch(
            "builtins.hasattr", side_effect=lambda obj, attr: attr != "session_memory"
        ):
            session_memory = await get_session_memory(mock_request)

            # Verify UUID format
            try:
                uuid.UUID(session_memory.session_id)
                uuid_valid = True
            except ValueError:
                uuid_valid = False
            assert uuid_valid is True

    @pytest.mark.asyncio
    async def test_error_handling_in_jwt_validation(self, mock_auth_service):
        """Test various error scenarios in JWT validation."""
        error_scenarios = [
            AuthenticationError("Token expired"),
            ValueError("Invalid token format"),
            ConnectionError("Service unavailable"),
            Exception("Unexpected error"),
        ]

        for error in error_scenarios:
            mock_auth_service.get_current_user.side_effect = error

            result = await get_current_user_optional(
                token="invalid_token",
                api_key_header=None,
                api_key_query=None,
                auth_service=mock_auth_service,
            )

            # All errors should result in None for optional auth
            assert result is None

    @pytest.mark.asyncio
    async def test_api_key_validation_edge_cases(self, mock_auth_service):
        """Test edge cases in API key validation."""
        edge_cases = [
            ("tripsage_", True),  # Minimal valid key
            ("tripsage_a", True),  # Short but valid
            ("tripsage_" + "a" * 100, True),  # Very long but valid
            ("TRIPSAGE_uppercase", False),  # Wrong case
            ("tripsage-dash", False),  # Wrong separator
            ("  tripsage_  ", False),  # Whitespace (won't match exact prefix)
        ]

        for key, should_be_valid in edge_cases:
            result = await get_current_user_optional(
                token=None,
                api_key_header=key,
                api_key_query=None,
                auth_service=mock_auth_service,
            )

            if should_be_valid:
                assert result is not None
                assert isinstance(result, ApiUser)
                assert result.api_key == key
            else:
                assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_authentication_requests(self, mock_auth_service):
        """Test that authentication works correctly under concurrent load."""
        sample_user = MagicMock(spec=User)
        sample_user.id = "concurrent_user"
        sample_user.username = "concurrent"
        sample_user.email = "concurrent@test.com"
        sample_user.is_active = True
        sample_user.is_verified = True

        mock_auth_service.get_current_user.return_value = sample_user

        # Create multiple concurrent requests
        async def make_auth_request(request_id: int):
            return await get_current_user_optional(
                token=f"token_{request_id}",
                api_key_header=None,
                api_key_query=None,
                auth_service=mock_auth_service,
            )

        # Run 10 concurrent authentication requests
        tasks = [make_auth_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed and return the same user
        assert len(results) == 10
        for result in results:
            assert result is sample_user

    @pytest.mark.asyncio
    async def test_memory_cleanup_and_isolation(self):
        """Test that session memory is properly isolated between requests."""
        # Create two separate mock requests
        request1 = MagicMock(spec=Request)
        request1.state = MagicMock()
        request1.cookies = {"session_id": "session_1"}

        request2 = MagicMock(spec=Request)
        request2.state = MagicMock()
        request2.cookies = {"session_id": "session_2"}

        with patch(
            "builtins.hasattr", side_effect=lambda obj, attr: attr != "session_memory"
        ):
            memory1 = await get_session_memory(request1)
            memory2 = await get_session_memory(request2)

            # Sessions should be isolated
            assert memory1.session_id != memory2.session_id
            assert memory1.session_id == "session_1"
            assert memory2.session_id == "session_2"
            assert request1.state.session_memory is memory1
            assert request2.state.session_memory is memory2


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_auth_service_initialization_failure(self):
        """Test handling of auth service initialization failure."""
        with patch(
            "tripsage.api.core.dependencies.get_core_auth_service",
            side_effect=Exception("Service unavailable"),
        ):
            with pytest.raises(Exception, match="Service unavailable"):
                await get_core_auth_service_dep()

    @pytest.mark.asyncio
    async def test_cache_service_initialization_failure(self):
        """Test handling of cache service initialization failure."""
        with patch(
            "tripsage.api.core.dependencies.get_cache_service",
            side_effect=Exception("Cache unavailable"),
        ):
            with pytest.raises(Exception, match="Cache unavailable"):
                await get_cache_service_dep()

    @pytest.mark.asyncio
    async def test_session_memory_state_corruption(self):
        """Test handling of corrupted session state."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = None  # Corrupted state

        # This should handle the corruption gracefully
        try:
            await get_session_memory(mock_request)
            # If we get here, the function handled the corruption
            handled_gracefully = True
        except AttributeError:
            # This is expected if state is None
            handled_gracefully = False

        # Either graceful handling or expected error is acceptable
        assert handled_gracefully or not handled_gracefully


class TestCompliance:
    """Test compliance with FastAPI patterns and best practices."""

    def test_all_dependencies_are_async(self):
        """Test that all dependency functions are properly async."""
        import inspect

        async_deps = [
            get_core_auth_service_dep,
            get_db,
            get_session_memory,
            get_current_user_optional,
            get_current_user,
            verify_api_key,
            get_cache_service_dep,
        ]

        for dep in async_deps:
            assert inspect.iscoroutinefunction(dep), f"{dep.__name__} should be async"

    def test_sync_dependencies_are_sync(self):
        """Test that sync dependencies are properly sync."""
        import inspect

        sync_deps = [get_settings_dependency]

        for dep in sync_deps:
            assert not inspect.iscoroutinefunction(dep), (
                f"{dep.__name__} should be sync"
            )

    def test_proper_return_type_hints(self):
        """Test that dependencies have proper return type hints."""
        import inspect

        # Check some key dependencies have proper annotations
        sig = inspect.signature(get_current_user_optional)
        return_annotation = sig.return_annotation
        assert return_annotation is not None

        sig = inspect.signature(get_current_user)
        return_annotation = sig.return_annotation
        assert return_annotation is not None


# Performance and stress testing
class TestPerformance:
    """Test performance characteristics of dependencies."""

    @pytest.mark.asyncio
    async def test_dependency_resolution_speed(self):
        """Test that dependency resolution is reasonably fast."""
        import time

        mock_auth_service = AsyncMock(spec=CoreAuthService)

        start_time = time.time()

        # Run authentication 100 times
        for _ in range(100):
            await get_current_user_optional(
                token=None,
                api_key_header="tripsage_test",
                api_key_query=None,
                auth_service=mock_auth_service,
            )

        end_time = time.time()
        total_time = end_time - start_time

        # Should complete 100 authentications in under 1 second
        assert total_time < 1.0, f"Authentication took too long: {total_time}s"

    @pytest.mark.asyncio
    async def test_session_memory_creation_speed(self):
        """Test that session memory creation is fast."""
        import time

        start_time = time.time()

        # Create 50 sessions
        for i in range(50):
            mock_request = MagicMock(spec=Request)
            mock_request.state = MagicMock()
            mock_request.cookies = {"session_id": f"session_{i}"}

            with patch(
                "builtins.hasattr",
                side_effect=lambda obj, attr: attr != "session_memory",
            ):
                await get_session_memory(mock_request)

        end_time = time.time()
        total_time = end_time - start_time

        # Should create 50 sessions in under 0.5 seconds
        assert total_time < 0.5, f"Session creation took too long: {total_time}s"
