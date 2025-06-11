"""Modernized unit tests for trips router focusing on service layer testing."""

from datetime import date
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage.api.schemas.requests.trips import CreateTripRequest, UpdateTripRequest
from tripsage.api.schemas.responses.trips import TripResponse
from tripsage.api.services.trip import TripService
from tripsage_core.models.schemas_common.geographic import Coordinates
from tripsage_core.models.schemas_common.travel import TripDestination


class TestTripService:
    """Test suite for TripService focusing on business logic."""

    def setup_method(self):
        """Set up test data and mocks."""
        self.test_user_id = "test-user-123"
        self.test_trip_id = uuid4()

        # Create mock core service
        self.mock_core_service = Mock()

        # Initialize service with mock
        self.service = TripService(core_trip_service=self.mock_core_service)

        # Sample test data
        self.sample_destination = TripDestination(
            name="Paris",
            country="France",
            city="Paris",
            coordinates=Coordinates(latitude=48.8566, longitude=2.3522),
            duration_days=4,
        )

        self.sample_create_request = CreateTripRequest(
            title="European Adventure",
            description="A wonderful trip through Europe",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 15),
            destinations=[self.sample_destination],
        )

        self.sample_core_response = Mock()
        self.sample_core_response.id = str(self.test_trip_id)
        self.sample_core_response.user_id = self.test_user_id
        self.sample_core_response.title = "European Adventure"
        self.sample_core_response.description = "A wonderful trip through Europe"
        self.sample_core_response.start_date = date(2024, 6, 1)
        self.sample_core_response.end_date = date(2024, 6, 15)
        # Create destination that matches what adapter method expects (dict coordinates)
        mock_destination = Mock()
        mock_destination.name = "Paris"
        mock_destination.country = "France"
        mock_destination.city = "Paris"
        mock_destination.coordinates = {
            "lat": 48.8566,
            "lng": 2.3522,
        }  # Dict format expected by adapter

        self.sample_core_response.destinations = [mock_destination]
        self.sample_core_response.preferences = {}
        self.sample_core_response.status = "planning"
        self.sample_core_response.created_at = "2024-01-01T00:00:00Z"
        self.sample_core_response.updated_at = "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_create_trip_success(self):
        """Test successful trip creation through service layer."""
        # Arrange
        self.mock_core_service.create_trip = AsyncMock(
            return_value=self.sample_core_response
        )

        # Act
        result = await self.service.create_trip(
            self.test_user_id, self.sample_create_request
        )

        # Assert
        assert isinstance(result, TripResponse)
        assert result.title == "European Adventure"
        assert result.user_id == self.test_user_id
        assert len(result.destinations) == 1
        assert result.destinations[0].name == "Paris"
        assert result.status == "planning"

        # Verify core service was called correctly
        self.mock_core_service.create_trip.assert_called_once()
        call_args = self.mock_core_service.create_trip.call_args
        assert call_args[0][0] == self.test_user_id  # user_id
        assert call_args[0][1].title == "European Adventure"  # core request

    @pytest.mark.asyncio
    async def test_create_trip_service_error(self):
        """Test trip creation when core service raises an error."""
        # Arrange
        self.mock_core_service.create_trip = AsyncMock(
            side_effect=Exception("Core service error")
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await self.service.create_trip(
                self.test_user_id, self.sample_create_request
            )

        assert "Trip creation failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_trip_success(self):
        """Test successful trip retrieval."""
        # Arrange
        self.mock_core_service.get_trip = AsyncMock(
            return_value=self.sample_core_response
        )

        # Act
        result = await self.service.get_trip(self.test_user_id, self.test_trip_id)

        # Assert
        assert isinstance(result, TripResponse)
        assert result.title == "European Adventure"
        assert result.user_id == self.test_user_id

        # Verify core service was called correctly
        self.mock_core_service.get_trip.assert_called_once_with(
            self.test_user_id, str(self.test_trip_id)
        )

    @pytest.mark.asyncio
    async def test_get_trip_not_found(self):
        """Test trip retrieval when trip doesn't exist."""
        # Arrange
        self.mock_core_service.get_trip = AsyncMock(return_value=None)

        # Act
        result = await self.service.get_trip(self.test_user_id, self.test_trip_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_list_trips_success(self):
        """Test successful trip listing."""
        # Arrange
        self.mock_core_service.list_trips = AsyncMock(
            return_value=[self.sample_core_response]
        )

        # Act
        result = await self.service.list_trips(self.test_user_id, limit=10, offset=0)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TripResponse)
        assert result[0].title == "European Adventure"

        # Verify core service was called correctly
        self.mock_core_service.list_trips.assert_called_once_with(
            self.test_user_id, 10, 0
        )

    @pytest.mark.asyncio
    async def test_update_trip_success(self):
        """Test successful trip update."""
        # Arrange
        self.mock_core_service.update_trip = AsyncMock(
            return_value=self.sample_core_response
        )
        update_request = UpdateTripRequest(title="Updated Title")

        # Act
        result = await self.service.update_trip(
            self.test_user_id, self.test_trip_id, update_request
        )

        # Assert
        assert isinstance(result, TripResponse)
        assert result.title == "European Adventure"  # Mock returns original title

        # Verify core service was called correctly
        self.mock_core_service.update_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_trip_not_found(self):
        """Test trip update when trip doesn't exist."""
        # Arrange
        self.mock_core_service.update_trip = AsyncMock(return_value=None)
        update_request = UpdateTripRequest(title="Updated Title")

        # Act
        result = await self.service.update_trip(
            self.test_user_id, self.test_trip_id, update_request
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_trip_success(self):
        """Test successful trip deletion."""
        # Arrange
        self.mock_core_service.delete_trip = AsyncMock(return_value=True)

        # Act
        result = await self.service.delete_trip(self.test_user_id, self.test_trip_id)

        # Assert
        assert result is True

        # Verify core service was called correctly
        self.mock_core_service.delete_trip.assert_called_once_with(
            self.test_user_id, str(self.test_trip_id)
        )

    @pytest.mark.asyncio
    async def test_delete_trip_not_found(self):
        """Test trip deletion when trip doesn't exist."""
        # Arrange
        self.mock_core_service.delete_trip = AsyncMock(return_value=False)

        # Act
        result = await self.service.delete_trip(self.test_user_id, self.test_trip_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_search_trips_success(self):
        """Test successful trip search."""
        # Arrange
        self.mock_core_service.search_trips = AsyncMock(
            return_value=[self.sample_core_response]
        )

        # Act
        result = await self.service.search_trips(self.test_user_id, "Europe", limit=20)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TripResponse)

        # Verify core service was called correctly
        self.mock_core_service.search_trips.assert_called_once_with(
            self.test_user_id, "Europe", 20
        )

    @pytest.mark.asyncio
    async def test_get_trip_summary_success(self):
        """Test successful trip summary retrieval."""
        # Arrange
        # Mock the get_trip method to return our sample response
        self.service.get_trip = AsyncMock(
            return_value=TripResponse(
                id=str(self.test_trip_id),
                user_id=self.test_user_id,
                title="European Adventure",
                description="A wonderful trip through Europe",
                start_date=date(2024, 6, 1),
                end_date=date(2024, 6, 15),
                duration_days=14,
                destinations=[self.sample_destination],
                preferences={},
                status="planning",
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
        )

        # Act
        result = await self.service.get_trip_summary(
            self.test_user_id, self.test_trip_id
        )

        # Assert
        assert isinstance(result, dict)
        assert result["id"] == str(self.test_trip_id)
        assert result["title"] == "European Adventure"
        assert result["duration_days"] == 14
        assert "budget_summary" in result
        assert "completion_percentage" in result

    @pytest.mark.asyncio
    async def test_get_trip_summary_not_found(self):
        """Test trip summary when trip doesn't exist."""
        # Arrange
        self.service.get_trip = AsyncMock(return_value=None)

        # Act
        result = await self.service.get_trip_summary(
            self.test_user_id, self.test_trip_id
        )

        # Assert
        assert result is None

    def test_adapt_create_trip_request(self):
        """Test request adaptation to core model."""
        # Act
        core_request = self.service._adapt_create_trip_request(
            self.sample_create_request
        )

        # Assert
        assert core_request.title == "European Adventure"
        assert core_request.description == "A wonderful trip through Europe"
        assert len(core_request.destinations) == 1
        assert core_request.destinations[0].name == "Paris"
        assert core_request.destinations[0].coordinates["lat"] == 48.8566

    def test_adapt_trip_response(self):
        """Test response adaptation from core model."""
        # Act
        api_response = self.service._adapt_trip_response(self.sample_core_response)

        # Assert
        assert isinstance(api_response, TripResponse)
        assert api_response.title == "European Adventure"
        assert api_response.user_id == self.test_user_id
        assert len(api_response.destinations) == 1
        assert api_response.destinations[0].name == "Paris"


class TestTripServiceEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test data and mocks."""
        self.service = TripService()

    @pytest.mark.asyncio
    async def test_service_initialization_lazy_loading(self):
        """Test that core service is lazily loaded."""
        # Arrange - service without core service
        service = TripService(core_trip_service=None)

        # Mock the get_core_trip_service function
        with patch("tripsage.api.services.trip.get_core_trip_service") as mock_get_core:
            mock_core = Mock()
            mock_get_core.return_value = mock_core

            # Act - call _get_core_trip_service
            result = await service._get_core_trip_service()

            # Assert
            assert result == mock_core
            assert service.core_trip_service == mock_core
            mock_get_core.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_trip_success(self):
        """Test successful trip duplication."""
        # Arrange
        service = TripService()
        test_trip_id = uuid4()
        test_user_id = "test-user-123"

        # Mock the original trip with destinations (required by validation)
        original_trip = TripResponse(
            id=str(test_trip_id),
            user_id=test_user_id,
            title="Original Trip",
            description="Original description",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 15),
            duration_days=14,
            destinations=[
                TripDestination(
                    name="Rome",
                    country="Italy",
                    city="Rome",
                    coordinates=Coordinates(latitude=41.9028, longitude=12.4964),
                    duration_days=7,
                )
            ],
            preferences={},
            status="planning",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        duplicated_trip = TripResponse(
            id=str(uuid4()),
            user_id=test_user_id,
            title="Copy of Original Trip",
            description="Original description",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 15),
            duration_days=14,
            destinations=[
                TripDestination(
                    name="Rome",
                    country="Italy",
                    city="Rome",
                    coordinates=Coordinates(latitude=41.9028, longitude=12.4964),
                    duration_days=7,
                )
            ],
            preferences={},
            status="planning",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )

        # Mock methods
        service.get_trip = AsyncMock(return_value=original_trip)
        service.create_trip = AsyncMock(return_value=duplicated_trip)

        # Act
        result = await service.duplicate_trip(test_user_id, test_trip_id)

        # Assert
        assert result == duplicated_trip
        assert result.title == "Copy of Original Trip"
        service.get_trip.assert_called_once_with(test_user_id, test_trip_id)
        service.create_trip.assert_called_once()

    @pytest.mark.asyncio
    async def test_duplicate_trip_not_found(self):
        """Test trip duplication when original trip doesn't exist."""
        # Arrange
        service = TripService()
        service.get_trip = AsyncMock(return_value=None)

        # Act
        result = await service.duplicate_trip("user-123", uuid4())

        # Assert
        assert result is None
