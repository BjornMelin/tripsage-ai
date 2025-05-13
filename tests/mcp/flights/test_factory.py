"""
Tests for the Flights MCP Client Factory.

This module contains unit tests for the Flights MCP Client Factory implementation,
testing configuration validation, client creation, and instance management.
"""

import sys
import pytest
from unittest.mock import patch, MagicMock

# Create mocks
mock_redis_cache = MagicMock()
mock_redis_cache.get = MagicMock(return_value=None)
mock_redis_cache.set = MagicMock(return_value=None)
mock_redis_cache.cached = MagicMock(side_effect=lambda name, ttl=None: lambda f: f)

# Mock all required modules and classes
sys.modules["src.cache.redis_cache"] = MagicMock()
sys.modules["src.cache.redis_cache"].redis_cache = mock_redis_cache
sys.modules["src.cache.redis_cache"].RedisCache = MagicMock(return_value=mock_redis_cache)
sys.modules["src.cache.redis_cache"].get_cache = MagicMock(return_value=mock_redis_cache)

# Mock settings module
mock_settings = MagicMock()
mock_api_key = MagicMock()
mock_api_key.get_secret_value.return_value = "mocked-duffel-api-key"
mock_settings.flights_mcp = MagicMock(
    endpoint="http://mocked-flights-server.example.com",
    api_key=mock_api_key,
    timeout=60.0,
)

# Add settings to sys.modules
sys.modules["src.utils.settings"] = MagicMock()
sys.modules["src.utils.settings"].settings = mock_settings

# Now import the modules that depend on these mocks
from src.mcp.flights.factory import FlightsMCPClientFactory, FlightsMCPConfig


# Mock FastMCPClient for clean testing
mock_client = MagicMock()
sys.modules["src.mcp.fastmcp"] = MagicMock()
sys.modules["src.mcp.fastmcp"].FastMCPClient = MagicMock
sys.modules["src.mcp.base_mcp_client"] = MagicMock()
sys.modules["src.mcp.base_mcp_client"].BaseMCPClient = MagicMock


# Create a simple mock for FlightsMCPClient
class MockFlightsMCPClient:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def flights_factory():
    """Create a Flights MCP Client Factory for testing."""
    # Set up the mock client class
    FlightsMCPClientFactory.client_class = MockFlightsMCPClient
    
    factory = FlightsMCPClientFactory()
    # Mock the _load_config_from_settings method to return test values
    factory._load_config_from_settings = MagicMock(return_value={
        "endpoint": "http://test-flights-mcp.example.com",
        "api_key": "test-duffel-api-key",
        "timeout": 60.0,
        "use_cache": True,
        "cache_ttl": 1800,
    })
    return factory


def test_flights_config_validation():
    """Test the Flights MCP configuration validation."""
    # Test valid configuration
    config = FlightsMCPConfig(
        endpoint="http://flights-mcp.example.com",
        api_key="test-duffel-api-key",
        timeout=60.0,
        use_cache=True,
        cache_ttl=1800,
    )
    assert config.endpoint == "http://flights-mcp.example.com"
    assert config.api_key == "test-duffel-api-key"
    assert config.timeout == 60.0
    assert config.use_cache is True
    assert config.cache_ttl == 1800
    
    # Test endpoint protocol correction
    config = FlightsMCPConfig(
        endpoint="flights-mcp.example.com",
        api_key="test-duffel-api-key",
    )
    assert config.endpoint == "https://flights-mcp.example.com"
    
    # Test validation error for timeout range - flights have a higher minimum
    with pytest.raises(ValueError):
        FlightsMCPConfig(
            endpoint="http://flights-mcp.example.com",
            timeout=4.0,  # Too small for flights (min 5.0)
        )
    
    # Valid timeout at minimum boundary
    config = FlightsMCPConfig(
        endpoint="http://flights-mcp.example.com",
        timeout=5.0,  # Minimum acceptable
    )
    assert config.timeout == 5.0


def test_create_client(flights_factory):
    """Test creating a new Flights MCP Client instance."""
    # Create a client with default configuration
    client = flights_factory.create_client()
    assert isinstance(client, FlightsMCPClient)
    assert client.endpoint == "http://test-flights-mcp.example.com"
    assert client.api_key == "test-duffel-api-key"
    assert client.timeout == 60.0
    assert client.use_cache is True
    assert client.cache_ttl == 1800
    assert client.server_name == "Flights"
    
    # Create a client with overridden configuration
    client = flights_factory.create_client(
        endpoint="http://override.example.com",
        timeout=90.0,
    )
    assert client.endpoint == "http://override.example.com"
    assert client.timeout == 90.0
    # Other values should remain unchanged
    assert client.api_key == "test-duffel-api-key"
    assert client.use_cache is True
    assert client.cache_ttl == 1800


@patch("src.mcp.flights.factory.settings")
def test_load_config_from_settings(mock_settings):
    """Test loading configuration from application settings."""
    # Setup mock API key with get_secret_value method
    mock_api_key = MagicMock()
    mock_api_key.get_secret_value.return_value = "secret-duffel-api-key"
    
    # Create mock settings with flights_mcp configuration
    mock_flights_mcp = MagicMock()
    mock_flights_mcp.endpoint = "http://settings-flights-mcp.example.com"
    mock_flights_mcp.api_key = mock_api_key
    mock_flights_mcp.timeout = 90.0
    mock_settings.flights_mcp = mock_flights_mcp
    
    # Create factory with real _load_config_from_settings method
    factory = FlightsMCPClientFactory()
    
    # Load config from settings
    config = factory._load_config_from_settings()
    
    # Verify config values
    assert config["endpoint"] == "http://settings-flights-mcp.example.com"
    assert config["api_key"] == "secret-duffel-api-key"
    assert config["timeout"] == 90.0
    
    # Test with string API key instead of SecretStr
    mock_flights_mcp.api_key = "plain-text-api-key"
    config = factory._load_config_from_settings()
    assert config["api_key"] == "plain-text-api-key"
    
    # Test with missing settings
    delattr(mock_settings, "flights_mcp")
    config = factory._load_config_from_settings()
    
    # Should use default values
    assert config["endpoint"] == "http://localhost:3000"
    assert config["api_key"] is None
    assert config["timeout"] == 30.0
    assert config["use_cache"] is True
    assert config["cache_ttl"] == 1800