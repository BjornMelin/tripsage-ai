"""Unit tests for :mod:`tripsage.agents.service_registry`."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from tripsage.agents.service_registry import ServiceRegistry
from tripsage_core.services.business.user_service import UserService
from tripsage_core.services.infrastructure import DatabaseService


@pytest.fixture()
def mock_database_service() -> DatabaseService:
    """Create a mock database service for testing."""
    return MagicMock(spec=DatabaseService)


@pytest.fixture()
def mock_user_service() -> UserService:
    """Create a mock user service for testing."""
    return MagicMock(spec=UserService)


@pytest.fixture()
def empty_registry() -> ServiceRegistry:
    """Create an empty service registry for testing."""
    return ServiceRegistry()


@pytest.fixture()
def populated_registry(mock_user_service: UserService) -> ServiceRegistry:
    """Create a registry with some services populated."""
    return ServiceRegistry(user_service=mock_user_service)


def test_service_registry_initialization_empty(empty_registry: ServiceRegistry) -> None:
    """ServiceRegistry initializes with all services None by default."""
    assert empty_registry.accommodation_service is None
    assert empty_registry.chat_service is None
    assert empty_registry.user_service is None
    assert empty_registry.database_service is None
    assert empty_registry.checkpoint_service is None
    assert empty_registry.memory_bridge is None
    assert empty_registry.mcp_bridge is None


def test_service_registry_initialization_with_services(
    populated_registry: ServiceRegistry, mock_user_service: UserService
) -> None:
    """ServiceRegistry can be initialized with specific services."""
    assert populated_registry.user_service == mock_user_service


def test_get_required_service_success(
    populated_registry: ServiceRegistry, mock_user_service: UserService
) -> None:
    """get_required_service returns service when present."""
    result = populated_registry.get_required_service(
        "user_service", expected_type=UserService
    )
    assert result == mock_user_service


def test_get_required_service_missing(empty_registry: ServiceRegistry) -> None:
    """get_required_service raises ValueError when service is missing."""
    with pytest.raises(
        ValueError, match="Required service 'user_service' is not initialized"
    ):
        empty_registry.get_required_service("user_service")


def test_get_required_service_wrong_type(
    populated_registry: ServiceRegistry, mock_user_service: UserService
) -> None:
    """get_required_service raises TypeError when service type doesn't match."""
    with pytest.raises(
        TypeError, match="Service 'user_service' is not of expected type str"
    ):
        populated_registry.get_required_service("user_service", expected_type=str)


def test_get_optional_service_success(
    populated_registry: ServiceRegistry, mock_user_service: UserService
) -> None:
    """get_optional_service returns service when present."""
    result = populated_registry.get_optional_service(
        "user_service", expected_type=UserService
    )
    assert result == mock_user_service


def test_get_optional_service_missing(empty_registry: ServiceRegistry) -> None:
    """get_optional_service returns None when service is missing."""
    result = empty_registry.get_optional_service("user_service")
    assert result is None


def test_get_optional_service_wrong_type(
    populated_registry: ServiceRegistry, mock_user_service: UserService
) -> None:
    """get_optional_service raises TypeError when service type doesn't match."""
    with pytest.raises(
        TypeError, match="Service 'user_service' is not of expected type str"
    ):
        populated_registry.get_optional_service("user_service", expected_type=str)


def test_get_checkpoint_service_success() -> None:
    """get_checkpoint_service returns checkpoint service when present."""
    mock_checkpoint = MagicMock()
    registry = ServiceRegistry(checkpoint_service=mock_checkpoint)

    result = registry.get_checkpoint_service()
    assert result == mock_checkpoint


def test_get_checkpoint_service_missing(empty_registry: ServiceRegistry) -> None:
    """get_checkpoint_service raises ValueError when not configured."""
    with pytest.raises(ValueError, match="Checkpoint manager is not configured"):
        empty_registry.get_checkpoint_service()


def test_get_memory_bridge_success() -> None:
    """get_memory_bridge returns memory bridge when present."""
    mock_memory_bridge = MagicMock()
    registry = ServiceRegistry(memory_bridge=mock_memory_bridge)

    result = registry.get_memory_bridge()
    assert result == mock_memory_bridge


def test_get_memory_bridge_missing(empty_registry: ServiceRegistry) -> None:
    """get_memory_bridge raises ValueError when not configured."""
    with pytest.raises(ValueError, match="Memory bridge is not configured"):
        empty_registry.get_memory_bridge()


@pytest.mark.asyncio
async def test_get_mcp_bridge_success() -> None:
    """get_mcp_bridge returns initialized MCP bridge when present."""
    mock_mcp_bridge = MagicMock()
    mock_mcp_bridge.is_initialized = True
    registry = ServiceRegistry(mcp_bridge=mock_mcp_bridge)

    result = await registry.get_mcp_bridge()
    assert result == mock_mcp_bridge
    mock_mcp_bridge.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_get_mcp_bridge_initializes_if_needed() -> None:
    """get_mcp_bridge initializes MCP bridge if not already initialized."""
    mock_mcp_bridge = MagicMock()
    mock_mcp_bridge.is_initialized = False
    mock_mcp_bridge.initialize = AsyncMock()
    registry = ServiceRegistry(mcp_bridge=mock_mcp_bridge)

    result = await registry.get_mcp_bridge()
    assert result == mock_mcp_bridge
    mock_mcp_bridge.initialize.assert_called_once()


@pytest.mark.asyncio
async def test_get_mcp_bridge_missing(empty_registry: ServiceRegistry) -> None:
    """get_mcp_bridge raises ValueError when not configured."""
    with pytest.raises(ValueError, match="MCP bridge is not configured"):
        await empty_registry.get_mcp_bridge()
