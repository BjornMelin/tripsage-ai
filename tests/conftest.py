"""Root test configuration for TripSage test suite.

This module provides shared fixtures and configuration for all tests.
Updated for Pydantic v2 and modern pytest patterns (2025).
"""

import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import SecretStr

# Configure pytest-asyncio - updated for pytest-asyncio 1.0
# No longer need event_loop fixture with pytest-asyncio 1.0


# Global mock for cache service to prevent Redis connection errors in tests
@pytest.fixture(scope="session", autouse=True)
def mock_cache_globally():
    """Mock cache service globally to prevent Redis connection issues."""
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock(return_value=True)
    mock_cache.delete = AsyncMock(return_value=True)
    mock_cache.exists = AsyncMock(return_value=False)
    mock_cache.connect = AsyncMock()
    mock_cache.disconnect = AsyncMock()
    mock_cache.ping = AsyncMock(return_value=True)
    mock_cache.health_check = AsyncMock(return_value=True)
    mock_cache.is_connected = True
    mock_cache._connected = True

    # Patch the service getter AND the CacheService class itself
    with (
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            return_value=mock_cache,
        ),
        patch(
            "tripsage_core.services.infrastructure.cache_service.CacheService",
            return_value=mock_cache,
        ),
    ):
        yield mock_cache


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    test_env = {
        "ENVIRONMENT": "testing",
        "DEBUG": "True",
        "DATABASE_URL": "https://test.supabase.com",
        "DATABASE_PUBLIC_KEY": "test-public-key",
        "DATABASE_SERVICE_KEY": "test-service-key",
        "DATABASE_JWT_SECRET": "test-jwt-secret-for-testing-only",
        "SECRET_KEY": "test-application-secret-key-for-testing-only",
        "REDIS_URL": "redis://localhost:6379/1",
        "REDIS_PASSWORD": "test-password",
        "OPENAI_API_KEY": "sk-test-1234567890",
        "WEATHER_API_KEY": "test-weather-key",
        "GOOGLE_MAPS_API_KEY": "test-maps-key",
        "DUFFEL_API_KEY": "test-duffel-key",
    }

    # Save original environment
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    from tripsage_core.config import Settings

    settings = MagicMock(spec=Settings)
    settings.environment = "testing"
    settings.debug = True
    settings.database_url = "https://test.supabase.com"
    settings.database_public_key = SecretStr("test-public-key")
    settings.database_service_key = SecretStr("test-service-key")
    settings.database_jwt_secret = SecretStr("test-jwt-secret-for-testing-only")
    settings.secret_key = SecretStr("test-application-secret-key-for-testing-only")
    settings.redis_url = "redis://localhost:6379/1"
    settings.redis_password = "test-password"
    settings.redis_max_connections = 50
    settings.openai_api_key = SecretStr("sk-test-1234567890")
    settings.openai_model = "gpt-4"
    settings.weather_api_key = SecretStr("test-weather-key")
    settings.google_maps_api_key = SecretStr("test-maps-key")
    settings.duffel_api_key = SecretStr("test-duffel-key")
    settings.rate_limit_requests = 100
    settings.rate_limit_window = 60

    # Add commonly used methods
    settings.validate_critical_settings = MagicMock()

    return settings


@pytest.fixture
def mock_database_service():
    """Create mock database service."""
    db_service = AsyncMock()

    # Common database operations
    db_service.fetch_one = AsyncMock(return_value=None)
    db_service.fetch_all = AsyncMock(return_value=[])
    db_service.execute = AsyncMock(return_value=None)
    db_service.execute_many = AsyncMock(return_value=None)

    # Transaction support
    db_service.begin = AsyncMock()
    db_service.commit = AsyncMock()
    db_service.rollback = AsyncMock()

    return db_service


@pytest.fixture
def mock_cache_service():
    """Create mock cache service."""
    cache_service = AsyncMock()

    # Common cache operations
    cache_service.get = AsyncMock(return_value=None)
    cache_service.set = AsyncMock(return_value=True)
    cache_service.delete = AsyncMock(return_value=True)
    cache_service.exists = AsyncMock(return_value=False)
    cache_service.expire = AsyncMock(return_value=True)
    cache_service.ttl = AsyncMock(return_value=-1)

    # Connection state
    cache_service.is_connected = True
    cache_service.connect = AsyncMock()
    cache_service.disconnect = AsyncMock()

    return cache_service


@pytest.fixture
def sample_user_id() -> str:
    """Generate a sample user ID."""
    return str(uuid4())


@pytest.fixture
def sample_trip_id() -> str:
    """Generate a sample trip ID."""
    return str(uuid4())


@pytest.fixture
def sample_timestamp() -> datetime:
    """Generate a sample timestamp."""
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_user_data(sample_user_id: str) -> dict[str, Any]:
    """Create sample user data."""
    return {
        "id": sample_user_id,
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "is_active": True,
        "is_verified": True,
    }


@pytest.fixture
def sample_trip_data(sample_trip_id: str, sample_user_id: str) -> dict[str, Any]:
    """Create sample trip data."""
    return {
        "id": sample_trip_id,
        "user_id": sample_user_id,
        "name": "Test Trip to Paris",
        "description": "A wonderful trip to the City of Light",
        "start_date": "2025-07-01",
        "end_date": "2025-07-10",
        "destination": "Paris, France",
        "status": "planning",
        "budget": 5000.00,
        "currency": "USD",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest_asyncio.fixture
async def mock_supabase_client():
    """Create mock Supabase client."""
    client = AsyncMock()

    # Table operations
    table_mock = AsyncMock()
    table_mock.select = AsyncMock(return_value=table_mock)
    table_mock.insert = AsyncMock(return_value=table_mock)
    table_mock.update = AsyncMock(return_value=table_mock)
    table_mock.delete = AsyncMock(return_value=table_mock)
    table_mock.eq = AsyncMock(return_value=table_mock)
    table_mock.neq = AsyncMock(return_value=table_mock)
    table_mock.gt = AsyncMock(return_value=table_mock)
    table_mock.gte = AsyncMock(return_value=table_mock)
    table_mock.lt = AsyncMock(return_value=table_mock)
    table_mock.lte = AsyncMock(return_value=table_mock)
    table_mock.like = AsyncMock(return_value=table_mock)
    table_mock.ilike = AsyncMock(return_value=table_mock)
    table_mock.is_ = AsyncMock(return_value=table_mock)
    table_mock.in_ = AsyncMock(return_value=table_mock)
    table_mock.order = AsyncMock(return_value=table_mock)
    table_mock.limit = AsyncMock(return_value=table_mock)
    table_mock.single = AsyncMock(return_value=table_mock)
    table_mock.execute = AsyncMock(return_value=Mock(data=[], count=0))

    client.table = AsyncMock(return_value=table_mock)

    # Auth operations
    auth_mock = AsyncMock()
    auth_mock.sign_up = AsyncMock()
    auth_mock.sign_in_with_password = AsyncMock()
    auth_mock.sign_out = AsyncMock()
    auth_mock.get_user = AsyncMock()
    auth_mock.update_user = AsyncMock()

    client.auth = auth_mock

    # Storage operations
    storage_mock = AsyncMock()
    bucket_mock = AsyncMock()
    bucket_mock.upload = AsyncMock()
    bucket_mock.download = AsyncMock()
    bucket_mock.remove = AsyncMock()
    bucket_mock.list = AsyncMock(return_value=[])
    bucket_mock.get_public_url = Mock(
        return_value="https://test.supabase.com/storage/v1/object/public/test/file.jpg"
    )

    storage_mock.from_ = Mock(return_value=bucket_mock)
    client.storage = storage_mock

    return client


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client."""
    client = AsyncMock()

    # Chat completions
    chat_mock = AsyncMock()
    completions_mock = AsyncMock()

    # Create a mock response
    response_mock = Mock()
    response_mock.choices = [
        Mock(message=Mock(content="Test AI response"), finish_reason="stop")
    ]
    response_mock.usage = Mock(prompt_tokens=10, completion_tokens=20, total_tokens=30)

    completions_mock.create = AsyncMock(return_value=response_mock)
    chat_mock.completions = completions_mock
    client.chat = chat_mock

    # Embeddings
    embeddings_mock = AsyncMock()
    embedding_response = Mock()
    embedding_response.data = [Mock(embedding=[0.1] * 1536)]
    embeddings_mock.create = AsyncMock(return_value=embedding_response)
    client.embeddings = embeddings_mock

    return client


@pytest.fixture
def mock_service_registry():
    """Create mock service registry."""
    from tripsage.agents.service_registry import ServiceRegistry

    registry = ServiceRegistry()

    # Add commonly used services
    registry.register("database", AsyncMock())
    registry.register("cache", AsyncMock())
    registry.register("openai", AsyncMock())
    registry.register("memory", AsyncMock())
    registry.register("websocket", AsyncMock())

    return registry


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "external: Tests requiring external services")
    config.addinivalue_line("markers", "asyncio: Async tests")


# Skip slow tests by default
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on markers."""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="run slow tests"
    )
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="run tests requiring external services",
    )
