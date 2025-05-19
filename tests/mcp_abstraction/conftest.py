"""Configuration for MCP abstraction tests."""

# Import test initialization before any tripsage imports

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_mcp_manager():
    """Create a mock MCPManager for testing."""
    manager = MagicMock()
    manager.invoke = AsyncMock()
    manager.initialize = AsyncMock()
    manager.shutdown = AsyncMock()
    yield manager


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client for all tests."""
    mock_redis_client = MagicMock()

    # Create a mock for redis.from_url
    mock_from_url = MagicMock(return_value=mock_redis_client)

    # Patch both redis and redis.asyncio
    with patch("redis.from_url", mock_from_url):
        with patch("redis.asyncio.from_url", mock_from_url):
            yield mock_redis_client


@pytest.fixture(autouse=True)
def mock_general_settings():
    """Mock general settings for all tests."""
    with patch("tripsage.utils.settings.settings") as mock_general_settings:
        mock_general_settings.redis = MagicMock()
        mock_general_settings.redis.url = "redis://localhost:6379/0"
        yield mock_general_settings


@pytest.fixture(autouse=True)
def mock_mcp_settings():
    """Mock MCP settings for all tests."""
    with patch("tripsage.config.mcp_settings.mcp_settings") as mock_settings:
        # Create mock for supabase config
        mock_settings.supabase = MagicMock()
        mock_settings.supabase.enabled = True
        mock_settings.supabase.host = "localhost"
        mock_settings.supabase.port = 5432
        mock_settings.supabase.username = "postgres"
        mock_settings.supabase.password = MagicMock()
        mock_settings.supabase.password.get_secret_value.return_value = "password"
        mock_settings.supabase.database = "postgres"
        mock_settings.supabase.project_ref = "test"
        mock_settings.supabase.anon_key = MagicMock()
        mock_settings.supabase.anon_key.get_secret_value.return_value = "anon_key"
        mock_settings.supabase.service_key = MagicMock()
        mock_settings.supabase.service_key.get_secret_value.return_value = "service_key"

        # Create mock for neo4j_memory config
        mock_settings.neo4j_memory = MagicMock()
        mock_settings.neo4j_memory.enabled = True
        mock_settings.neo4j_memory.scheme = "bolt"
        mock_settings.neo4j_memory.host = "localhost"
        mock_settings.neo4j_memory.port = 7687
        mock_settings.neo4j_memory.username = "neo4j"
        mock_settings.neo4j_memory.password = MagicMock()
        mock_settings.neo4j_memory.password.get_secret_value.return_value = "password"

        # Create mock for duffel_flights config
        mock_settings.duffel_flights = MagicMock()
        mock_settings.duffel_flights.enabled = True
        mock_settings.duffel_flights.url = "https://api.duffel.com"
        mock_settings.duffel_flights.api_key = MagicMock()
        duffel_key = mock_settings.duffel_flights.api_key.get_secret_value
        duffel_key.return_value = "duffel_key"
        mock_settings.duffel_flights.timeout = 30
        mock_settings.duffel_flights.retry_attempts = 3
        mock_settings.duffel_flights.retry_backoff = 5

        # Create mock for airbnb config
        mock_settings.airbnb = MagicMock()
        mock_settings.airbnb.enabled = True
        mock_settings.airbnb.url = "https://api.airbnb.com"
        mock_settings.airbnb.timeout = 30
        mock_settings.airbnb.retry_attempts = 3
        mock_settings.airbnb.retry_backoff = 5

        yield mock_settings
