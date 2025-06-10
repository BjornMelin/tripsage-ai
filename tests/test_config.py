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
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from tripsage_core.config.base_app_settings import CoreAppSettings


def setup_test_environment() -> None:
    """Set up comprehensive test environment variables."""
    test_env = {
        # Core application settings
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "LOG_LEVEL": "INFO",
        
        # Database configuration (Supabase)
        "SUPABASE_URL": "https://test-project.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key-1234567890abcdef",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key-1234567890abcdef",
        "SUPABASE_JWT_SECRET": "test-jwt-secret-1234567890abcdef",
        "SUPABASE_PROJECT_ID": "test-project-id",
        
        # Cache configuration (DragonflyDB)
        "DRAGONFLY_URL": "redis://localhost:6379/1",
        "DRAGONFLY_PASSWORD": "test_dragonfly_password",
        
        # Core API Keys (safe test values)
        "OPENAI_API_KEY": "sk-test-openai-key-1234567890abcdef",
        "GOOGLE_MAPS_API_KEY": "test-google-maps-key-1234567890",
        "DUFFEL_API_KEY": "test-duffel-api-key-1234567890",
        "OPENWEATHERMAP_API_KEY": "test-weather-api-key-1234567890",
        "VISUAL_CROSSING_API_KEY": "test-visual-crossing-key-1234567890",
        
        # Security
        "API_KEY_MASTER_SECRET": "test-master-secret-for-byok-encryption",
        
        # External services
        "CRAWL4AI_API_URL": "http://localhost:8000/api",
        "CRAWL4AI_API_KEY": "test-crawl4ai-key-1234567890",
        
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


def create_test_settings(**overrides) -> CoreAppSettings:
    """
    Create a test settings instance with proper defaults.
    
    Args:
        **overrides: Optional overrides for specific settings
        
    Returns:
        CoreAppSettings instance configured for testing
    """
    # Ensure test environment is set up
    setup_test_environment()
    
    # Clear any cached settings
    from tripsage_core.config.base_app_settings import get_settings
    if hasattr(get_settings, 'cache_clear'):
        get_settings.cache_clear()
    
    # Create settings with test defaults
    defaults = {
        "environment": "testing",
        "debug": True,
        "log_level": "INFO",
    }
    defaults.update(overrides)
    
    # Create settings instance - Pydantic v2 will use environment variables automatically
    return CoreAppSettings(**defaults)


class MockCacheService:
    """Simple, reliable mock cache service for tests."""
    
    def __init__(self):
        self._storage: Dict[str, Any] = {}
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
    
    async def execute(self, query: str, params: Dict = None):
        return MagicMock()
    
    async def fetch_one(self, query: str, params: Dict = None):
        return None
    
    async def fetch_all(self, query: str, params: Dict = None):
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
        patch("tripsage_core.config.base_app_settings.get_settings", 
              side_effect=lambda: create_test_settings()),
        
        # Mock cache service
        patch("tripsage_core.services.infrastructure.cache_service.get_cache_service",
              return_value=mock_cache),
        
        # Mock database service  
        patch("tripsage_core.services.infrastructure.database_service.get_database_service",
              return_value=mock_db),
        
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
    
    mock_settings.get_rate_limit_for_endpoint.side_effect = lambda endpoint_type="general": (
        0 if not defaults["rate_limit_enabled"] else defaults["rate_limit_requests"]
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