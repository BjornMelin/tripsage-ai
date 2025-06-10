"""
Simplified, reliable test configuration for TripSage.

This conftest provides a clean, minimal test setup that:
1. Uses environment variables exclusively
2. Avoids import-time configuration instantiation  
3. Provides simple, effective mocking
4. Works seamlessly with Pydantic v2
5. Eliminates validation errors
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our clean test configuration
from tests.test_config import (
    MockCacheService,
    MockDatabaseService, 
    clean_test_environment,
    create_mock_api_settings,
    create_test_settings,
    setup_test_environment,
)

# Set up test environment immediately on import
setup_test_environment()

# Import test factories
from tests.factories import (
    AccommodationFactory,
    APIKeyFactory,
    ChatFactory,
    DestinationFactory,
    FlightFactory,
    ItineraryFactory,
    MemoryFactory,
    TripFactory,
    UserFactory,
    WebSocketFactory,
)


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture  
def mock_settings():
    """Provide clean test settings."""
    return create_test_settings()


@pytest.fixture
def mock_api_settings():
    """Provide mock API settings for API tests."""
    return create_mock_api_settings()


# Sample data fixtures using factories
@pytest.fixture
def sample_user():
    """Sample user data."""
    return UserFactory.create()


@pytest.fixture
def sample_trip():
    """Sample trip data."""
    return TripFactory.create()


@pytest.fixture
def sample_accommodation():
    """Sample accommodation data."""
    return AccommodationFactory.create()


@pytest.fixture
def sample_flight():
    """Sample flight data."""
    return FlightFactory.create()


@pytest.fixture  
def sample_chat_message():
    """Sample chat message."""
    return ChatFactory.create_message()


@pytest.fixture
def sample_api_key():
    """Sample API key data."""
    return APIKeyFactory.create()


@pytest.fixture
def sample_destination():
    """Sample destination data."""
    return DestinationFactory.create()


@pytest.fixture
def sample_itinerary():
    """Sample itinerary data."""
    return ItineraryFactory.create()


@pytest.fixture
def sample_memory():
    """Sample memory data."""
    return MemoryFactory.create_conversation_result()


@pytest.fixture
def sample_websocket_message():
    """Sample WebSocket message."""
    return WebSocketFactory.create_chat_message()


# Service mocks
@pytest.fixture
def mock_mcp_manager():
    """Mock MCP manager for testing."""
    manager = MagicMock()
    manager.invoke = AsyncMock(return_value={"success": True, "data": {}})
    manager.initialize = AsyncMock()
    manager.initialize_all_enabled = AsyncMock()
    manager.get_available_mcps = Mock(return_value=[])
    manager.get_initialized_mcps = Mock(return_value=[])
    manager.shutdown = AsyncMock()
    return manager


@pytest.fixture
def mock_memory_service():
    """Mock memory service."""
    service = MagicMock()
    service.add_memory = AsyncMock(return_value={"memory_id": "test-memory-id"})
    service.get_memories = AsyncMock(return_value=[])
    service.search_memories = AsyncMock(return_value=[])
    service.delete_memory = AsyncMock(return_value=True)
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture  
def mock_auth_service():
    """Mock authentication service."""
    service = MagicMock()
    service.verify_token = AsyncMock(return_value={"user_id": "test-user", "email": "test@example.com"})
    service.create_access_token = Mock(return_value="test-token")
    service.hash_password = Mock(return_value="hashed-password")
    service.verify_password = Mock(return_value=True)
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_chat_service():
    """Mock chat service."""
    service = MagicMock() 
    service.process_message = AsyncMock(return_value={
        "response": "Test response",
        "session_id": "test-session",
        "status": "completed"
    })
    service.get_conversation = AsyncMock(return_value=[])
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_trip_service():
    """Mock trip service."""
    service = MagicMock()
    service.create_trip = AsyncMock(return_value=TripFactory.create())
    service.get_trip = AsyncMock(return_value=TripFactory.create())
    service.list_trips = AsyncMock(return_value=[])
    service.update_trip = AsyncMock(return_value=TripFactory.create())
    service.delete_trip = AsyncMock(return_value=True)
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_flight_service():
    """Mock flight service."""
    service = MagicMock()
    service.search_flights = AsyncMock(return_value={"flights": [], "total": 0})
    service.get_flight_details = AsyncMock(return_value=FlightFactory.create())
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_accommodation_service():
    """Mock accommodation service."""
    service = MagicMock()
    service.search_accommodations = AsyncMock(return_value={"accommodations": [], "total": 0})
    service.get_accommodation_details = AsyncMock(return_value=AccommodationFactory.create())
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_destination_service():
    """Mock destination service.""" 
    service = MagicMock()
    service.search_destinations = AsyncMock(return_value={"destinations": [], "total": 0})
    service.get_destination_details = AsyncMock(return_value=DestinationFactory.create())
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_itinerary_service():
    """Mock itinerary service."""
    service = MagicMock()
    service.create_itinerary = AsyncMock(return_value=ItineraryFactory.create())
    service.get_itinerary = AsyncMock(return_value=ItineraryFactory.create())
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def mock_key_management_service():
    """Mock key management service."""
    service = MagicMock()
    service.store_api_key = AsyncMock(return_value=APIKeyFactory.create())
    service.get_api_keys = AsyncMock(return_value=[])
    service.delete_api_key = AsyncMock(return_value=True)
    service.health_check = AsyncMock(return_value=True)
    return service


# WebSocket mocks
@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    websocket = MagicMock()
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock(return_value='{"type": "heartbeat"}')
    websocket.receive_json = AsyncMock(return_value={"type": "heartbeat"})
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.send_message = AsyncMock()
    manager.broadcast = AsyncMock()
    manager.get_active_connections = Mock(return_value=[])
    manager.health_check = AsyncMock(return_value=True)
    return manager


# HTTP client mocks
@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client."""
    client = AsyncMock()
    
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "data": {}}
    mock_response.text = "mock response"
    
    client.request = AsyncMock(return_value=mock_response)
    client.get = AsyncMock(return_value=mock_response)
    client.post = AsyncMock(return_value=mock_response)
    client.put = AsyncMock(return_value=mock_response)
    client.delete = AsyncMock(return_value=mock_response)
    client.aclose = AsyncMock()
    
    return client


# Database fixtures
@pytest.fixture
def mock_database_session():
    """Mock database session."""
    session = MagicMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session


# Utility fixtures
@pytest.fixture
def mock_successful_response():
    """Mock successful API response."""
    return {
        "success": True,
        "data": {"message": "Operation successful"},
        "status_code": 200
    }


@pytest.fixture
def mock_error_response():
    """Mock error API response."""
    return {
        "success": False,
        "error": "Test error",
        "status_code": 400
    }


# Test client fixtures for FastAPI
@pytest.fixture
def test_client():
    """Create FastAPI test client with mocked dependencies."""
    from fastapi.testclient import TestClient
    
    # Import the app with all dependencies mocked
    with (
        patch("tripsage_core.config.base_app_settings.get_settings", 
              side_effect=lambda: create_test_settings()),
        patch("tripsage_core.services.infrastructure.cache_service.get_cache_service",
              return_value=MockCacheService()),
        patch("tripsage_core.services.infrastructure.database_service.get_database_service", 
              return_value=MockDatabaseService()),
        patch("supabase.create_client", return_value=MagicMock()),
    ):
        from tripsage.api.main import app
        with TestClient(app) as client:
            yield client


@pytest.fixture
async def async_test_client():
    """Create async test client."""
    from httpx import AsyncClient
    
    # For async testing, create a simple client
    # Full app integration should use the sync test_client above
    async with AsyncClient(base_url="http://testserver") as client:
        yield client


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Timer for performance testing."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
            
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0
    
    return Timer()


# Cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    # Any cleanup logic can go here