"""
Pytest configuration for TripSage tests.

This module provides common fixtures and utilities used across all test suites.
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from pydantic import BaseModel

# Add the src directory to the path so tests can import modules directly from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment variables
os.environ.setdefault("AIRBNB_MCP_ENDPOINT", "http://localhost:3000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SUPABASE_URL", "https://test-supabase-url.com")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test-password")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("WEATHER_API_KEY", "test-weather-key")
os.environ.setdefault("GOOGLE_MAPS_API_KEY", "test-google-maps-key")
os.environ.setdefault("DUFFEL_API_KEY", "test-duffel-key")


# Mock MCP manager for use in tests
@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPManager for testing."""
    manager = MagicMock()
    manager.invoke = AsyncMock()
    manager.initialize = AsyncMock()
    manager.shutdown = AsyncMock()
    yield manager


# Mock MCP registry for use in tests
@pytest.fixture
def mock_mcp_registry():
    """Create a mock MCPClientRegistry for testing."""
    registry = MagicMock()
    registry.get = Mock()
    registry.register = Mock()
    registry.wrappers = {}
    yield registry


# Mock MCP wrapper for use in tests
@pytest.fixture
def mock_mcp_wrapper():
    """Create a generic mock MCP wrapper."""
    wrapper = MagicMock()
    wrapper.invoke_method = AsyncMock()
    wrapper.initialize = AsyncMock()
    wrapper.shutdown = AsyncMock()
    yield wrapper


# Common test data models
class TestRequest(BaseModel):
    """Generic test request model."""

    query: str
    limit: int = 10
    include_details: bool = False


class TestResponse(BaseModel):
    """Generic test response model."""

    results: List[Dict[str, Any]]
    total: int
    success: bool = True


# Mock response fixtures
@pytest.fixture
def mock_successful_response():
    """Create a successful mock response."""
    return TestResponse(
        results=[
            {"id": "1", "name": "Test Item 1", "score": 0.95},
            {"id": "2", "name": "Test Item 2", "score": 0.85},
        ],
        total=2,
        success=True,
    )


@pytest.fixture
def mock_error_response():
    """Create an error mock response."""
    return TestResponse(results=[], total=0, success=False)


# Async test utilities
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Common test utilities
def assert_mcp_invoked(
    mock_manager,
    service_name: str,
    method_name: str,
    params: Optional[Dict[str, Any]] = None,
):
    """Assert that MCPManager.invoke was called with expected parameters."""
    mock_manager.invoke.assert_called_once()
    call_args = mock_manager.invoke.call_args[0]

    assert call_args[0] == service_name
    assert call_args[1] == method_name
    if params:
        assert call_args[2] == params


def create_mock_tool_response(data: Any, error: Optional[str] = None):
    """Create a standardized tool response for testing."""
    if error:
        return {"error": error, "success": False}
    return {"data": data, "success": True}


# WebOperationsCache fixture
@pytest.fixture
def mock_web_operations_cache():
    """Create a mock WebOperationsCache for testing."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.invalidate_pattern = AsyncMock(return_value=0)
    cache.get_stats = AsyncMock(return_value={})
    cache.determine_content_type = Mock()
    yield cache


@pytest.fixture
def mock_redis():
    """Mock Redis cache for tests that need it.

    Note: This is no longer autouse to avoid initializing the entire dependency chain.
    """
    with patch("src.cache.redis_cache.redis_cache") as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        yield mock_cache


# Clean up after tests
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    # Add any cleanup logic here if needed
