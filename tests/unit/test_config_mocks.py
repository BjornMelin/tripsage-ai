"""Mock configuration objects for isolated testing.

This module provides mocking of configuration objects
to enable isolated testing without external dependencies.
"""

import os
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr


class MockSettings:
    """Mock version of flat Settings for testing."""

    def __init__(self):
        """Initialize mock settings with testing defaults."""
        # Environment & Core (flat structure)
        self.environment = "testing"
        self.debug = True
        self.log_level = "INFO"

        # API Configuration (flat structure)
        self.api_title = "TripSage API"
        self.api_version = "1.0.0"
        self.cors_origins = ["http://localhost:3000", "http://localhost:3001"]
        self.cors_credentials = True

        # Database (flat structure)
        self.database_url = "https://test-project.supabase.co"
        self.database_public_key = SecretStr("test-anon-key")
        self.database_service_key = SecretStr("test-service-key")
        self.database_jwt_secret = SecretStr("test-jwt-secret")

        # Application Security (flat structure)
        self.secret_key = SecretStr("test-secret-key")

        # Redis/Cache (flat structure)
        self.redis_url = None  # Optional in test
        self.redis_password = None
        self.redis_max_connections = 50

        # AI Services (flat structure)
        self.openai_api_key = SecretStr("sk-test-openai-key-1234567890abcdef")
        self.openai_model = "gpt-5"

        # Rate Limiting (flat structure)
        self.rate_limit_requests = 100
        self.rate_limit_window = 60

    @property
    def is_production(self) -> bool:
        """Return True when environment is production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Return True when environment is development."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Return True when environment denotes testing."""
        return self.environment in ("test", "testing")


# Legacy mock configuration classes removed - no longer needed with flat Settings
# structure. The flat Settings structure handles all configuration directly.


@pytest.fixture
def mock_settings():
    """Fixture providing mock settings for tests."""
    return MockSettings()


def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        "TRIPSAGE_TEST_MODE": "true",
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        # Database
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
        # Cache
        "REDIS_URL": "redis://localhost:6379/1",
        # API Keys (safe test values)
        "OPENAI_API_KEY": "sk-test-openai-key-1234567890abcdef",
        "GOOGLE_MAPS_API_KEY": "test-google-maps-key",
        "DUFFEL_API_KEY": "test-duffel-api-key",
        "OPENWEATHERMAP_API_KEY": "test-weather-api-key",
        # Security
        "JWT_SECRET_KEY": "test-jwt-secret-key",
        "API_KEY_MASTER_SECRET": "test-master-secret",
        # Services
        "CRAWL4AI_API_URL": "http://localhost:8000/api",
        "CRAWL4AI_API_KEY": "test-crawl4ai-key",
        # Feature flags
        "ENABLE_STREAMING_RESPONSES": "false",
        "ENABLE_RATE_LIMITING": "false",
        "ENABLE_CACHING": "false",
        "ENABLE_DEBUG_MODE": "true",
        "ENABLE_TRACING": "false",
    }

    for key, value in test_env.items():
        os.environ[key] = value


@pytest.fixture(autouse=True)
def setup_test_env():
    """Automatically set up test environment for all tests."""
    setup_test_environment()
    yield
    # Cleanup is handled by test isolation


class MockMCPBridge:
    """Mock MCP Manager for testing."""

    def __init__(self):
        """Initialize a mock MCP manager with async fakes."""
        self.invoke = AsyncMock()
        self.is_connected = AsyncMock(return_value=True)
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()

    async def invoke(self, method_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Mock MCP invoke method."""
        # Return different mock responses based on method name
        if "search_flights" in method_name:
            return {
                "flights": [
                    {"id": "flight_123", "price": 299.99, "airline": "Test Airways"}
                ]
            }
        elif "search_accommodations" in method_name:
            return {
                "accommodations": [
                    {"id": "hotel_123", "price_per_night": 150.0, "name": "Test Hotel"}
                ]
            }
        elif "weather" in method_name:
            return {"temperature": 75, "condition": "sunny"}
        else:
            return {"status": "success", "result": "mock_result"}


@pytest.fixture
def mock_mcp_manager():
    """Fixture providing mock MCP manager."""
    return MockMCPBridge()


def mock_pydantic_settings():
    """Mock Pydantic settings to avoid validation errors."""

    def mock_init(self, **kwargs):
        # Set all attributes from mock configurations
        mock_settings = MockSettings()
        for key, value in mock_settings.__dict__.items():
            setattr(self, key, value)

    return mock_init


# Test configuration validation
def test_mock_settings_validation():
    """Test that mock settings are valid."""
    settings = MockSettings()

    # Basic validation (flat structure)
    assert settings.api_title == "TripSage API"
    assert settings.environment == "testing"
    assert settings.is_testing is True
    assert settings.is_production is False

    # API keys validation (flat structure)
    assert settings.openai_api_key.get_secret_value() is not None
    assert settings.database_jwt_secret.get_secret_value() is not None

    # Config validation (flat structure)
    assert settings.database_url is not None
    assert settings.redis_url is None  # Optional in test config
