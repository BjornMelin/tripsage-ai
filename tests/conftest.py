"""
Global test configuration and fixtures.

This module provides centralized test configuration, fixtures, and setup
for the entire TripSage test suite with proper async support and mocking.
"""

import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Load test environment variables FIRST - before any other imports
from dotenv import load_dotenv

# Load test environment immediately
load_dotenv(".env.test", override=True)


# Set up test environment variables before any TripSage imports
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
        "DRAGONFLY_URL": "redis://localhost:6379/1",
        "DRAGONFLY_PASSWORD": "test_dragonfly_password",
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


# Set up test environment immediately
setup_test_environment()

# Now safe to import pydantic and TripSage modules
from pydantic import BaseModel

from tripsage_core.models.schemas_common.enums import (
    AccommodationType,
    BookingStatus,
    CancellationPolicy,
)

# Add the project root directory to the path so tests can import modules directly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def mock_problematic_imports():
    """Mock problematic imports that might cause test failures."""
    import importlib.util

    # Check and mock langchain modules
    if importlib.util.find_spec("langchain_core") is None:
        sys.modules["langchain_core"] = MagicMock()
        sys.modules["langchain_core.language_models"] = MagicMock()
        sys.modules["langchain_core.language_models.chat_models"] = MagicMock()

    if importlib.util.find_spec("langchain_openai") is None:
        sys.modules["langchain_openai"] = MagicMock()
        sys.modules["langchain_openai.chat_models"] = MagicMock()
        # Mock ChatOpenAI class
        mock_chat_openai = MagicMock()
        mock_chat_openai.return_value = AsyncMock()
        sys.modules["langchain_openai"].ChatOpenAI = mock_chat_openai

    if importlib.util.find_spec("langgraph") is None:
        sys.modules["langgraph"] = MagicMock()
        sys.modules["langgraph.graph"] = MagicMock()
        sys.modules["langgraph.checkpoint"] = MagicMock()

    if importlib.util.find_spec("mem0ai") is None:
        sys.modules["mem0ai"] = MagicMock()
        sys.modules["mem0"] = MagicMock()


# Mock problematic imports immediately
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
    # Import the mock cache service
    from tests.test_cache_mock import MockCacheService, mock_get_cache_service

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
    mock_settings.database_url = (
        "postgresql://postgres:password@localhost:5432/postgres"
    )
    mock_settings.database_password = "password"

    # Mock memory service (Mem0)
    mock_settings.memory.service_type = "mem0"
    mock_settings.memory.api_key = "test_mem0_key"

    # Mock cache settings
    mock_settings.enable_caching = False  # Disable caching for tests
    mock_settings.dragonfly = MagicMock()
    mock_settings.dragonfly.url = "redis://localhost:6379/1"
    mock_settings.dragonfly.password = "test_password"
    mock_settings.dragonfly.max_connections = 10
    mock_settings.dragonfly.ttl_short = 300
    mock_settings.dragonfly.ttl_medium = 3600
    mock_settings.dragonfly.ttl_long = 86400

    # Mock Airbnb MCP settings
    mock_settings.airbnb = MagicMock()
    mock_settings.airbnb.enabled = False  # Disable Airbnb for tests
    mock_settings.airbnb.url = "http://localhost:3012"
    mock_settings.airbnb.timeout = 30
    mock_settings.airbnb.retry_attempts = 3
    mock_settings.airbnb.retry_backoff = 5

    # Mock Redis client
    mock_redis_client = MagicMock()
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock(return_value=True)
    mock_redis_client.delete = AsyncMock(return_value=1)
    mock_redis_client.scan_iter = AsyncMock(return_value=[])
    mock_redis_client.incr = AsyncMock(return_value=1)
    mock_redis_client.expire = AsyncMock(return_value=True)

    mock_from_url = MagicMock(return_value=mock_redis_client)

    # Create mock cache service instance
    mock_cache_instance = MockCacheService()

    # Create mock database service
    mock_db_service = MagicMock()
    mock_db_service.get_session = AsyncMock()
    mock_db_service.execute = AsyncMock()
    mock_db_service.fetch_one = AsyncMock()
    mock_db_service.fetch_all = AsyncMock()
    mock_db_service.save = AsyncMock()
    mock_db_service.delete = AsyncMock()
    mock_db_service.update = AsyncMock()
    mock_db_service.create = AsyncMock()
    mock_db_service.get_user_by_email = AsyncMock(return_value=None)
    mock_db_service.get_user = AsyncMock(return_value=None)

    async def mock_get_database_service():
        """Mock get_database_service function."""
        return mock_db_service

    # Apply all the patches we need
    with (
        patch(
            "tripsage_core.config.base_app_settings.get_settings",
            return_value=mock_settings,
        ),
        patch("tripsage_core.config.base_app_settings.settings", mock_settings),
        patch("redis.asyncio.from_url", mock_from_url),
        patch("redis.from_url", mock_from_url),
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            mock_get_cache_service,
        ),
        patch(
            "tripsage_core.services.infrastructure.get_cache_service",
            mock_get_cache_service,
        ),
        patch(
            "tripsage_core.utils.cache_utils.get_cache_instance", mock_get_cache_service
        ),
        patch(
            "tripsage_core.services.infrastructure.database_service.get_database_service",
            mock_get_database_service,
        ),
        patch(
            "tripsage_core.services.infrastructure.get_database_service",
            mock_get_database_service,
        ),
    ):
        yield {
            "settings": mock_settings,
            "redis": mock_redis_client,
            "cache": mock_cache_instance,
            "database": mock_db_service,
        }


# Sample data fixtures using factories
from tests.factories import (
    AccommodationFactory,
    APIKeyFactory,
    ChatFactory,
    DestinationFactory,
    FlightFactory,
    ItineraryFactory,
    TripFactory,
    UserFactory,
    WebSocketFactory,
)


@pytest.fixture
def sample_accommodation_dict():
    """Sample accommodation data for testing."""
    return AccommodationFactory.create()


@pytest.fixture
def sample_flight_dict():
    """Sample flight data for testing."""
    return FlightFactory.create()


@pytest.fixture
def sample_trip_dict():
    """Sample trip data for testing."""
    return TripFactory.create()


@pytest.fixture
def sample_user_dict():
    """Sample user data for testing."""
    return UserFactory.create()


# Additional factory-based fixtures
@pytest.fixture
def sample_chat_message_dict():
    """Sample chat message for testing."""
    return ChatFactory.create_message()


@pytest.fixture
def sample_chat_conversation():
    """Sample chat conversation with multiple messages."""
    return ChatFactory.create_conversation()


@pytest.fixture
def sample_api_key_dict():
    """Sample API key data for testing."""
    return APIKeyFactory.create()


@pytest.fixture
def sample_destination_dict():
    """Sample destination data for testing."""
    return DestinationFactory.create()


@pytest.fixture
def sample_itinerary_dict():
    """Sample itinerary data for testing."""
    return ItineraryFactory.create()


@pytest.fixture
def sample_websocket_message():
    """Sample WebSocket message for testing."""
    return WebSocketFactory.create_chat_message()


# Import MockCacheService for the client fixture
from tests.test_cache_mock import MockCacheService


# Mock service fixtures
@pytest.fixture
def mock_database_service():
    """Mock database service with async methods."""
    mock = MagicMock()
    mock.get_session = AsyncMock()
    mock.execute = AsyncMock()
    mock.fetch_one = AsyncMock()
    mock.fetch_all = AsyncMock()
    mock.save = AsyncMock()
    mock.delete = AsyncMock()
    mock.update = AsyncMock()
    mock.create = AsyncMock()
    mock.get_user_by_email = AsyncMock(return_value=None)
    mock.get_user = AsyncMock(return_value=None)
    mock.update_user = AsyncMock(
        return_value={"id": "test-id", "email": "test@example.com"}
    )
    mock.delete_user = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_cache_service():
    """Mock cache service with async methods."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.invalidate_pattern = AsyncMock(return_value=0)
    mock.get_ttl = Mock(return_value=3600)
    return mock


@pytest.fixture
def mock_auth_service():
    """Mock authentication service."""
    mock = MagicMock()
    mock.verify_token = AsyncMock(
        return_value={"user_id": 1, "email": "test@example.com"}
    )
    mock.create_access_token = Mock(return_value="test-jwt-token")
    mock.create_refresh_token = Mock(return_value="test-refresh-token")
    mock.hash_password = Mock(return_value="hashed-password")
    mock.verify_password = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_memory_service():
    """Mock memory service (Mem0)."""
    mock = MagicMock()
    mock.add_memory = AsyncMock(return_value={"memory_id": "test-memory-id"})
    mock.get_memories = AsyncMock(return_value=[])
    mock.search_memories = AsyncMock(return_value=[])
    mock.delete_memory = AsyncMock(return_value=True)
    return mock


# Validation test helpers
class ValidationTestHelper:
    """Helper class for testing Pydantic model validation."""

    @staticmethod
    def assert_validation_error(model_class, data, field_name, error_message_part):
        """Assert that creating a model with invalid data raises ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            model_class(**data)

        errors = exc_info.value.errors()
        field_errors = [e for e in errors if e["loc"][0] == field_name]
        assert len(field_errors) > 0, (
            f"No validation error found for field '{field_name}'"
        )
        actual_msg = field_errors[0]["msg"]
        assert error_message_part in str(actual_msg), (
            f"Expected error message containing '{error_message_part}' "
            f"but got '{actual_msg}'"
        )

    @staticmethod
    def assert_field_valid(model_class, data, field_name, valid_value):
        """Assert that a field accepts a valid value."""
        test_data = data.copy()
        test_data[field_name] = valid_value
        instance = model_class(**test_data)
        assert getattr(instance, field_name) == valid_value


# Serialization test helpers
class SerializationTestHelper:
    """Helper class for testing model serialization."""

    @staticmethod
    def test_json_round_trip(model_instance):
        """Test that a model can be serialized to JSON and back."""
        json_str = model_instance.model_dump_json()
        reconstructed = model_instance.__class__.model_validate_json(json_str)
        return reconstructed

    @staticmethod
    def test_dict_round_trip(model_instance):
        """Test that a model can be converted to dict and back."""
        data_dict = model_instance.model_dump()
        reconstructed = model_instance.__class__.model_validate(data_dict)
        return reconstructed


@pytest.fixture
def validation_helper():
    """Fixture providing validation test utilities."""
    return ValidationTestHelper()


@pytest.fixture
def serialization_helper():
    """Fixture providing serialization test utilities."""
    return SerializationTestHelper()


# Performance testing fixtures
@pytest.fixture
def large_dataset():
    """Large dataset for performance testing."""
    today = date.today()
    return {
        "accommodations": [
            {
                "id": i,
                "trip_id": 1,
                "name": f"Hotel {i}",
                "accommodation_type": AccommodationType.HOTEL,
                "check_in": today + timedelta(days=i),
                "check_out": today + timedelta(days=i + 7),
                "price_per_night": 100.0 + i,
                "total_price": (100.0 + i) * 7,
                "location": f"City {i}",
                "rating": min(5.0, 3.0 + (i % 3)),
                "booking_status": BookingStatus.VIEWED,
            }
            for i in range(1000)
        ]
    }


# Edge case testing data
@pytest.fixture
def edge_case_data():
    """Edge case data for testing boundary conditions."""
    today = date.today()
    return {
        "min_price": 0.01,
        "max_price": 99999.99,
        "min_rating": 0.0,
        "max_rating": 5.0,
        "past_date": today - timedelta(days=365),
        "far_future_date": today + timedelta(days=365 * 5),
        "empty_string": "",
        "very_long_string": "x" * 1000,
        "unicode_string": "🏨🌟✈️🏝️",
    }


# Parametrized test data
@pytest.fixture
def accommodation_types():
    """All accommodation types for parametrized testing."""
    return list(AccommodationType)


@pytest.fixture
def booking_statuses():
    """All booking statuses for parametrized testing."""
    return list(BookingStatus)


@pytest.fixture
def cancellation_policies():
    """All cancellation policies for parametrized testing."""
    return list(CancellationPolicy)


# Mock external API responses
@pytest.fixture
def mock_airbnb_search_response():
    """Mock Airbnb search response."""
    return {
        "listings": [
            {
                "id": "12345",
                "name": "Beautiful Apartment in Tokyo",
                "price_per_night": 150.00,
                "rating": 4.8,
                "location": "Shibuya, Tokyo",
                "amenities": ["wifi", "kitchen", "tv"],
            }
        ],
        "count": 1,
        "has_more": False,
    }


# Database mock fixtures
@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = MagicMock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    session.execute = Mock()
    return session


# Mock Supabase client
@pytest.fixture(autouse=True)
def mock_supabase_client():
    """Mock Supabase client to avoid connection issues during tests."""
    mock_client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.insert = MagicMock(return_value=mock_table)
    mock_table.update = MagicMock(return_value=mock_table)
    mock_table.delete = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.execute = AsyncMock(return_value={"data": [], "error": None})

    # Mock auth operations
    mock_auth = MagicMock()
    mock_auth.sign_up = AsyncMock(
        return_value={"user": {"id": "test-user-id"}, "session": None}
    )
    mock_auth.sign_in_with_password = AsyncMock(
        return_value={
            "user": {"id": "test-user-id"},
            "session": {"access_token": "test-token"},
        }
    )
    mock_auth.sign_out = AsyncMock(return_value=None)
    mock_auth.get_user = AsyncMock(
        return_value={"user": {"id": "test-user-id", "email": "test@example.com"}}
    )

    mock_client.table = MagicMock(return_value=mock_table)
    mock_client.auth = mock_auth
    mock_client.from_ = MagicMock(return_value=mock_table)

    # Patch Supabase client creation
    with patch("supabase.create_client", return_value=mock_client):
        yield mock_client


# FastAPI TestClient fixture for E2E tests
@pytest.fixture
def client():
    """Create a FastAPI TestClient for E2E testing."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi.testclient import TestClient

    from tripsage.api.main import app

    # Create a mock MCP manager that matches the expected interface
    mock_mcp_manager = MagicMock()
    mock_mcp_manager.initialize_all_enabled = AsyncMock()
    mock_mcp_manager.get_available_mcps = MagicMock(return_value=[])
    mock_mcp_manager.get_initialized_mcps = MagicMock(return_value=[])
    mock_mcp_manager.shutdown = AsyncMock()

    # Mock all the services that the app tries to initialize
    with (
        # Mock authentication service and middleware
        patch(
            "tripsage_core.services.business.auth_service.get_auth_service",
            return_value=AsyncMock(),
        ),
        # Mock database service
        patch(
            "tripsage_core.services.infrastructure.database_service.get_database_service",
            return_value=AsyncMock(),
        ),
        # Mock cache service
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            return_value=MockCacheService(),
        ),
        # Mock MCP manager - patch all possible import paths
        patch("tripsage_core.mcp_abstraction.manager.mcp_manager", mock_mcp_manager),
        patch("tripsage_core.mcp_abstraction.mcp_manager", mock_mcp_manager),
        patch("tripsage.api.main.mcp_manager", mock_mcp_manager),
        # Mock memory service
        patch(
            "tripsage_core.services.business.memory_service.get_memory_service",
            return_value=AsyncMock(),
        ),
        # Mock all business services
        patch(
            "tripsage_core.services.business.chat_service.get_chat_service",
            return_value=AsyncMock(),
        ),
        patch(
            "tripsage_core.services.business.trip_service.get_trip_service",
            return_value=AsyncMock(),
        ),
        patch(
            "tripsage_core.services.business.flight_service.get_flight_service",
            return_value=AsyncMock(),
        ),
        patch(
            "tripsage_core.services.business.accommodation_service.get_accommodation_service",
            return_value=AsyncMock(),
        ),
        patch(
            "tripsage_core.services.business.destination_service.get_destination_service",
            return_value=AsyncMock(),
        ),
        patch(
            "tripsage_core.services.business.itinerary_service.get_itinerary_service",
            return_value=AsyncMock(),
        ),
        patch(
            "tripsage_core.services.business.key_management_service.get_key_management_service",
            return_value=AsyncMock(),
        ),
        # Mock authentication middleware
        patch(
            "tripsage.api.middlewares.authentication.AuthenticationMiddleware._ensure_services",
            new_callable=AsyncMock,
        ),
        # Mock WebSocket manager
        patch(
            "tripsage_core.services.infrastructure.websocket_manager.websocket_manager",
            MagicMock(start=AsyncMock(), stop=AsyncMock()),
        ),
        # Mock Supabase client initialization
        patch("supabase.create_client", return_value=MagicMock()),
    ):
        with TestClient(app) as test_client:
            yield test_client


# AsyncClient fixture for async API testing
@pytest.fixture
async def async_client():
    """Create an AsyncClient for async API testing."""
    from httpx import AsyncClient
    from unittest.mock import AsyncMock, MagicMock, patch

    from tripsage.api.main import app

    # Simple mock for basic async client functionality
    # This doesn't mock all services to avoid dependency issues
    with (
        # Mock Supabase client initialization
        patch("supabase.create_client", return_value=MagicMock()),
        # Mock cache service
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            return_value=MockCacheService(),
        ),
    ):
        # For now, create a simple AsyncClient that can be used for basic HTTP testing
        # The router tests should be simplified to not depend on the full app integration
        async with AsyncClient(base_url="http://testserver") as client:
            yield client


# Clean up after tests
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up resources after each test."""
    yield
    # Add any cleanup logic here if needed
