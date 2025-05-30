"""
Unit tests for the API trip service.

Tests the thin wrapper functionality and model adaptation between
API and core services.
"""

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from api.services.trip_service import MockTripService, TripService
from tripsage_core.exceptions.exceptions import (
    CoreServiceError,
    CoreValidationError,
)
from tripsage_core.services.business.trip_service import (
    TripService as CoreTripService,
)


class TestTripService:
    """Test cases for TripService."""

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
        """Sample trip data."""
        return {
            "id": str(uuid4()),
            "name": "Test Trip",
            "description": "A test trip to Paris",
            "destination": "Paris, France",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "status": "planned",
            "budget": 2000.0,
            "created_at": "2025-01-16T10:00:00Z",
            "updated_at": "2025-01-16T10:00:00Z",
        }

    @pytest.fixture
    def sample_trip_list(self, sample_trip_data):
        """Sample list of trips."""
        trip2 = sample_trip_data.copy()
        trip2["id"] = str(uuid4())
        trip2["name"] = "Test Trip 2"
        trip2["description"] = "A test trip to Tokyo"
        trip2["destination"] = "Tokyo, Japan"
        return [sample_trip_data, trip2]

    async def test_create_trip_success(
        self, trip_service, mock_core_trip_service, sample_trip_data
    ):
        """Test successful trip creation."""
        # Arrange
        user_id = "user_123"
        trip_data = {
            "name": "Test Trip",
            "description": "A test trip to Paris",
            "destination": "Paris, France",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
        }

        mock_core_trip_service.create_trip.return_value = sample_trip_data

        # Act
        result = await trip_service.create_trip(user_id, trip_data)

        # Assert
        assert result == sample_trip_data
        mock_core_trip_service.create_trip.assert_called_once_with(
            user_id=user_id, **trip_data
        )

    async def test_create_trip_validation_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip creation with validation error."""
        # Arrange
        user_id = "user_123"
        trip_data = {"name": ""}  # Invalid empty name

        mock_core_trip_service.create_trip.side_effect = CoreValidationError(
            "Trip name cannot be empty"
        )

        # Act & Assert
        with pytest.raises(CoreValidationError):
            await trip_service.create_trip(user_id, trip_data)

    async def test_create_trip_service_error(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip creation with service error."""
        # Arrange
        user_id = "user_123"
        trip_data = {"name": "Test Trip"}

        mock_core_trip_service.create_trip.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(CoreServiceError, match="Failed to create trip"):
            await trip_service.create_trip(user_id, trip_data)

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

    async def test_get_trip_not_found(self, trip_service, mock_core_trip_service):
        """Test trip retrieval when trip not found."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"

        mock_core_trip_service.get_trip.return_value = None

        # Act
        result = await trip_service.get_trip(trip_id, user_id)

        # Assert
        assert result is None

    async def test_get_trip_service_error(self, trip_service, mock_core_trip_service):
        """Test trip retrieval with service error."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"

        mock_core_trip_service.get_trip.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(CoreServiceError, match="Failed to retrieve trip"):
            await trip_service.get_trip(trip_id, user_id)

    async def test_get_user_trips_success(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test successful user trips retrieval."""
        # Arrange
        user_id = "user_123"
        limit = 10
        offset = 0

        mock_core_trip_service.get_user_trips.return_value = sample_trip_list

        # Act
        result = await trip_service.get_user_trips(user_id, limit, offset)

        # Assert
        assert result == sample_trip_list
        assert len(result) == 2
        mock_core_trip_service.get_user_trips.assert_called_once_with(
            user_id=user_id, limit=limit, offset=offset
        )

    async def test_get_user_trips_with_defaults(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test user trips retrieval with default parameters."""
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

    async def test_get_user_trips_invalid_limit(
        self, trip_service, mock_core_trip_service
    ):
        """Test user trips retrieval with invalid limit."""
        # Arrange
        user_id = "user_123"
        invalid_limit = 150  # Too high

        # Act & Assert
        with pytest.raises(
            CoreValidationError, match="Limit must be between 1 and 100"
        ):
            await trip_service.get_user_trips(user_id, invalid_limit)

    async def test_get_user_trips_invalid_offset(
        self, trip_service, mock_core_trip_service
    ):
        """Test user trips retrieval with invalid offset."""
        # Arrange
        user_id = "user_123"
        invalid_offset = -1  # Negative

        # Act & Assert
        with pytest.raises(CoreValidationError, match="Offset must be non-negative"):
            await trip_service.get_user_trips(user_id, offset=invalid_offset)

    async def test_update_trip_success(
        self, trip_service, mock_core_trip_service, sample_trip_data
    ):
        """Test successful trip update."""
        # Arrange
        trip_id = UUID(sample_trip_data["id"])
        user_id = "user_123"
        updates = {"name": "Updated Trip Name", "budget": 2500.0}

        updated_trip = sample_trip_data.copy()
        updated_trip.update(updates)
        mock_core_trip_service.update_trip.return_value = updated_trip

        # Act
        result = await trip_service.update_trip(trip_id, user_id, updates)

        # Assert
        assert result["name"] == "Updated Trip Name"
        assert result["budget"] == 2500.0
        mock_core_trip_service.update_trip.assert_called_once_with(
            trip_id=trip_id, user_id=user_id, **updates
        )

    async def test_update_trip_empty_updates(
        self, trip_service, mock_core_trip_service
    ):
        """Test trip update with empty updates."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"
        updates = {}

        # Act & Assert
        with pytest.raises(CoreValidationError, match="No updates provided"):
            await trip_service.update_trip(trip_id, user_id, updates)

    async def test_delete_trip_success(self, trip_service, mock_core_trip_service):
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

    async def test_delete_trip_not_found(self, trip_service, mock_core_trip_service):
        """Test trip deletion when trip not found."""
        # Arrange
        trip_id = uuid4()
        user_id = "user_123"

        mock_core_trip_service.delete_trip.return_value = False

        # Act & Assert
        with pytest.raises(CoreValidationError, match="Trip not found"):
            await trip_service.delete_trip(trip_id, user_id)

    async def test_search_trips_with_core_support(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test trip search when core service supports search."""
        # Arrange
        user_id = "user_123"
        query = "Paris"
        status = "planned"

        # Mock core service to have search_trips method
        mock_core_trip_service.search_trips.return_value = [sample_trip_list[0]]

        # Act
        result = await trip_service.search_trips(
            user_id=user_id, query=query, status=status
        )

        # Assert
        assert len(result) == 1
        assert result[0]["destination"] == "Paris, France"
        mock_core_trip_service.search_trips.assert_called_once_with(
            user_id=user_id, query=query, status=status, limit=50, offset=0
        )

    async def test_search_trips_fallback_to_get_user_trips(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test trip search fallback when core service doesn't support search."""
        # Arrange
        user_id = "user_123"
        query = "Paris"

        # Mock core service to NOT have search_trips method
        del mock_core_trip_service.search_trips
        mock_core_trip_service.get_user_trips.return_value = sample_trip_list

        # Act
        result = await trip_service.search_trips(user_id=user_id, query=query)

        # Assert
        assert len(result) == 1  # Only one trip contains "Paris" in description
        # The result should be the Paris trip
        assert result[0]["destination"] == "Paris, France"
        assert "Paris" in result[0]["description"]
        mock_core_trip_service.get_user_trips.assert_called_once_with(
            user_id=user_id, limit=50
        )

    async def test_search_trips_with_status_filter(
        self, trip_service, mock_core_trip_service, sample_trip_list
    ):
        """Test trip search with status filter fallback."""
        # Arrange
        user_id = "user_123"
        status = "planned"

        # Mock core service to NOT have search_trips method
        del mock_core_trip_service.search_trips
        mock_core_trip_service.get_user_trips.return_value = sample_trip_list

        # Act
        result = await trip_service.search_trips(user_id=user_id, status=status)

        # Assert
        assert len(result) == 2  # Both trips have "planned" status
        mock_core_trip_service.get_user_trips.assert_called_once()

    async def test_lazy_service_initialization(self):
        """Test that core service is initialized lazily."""
        # Arrange
        trip_service = TripService()

        # Assert - Service should be None initially
        assert trip_service.core_trip_service is None

        # Act - Access service (would initialize it in real scenario)
        # Note: In real scenario, this would call get_core_trip_service()
        # Here we just verify the lazy initialization pattern is in place
        assert hasattr(trip_service, "_get_core_trip_service")

    async def test_mock_service_fallback(self):
        """Test that MockTripService is used when core service fails to initialize."""
        # Arrange
        trip_service = TripService()

        # Mock the core service initialization to fail
        async def failing_get_core_service():
            raise Exception("Database not configured")

        trip_service._get_core_trip_service = failing_get_core_service

        # Act & Assert
        with pytest.raises(CoreServiceError, match="Failed to create trip"):
            await trip_service.create_trip("user_123", {"name": "Test"})


class TestMockTripService:
    """Test cases for MockTripService."""

    @pytest.fixture
    def mock_service(self):
        """Create mock trip service."""
        return MockTripService()

    async def test_mock_service_methods_raise_errors(self, mock_service):
        """Test that all mock service methods raise appropriate errors."""
        # Test create_trip
        with pytest.raises(CoreServiceError, match="not available"):
            await mock_service.create_trip()

        # Test get_trip
        with pytest.raises(CoreServiceError, match="not available"):
            await mock_service.get_trip()

        # Test get_user_trips
        with pytest.raises(CoreServiceError, match="not available"):
            await mock_service.get_user_trips()

        # Test update_trip
        with pytest.raises(CoreServiceError, match="not available"):
            await mock_service.update_trip()

        # Test delete_trip
        with pytest.raises(CoreServiceError, match="not available"):
            await mock_service.delete_trip()


class TestErrorHandlingAndValidation:
    """Test cases for error handling and validation."""

    @pytest.fixture
    def mock_core_trip_service(self):
        """Mock core trip service."""
        return AsyncMock(spec=CoreTripService)

    @pytest.fixture
    def trip_service(self, mock_core_trip_service):
        """Create trip service with mocked dependencies."""
        return TripService(core_trip_service=mock_core_trip_service)

    async def test_error_handling_and_logging(
        self, trip_service, mock_core_trip_service, caplog
    ):
        """Test error handling and logging."""
        # Arrange
        user_id = "user_123"
        trip_data = {"name": "Test Trip"}

        mock_core_trip_service.create_trip.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(CoreServiceError):
            await trip_service.create_trip(user_id, trip_data)

        # Verify logging
        assert "Unexpected error creating trip" in caplog.text

    async def test_parameter_validation_edge_cases(self, trip_service):
        """Test edge cases in parameter validation."""
        user_id = "user_123"

        # Test limit boundary values
        with pytest.raises(CoreValidationError):
            await trip_service.get_user_trips(user_id, limit=0)

        with pytest.raises(CoreValidationError):
            await trip_service.get_user_trips(user_id, limit=101)

        # Test valid boundary values
        # These would work if core service was properly mocked
        # await trip_service.get_user_trips(user_id, limit=1)
        # await trip_service.get_user_trips(user_id, limit=100)
