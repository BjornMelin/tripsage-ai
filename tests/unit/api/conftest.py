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

def create_authenticated_test_client(mock_principal):
    """Create an authenticated test client with all dependencies mocked.

    This is a helper function for creating test clients that need authentication.
    Use this pattern in router tests for authenticated endpoints.
    """
    from fastapi.testclient import TestClient

    from tripsage.api.core.dependencies import (
        get_current_principal,
        require_principal,
        require_user_principal,
    )
    from tripsage.api.main import app

    # Override authentication dependencies
    app.dependency_overrides[get_current_principal] = lambda: mock_principal
    app.dependency_overrides[require_principal] = lambda: mock_principal
    app.dependency_overrides[require_user_principal] = lambda: mock_principal

    return TestClient(app)

def create_unauthenticated_test_client():
    """Create an unauthenticated test client with authentication
    dependencies returning None.

    This is a helper function for creating test clients for testing unauthorized
    access. Use this pattern in router tests for testing authentication failures.
    """
    from fastapi.testclient import TestClient

    from tripsage.api.core.dependencies import get_current_principal
    from tripsage.api.main import app

    # Override authentication dependencies to return None (unauthenticated)
    app.dependency_overrides[get_current_principal] = lambda: None

    return TestClient(app)

@pytest.fixture
def api_test_client(mock_cache_service, mock_database_service, mock_principal):
    """Create FastAPI test client with all dependencies properly mocked."""
    with (
        # Mock settings
        patch("tripsage_core.config.get_settings") as mock_settings,
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
        # Mock legacy MCP references (removed during modernization)
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
        patch(
            "tripsage_core.services.business.flight_service.get_flight_service"
        ) as mock_flight_service_getter,
        patch(
            "tripsage_core.services.business.destination_service.get_destination_service"
        ) as mock_destination_service_getter,
        patch("tripsage_core.services.business.chat_service.get_chat_service"),
        patch("tripsage_core.services.business.memory_service.get_memory_service"),
        patch(
            "tripsage_core.services.business.key_management_service.get_key_management_service"
        ),
        patch(
            "tripsage_core.services.business.user_service.get_user_service"
        ) as mock_user_service_getter,
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

        # Configure destination service mock with simple return values
        mock_destination_service = AsyncMock()
        mock_destination_service_getter.return_value = mock_destination_service

        # Configure destination service mock responses with minimal data
        from tripsage.api.schemas.destinations import (
            DestinationDetailsResponse,
            DestinationSearchResponse,
        )
        from tripsage_core.models.schemas_common.geographic import Place as Destination

        # Simple mock that just returns empty result
        mock_search_response = DestinationSearchResponse(
            destinations=[],
            count=0,
            query="Tokyo",
        )

        mock_destination_service.search_destinations = AsyncMock(
            return_value=mock_search_response
        )

        # Simple mock destination for details
        mock_destination = Destination(
            id="test-destination-id",
            name="Tokyo",
            description="A vibrant city in Japan",
            latitude=35.6762,
            longitude=139.6503,
            country="Japan",
            city="Tokyo",
            region="Kanto",
            type="city",
        )

        mock_destination_service.get_destination_details = AsyncMock(
            return_value=DestinationDetailsResponse(destination=mock_destination)
        )

        mock_destination_service.get_destination_recommendations = AsyncMock(
            return_value=[]
        )

        # Configure user service mock
        mock_user_service = AsyncMock()
        mock_user_service_getter.return_value = mock_user_service

        # Configure user service mock responses
        from datetime import datetime, timezone

        from tripsage_core.services.business.user_service import UserResponse

        def mock_get_user_by_id(user_id):
            """Mock get user by id method."""
            from unittest.mock import MagicMock

            mock_user = MagicMock()
            mock_user.id = user_id
            mock_user.preferences_json = {
                "theme": "dark",
                "currency": "USD",
                "language": "en",
                "notifications": {
                    "email": True,
                    "push": False,
                    "marketing": False,
                },
            }
            return mock_user

        mock_user_service.get_user_by_id = AsyncMock(side_effect=mock_get_user_by_id)

        def mock_update_user_preferences(user_id, preferences):
            """Mock update user preferences method."""
            return UserResponse(
                id=user_id,
                email="test@example.com",
                is_active=True,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                preferences=preferences,
            )

        mock_user_service.update_user_preferences = AsyncMock(
            side_effect=mock_update_user_preferences
        )

        # Configure flight service mock
        mock_flight_service = AsyncMock()
        mock_flight_service_getter.return_value = mock_flight_service

        # Configure mock search flights response
        from tripsage_core.models.schemas_common.enums import CabinClass
        from tripsage_core.models.schemas_common.flight_schemas import (
            FlightSearchResponse,
        )

        def mock_search_flights(request):
            """Mock search flights method that returns API response format."""
            # Return proper FlightSearchResponse object
            return FlightSearchResponse(
                results=[],
                count=0,
                currency="USD",
                search_id="mock-search-id",
                search_request=request,
            )

        mock_flight_service.search_flights = AsyncMock(side_effect=mock_search_flights)

        # Configure get flight offer mock
        from datetime import timedelta

        from tripsage_core.models.domain.flight import Airport, FlightOffer

        def mock_get_flight_offer(offer_id):
            """Mock get flight offer method."""
            return FlightOffer(
                id=offer_id,
                origin_airport=Airport(
                    iata_code="LAX",
                    name="Los Angeles International Airport",
                    city="Los Angeles",
                    country="United States",
                    latitude=33.9425,
                    longitude=-118.4081,
                ),
                destination_airport=Airport(
                    iata_code="NRT",
                    name="Narita International Airport",
                    city="Tokyo",
                    country="Japan",
                    latitude=35.7647,
                    longitude=140.3864,
                ),
                departure_time=datetime.now() + timedelta(days=30),
                arrival_time=datetime.now() + timedelta(days=30, hours=12),
                duration_minutes=720,
                stops=0,
                price=899.99,
                currency="USD",
                airline_code="AA",
                flight_number="AA0001",
                cabin_class=CabinClass.ECONOMY,
                seats_available=42,
            )

        mock_flight_service.get_flight_offer = AsyncMock(
            side_effect=mock_get_flight_offer
        )

        # Configure save flight mock
        from tripsage_core.models.schemas_common.flight_schemas import (
            SavedFlightResponse,
        )

        def mock_save_flight(user_id, request):
            """Mock save flight method."""
            return SavedFlightResponse(
                id="saved-flight-123",
                user_id=user_id,
                trip_id=request.trip_id,
                offer_id=request.offer_id,
                saved_at=datetime.now(),
                notes=request.notes,
            )

        mock_flight_service.save_flight = AsyncMock(side_effect=mock_save_flight)

        # Configure file processing service mock
        mock_file_instance = Mock()
        mock_file_service.return_value = mock_file_instance

        # Mock file upload methods

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
            upload_timestamp=datetime.now(),
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
        patch("tripsage_core.config.get_settings") as mock_settings,
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
        # Mock legacy MCP references (removed during modernization)
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
    from tripsage.api.middlewares.authentication import Principal

    return Principal(
        id="test-user-id",
        type="user",
        email="test@example.com",
        auth_method="jwt",
        scopes=["read", "write"],
        metadata={"role": "authenticated", "aud": "authenticated"},
    )

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
        "adults": 1,
        "children": 0,
        "infants": 0,
        "cabin_class": "economy",
    }

@pytest.fixture
def valid_flight_details():
    """Valid flight details request data."""
    return {
        "offer_id": "test-offer-id",  # Changed from flight_id
    }

@pytest.fixture
def valid_save_flight():
    """Valid save flight request data."""
    return {
        "offer_id": "test-offer-id",  # Changed from flight_id
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
