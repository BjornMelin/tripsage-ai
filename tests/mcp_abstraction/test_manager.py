"""
Tests for MCPManager.

This module tests the centralized MCP manager that coordinates all MCP operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.mcp_abstraction.exceptions import (
    MCPConfigurationError,
    MCPConnectionError,
    MCPNotFoundError,
    MCPTimeoutError,
    TripSageMCPError,
)
from tripsage.mcp_abstraction.manager import MCPManager


class TestMCPManager:
    """Tests for MCPManager functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry with some registered wrappers."""
        registry = MagicMock()

        # Mock wrapper
        mock_wrapper = MagicMock()
        mock_wrapper.invoke_method = AsyncMock()

        # Configure registry get method
        registry.get.return_value = mock_wrapper

        return registry, mock_wrapper

    @patch("tripsage.mcp_abstraction.manager.MCPSettings")
    @patch("tripsage.mcp_abstraction.manager.MCPClientRegistry")
    def test_initialization(self, mock_registry_class, mock_settings_class):
        """Test MCPManager initialization."""
        # Configure mocks
        mock_settings = MagicMock()
        mock_settings_class.return_value = mock_settings
        mock_registry = MagicMock()
        mock_registry_class.return_value = mock_registry

        # Create manager
        manager = MCPManager()

        # Verify initialization
        assert manager.settings == mock_settings
        assert manager.registry == mock_registry
        assert manager.initialized is False

    @pytest.mark.asyncio
    async def test_invoke_success(self, mock_registry):
        """Test successful MCP invocation."""
        registry, wrapper = mock_registry

        # Configure wrapper response
        wrapper.invoke_method.return_value = {
            "result": "success",
            "data": {"value": 42},
        }

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test invocation
            result = await manager.invoke(
                "test-service", "test-method", {"param": "value"}
            )

            # Verify
            registry.get.assert_called_once_with("test-service")
            wrapper.invoke_method.assert_called_once_with(
                "test-method", {"param": "value"}
            )
            assert result == {"result": "success", "data": {"value": 42}}

    @pytest.mark.asyncio
    async def test_invoke_wrapper_not_found(self, mock_registry):
        """Test invocation when wrapper is not found."""
        registry, _ = mock_registry

        # Configure registry to return None
        registry.get.return_value = None

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test invocation
            with pytest.raises(MCPNotFoundError) as exc_info:
                await manager.invoke("unknown-service", "test-method", {})

            assert "No wrapper found for service: unknown-service" in str(
                exc_info.value
            )

    @pytest.mark.asyncio
    async def test_invoke_with_error(self, mock_registry):
        """Test invocation when MCP service returns an error."""
        registry, wrapper = mock_registry

        # Configure wrapper to raise an exception
        wrapper.invoke_method.side_effect = TripSageMCPError("Test error")

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test invocation
            with pytest.raises(TripSageMCPError) as exc_info:
                await manager.invoke("test-service", "test-method", {})

            assert "Test error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_timeout(self, mock_registry):
        """Test invocation timeout handling."""
        registry, wrapper = mock_registry

        # Configure wrapper to raise timeout error
        wrapper.invoke_method.side_effect = MCPTimeoutError("Request timed out")

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test invocation
            with pytest.raises(MCPTimeoutError) as exc_info:
                await manager.invoke("test-service", "test-method", {})

            assert "Request timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize(self, mock_registry):
        """Test manager initialization."""
        registry, wrapper = mock_registry

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test initialization
            await manager.initialize()

            # Verify state
            assert manager.initialized is True

    @pytest.mark.asyncio
    async def test_shutdown(self, mock_registry):
        """Test manager shutdown."""
        registry, wrapper = mock_registry

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Initialize first
            await manager.initialize()

            # Test shutdown
            await manager.shutdown()

            # Verify state
            assert manager.initialized is False

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_registry):
        """Test using MCPManager as a context manager."""
        registry, wrapper = mock_registry

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Use as context manager
            async with manager:
                assert manager.initialized is True

                # Make a call within context
                wrapper.invoke_method.return_value = {"success": True}
                result = await manager.invoke("test-service", "test-method", {})
                assert result == {"success": True}

            # After context exit
            assert manager.initialized is False

    def test_singleton_pattern(self):
        """Test that MCPManager follows singleton pattern."""
        with patch("tripsage.mcp_abstraction.manager.MCPSettings"):
            with patch("tripsage.mcp_abstraction.manager.MCPClientRegistry"):
                manager1 = MCPManager()
                manager2 = MCPManager()

                # Should be the same instance
                assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_invoke_with_retry(self, mock_registry):
        """Test invocation with retry logic."""
        registry, wrapper = mock_registry

        # Configure wrapper to fail first, then succeed
        wrapper.invoke_method.side_effect = [
            MCPConnectionError("Connection failed"),
            {"result": "success"},
        ]

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test invocation with retry
            result = await manager.invoke("test-service", "test-method", {}, retry=True)

            # Verify retry was attempted
            assert wrapper.invoke_method.call_count == 2
            assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_invoke_no_retry_on_configuration_error(self, mock_registry):
        """Test that configuration errors are not retried."""
        registry, wrapper = mock_registry

        # Configure wrapper to raise configuration error
        wrapper.invoke_method.side_effect = MCPConfigurationError("Invalid config")

        # Create manager with mocked registry
        with patch(
            "tripsage.mcp_abstraction.manager.MCPClientRegistry", return_value=registry
        ):
            manager = MCPManager()

            # Test invocation
            with pytest.raises(MCPConfigurationError):
                await manager.invoke("test-service", "test-method", {}, retry=True)

            # Verify only called once (no retry)
            assert wrapper.invoke_method.call_count == 1
