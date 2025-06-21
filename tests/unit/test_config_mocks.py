"""
Mock configuration objects for isolated testing.

This module provides comprehensive mocking of configuration objects
to enable isolated testing without external dependencies.
"""

import os
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock

import pytest
from pydantic import SecretStr


class MockSettings:
    """Mock version of flat Settings for testing."""

    def __init__(self):
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
        self.openai_model = "gpt-4o"

        # Rate Limiting (flat structure)
        self.rate_limit_requests = 100
        self.rate_limit_window = 60

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
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


class MockServiceRegistry:
    """Mock service registry for dependency injection testing."""

    def __init__(self):
        self._services = {}

    def register_service(self, name: str, service: Any):
        """Register a mock service."""
        self._services[name] = service

    def get_service(self, name: str) -> Any:
        """Get a mock service."""
        if name in self._services:
            return self._services[name]

        # Return appropriate mock based on service name
        if "accommodation" in name.lower():
            return self._create_accommodation_service_mock()
        elif "flight" in name.lower():
            return self._create_flight_service_mock()
        elif "memory" in name.lower():
            return self._create_memory_service_mock()
        elif "weather" in name.lower():
            return self._create_weather_service_mock()
        else:
            return AsyncMock()

    def get_optional_service(self, name: str) -> Optional[Any]:
        """Get an optional mock service."""
        try:
            return self.get_service(name)
        except Exception:
            return None

    def _create_accommodation_service_mock(self):
        """Create mock accommodation service."""
        service = AsyncMock()
        service.search_accommodations = AsyncMock(
            return_value={
                "accommodations": [
                    {
                        "id": "hotel_123",
                        "name": "Test Hotel",
                        "price_per_night": 150.0,
                        "rating": 4.5,
                        "location": "Test City",
                    }
                ],
                "total_count": 1,
            }
        )
        service.book_accommodation = AsyncMock(return_value={"booking_id": "booking_456", "status": "confirmed"})
        return service

    def _create_flight_service_mock(self):
        """Create mock flight service."""
        service = AsyncMock()
        service.search_flights = AsyncMock(
            return_value={
                "flights": [
                    {
                        "id": "flight_123",
                        "airline": "Test Airways",
                        "origin": "NYC",
                        "destination": "LAX",
                        "price": 299.99,
                        "duration": "5h 30m",
                    }
                ],
                "total_count": 1,
            }
        )
        return service

    def _create_memory_service_mock(self):
        """Create mock memory service."""
        service = AsyncMock()
        service.search_memories = AsyncMock(
            return_value={
                "memories": [
                    {
                        "id": "memory_123",
                        "content": "User prefers boutique hotels",
                        "relevance": 0.95,
                    }
                ]
            }
        )
        service.add_conversation_memory = AsyncMock(return_value={"memory_id": "memory_456", "status": "stored"})
        service.connect = AsyncMock()
        return service

    def _create_weather_service_mock(self):
        """Create mock weather service."""
        service = AsyncMock()
        service.get_current_weather = AsyncMock(return_value={"temperature": 75, "condition": "sunny", "humidity": 60})
        return service


@pytest.fixture
def mock_service_registry():
    """Fixture providing mock service registry."""
    return MockServiceRegistry()


class MockMCPManager:
    """Mock MCP Manager for testing."""

    def __init__(self):
        self.invoke = AsyncMock()
        self.is_connected = AsyncMock(return_value=True)
        self.connect = AsyncMock()
        self.disconnect = AsyncMock()

    async def invoke(self, method_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mock MCP invoke method."""
        # Return different mock responses based on method name
        if "search_flights" in method_name:
            return {"flights": [{"id": "flight_123", "price": 299.99, "airline": "Test Airways"}]}
        elif "search_accommodations" in method_name:
            return {"accommodations": [{"id": "hotel_123", "price_per_night": 150.0, "name": "Test Hotel"}]}
        elif "weather" in method_name:
            return {"temperature": 75, "condition": "sunny"}
        else:
            return {"status": "success", "result": "mock_result"}


@pytest.fixture
def mock_mcp_manager():
    """Fixture providing mock MCP manager."""
    return MockMCPManager()


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


def test_mock_service_registry():
    """Test mock service registry functionality."""
    registry = MockServiceRegistry()

    # Test service registration
    mock_service = AsyncMock()
    registry.register_service("test_service", mock_service)
    assert registry.get_service("test_service") == mock_service

    # Test automatic mock creation
    accommodation_service = registry.get_service("accommodation_service")
    assert accommodation_service is not None

    flight_service = registry.get_service("flight_service")
    assert flight_service is not None

    memory_service = registry.get_service("memory_service")
    assert memory_service is not None
