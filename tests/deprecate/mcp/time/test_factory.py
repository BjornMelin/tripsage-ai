"""
Tests for the Time MCP Client Factory.

This module contains unit tests for the Time MCP Client Factory implementation,
testing configuration validation, client creation, and instance management.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Create mocks
mock_redis_cache = MagicMock()
mock_redis_cache.get = MagicMock(return_value=None)
mock_redis_cache.set = MagicMock(return_value=None)
mock_redis_cache.cached = MagicMock(side_effect=lambda name, ttl=None: lambda f: f)

# Mock all required modules and classes
sys.modules["src.cache.redis_cache"] = MagicMock()
sys.modules["src.cache.redis_cache"].redis_cache = mock_redis_cache
sys.modules["src.cache.redis_cache"].RedisCache = MagicMock(
    return_value=mock_redis_cache
)
sys.modules["src.cache.redis_cache"].get_cache = MagicMock(
    return_value=mock_redis_cache
)

# Mock settings module
mock_settings = MagicMock()
mock_settings.time_mcp = MagicMock(
    endpoint="http://mocked-time-server.example.com",
    api_key="mocked-api-key",
    timeout=30.0,
)

# Add settings to sys.modules
sys.modules["src.utils.settings"] = MagicMock()
sys.modules["src.utils.settings"].settings = mock_settings

# Now import the modules that depend on these mocks
from tripsage.mcp.time.client import TimeMCPClient  # noqa: E402
from tripsage.mcp.time.factory import TimeMCPClientFactory, TimeMCPConfig  # noqa: E402

# Mock FastMCPClient for clean testing
mock_client = MagicMock()
sys.modules["src.mcp.fastmcp"] = MagicMock()
sys.modules["src.mcp.fastmcp"].FastMCPClient = MagicMock
sys.modules["src.mcp.base_mcp_client"] = MagicMock()
sys.modules["src.mcp.base_mcp_client"].BaseMCPClient = MagicMock


# Create a simple mock for TimeMCPClient
class MockTimeMCPClient:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def time_factory():
    """Create a Time MCP Client Factory for testing."""
    # Set up the mock client class
    TimeMCPClientFactory.client_class = MockTimeMCPClient

    factory = TimeMCPClientFactory()
    # Mock the _load_config_from_settings method to return test values
    factory._load_config_from_settings = MagicMock(
        return_value={
            "endpoint": "http://test-time-mcp.example.com",
            "api_key": "test-api-key",
            "timeout": 30.0,
            "use_cache": True,
            "cache_ttl": 1800,
        }
    )
    return factory


def test_time_config_validation():
    """Test the Time MCP configuration validation."""
    # Test valid configuration
    config = TimeMCPConfig(
        endpoint="http://time-mcp.example.com",
        api_key="test-api-key",
        timeout=30.0,
        use_cache=True,
        cache_ttl=1800,
    )
    assert config.endpoint == "http://time-mcp.example.com"
    assert config.api_key == "test-api-key"
    assert config.timeout == 30.0
    assert config.use_cache is True
    assert config.cache_ttl == 1800

    # Test endpoint protocol correction
    config = TimeMCPConfig(
        endpoint="time-mcp.example.com",
        api_key="test-api-key",
    )
    assert config.endpoint == "https://time-mcp.example.com"

    # Test trailing slash removal
    config = TimeMCPConfig(
        endpoint="http://time-mcp.example.com/",
        api_key="test-api-key",
    )
    assert config.endpoint == "http://time-mcp.example.com"

    # Test validation error for timeout range
    with pytest.raises(ValueError):
        TimeMCPConfig(
            endpoint="http://time-mcp.example.com",
            timeout=0.5,  # Too small
        )

    with pytest.raises(ValueError):
        TimeMCPConfig(
            endpoint="http://time-mcp.example.com",
            timeout=150.0,  # Too large
        )


def test_create_client(time_factory):
    """Test creating a new Time MCP Client instance."""
    # Create a client with default configuration
    client = time_factory.create_client()
    assert isinstance(client, TimeMCPClient)
    assert client.endpoint == "http://test-time-mcp.example.com"
    assert client.api_key == "test-api-key"
    assert client.timeout == 30.0
    assert client.use_cache is True
    assert client.cache_ttl == 1800
    assert client.server_name == "Time"

    # Create a client with overridden configuration
    client = time_factory.create_client(
        endpoint="http://override.example.com",
        timeout=20.0,
    )
    assert client.endpoint == "http://override.example.com"
    assert client.timeout == 20.0
    # Other values should remain unchanged
    assert client.api_key == "test-api-key"
    assert client.use_cache is True
    assert client.cache_ttl == 1800


def test_get_client(time_factory):
    """Test getting a cached Time MCP Client instance."""
    # First call should create a new instance
    client1 = time_factory.get_client()
    assert isinstance(client1, TimeMCPClient)

    # Second call should return the same instance
    client2 = time_factory.get_client()
    assert client1 is client2

    # Call with override_config should create a new instance
    client3 = time_factory.get_client(timeout=15.0)
    assert client1 is not client3
    assert client3.timeout == 15.0

    # Reset should clear the cached instance
    time_factory.reset_client()
    client4 = time_factory.get_client()
    assert client1 is not client4


@patch("src.mcp.time.factory.settings")
def test_load_config_from_settings(mock_settings):
    """Test loading configuration from application settings."""
    # Create mock settings with time_mcp configuration
    mock_time_mcp = MagicMock()
    mock_time_mcp.endpoint = "http://settings-time-mcp.example.com"
    mock_time_mcp.api_key = "settings-api-key"
    mock_time_mcp.timeout = 45.0
    mock_settings.time_mcp = mock_time_mcp

    # Create factory with real _load_config_from_settings method
    factory = TimeMCPClientFactory()

    # Load config from settings
    config = factory._load_config_from_settings()

    # Verify config values
    assert config["endpoint"] == "http://settings-time-mcp.example.com"
    assert config["api_key"] == "settings-api-key"
    assert config["timeout"] == 45.0

    # Test with missing settings
    delattr(mock_settings, "time_mcp")
    config = factory._load_config_from_settings()

    # Should use default values
    assert config["endpoint"] == "http://localhost:3000"
    assert config["api_key"] is None
    assert config["timeout"] == 30.0
    assert config["use_cache"] is True
    assert config["cache_ttl"] == 1800
