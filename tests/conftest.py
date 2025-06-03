"""
Global test configuration and fixtures.

This module provides centralized test configuration, fixtures, and setup
for the entire TripSage test suite with proper async support and mocking.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Load test environment variables FIRST
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(".env.test", override=True)

# Add the project root directory to the path so tests can import modules directly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def setup_test_environment():
    """Set up comprehensive test environment variables."""
    test_env = {
        # Core application settings
        "TRIPSAGE_TEST_MODE": "true",
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "LOG_LEVEL": "INFO",
        # Database configuration
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key-1234567890abcdef",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key-1234567890abcdef",
        "SUPABASE_PROJECT_ID": "test-project-id",
        # Cache configuration
        "REDIS_URL": "redis://localhost:6379/1",
        "DRAGONFLY_URL": "redis://localhost:6379/1",
        # API Keys (safe test values)
        "OPENAI_API_KEY": "sk-test-openai-key-1234567890abcdef",
        "ANTHROPIC_API_KEY": "sk-ant-test-anthropic-key-1234567890abcdef",
        "GOOGLE_MAPS_API_KEY": "test-google-maps-key-1234567890",
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
        "DUFFEL_API_KEY": "test-duffel-api-key-1234567890",
        "OPENWEATHERMAP_API_KEY": "test-weather-api-key-1234567890",
        "VISUAL_CROSSING_API_KEY": "test-visual-crossing-key-1234567890",
        # Security
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only",
        "API_KEY_MASTER_SECRET": "test-master-secret-for-byok-encryption",
        # External services
        "CRAWL4AI_API_URL": "http://localhost:8000/api",
        "CRAWL4AI_API_KEY": "test-crawl4ai-key-1234567890",
        "WEBCRAWL_CRAWL4AI_API_KEY": "test-crawl-key",
        "WEBCRAWL_FIRECRAWL_API_KEY": "test-firecrawl-key",
        # MCP Endpoints - All required MCP configurations
        "TIME_MCP_ENDPOINT": "http://localhost:3006",
        "WEATHER_MCP_ENDPOINT": "http://localhost:3007",
        "WEATHER_MCP_OPENWEATHERMAP_API_KEY": "test-weather-api-key",
        "GOOGLEMAPS_MCP_ENDPOINT": "http://localhost:3008",
        "GOOGLEMAPS_MCP_MAPS_API_KEY": "test-maps-api-key",
        "MEMORY_MCP_ENDPOINT": "http://localhost:3009",
        "WEBCRAWL_MCP_ENDPOINT": "http://localhost:3010",
        "FLIGHTS_MCP_ENDPOINT": "http://localhost:3011",
        "FLIGHTS_MCP_DUFFEL_API_KEY": "test-duffel-key",
        "ACCOMMODATIONS_MCP_AIRBNB_ENDPOINT": "http://localhost:3012",
        "PLAYWRIGHT_MCP_ENDPOINT": "http://localhost:3013",
        "CALENDAR_MCP_ENDPOINT": "http://localhost:3014",
        "CALENDAR_MCP_GOOGLE_CLIENT_ID": "test-client-id",
        "CALENDAR_MCP_GOOGLE_CLIENT_SECRET": "test-client-secret",
        "CALENDAR_MCP_GOOGLE_REDIRECT_URI": "http://localhost:3000/callback",
        "SUPABASE_MCP_ENDPOINT": "http://localhost:3016",
        # Feature flags for testing
        "ENABLE_STREAMING_RESPONSES": "false",
        "ENABLE_RATE_LIMITING": "false",
        "ENABLE_CACHING": "false",
        "ENABLE_DEBUG_MODE": "true",
        "ENABLE_TRACING": "false",
        "ENABLE_AGENT_MEMORY": "true",
        "ENABLE_PARALLEL_AGENTS": "true",
        "ENABLE_CRAWL4AI": "true",
        "ENABLE_MEM0": "true",
        "ENABLE_LANGGRAPH": "true",
    }

    # Apply all environment variables
    for key, value in test_env.items():
        os.environ[key] = value


def mock_problematic_imports():
    """Mock problematic imports that might cause test failures."""
    try:
        import langchain_core  # noqa: F401
        import langchain_openai  # noqa: F401
        import langgraph  # noqa: F401
    except ImportError:
        # Create mock modules if imports fail
        sys.modules["langchain_core"] = MagicMock()
        sys.modules["langchain_core.language_models"] = MagicMock()
        sys.modules["langchain_core.language_models.chat_models"] = MagicMock()
        sys.modules["langchain_openai"] = MagicMock()
        sys.modules["langchain_openai.chat_models"] = MagicMock()
        sys.modules["langgraph"] = MagicMock()
        sys.modules["langgraph.graph"] = MagicMock()
        sys.modules["langgraph.checkpoint"] = MagicMock()

        # Mock ChatOpenAI class
        mock_chat_openai = MagicMock()
        mock_chat_openai.return_value = AsyncMock()
        sys.modules["langchain_openai"].ChatOpenAI = mock_chat_openai

    try:
        import mem0ai  # noqa: F401
    except ImportError:
        sys.modules["mem0ai"] = MagicMock()
        sys.modules["mem0"] = MagicMock()


# Set up test environment immediately
setup_test_environment()
mock_problematic_imports()


@pytest.fixture(autouse=True)
def mock_environment_variables():
    """Ensure environment variables are available for tests."""
    # Environment already set above, just yield
    yield os.environ


# Mock MCP manager for use in tests
@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPManager for testing (Airbnb only)."""
    manager = MagicMock()
    manager.invoke = AsyncMock(return_value={})
    manager.initialize = AsyncMock()
    manager.get_available_methods = Mock(
        return_value=["search_listings", "get_listing_details", "check_availability"]
    )

    # Create a side effect that returns Airbnb-specific responses
    def invoke_side_effect(method_name, params=None, **kwargs):
        if method_name in ["search_listings", "search_accommodations", "search"]:
            return {"listings": [], "count": 0}
        elif method_name in ["get_listing_details", "get_listing", "get_details"]:
            return {"id": "123", "name": "Test Listing", "price_per_night": 100}
        elif method_name in ["check_availability", "check_listing_availability"]:
            return {"available": True, "dates": []}
        return {}

    manager.invoke.side_effect = invoke_side_effect

    with patch("tripsage.mcp_abstraction.manager.mcp_manager", manager):
        yield manager


# Mock MCP registry for use in tests
@pytest.fixture
def mock_mcp_registry():
    """Create a mock MCPRegistry for testing (Airbnb only)."""
    registry = MagicMock()
    registry._wrapper_class = None
    registry.register_airbnb = Mock()
    registry.get_airbnb_wrapper = Mock()

    # Mock the AirbnbMCPWrapper class
    mock_wrapper_class = MagicMock()
    mock_wrapper_class.__name__ = "AirbnbMCPWrapper"
    registry.get_airbnb_wrapper.return_value = mock_wrapper_class

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
    from tripsage_core.utils.content_utils import ContentType

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

    with patch("tripsage.tools.web_tools.web_cache", cache):
        yield cache


@pytest.fixture(autouse=True)
def mock_settings_and_redis(monkeypatch):
    """Mock settings and Redis client to avoid actual connections and
    validation errors."""
    # Set environment variables for testing
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test_anon_key")

    # Set API keys
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")

    # Create a comprehensive mock settings object
    mock_settings = MagicMock()
    mock_settings.agent.model_name = "gpt-4"
    mock_settings.agent.temperature = 0.7
    mock_settings.agent.max_tokens = 4096
    mock_settings.agent.timeout = 120
    mock_settings.agent.max_retries = 3

    # Mock database settings
    mock_settings.database.supabase_url = "https://test.supabase.co"
    mock_settings.database.supabase_anon_key = "test_anon_key"

    # Mock memory service (Mem0)
    mock_settings.memory.service_type = "mem0"
    mock_settings.memory.api_key = "test_mem0_key"

    # Mock Redis client
    mock_redis_client = MagicMock()
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock(return_value=True)
    mock_redis_client.delete = AsyncMock(return_value=1)
    mock_redis_client.scan_iter = AsyncMock(return_value=[])
    mock_redis_client.incr = AsyncMock(return_value=1)
    mock_redis_client.expire = AsyncMock(return_value=True)

    mock_from_url = MagicMock(return_value=mock_redis_client)

    # Apply all the patches we need
    with (
        patch(
            "tripsage_core.config.base_app_settings.get_settings",
            return_value=mock_settings,
        ),
        patch("tripsage_core.config.base_app_settings.settings", mock_settings),
        patch("redis.asyncio.from_url", mock_from_url),
        patch("redis.from_url", mock_from_url),
    ):
        yield {
            "settings": mock_settings,
            "redis": mock_redis_client,
        }


# Clean up after tests
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    # Add any cleanup logic here if needed
