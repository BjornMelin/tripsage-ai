"""Configuration for MCP abstraction tests."""

# Import test initialization before any tripsage imports
from . import test_init

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock


@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPManager for testing."""
    manager = MagicMock()
    manager.invoke = AsyncMock()
    manager.initialize = AsyncMock()
    manager.shutdown = AsyncMock()
    yield manager