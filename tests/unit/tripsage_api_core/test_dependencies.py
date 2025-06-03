"""
Test suite for unified API dependencies.

Tests the modern Principal-based dependency injection system.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from tripsage.api.core.dependencies import (
    get_cache_service_dep,
    get_current_principal,
    get_db,
    get_mcp_manager,
    get_principal_id,
    get_session_memory,
    get_settings_dependency,
    require_agent_principal,
    require_principal,
    require_user_principal,
    verify_service_access,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import CoreAuthenticationError
from tripsage_core.mcp_abstraction import MCPManager
from tripsage_core.utils.session_utils import SessionMemory


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
    async def test_get_db_yields_session(self):
        """Test that database dependency yields an AsyncSession."""
        with patch(
            "tripsage.api.core.dependencies.get_database_service"
        ) as mock_get_service:
            # Mock the database service
            mock_service = AsyncMock()
            mock_session = MagicMock(spec=AsyncSession)

            # Create async context manager mock
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None

            # Make get_session return the async context manager
            mock_service.get_session = MagicMock(return_value=mock_context_manager)
            mock_get_service.return_value = mock_service

            # Use the dependency as an async generator
            async for session in get_db():
                assert session == mock_session
                assert isinstance(session, AsyncSession)


class TestSessionMemoryDependency:
    """Test session memory dependency functionality."""

    @pytest.mark.asyncio
    async def test_get_session_memory_new_session(self):
        """Test getting session memory for a new session."""
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.cookies = {}

        memory = await get_session_memory(request)
        assert isinstance(memory, SessionMemory)
        assert memory.session_id is not None
        assert request.state.session_memory == memory

    @pytest.mark.asyncio
    async def test_get_session_memory_existing_session(self):
        """Test getting session memory with existing session ID."""
        session_id = str(uuid.uuid4())
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.cookies = {"session_id": session_id}

        memory = await get_session_memory(request)
        assert isinstance(memory, SessionMemory)
        assert memory.session_id == session_id

    @pytest.mark.asyncio
    async def test_get_session_memory_already_in_state(self):
        """Test getting session memory when already in request state."""
        existing_memory = SessionMemory(session_id="existing-session")
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.session_memory = existing_memory
        request.cookies = {}

        memory = await get_session_memory(request)
        assert memory == existing_memory


class TestPrincipalDependencies:
    """Test Principal-based authentication dependencies."""

    @pytest.mark.asyncio
    async def test_get_current_principal_present(self):
        """Test getting current principal when present in request state."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.principal = principal

        result = await get_current_principal(request)
        assert result == principal

    @pytest.mark.asyncio
    async def test_get_current_principal_not_present(self):
        """Test getting current principal when not present."""
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()

        result = await get_current_principal(request)
        assert result is None

    @pytest.mark.asyncio
    async def test_require_principal_success(self):
        """Test requiring principal when present."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.principal = principal

        result = await require_principal(request)
        assert result == principal

    @pytest.mark.asyncio
    async def test_require_principal_failure(self):
        """Test requiring principal when not present."""
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()

        with pytest.raises(CoreAuthenticationError) as exc_info:
            await require_principal(request)

        assert exc_info.value.code == "AUTH_REQUIRED"

    @pytest.mark.asyncio
    async def test_require_user_principal_success(self):
        """Test requiring user principal when user is present."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.principal = principal

        result = await require_user_principal(request)
        assert result == principal

    @pytest.mark.asyncio
    async def test_require_user_principal_failure_agent(self):
        """Test requiring user principal when agent is present."""
        principal = Principal(
            id="123",
            type="agent",
            auth_method="api_key",
            service="openai",
        )
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.principal = principal

        with pytest.raises(CoreAuthenticationError) as exc_info:
            await require_user_principal(request)

        assert exc_info.value.code == "USER_AUTH_REQUIRED"

    @pytest.mark.asyncio
    async def test_require_agent_principal_success(self):
        """Test requiring agent principal when agent is present."""
        principal = Principal(
            id="123",
            type="agent",
            auth_method="api_key",
            service="openai",
        )
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.principal = principal

        result = await require_agent_principal(request)
        assert result == principal

    @pytest.mark.asyncio
    async def test_require_agent_principal_failure_user(self):
        """Test requiring agent principal when user is present."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )
        request = MagicMock(spec=Request)
        request.state = type("State", (), {})()
        request.state.principal = principal

        with pytest.raises(CoreAuthenticationError) as exc_info:
            await require_agent_principal(request)

        assert exc_info.value.code == "AGENT_AUTH_REQUIRED"


class TestPrincipalUtilities:
    """Test principal utility functions."""

    def test_get_principal_id(self):
        """Test getting principal ID."""
        principal = Principal(
            id="test-id-123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )

        result = get_principal_id(principal)
        assert result == "test-id-123"


class TestServiceAccess:
    """Test service access verification."""

    @pytest.mark.asyncio
    async def test_verify_service_access_agent(self):
        """Test service access verification for agents."""
        principal = Principal(
            id="123",
            type="agent",
            auth_method="api_key",
            service="openai",
        )

        mock_db = MagicMock(spec=AsyncSession)
        mock_key_service = AsyncMock()

        result = await verify_service_access(
            principal, "openai", mock_db, mock_key_service
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_service_access_user_with_key(self):
        """Test service access verification for user with required key."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )

        mock_db = MagicMock(spec=AsyncSession)
        mock_key_service = AsyncMock()

        # Mock key exists
        mock_key = MagicMock()
        mock_key.service = "openai"
        mock_key_service.get_user_keys.return_value = [mock_key]

        result = await verify_service_access(
            principal, "openai", mock_db, mock_key_service
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_service_access_user_without_key(self):
        """Test service access verification for user without required key."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )

        mock_db = MagicMock(spec=AsyncSession)
        mock_key_service = AsyncMock()

        # Mock no matching key
        mock_key = MagicMock()
        mock_key.service = "google_maps"
        mock_key_service.get_user_keys.return_value = [mock_key]

        result = await verify_service_access(
            principal, "openai", mock_db, mock_key_service
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_service_access_service_error(self):
        """Test service access verification with service error."""
        principal = Principal(
            id="123",
            type="user",
            email="test@example.com",
            auth_method="jwt",
        )

        mock_db = MagicMock(spec=AsyncSession)
        mock_key_service = AsyncMock()
        mock_key_service.get_user_keys.side_effect = Exception("Service error")

        result = await verify_service_access(
            principal, "openai", mock_db, mock_key_service
        )
        assert result is False


class TestUtilityDependencies:
    """Test utility dependencies."""

    @pytest.mark.asyncio
    async def test_get_cache_service_dep(self):
        """Test cache service dependency."""
        with patch(
            "tripsage.api.core.dependencies.get_cache_service"
        ) as mock_get_cache:
            mock_cache = MagicMock()
            mock_get_cache.return_value = mock_cache

            cache = await get_cache_service_dep()
            assert cache == mock_cache

    def test_get_mcp_manager(self):
        """Test MCP manager dependency."""
        manager = get_mcp_manager()
        assert isinstance(manager, MCPManager)
