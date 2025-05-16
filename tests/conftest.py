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

# Mock environment variables instead of setting them directly
@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Mock common environment variables needed for tests."""
    env_vars = {
        "AIRBNB_MCP_ENDPOINT": "http://localhost:3000",
        "REDIS_URL": "redis://localhost:6379/0",
        "SUPABASE_URL": "https://test-supabase-url.com",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "test-password",
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "WEATHER_API_KEY": "test-weather-key",
        "GOOGLE_MAPS_API_KEY": "test-google-maps-key",
        "DUFFEL_API_KEY": "test-duffel-key",
        "PLAYWRIGHT_URL": "http://localhost:3003",
        "FIRECRAWL_URL": "http://localhost:3004",
        "CRAWL4AI_URL": "http://localhost:3005",
        "TIME_MCP_ENDPOINT": "http://localhost:3006",
        "WEATHER_MCP_ENDPOINT": "http://localhost:3007",
        "GOOGLEMAPS_MCP_ENDPOINT": "http://localhost:3008",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


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
    cache.get_stats = AsyncMock(return_value={
        "hits": 0,
        "misses": 0,
        "hit_ratio": 0.0,
        "total": 0
    })
    cache.determine_content_type = Mock(return_value=ContentType.DAILY)
    cache.generate_cache_key = Mock(return_value="test-key")
    
    # Add cached response helper
    def set_cached_response(key, value, content_type=ContentType.DAILY):
        cache.get.return_value = value
        cache.determine_content_type.return_value = content_type
        
    cache.set_cached_response = set_cached_response
    
    with patch("tripsage.utils.cache.web_cache", cache):
        yield cache


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client to avoid actual connections.
    
    This fixture is marked autouse=True since many components require Redis,
    including WebOperationsCache, which is initialized at module import.
    """
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.scan_iter = AsyncMock(return_value=[])
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    
    # Mock the redis module's from_url function to return our mock
    mock_from_url = MagicMock(return_value=mock_client)
    
    # We need to patch both redis.asyncio and redis directly
    with patch("redis.asyncio.from_url", mock_from_url):
        with patch("redis.from_url", mock_from_url):
            redis_mock = MagicMock(asyncio=MagicMock(from_url=mock_from_url))
            with patch("tripsage.utils.cache.redis", redis_mock):
                yield mock_client


# Clean up after tests
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    # Add any cleanup logic here if needed
