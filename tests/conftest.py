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

# Add the project root directory to the path so tests can import modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Completely mock settings to avoid Pydantic validation issues
# This must be done BEFORE any imports that try to load real settings

# Set minimal environment variables to satisfy required fields
os.environ.update(
    {
        "OPENAI_API_KEY": "test-key",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-key",
        "NEO4J_PASSWORD": "test-password",
        "WEATHER_MCP_OPENWEATHERMAP_API_KEY": "test-key",
        "GOOGLEMAPS_MCP_MAPS_API_KEY": "test-key",
        "WEBCRAWL_MCP_CRAWL4AI_API_KEY": "test-key",
        "WEBCRAWL_MCP_FIRECRAWL_API_KEY": "test-key",
        "FLIGHTS_MCP_DUFFEL_API_KEY": "test-key",
        "CALENDAR_MCP_GOOGLE_CLIENT_ID": "test-id",
        "CALENDAR_MCP_GOOGLE_CLIENT_SECRET": "test-secret",
        "CALENDAR_MCP_GOOGLE_REDIRECT_URI": "http://localhost",
    }
)


# Environment variables are set globally above


# Mock MCP manager for use in tests
@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPManager for testing."""
    manager = MagicMock()
    manager.invoke = AsyncMock(return_value={})
    manager.initialize_mcp = AsyncMock()
    manager.initialize_all_enabled = AsyncMock()
    available_mcps = ["weather", "time", "googlemaps", "supabase"]
    manager.get_available_mcps = Mock(return_value=available_mcps)
    manager.get_initialized_mcps = Mock(return_value=[])
    manager.load_configurations = Mock()

    # Create a side effect that returns different responses based on the MCP type
    def invoke_side_effect(mcp_name, method_name, params=None, **kwargs):
        if mcp_name == "weather":
            return {"temperature": 22.5, "conditions": "Sunny"}
        elif mcp_name == "time":
            return {"current_time": "2025-01-16T12:00:00Z", "timezone": "UTC"}
        elif mcp_name == "googlemaps":
            return {"latitude": 37.7749, "longitude": -122.4194}
        elif mcp_name == "supabase":
            return {"id": "123", "created_at": "2025-01-16T12:00:00Z"}
        return {}

    manager.invoke.side_effect = invoke_side_effect

    with patch("tripsage.mcp_abstraction.manager.mcp_manager", manager):
        yield manager


# Mock MCP registry for use in tests
@pytest.fixture
def mock_mcp_registry():
    """Create a mock MCPClientRegistry for testing."""
    registry = MagicMock()
    registry._registry = {}  # Empty registry
    registry._lazy_loaders = {}  # Empty lazy loaders
    registry.register = Mock()
    registry.register_lazy = Mock()
    registry.get_wrapper_class = Mock()
    registry.is_registered = Mock(return_value=False)
    registry.get_registered_mcps = Mock(return_value=[])

    # Setup side_effect for get_wrapper_class
    def get_wrapper_class_side_effect(mcp_name):
        if mcp_name == "weather":
            return MagicMock(__name__="WeatherMCPWrapper")
        elif mcp_name == "time":
            return MagicMock(__name__="TimeMCPWrapper")
        elif mcp_name == "googlemaps":
            return MagicMock(__name__="GoogleMapsMCPWrapper")
        elif mcp_name == "supabase":
            return MagicMock(__name__="SupabaseMCPWrapper")
        else:
            raise KeyError(f"MCP '{mcp_name}' not found in registry")

    registry.get_wrapper_class.side_effect = get_wrapper_class_side_effect

    with patch("tripsage.mcp_abstraction.registry.registry", registry):
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
    from tripsage.utils.cache import ContentType

    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.invalidate_pattern = AsyncMock(return_value=0)
    cache.get_stats = AsyncMock(
        return_value={"hits": 0, "misses": 0, "hit_ratio": 0.0, "total": 0}
    )
    cache.determine_content_type = Mock(return_value=ContentType.DAILY)
    cache.generate_cache_key = Mock(return_value="test-key")

    # Add cached response helper
    def set_cached_response(key, value, content_type=ContentType.DAILY):
        cache.get.return_value = value
        cache.determine_content_type.return_value = content_type

    cache.set_cached_response = set_cached_response

    with patch("tripsage.utils.cache.web_cache", cache):
        yield cache


@pytest.fixture
def mock_settings():
    """Create a mock settings object for tests."""
    mock_settings = MagicMock()
    mock_settings.agent.model_name = "gpt-4"
    mock_settings.agent.temperature = 0.7
    mock_settings.agent.max_tokens = 4096
    mock_settings.agent.timeout = 120
    mock_settings.agent.max_retries = 3
    return mock_settings


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for tests."""
    mock_redis_client = MagicMock()
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock(return_value=True)
    mock_redis_client.delete = AsyncMock(return_value=1)
    mock_redis_client.scan_iter = AsyncMock(return_value=[])
    mock_redis_client.incr = AsyncMock(return_value=1)
    mock_redis_client.expire = AsyncMock(return_value=True)
    return mock_redis_client


# Clean up after tests
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    # Add any cleanup logic here if needed
