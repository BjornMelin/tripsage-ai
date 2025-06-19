"""
Clean test configuration module for TripSage.

This module provides a simplified, robust test configuration approach that:
1. Uses environment variables exclusively for configuration
2. Avoids module-level imports of settings
3. Provides clear, simple mocking patterns
4. Works properly with Pydantic v2
5. Eliminates validation errors during test setup
"""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.config import Settings


def setup_test_environment() -> None:
    """Set up comprehensive test environment variables."""
    test_env = {
        # Core application settings
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "LOG_LEVEL": "INFO",
        # Database configuration (flat structure)
        "DATABASE_URL": "https://test-project.supabase.co",
        "DATABASE_PUBLIC_KEY": "test-anon-key-1234567890abcdef",
        "DATABASE_SERVICE_KEY": "test-service-role-key-1234567890abcdef",
        "DATABASE_JWT_SECRET": "test-jwt-secret-1234567890abcdef",
        # Application security
        "SECRET_KEY": "test-secret-key-1234567890abcdef",
        # Cache configuration (flat structure)
        "REDIS_URL": "redis://localhost:6379/1",
        "REDIS_PASSWORD": "tripsage_secure_password",
        "REDIS_MAX_CONNECTIONS": "50",
        # AI services (flat structure)
        "OPENAI_API_KEY": "sk-test-openai-key-1234567890abcdef",
        "OPENAI_MODEL": "gpt-4o",
        # Rate limiting (flat structure)
        "RATE_LIMIT_REQUESTS": "100",
        "RATE_LIMIT_WINDOW": "60",
    }

    # Apply all environment variables
    for key, value in test_env.items():
        os.environ[key] = value


def create_test_settings(**overrides) -> Settings:
    """
    Create a test settings instance with proper defaults.

    Args:
        **overrides: Optional overrides for specific settings

    Returns:
        Settings instance configured for testing
    """
    # Ensure test environment is set up
    setup_test_environment()

    # Clear any cached settings
    from tripsage_core.config import get_settings

    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()

    # Apply any overrides to environment variables
    for key, value in overrides.items():
        env_key = key.upper()
        if isinstance(value, (str, int, float, bool)):
            os.environ[env_key] = str(value)

    # Create settings instance - Pydantic v2 reads from environment variables
    # Don't pass any config to the constructor
    return Settings()


class MockCacheService:
    """Simple, reliable mock cache service for tests."""

    def __init__(self):
        self._storage: dict[str, Any] = {}
        self._connected = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def ensure_connected(self) -> None:
        pass

    async def get_json(self, key: str) -> Any:
        return self._storage.get(key)

    async def set_json(self, key: str, value: Any, ttl: int = None) -> bool:
        self._storage[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._storage:
                del self._storage[key]
                count += 1
        return count

    async def health_check(self) -> bool:
        return True


class MockDatabaseService:
    """Simple, reliable mock database service for tests."""

    def __init__(self):
        self._connected = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def get_session(self):
        return MagicMock()

    async def execute(self, query: str, params: dict = None):
        return MagicMock()

    async def fetch_one(self, query: str, params: dict = None):
        return None

    async def fetch_all(self, query: str, params: dict = None):
        return []

    async def health_check(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def clean_test_environment():
    """Automatically set up clean test environment for each test."""
    # Set up test environment
    setup_test_environment()

    # Mock all external dependencies
    mock_cache = MockCacheService()
    mock_db = MockDatabaseService()

    with (
        # Mock settings functions to avoid import-time instantiation
        patch(
            "tripsage_core.config.get_settings",
            side_effect=lambda: create_test_settings(),
        ),
        # Mock cache service
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            return_value=mock_cache,
        ),
        # Mock database service
        patch(
            "tripsage_core.services.infrastructure.database_service.get_database_service",
            return_value=mock_db,
        ),
        # Mock Redis clients
        patch("redis.asyncio.from_url", return_value=AsyncMock()),
        patch("redis.from_url", return_value=MagicMock()),
        # Mock Supabase client
        patch("supabase.create_client", return_value=MagicMock()),
    ):
        yield {
            "cache": mock_cache,
            "database": mock_db,
        }


@pytest.fixture
def test_settings():
    """Provide test settings instance."""
    return create_test_settings()


@pytest.fixture
def mock_cache_service():
    """Provide mock cache service."""
    return MockCacheService()


@pytest.fixture
def mock_database_service():
    """Provide mock database service."""
    return MockDatabaseService()


def create_mock_api_settings(**overrides) -> Any:
    """
    Create mock API settings for tests that need API configuration.

    Args:
        **overrides: Optional overrides for specific settings

    Returns:
        Mock API settings object
    """
    defaults = {
        "api_prefix": "/api/v1",
        "api_title": "TripSage API",
        "api_version": "1.0.0",
        "cors_origins": ["http://localhost:3000"],
        "cors_allow_credentials": True,
        "cors_allow_methods": ["GET", "POST", "PUT", "DELETE"],
        "cors_allow_headers": ["*"],
        "rate_limit_enabled": False,  # Disabled for tests
        "rate_limit_requests": 100,
        "enable_byok": True,
        "byok_services": ["openai", "google_maps", "duffel"],
        "byok_encryption_enabled": True,
        "websocket_max_connections": 1000,
        "websocket_heartbeat_interval": 30,
        "request_timeout": 30,
        "max_file_size": 52428800,
        "allowed_file_types": ["image/jpeg", "image/png", "application/pdf"],
    }
    defaults.update(overrides)

    # Create a mock object with all the attributes
    mock_settings = MagicMock()
    for key, value in defaults.items():
        setattr(mock_settings, key, value)

    # Add utility methods
    mock_settings.get_cors_config.return_value = {
        "allow_origins": defaults["cors_origins"],
        "allow_credentials": defaults["cors_allow_credentials"],
        "allow_methods": defaults["cors_allow_methods"],
        "allow_headers": defaults["cors_allow_headers"],
    }

    mock_settings.is_byok_service_enabled.side_effect = lambda service: (
        defaults["enable_byok"] and service in defaults["byok_services"]
    )

    mock_settings.get_rate_limit_for_endpoint.side_effect = (
        lambda endpoint_type="general": (
            0 if not defaults["rate_limit_enabled"] else defaults["rate_limit_requests"]
        )
    )

    return mock_settings


@pytest.fixture
def mock_api_settings():
    """Provide mock API settings."""
    return create_mock_api_settings()


# Export convenience functions
__all__ = [
    "setup_test_environment",
    "create_test_settings",
    "create_mock_api_settings",
    "MockCacheService",
    "MockDatabaseService",
    "clean_test_environment",
    "test_settings",
    "mock_cache_service",
    "mock_database_service",
    "mock_api_settings",
]
