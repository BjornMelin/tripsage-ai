"""
Common test configuration for API router tests.

This module provides a comprehensive test setup that properly mocks all services
and dependencies needed for API router testing, ensuring that validation tests
can run without interference from authentication or cache connection issues.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="function", autouse=True)
def setup_test_environment():
    """Set up test environment for API tests."""
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "ENABLE_RATE_LIMITING": "false",
        "ENABLE_CACHING": "false",
        "ENABLE_TRACING": "false",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        "DRAGONFLY_URL": "redis://localhost:6379/1",
        "DRAGONFLY_PASSWORD": "test-password",
    }

    # Apply environment variables
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_cache_service():
    """Mock cache service for tests."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=False)
    cache.ping = AsyncMock(return_value=True)
    cache.connect = AsyncMock()
    cache.disconnect = AsyncMock()
    cache._connected = True
    return cache


@pytest.fixture
def mock_database_service():
    """Mock database service for tests."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.fetch_one = AsyncMock()
    db.fetch_all = AsyncMock()
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    return db


@pytest.fixture
def api_test_client(mock_cache_service, mock_database_service, mock_principal):
    """Create FastAPI test client with all dependencies properly mocked."""
    with (
        # Mock settings
        patch("tripsage_core.config.base_app_settings.get_settings") as mock_settings,
        # Mock cache service
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            return_value=mock_cache_service,
        ),
        # Mock database service
        patch(
            "tripsage_core.services.infrastructure.database_service.get_database_service",
            return_value=mock_database_service,
        ),
        # Mock Supabase client
        patch("supabase.create_client", return_value=Mock()),
        # Mock MCP manager to prevent initialization issues
        patch(
            "tripsage_core.mcp_abstraction.manager.MCPManager.initialize_all_enabled",
            new_callable=AsyncMock,
        ),
        patch(
            "tripsage_core.mcp_abstraction.manager.MCPManager.initialize",
            new_callable=AsyncMock,
        ),
        # Mock rate limiting middleware to disable it
        patch(
            "tripsage.api.middlewares.rate_limiting.EnhancedRateLimitMiddleware.dispatch"
        ) as mock_rate_limit,
        # Mock the authentication dependency to return a valid principal
        patch(
            "tripsage.api.core.dependencies.get_current_principal",
            return_value=mock_principal,
        ),
        # Mock all service dependencies to prevent real service calls
        patch(
            "tripsage_core.services.business.accommodation_service.get_accommodation_service"
        ) as mock_acc_service,
        patch("tripsage_core.services.business.trip_service.get_trip_service"),
        patch("tripsage_core.services.business.flight_service.get_flight_service"),
        patch(
            "tripsage_core.services.business.destination_service.get_destination_service"
        ),
        patch("tripsage_core.services.business.chat_service.get_chat_service"),
        patch("tripsage_core.services.business.memory_service.get_memory_service"),
        patch(
            "tripsage_core.services.business.key_management_service.get_key_management_service"
        ),
        patch("tripsage_core.services.business.user_service.get_user_service"),
        patch(
            "tripsage_core.services.business.itinerary_service.get_itinerary_service"
        ),
        # Mock file processing service
        patch(
            "tripsage_core.services.business.file_processing_service.FileProcessingService"
        ) as mock_file_service,
    ):
        # Configure mock settings
        from tests.test_config import create_test_settings

        mock_settings.return_value = create_test_settings()

        # Configure rate limiting middleware to pass through
        async def pass_through_middleware(request, call_next):
            return await call_next(request)

        mock_rate_limit.side_effect = pass_through_middleware

        # Import app after all patches are in place
        # Configure service mocks to return mock instances
        mock_accommodation_service = AsyncMock()
        mock_acc_service.return_value = mock_accommodation_service

        # Configure default mock responses that match the expected API response schema

        from tripsage.api.schemas.accommodations import AccommodationSearchResponse

        def mock_search_accommodations(request):
            """Mock search accommodations method that returns API response format."""
            # Create a valid AccommodationSearchRequest for the response
            from datetime import date

            from tripsage.api.schemas.accommodations import (
                AccommodationSearchRequest as APISearchRequest,
            )

            # Create a mock API request with default values
            api_request = APISearchRequest(
                location="Tokyo",
                check_in=date(2024, 3, 15),
                check_out=date(2024, 3, 18),
                adults=2,
            )

            return AccommodationSearchResponse(
                listings=[],
                count=0,
                currency="USD",
                search_id="mock-search-id",
                search_request=api_request,
            )

        mock_accommodation_service.search_accommodations = AsyncMock(
            side_effect=mock_search_accommodations
        )

        mock_accommodation_service.get_accommodation_details = AsyncMock(
            return_value={
                "listing": {
                    "id": "test-listing",
                    "name": "Test Accommodation",
                    "property_type": "apartment",
                    "location": {
                        "city": "Test City",
                        "country": "Test Country",
                        "latitude": 0.0,
                        "longitude": 0.0,
                    },
                    "price_per_night": 100.0,
                    "currency": "USD",
                    "amenities": [],
                    "images": [],
                    "max_guests": 2,
                    "bedrooms": 1,
                    "beds": 1,
                    "bathrooms": 1.0,
                },
                "availability": True,
            }
        )

        mock_accommodation_service.save_accommodation = AsyncMock(
            return_value={
                "id": "saved-123",
                "user_id": "test-user-id",
                "trip_id": "test-trip-id",
                "listing": {"id": "test-listing"},
                "check_in": "2024-03-15",
                "check_out": "2024-03-18",
                "saved_at": "2024-01-01",
                "status": "SAVED",
            }
        )

        # Configure file processing service mock
        mock_file_instance = Mock()
        mock_file_service.return_value = mock_file_instance
        
        # Mock file upload methods
        from datetime import datetime

        from tripsage_core.services.business.file_processing_service import (
            FileType,
            ProcessedFile,
            ProcessingStatus,
            StorageProvider,
        )
        
        mock_upload_result = ProcessedFile(
            id="test-file-id",
            user_id="test-user-id",
            original_filename="test.txt",
            stored_filename="test-stored.txt",
            file_size=1024,
            file_type=FileType.TEXT,
            mime_type="text/plain",
            file_hash="test-hash",
            storage_provider=StorageProvider.LOCAL,
            storage_path="/test/path",
            processing_status=ProcessingStatus.COMPLETED,
            upload_timestamp=datetime.now()
        )
        
        mock_file_instance.upload_file = AsyncMock(return_value=mock_upload_result)
        mock_file_instance.upload_files_batch = AsyncMock(
            return_value=[mock_upload_result]
        )
        mock_file_instance.get_file = AsyncMock(return_value=mock_upload_result)
        mock_file_instance.get_file_content = AsyncMock(
            return_value=b"test file content"
        )
        mock_file_instance.delete_file = AsyncMock(return_value=True)
        mock_file_instance.search_files = AsyncMock(return_value=[])

        from tripsage.api.main import app

        with TestClient(app) as client:
            yield client


@pytest.fixture
def unauthenticated_test_client(mock_cache_service, mock_database_service):
    """Create FastAPI test client for testing unauthenticated requests."""
    with (
        # Mock settings
        patch("tripsage_core.config.base_app_settings.get_settings") as mock_settings,
        # Mock cache service
        patch(
            "tripsage_core.services.infrastructure.cache_service.get_cache_service",
            return_value=mock_cache_service,
        ),
        # Mock database service
        patch(
            "tripsage_core.services.infrastructure.database_service.get_database_service",
            return_value=mock_database_service,
        ),
        # Mock Supabase client
        patch("supabase.create_client", return_value=Mock()),
        # Mock MCP manager to prevent initialization issues
        patch(
            "tripsage_core.mcp_abstraction.manager.MCPManager.initialize_all_enabled",
            new_callable=AsyncMock,
        ),
        patch(
            "tripsage_core.mcp_abstraction.manager.MCPManager.initialize",
            new_callable=AsyncMock,
        ),
        # Mock rate limiting middleware to disable it
        patch(
            "tripsage.api.middlewares.rate_limiting.EnhancedRateLimitMiddleware.dispatch"
        ) as mock_rate_limit,
        # Mock the authentication dependency to return None (unauthenticated)
        patch(
            "tripsage.api.core.dependencies.get_current_principal", return_value=None
        ),
        # Mock file processing service
        patch(
            "tripsage_core.services.business.file_processing_service.FileProcessingService"
        ) as mock_file_service,
    ):
        # Configure mock settings
        from tests.test_config import create_test_settings

        mock_settings.return_value = create_test_settings()

        # Configure rate limiting middleware to pass through
        async def pass_through_middleware(request, call_next):
            return await call_next(request)

        mock_rate_limit.side_effect = pass_through_middleware

        # Configure file processing service mock  
        mock_file_instance = Mock()
        mock_file_service.return_value = mock_file_instance

        # Import app after all patches are in place
        from tripsage.api.main import app

        with TestClient(app) as client:
            yield client


@pytest.fixture
def authenticated_headers():
    """Standard authentication headers for tests."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_principal():
    """Mock principal for authentication tests."""
    principal = Mock()
    principal.id = "test-user-id"
    principal.email = "test@example.com"
    return principal


# Validation test data fixtures
@pytest.fixture
def valid_accommodation_search():
    """Valid accommodation search request data."""
    return {
        "location": "Tokyo",
        "check_in": "2024-03-15",
        "check_out": "2024-03-18",
        "adults": 2,
    }


@pytest.fixture
def invalid_accommodation_search_data():
    """Invalid accommodation search request data for validation testing."""
    return [
        # Invalid adults count
        {
            "location": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 0,
        },
        {
            "location": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": -1,
        },
        {
            "location": "Tokyo",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 17,
        },
        # Invalid location
        {
            "location": "",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 2,
        },
        {
            "location": " ",
            "check_in": "2024-03-15",
            "check_out": "2024-03-18",
            "adults": 2,
        },
        # Invalid dates
        {
            "location": "Tokyo",
            "check_in": "2024-03-18",
            "check_out": "2024-03-15",
            "adults": 2,
        },
    ]


@pytest.fixture
def valid_accommodation_details():
    """Valid accommodation details request data."""
    return {
        "listing_id": "test-listing-id",
    }


@pytest.fixture
def valid_save_accommodation():
    """Valid save accommodation request data."""
    return {
        "listing_id": "test-listing-id",
        "trip_id": "550e8400-e29b-41d4-a716-446655440000",
        "check_in": "2024-03-15",
        "check_out": "2024-03-18",
        "notes": "Great location!",
    }


# === FLIGHTS FIXTURES ===


@pytest.fixture
def valid_flight_search():
    """Valid flight search request data."""
    return {
        "origin": "LAX",
        "destination": "NRT",
        "departure_date": "2024-03-15",
        "return_date": "2024-03-22",
        "passengers": {
            "adults": 1,
            "children": 0,
            "infants": 0,
        },
        "cabin_class": "economy",
    }


@pytest.fixture
def valid_flight_details():
    """Valid flight details request data."""
    return {
        "flight_id": "test-flight-id",
        "include_baggage": True,
        "include_seat_map": True,
    }


@pytest.fixture
def valid_save_flight():
    """Valid save flight request data."""
    return {
        "flight_id": "test-flight-id",
        "trip_id": "550e8400-e29b-41d4-a716-446655440000",
        "notes": "Great price!",
    }


# === DESTINATIONS FIXTURES ===


@pytest.fixture
def valid_destination_search():
    """Valid destination search request data."""
    return {
        "query": "Tokyo",
        "limit": 10,
    }


@pytest.fixture
def valid_destination_details():
    """Valid destination details request data."""
    return {
        "destination_id": "test-destination-id",
        "include_weather": True,
        "include_activities": True,
    }


@pytest.fixture
def valid_destination_recommendations():
    """Valid destination recommendations request data."""
    return {
        "preferences": {
            "climate": "tropical",
            "activities": ["beach", "culture"],
            "budget_range": "medium",
        },
        "limit": 5,
    }


# === TRIPS FIXTURES ===


@pytest.fixture
def valid_trip_create():
    """Valid trip creation request data."""
    return {
        "title": "Tokyo Adventure",
        "description": "Amazing trip to Tokyo",
        "destination": "Tokyo, Japan",
        "start_date": "2024-03-15",
        "end_date": "2024-03-22",
        "budget": 5000.0,
        "currency": "USD",
    }


@pytest.fixture
def valid_trip_update():
    """Valid trip update request data."""
    return {
        "title": "Updated Tokyo Adventure",
        "description": "Updated amazing trip to Tokyo",
        "budget": 6000.0,
    }
