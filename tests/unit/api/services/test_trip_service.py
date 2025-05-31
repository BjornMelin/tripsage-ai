"""
Comprehensive tests for the refactored API trip service.

Tests the thin wrapper functionality, model adaptation, error handling,
and dependency injection patterns of the TripService.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

from api.services.trip_service import TripService, MockTripService
from tripsage_core.exceptions.exceptions import (
    CoreServiceError as ServiceError,
    CoreValidationError as ValidationError,
)
from tripsage_core.services.business.trip_service import (
    TripService as CoreTripService,
)


class TestTripService:
    """Comprehensive test cases for TripService thin wrapper."""

    @pytest.fixture
    def mock_core_trip_service(self):
        """Mock core trip service."""
        return AsyncMock(spec=CoreTripService)

    @pytest.fixture
    def trip_service(self, mock_core_trip_service):
        """Create trip service with mocked dependencies."""
        return TripService(core_trip_service=mock_core_trip_service)

    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data for testing."""
        return {
            "id": str(uuid4()),
            "name": "European Adventure",
            "description": "A wonderful trip across Europe",
            "destination": "Europe",
            "start_date": "2024-06-15",
            "end_date": "2024-06-25",
            "budget": 5000.0,
            "status": "planning",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @pytest.fixture
    def sample_trip_list(self, sample_trip_data):
        """Sample list of trips."""
        trip2 = sample_trip_data.copy()
        trip2.update({
            "id": str(uuid4()),
            "name": "Asian Journey",
            "description": "Exploring Asian cultures",
            "destination": "Asia",
            "status": "active",
        })
        
        trip3 = sample_trip_data.copy()
        trip3.update({
            "id": str(uuid4()),
            "name": "American Road Trip", 
            "description": "Cross-country adventure",
            "destination": "USA",
            "status": "completed",
        })
        
        return [sample_trip_data, trip2, trip3]

    # Trip Creation Tests
    async def test_create_trip_success(
        self, trip_service, mock_core_trip_service, sample_trip_data
    ):
        """Test successful trip creation."""
        # Arrange
        user_id = "user_123"
        trip_input = {
            "name": "European Adventure",
            "description": "A wonderful trip across Europe",
            "destination": "Europe",
            "start_date": "2024-06-15",
            "end_date": "2024-06-25",
            "budget": 5000.0,
        }
        
        mock_core_trip_service.create_trip.return_value = sample_trip_data

        # Act
        result = await trip_service.create_trip(user_id, trip_input)

        # Assert
        assert result == sample_trip_data
        mock_core_trip_service.create_trip.assert_called_once_with(
            user_id=user_id, **trip_input
        )

    async def test_create_trip_validation_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip creation with validation error."""
        # Arrange
        user_id = "user_123"
        trip_input = {"name": ""}  # Invalid empty name
        
        mock_core_trip_service.create_trip.side_effect = ValidationError(
            "Trip name cannot be empty"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Trip name cannot be empty"):
            await trip_service.create_trip(user_id, trip_input)

    async def test_create_trip_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip creation with service error."""
        # Arrange
        user_id = "user_123"
        trip_input = {"name": "Test Trip"}
        
        mock_core_trip_service.create_trip.side_effect = ServiceError(
            "Database connection failed"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Database connection failed"):
            await trip_service.create_trip(user_id, trip_input)

    async def test_create_trip_unexpected_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip creation with unexpected error."""
        # Arrange
        user_id = "user_123"
        trip_input = {"name": "Test Trip"}
        
        mock_core_trip_service.create_trip.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to create trip"):
            await trip_service.create_trip(user_id, trip_input)

    # Trip Retrieval Tests
    async def test_get_trip_success(
        self, trip_service, mock_core_trip_service, sample_trip_data
    ):
        """Test successful trip retrieval."""
        # Arrange
        trip_id = UUID(sample_trip_data["id"])
        user_id = "user_123"
        mock_core_trip_service.get_trip.return_value = sample_trip_data

        # Act
        result = await trip_service.get_trip(trip_id, user_id)

        # Assert
        assert result == sample_trip_data
        mock_core_trip_service.get_trip.assert_called_once_with(
            trip_id=trip_id, user_id=user_id
        )

    async def test_get_trip_not_found(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip retrieval when trip not found."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.get_trip.return_value = None

        # Act
        result = await trip_service.get_trip(trip_id, user_id)

        # Assert
        assert result is None
        mock_core_trip_service.get_trip.assert_called_once_with(
            trip_id=trip_id, user_id=user_id
        )

    async def test_get_trip_validation_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip retrieval with validation error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.get_trip.side_effect = ValidationError(
            "Invalid trip ID format"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid trip ID format"):
            await trip_service.get_trip(trip_id, user_id)

    async def test_get_trip_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip retrieval with service error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.get_trip.side_effect = ServiceError(
            "Database error"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Database error"):
            await trip_service.get_trip(trip_id, user_id)

    async def test_get_trip_unexpected_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip retrieval with unexpected error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.get_trip.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to retrieve trip"):
            await trip_service.get_trip(trip_id, user_id)

    # User Trips Retrieval Tests
    async def test_get_user_trips_success(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test successful user trips retrieval."""
        # Arrange
        user_id = "user_123"
        mock_core_trip_service.get_user_trips.return_value = sample_trip_list

        # Act
        result = await trip_service.get_user_trips(user_id)

        # Assert
        assert result == sample_trip_list
        mock_core_trip_service.get_user_trips.assert_called_once_with(
            user_id=user_id, limit=50, offset=0
        )

    async def test_get_user_trips_with_pagination(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test user trips retrieval with custom pagination."""
        # Arrange
        user_id = "user_123"
        limit = 10
        offset = 20
        mock_core_trip_service.get_user_trips.return_value = sample_trip_list

        # Act
        result = await trip_service.get_user_trips(user_id, limit=limit, offset=offset)

        # Assert
        assert result == sample_trip_list
        mock_core_trip_service.get_user_trips.assert_called_once_with(
            user_id=user_id, limit=limit, offset=offset
        )

    async def test_get_user_trips_empty_result(
        self, trip_service, mock_core_trip_service
    ):
        """Test user trips retrieval with empty result."""
        # Arrange
        user_id = "user_123"
        mock_core_trip_service.get_user_trips.return_value = []

        # Act
        result = await trip_service.get_user_trips(user_id)

        # Assert
        assert result == []

    async def test_get_user_trips_invalid_limit(self, trip_service):
        """Test user trips retrieval with invalid limit."""
        # Arrange
        user_id = "user_123"

        # Act & Assert - Limit too high
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await trip_service.get_user_trips(user_id, limit=101)

        # Act & Assert - Limit too low
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await trip_service.get_user_trips(user_id, limit=0)

    async def test_get_user_trips_invalid_offset(self, trip_service):
        """Test user trips retrieval with invalid offset."""
        # Arrange
        user_id = "user_123"

        # Act & Assert
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            await trip_service.get_user_trips(user_id, offset=-1)

    async def test_get_user_trips_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test user trips retrieval with service error."""
        # Arrange
        user_id = "user_123"
        mock_core_trip_service.get_user_trips.side_effect = ServiceError(
            "Database error"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Database error"):
            await trip_service.get_user_trips(user_id)

    # Trip Update Tests
    async def test_update_trip_success(
        self, trip_service, mock_core_trip_service, sample_trip_data
    ):
        """Test successful trip update."""
        # Arrange
        trip_id = UUID(sample_trip_data["id"])
        user_id = "user_123"
        updates = {"name": "Updated Trip Name", "budget": 6000.0}
        
        updated_trip = sample_trip_data.copy()
        updated_trip.update(updates)
        mock_core_trip_service.update_trip.return_value = updated_trip

        # Act
        result = await trip_service.update_trip(trip_id, user_id, updates)

        # Assert
        assert result == updated_trip
        mock_core_trip_service.update_trip.assert_called_once_with(
            trip_id=trip_id, user_id=user_id, **updates
        )

    async def test_update_trip_empty_updates(self, trip_service):
        """Test trip update with empty updates."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        updates = {}

        # Act & Assert
        with pytest.raises(ValidationError, match="No updates provided"):
            await trip_service.update_trip(trip_id, user_id, updates)

    async def test_update_trip_validation_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip update with validation error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        updates = {"name": ""}  # Invalid empty name
        
        mock_core_trip_service.update_trip.side_effect = ValidationError(
            "Trip name cannot be empty"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Trip name cannot be empty"):
            await trip_service.update_trip(trip_id, user_id, updates)

    async def test_update_trip_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip update with service error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        updates = {"name": "Updated Name"}
        
        mock_core_trip_service.update_trip.side_effect = ServiceError(
            "Database error"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Database error"):
            await trip_service.update_trip(trip_id, user_id, updates)

    async def test_update_trip_unexpected_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip update with unexpected error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        updates = {"name": "Updated Name"}
        
        mock_core_trip_service.update_trip.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to update trip"):
            await trip_service.update_trip(trip_id, user_id, updates)

    # Trip Deletion Tests
    async def test_delete_trip_success(
        self, trip_service, mock_core_trip_service
    ):
        """Test successful trip deletion."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.delete_trip.return_value = True

        # Act
        result = await trip_service.delete_trip(trip_id, user_id)

        # Assert
        assert result is True
        mock_core_trip_service.delete_trip.assert_called_once_with(
            trip_id=trip_id, user_id=user_id
        )

    async def test_delete_trip_not_found(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip deletion when trip not found."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.delete_trip.return_value = False

        # Act & Assert
        with pytest.raises(ValidationError, match="Trip not found"):
            await trip_service.delete_trip(trip_id, user_id)

    async def test_delete_trip_validation_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip deletion with validation error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.delete_trip.side_effect = ValidationError(
            "Invalid trip ID"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid trip ID"):
            await trip_service.delete_trip(trip_id, user_id)

    async def test_delete_trip_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip deletion with service error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.delete_trip.side_effect = ServiceError(
            "Database error"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Database error"):
            await trip_service.delete_trip(trip_id, user_id)

    async def test_delete_trip_unexpected_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip deletion with unexpected error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        mock_core_trip_service.delete_trip.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to delete trip"):
            await trip_service.delete_trip(trip_id, user_id)

    # Search Trips Tests
    async def test_search_trips_success_with_search_method(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test successful trip search when core service supports search."""
        # Arrange
        user_id = "user_123"
        query = "European"
        status = "planning"
        
        # Mock the core service to have search_trips method
        mock_core_trip_service.search_trips.return_value = [sample_trip_list[0]]

        # Act
        result = await trip_service.search_trips(user_id, query=query, status=status)

        # Assert
        assert result == [sample_trip_list[0]]
        mock_core_trip_service.search_trips.assert_called_once_with(
            user_id=user_id, query=query, status=status, limit=50, offset=0
        )

    async def test_search_trips_fallback_to_get_user_trips(
        self, trip_service, sample_trip_list
    ):
        """Test trip search fallback when core service doesn't support search."""
        # Arrange
        user_id = "user_123"
        query = "European"
        
        # Create a mock core service without search_trips method
        mock_core_service = AsyncMock()
        # Remove search_trips method to simulate fallback scenario
        del mock_core_service.search_trips
        mock_core_service.get_user_trips.return_value = sample_trip_list
        
        trip_service.core_trip_service = mock_core_service

        # Act
        result = await trip_service.search_trips(user_id, query=query)

        # Assert - Should find the trip containing "European" in name
        assert len(result) == 1
        assert result[0]["name"] == "European Adventure"
        mock_core_service.get_user_trips.assert_called_once_with(
            user_id=user_id, limit=50
        )

    async def test_search_trips_fallback_with_status_filter(
        self, trip_service, sample_trip_list
    ):
        """Test trip search fallback with status filtering."""
        # Arrange
        user_id = "user_123"
        status = "active"
        
        # Create a mock core service without search_trips method
        mock_core_service = AsyncMock()
        del mock_core_service.search_trips
        mock_core_service.get_user_trips.return_value = sample_trip_list
        
        trip_service.core_trip_service = mock_core_service

        # Act
        result = await trip_service.search_trips(user_id, status=status)

        # Assert - Should find the trip with "active" status
        assert len(result) == 1
        assert result[0]["status"] == "active"

    async def test_search_trips_fallback_with_query_and_status(
        self, trip_service, sample_trip_list
    ):
        """Test trip search fallback with both query and status filtering."""
        # Arrange
        user_id = "user_123"
        query = "Asian"
        status = "active"
        
        # Create a mock core service without search_trips method
        mock_core_service = AsyncMock()
        del mock_core_service.search_trips
        mock_core_service.get_user_trips.return_value = sample_trip_list
        
        trip_service.core_trip_service = mock_core_service

        # Act
        result = await trip_service.search_trips(user_id, query=query, status=status)

        # Assert - Should find the Asian trip with active status
        assert len(result) == 1
        assert result[0]["name"] == "Asian Journey"
        assert result[0]["status"] == "active"

    async def test_search_trips_invalid_limit(self, trip_service):
        """Test trip search with invalid limit."""
        # Arrange
        user_id = "user_123"

        # Act & Assert - Limit too high
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await trip_service.search_trips(user_id, limit=101)

        # Act & Assert - Limit too low
        with pytest.raises(ValidationError, match="Limit must be between 1 and 100"):
            await trip_service.search_trips(user_id, limit=0)

    async def test_search_trips_invalid_offset(self, trip_service):
        """Test trip search with invalid offset."""
        # Arrange
        user_id = "user_123"

        # Act & Assert
        with pytest.raises(ValidationError, match="Offset must be non-negative"):
            await trip_service.search_trips(user_id, offset=-1)

    async def test_search_trips_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip search with service error."""
        # Arrange
        user_id = "user_123"
        mock_core_trip_service.search_trips.side_effect = ServiceError(
            "Database error"
        )

        # Act & Assert
        with pytest.raises(ServiceError, match="Database error"):
            await trip_service.search_trips(user_id)

    async def test_search_trips_unexpected_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip search with unexpected error."""
        # Arrange
        user_id = "user_123"
        mock_core_trip_service.search_trips.side_effect = Exception("Unexpected error")

        # Act & Assert
        with pytest.raises(ServiceError, match="Failed to search trips"):
            await trip_service.search_trips(user_id)

    # Lazy Initialization Tests
    async def test_lazy_service_initialization(self):
        """Test that core service is initialized lazily."""
        # Arrange
        trip_service = TripService()

        # Assert - Service should be None initially
        assert trip_service.core_trip_service is None

        # Verify lazy initialization method exists
        assert hasattr(trip_service, "_get_core_trip_service")

    async def test_get_core_trip_service_lazy_initialization(self):
        """Test core trip service lazy initialization."""
        # Arrange
        trip_service = TripService()
        
        # Mock the lazy initialization
        mock_service = AsyncMock(spec=CoreTripService)
        
        # Mock the get_core_trip_service function
        async def mock_get_core_trip_service():
            return mock_service
            
        # Replace the function
        import api.services.trip_service
        original_fn = api.services.trip_service.get_core_trip_service
        api.services.trip_service.get_core_trip_service = mock_get_core_trip_service
        
        try:
            # Act
            result = await trip_service._get_core_trip_service()
            
            # Assert
            assert result is mock_service
            assert trip_service.core_trip_service is mock_service
        finally:
            # Restore original function
            api.services.trip_service.get_core_trip_service = original_fn

    async def test_get_core_trip_service_initialization_failure(self):
        """Test core trip service initialization failure fallback."""
        # Arrange
        trip_service = TripService()
        
        # Mock the get_core_trip_service to raise an exception
        async def mock_get_core_trip_service():
            raise Exception("Database not configured")
            
        # Replace the function
        import api.services.trip_service
        original_fn = api.services.trip_service.get_core_trip_service
        api.services.trip_service.get_core_trip_service = mock_get_core_trip_service
        
        try:
            # Act
            result = await trip_service._get_core_trip_service()
            
            # Assert
            assert isinstance(result, MockTripService)
            assert trip_service.core_trip_service is result
        finally:
            # Restore original function
            api.services.trip_service.get_core_trip_service = original_fn

    # MockTripService Tests
    async def test_mock_trip_service_operations(self):
        """Test that MockTripService raises appropriate errors."""
        # Arrange
        mock_service = MockTripService()

        # Assert all operations raise ServiceError
        with pytest.raises(ServiceError, match="Trip service not available"):
            await mock_service.create_trip()

        with pytest.raises(ServiceError, match="Trip service not available"):
            await mock_service.get_trip()

        with pytest.raises(ServiceError, match="Trip service not available"):
            await mock_service.get_user_trips()

        with pytest.raises(ServiceError, match="Trip service not available"):
            await mock_service.update_trip()

        with pytest.raises(ServiceError, match="Trip service not available"):
            await mock_service.delete_trip()

    # Integration and Edge Case Tests
    async def test_comprehensive_error_logging(
        self, trip_service, mock_core_trip_service, caplog
    ):
        """Test that errors are properly logged."""
        # Arrange
        user_id = "user_123"
        trip_input = {"name": "Test Trip"}
        mock_core_trip_service.create_trip.side_effect = ServiceError("Database error")

        # Act
        with pytest.raises(ServiceError):
            await trip_service.create_trip(user_id, trip_input)

        # Assert - Check that error was logged
        assert "Failed to create trip for user user_123" in caplog.text
        assert "Database error" in caplog.text

    async def test_multiple_service_calls_use_same_instance(self, trip_service):
        """Test that multiple calls use the same service instance."""
        # Arrange
        mock_core_service = AsyncMock(spec=CoreTripService)
        trip_service.core_trip_service = mock_core_service

        # Act
        service1 = await trip_service._get_core_trip_service()
        service2 = await trip_service._get_core_trip_service()

        # Assert - Same instance should be returned
        assert service1 is service2
        assert service1 is mock_core_service

    async def test_case_insensitive_search_fallback(
        self, trip_service, sample_trip_list
    ):
        """Test that fallback search is case-insensitive."""
        # Arrange
        user_id = "user_123"
        query = "EUROPEAN"  # Upper case query
        
        # Create a mock core service without search_trips method
        mock_core_service = AsyncMock()
        del mock_core_service.search_trips
        mock_core_service.get_user_trips.return_value = sample_trip_list
        
        trip_service.core_trip_service = mock_core_service

        # Act
        result = await trip_service.search_trips(user_id, query=query)

        # Assert - Should find the trip despite case difference
        assert len(result) == 1
        assert result[0]["name"] == "European Adventure"

    async def test_search_fallback_description_matching(
        self, trip_service, sample_trip_list
    ):
        """Test that fallback search matches description field."""
        # Arrange
        user_id = "user_123"
        query = "cultures"  # This appears in Asian trip description
        
        # Create a mock core service without search_trips method
        mock_core_service = AsyncMock()
        del mock_core_service.search_trips
        mock_core_service.get_user_trips.return_value = sample_trip_list
        
        trip_service.core_trip_service = mock_core_service

        # Act
        result = await trip_service.search_trips(user_id, query=query)

        # Assert - Should find the Asian trip based on description
        assert len(result) == 1
        assert result[0]["name"] == "Asian Journey"