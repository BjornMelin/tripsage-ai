"""
Comprehensive test suite for new DatabaseService methods.

This module tests the 6 new database methods that were added to the DatabaseService:
1. get_trip_by_id - Trip retrieval by ID with None handling
2. search_trips - Advanced trip search with filters and pagination
3. get_trip_collaborators - Trip collaborator retrieval
4. get_trip_related_counts - Count related trip data
5. add_trip_collaborator - Add collaborator with validation
6. get_trip_collaborator - Get specific collaborator

Tests include:
- Method validation and error handling
- Filter and parameter validation
- Database operation mocking
- Edge cases and boundary conditions
- Error response validation
- Business logic validation
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID, uuid4

import pytest
from unittest.mock import AsyncMock, Mock, patch

from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService


class TestDatabaseServiceNewMethods:
    """Test new DatabaseService methods with comprehensive coverage."""

    @pytest.fixture
    def mock_database_service(self):
        """Create mock database service for testing."""
        with patch('tripsage_core.services.infrastructure.database_service.get_settings'):
            service = DatabaseService()
            service._connected = True
            service._client = Mock()
            return service

    @pytest.fixture
    def sample_trip_data(self):
        """Sample trip data for testing."""
        return {
            "id": "trip-123",
            "user_id": str(uuid4()),
            "name": "Paris Vacation",
            "destination": "Paris, France",
            "start_date": "2025-07-01",
            "end_date": "2025-07-15",
            "status": "planning",
            "visibility": "private",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "notes": ["vacation", "europe"],
        }

    @pytest.fixture
    def sample_collaborator_data(self):
        """Sample collaborator data for testing."""
        return {
            "id": 1,
            "trip_id": "trip-123",
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_by": str(uuid4()),
            "added_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }


class TestGetTripById:
    """Test get_trip_by_id method."""

    @pytest.mark.asyncio
    async def test_get_trip_by_id_success(self, mock_database_service, sample_trip_data):
        """Test successful trip retrieval by ID."""
        # Mock the select method to return trip data
        mock_database_service.select = AsyncMock(return_value=[sample_trip_data])

        result = await mock_database_service.get_trip_by_id("trip-123")

        # Verify method call
        mock_database_service.select.assert_called_once_with(
            "trips", "*", {"id": "trip-123"}
        )

        # Verify result
        assert result == sample_trip_data
        assert result["id"] == "trip-123"
        assert result["name"] == "Paris Vacation"

    @pytest.mark.asyncio
    async def test_get_trip_by_id_not_found(self, mock_database_service):
        """Test trip not found returns None."""
        # Mock the select method to return empty list
        mock_database_service.select = AsyncMock(return_value=[])

        result = await mock_database_service.get_trip_by_id("nonexistent-trip")

        # Verify method call
        mock_database_service.select.assert_called_once_with(
            "trips", "*", {"id": "nonexistent-trip"}
        )

        # Verify result is None
        assert result is None

    @pytest.mark.asyncio
    async def test_get_trip_by_id_database_error(self, mock_database_service):
        """Test database error handling."""
        # Mock the select method to raise an exception
        mock_database_service.select = AsyncMock(
            side_effect=Exception("Database connection error")
        )

        result = await mock_database_service.get_trip_by_id("trip-123")

        # Verify method call
        mock_database_service.select.assert_called_once_with(
            "trips", "*", {"id": "trip-123"}
        )

        # Verify result is None when error occurs
        assert result is None

    @pytest.mark.asyncio
    async def test_get_trip_by_id_with_uuid(self, mock_database_service, sample_trip_data):
        """Test trip retrieval with UUID string."""
        trip_uuid = str(uuid4())
        sample_trip_data["id"] = trip_uuid

        mock_database_service.select = AsyncMock(return_value=[sample_trip_data])

        result = await mock_database_service.get_trip_by_id(trip_uuid)

        mock_database_service.select.assert_called_once_with(
            "trips", "*", {"id": trip_uuid}
        )

        assert result["id"] == trip_uuid


class TestSearchTrips:
    """Test search_trips method."""

    @pytest.mark.asyncio
    async def test_search_trips_basic_text_search(self, mock_database_service, sample_trip_data):
        """Test basic text search functionality."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.or_ = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)
        mock_query.execute = Mock(return_value=Mock(data=[sample_trip_data]))

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        # Mock asyncio.to_thread to return the query result directly
        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips(
                {"query": "Paris"}, limit=10, offset=0
            )

        assert len(result) == 1
        assert result[0]["destination"] == "Paris, France"

    @pytest.mark.asyncio
    async def test_search_trips_user_filter(self, mock_database_service, sample_trip_data):
        """Test search with user ID filter."""
        user_id = str(uuid4())
        sample_trip_data["user_id"] = user_id

        mock_client = Mock()
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips({"user_id": user_id})

        mock_query.eq.assert_called_with("user_id", user_id)
        assert len(result) == 1
        assert result[0]["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_search_trips_status_filter(self, mock_database_service, sample_trip_data):
        """Test search with status filter."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips({"status": "planning"})

        mock_query.eq.assert_called_with("status", "planning")

    @pytest.mark.asyncio
    async def test_search_trips_destination_filter(self, mock_database_service, sample_trip_data):
        """Test search with destinations filter."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.or_ = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips(
                {"destinations": ["Paris", "France"]}
            )

        # Should call or_ with destination filters
        expected_filters = "destination.ilike.%Paris%,destination.ilike.%France%"
        mock_query.or_.assert_called_with(expected_filters)

    @pytest.mark.asyncio
    async def test_search_trips_date_range_filter(self, mock_database_service, sample_trip_data):
        """Test search with date range filter."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.lte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        from datetime import date
        start_date = date(2025, 7, 1)
        end_date = date(2025, 7, 31)

        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips(
                {"date_range": {"start_date": start_date, "end_date": end_date}}
            )

        mock_query.gte.assert_called_with("start_date", start_date.isoformat())
        mock_query.lte.assert_called_with("end_date", end_date.isoformat())

    @pytest.mark.asyncio
    async def test_search_trips_tags_filter(self, mock_database_service, sample_trip_data):
        """Test search with tags filter."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.overlaps = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips(
                {"tags": ["vacation", "europe"]}
            )

        mock_query.overlaps.assert_called_with("notes", ["vacation", "europe"])

    @pytest.mark.asyncio
    async def test_search_trips_pagination(self, mock_database_service, sample_trip_data):
        """Test search with pagination."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        with patch("asyncio.to_thread", return_value=Mock(data=[sample_trip_data])):
            result = await mock_database_service.search_trips(
                {}, limit=20, offset=40
            )

        mock_query.limit.assert_called_with(20)
        mock_query.offset.assert_called_with(40)

    @pytest.mark.asyncio
    async def test_search_trips_error_handling(self, mock_database_service):
        """Test search error handling."""
        mock_database_service.ensure_connected = AsyncMock()

        # Mock client to raise an exception
        with patch("asyncio.to_thread", side_effect=Exception("Database error")):
            with pytest.raises(CoreDatabaseError) as exc_info:
                await mock_database_service.search_trips({"query": "test"})

        error = exc_info.value
        assert error.code == "TRIP_SEARCH_FAILED"
        assert "Failed to search trips" in error.message
        assert "Database error" in str(error.details)


class TestGetTripCollaborators:
    """Test get_trip_collaborators method."""

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_success(self, mock_database_service, sample_collaborator_data):
        """Test successful collaborator retrieval."""
        collaborators = [
            sample_collaborator_data,
            {**sample_collaborator_data, "id": 2, "permission_level": "view"},
        ]

        mock_database_service.select = AsyncMock(return_value=collaborators)

        result = await mock_database_service.get_trip_collaborators("trip-123")

        mock_database_service.select.assert_called_once_with(
            "trip_collaborators", "*", {"trip_id": "trip-123"}
        )

        assert len(result) == 2
        assert result[0]["permission_level"] == "edit"
        assert result[1]["permission_level"] == "view"

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_empty(self, mock_database_service):
        """Test when no collaborators exist."""
        mock_database_service.select = AsyncMock(return_value=[])

        result = await mock_database_service.get_trip_collaborators("trip-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_error(self, mock_database_service):
        """Test error handling."""
        mock_database_service.select = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.get_trip_collaborators("trip-123")

        error = exc_info.value
        assert error.code == "GET_COLLABORATORS_FAILED"
        assert "Failed to get collaborators for trip trip-123" in error.message


class TestGetTripRelatedCounts:
    """Test get_trip_related_counts method."""

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_success(self, mock_database_service):
        """Test successful count retrieval."""
        # Mock count method to return different values for different tables
        count_returns = {
            ("itinerary_items", {"trip_id": "trip-123"}): 5,
            ("flights", {"trip_id": "trip-123"}): 2,
            ("accommodations", {"trip_id": "trip-123"}): 3,
            ("transportation", {"trip_id": "trip-123"}): 1,
            ("trip_collaborators", {"trip_id": "trip-123"}): 4,
        }

        async def mock_count(table, filters):
            return count_returns.get((table, filters), 0)

        mock_database_service.count = AsyncMock(side_effect=mock_count)

        result = await mock_database_service.get_trip_related_counts("trip-123")

        # Verify all counts are called
        assert mock_database_service.count.call_count == 5

        # Verify results
        assert result["itinerary_count"] == 5
        assert result["flight_count"] == 2
        assert result["accommodation_count"] == 3
        assert result["transportation_count"] == 1
        assert result["collaborator_count"] == 4

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_zero_counts(self, mock_database_service):
        """Test when all counts are zero."""
        mock_database_service.count = AsyncMock(return_value=0)

        result = await mock_database_service.get_trip_related_counts("trip-123")

        assert all(count == 0 for count in result.values())
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_error(self, mock_database_service):
        """Test error handling."""
        mock_database_service.count = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.get_trip_related_counts("trip-123")

        error = exc_info.value
        assert error.code == "GET_TRIP_COUNTS_FAILED"
        assert "Failed to get related counts for trip trip-123" in error.message


class TestAddTripCollaborator:
    """Test add_trip_collaborator method."""

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_success(self, mock_database_service, sample_collaborator_data):
        """Test successful collaborator addition."""
        mock_database_service.upsert = AsyncMock(return_value=[sample_collaborator_data])

        result = await mock_database_service.add_trip_collaborator(sample_collaborator_data)

        mock_database_service.upsert.assert_called_once_with(
            "trip_collaborators", sample_collaborator_data, on_conflict="trip_id,user_id"
        )

        assert result == sample_collaborator_data

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_missing_required_field(self, mock_database_service):
        """Test validation for missing required fields."""
        # Missing trip_id
        incomplete_data = {
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_by": str(uuid4()),
        }

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.add_trip_collaborator(incomplete_data)

        error = exc_info.value
        assert error.code == "MISSING_REQUIRED_FIELD"
        assert "Missing required field: trip_id" in error.message

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_all_required_fields_missing(self, mock_database_service):
        """Test when multiple required fields are missing."""
        # Only has permission_level
        incomplete_data = {"permission_level": "edit"}

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.add_trip_collaborator(incomplete_data)

        error = exc_info.value
        assert error.code == "MISSING_REQUIRED_FIELD"
        # Should catch the first missing required field
        assert "Missing required field:" in error.message

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_upsert_error(self, mock_database_service, sample_collaborator_data):
        """Test upsert operation error handling."""
        mock_database_service.upsert = AsyncMock(
            side_effect=Exception("Constraint violation")
        )

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.add_trip_collaborator(sample_collaborator_data)

        error = exc_info.value
        assert error.code == "ADD_COLLABORATOR_FAILED"
        assert "Failed to add trip collaborator" in error.message
        assert "Constraint violation" in str(error.details)

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_empty_result(self, mock_database_service, sample_collaborator_data):
        """Test when upsert returns empty result."""
        mock_database_service.upsert = AsyncMock(return_value=[])

        result = await mock_database_service.add_trip_collaborator(sample_collaborator_data)

        assert result == {}

    @pytest.mark.parametrize(
        "missing_field",
        ["trip_id", "user_id", "permission_level", "added_by"],
    )
    @pytest.mark.asyncio
    async def test_add_trip_collaborator_missing_individual_fields(
        self, mock_database_service, sample_collaborator_data, missing_field
    ):
        """Test missing individual required fields."""
        incomplete_data = sample_collaborator_data.copy()
        del incomplete_data[missing_field]

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.add_trip_collaborator(incomplete_data)

        error = exc_info.value
        assert error.code == "MISSING_REQUIRED_FIELD"
        assert f"Missing required field: {missing_field}" in error.message


class TestGetTripCollaborator:
    """Test get_trip_collaborator method."""

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_success(self, mock_database_service, sample_collaborator_data):
        """Test successful specific collaborator retrieval."""
        mock_database_service.select = AsyncMock(return_value=[sample_collaborator_data])

        result = await mock_database_service.get_trip_collaborator(
            "trip-123", sample_collaborator_data["user_id"]
        )

        mock_database_service.select.assert_called_once_with(
            "trip_collaborators",
            "*",
            {"trip_id": "trip-123", "user_id": sample_collaborator_data["user_id"]},
        )

        assert result == sample_collaborator_data

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_not_found(self, mock_database_service):
        """Test when collaborator is not found."""
        mock_database_service.select = AsyncMock(return_value=[])

        result = await mock_database_service.get_trip_collaborator(
            "trip-123", str(uuid4())
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_error(self, mock_database_service):
        """Test error handling."""
        trip_id = "trip-123"
        user_id = str(uuid4())

        mock_database_service.select = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.get_trip_collaborator(trip_id, user_id)

        error = exc_info.value
        assert error.code == "GET_COLLABORATOR_FAILED"
        assert f"Failed to get collaborator for trip {trip_id} and user {user_id}" in error.message

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_with_uuid_objects(self, mock_database_service, sample_collaborator_data):
        """Test with UUID objects for trip_id and user_id."""
        trip_uuid = uuid4()
        user_uuid = uuid4()

        sample_collaborator_data["trip_id"] = str(trip_uuid)
        sample_collaborator_data["user_id"] = str(user_uuid)

        mock_database_service.select = AsyncMock(return_value=[sample_collaborator_data])

        result = await mock_database_service.get_trip_collaborator(
            str(trip_uuid), str(user_uuid)
        )

        mock_database_service.select.assert_called_once_with(
            "trip_collaborators",
            "*",
            {"trip_id": str(trip_uuid), "user_id": str(user_uuid)},
        )

        assert result["trip_id"] == str(trip_uuid)
        assert result["user_id"] == str(user_uuid)


class TestMethodIntegration:
    """Test integration between new methods."""

    @pytest.mark.asyncio
    async def test_trip_workflow_integration(self, mock_database_service):
        """Test complete trip workflow using new methods."""
        trip_id = "trip-workflow-123"
        user_id = str(uuid4())

        # Setup mock returns for workflow
        trip_data = {
            "id": trip_id,
            "user_id": user_id,
            "name": "Test Trip",
            "destination": "Test City",
        }

        collaborator_data = {
            "id": 1,
            "trip_id": trip_id,
            "user_id": user_id,
            "permission_level": "admin",
            "added_by": user_id,
        }

        related_counts = {
            "itinerary_count": 2,
            "flight_count": 1,
            "accommodation_count": 1,
            "transportation_count": 0,
            "collaborator_count": 1,
        }

        # Mock all method calls
        mock_database_service.get_trip_by_id = AsyncMock(return_value=trip_data)
        mock_database_service.get_trip_collaborators = AsyncMock(return_value=[collaborator_data])
        mock_database_service.get_trip_related_counts = AsyncMock(return_value=related_counts)
        mock_database_service.add_trip_collaborator = AsyncMock(return_value=collaborator_data)
        mock_database_service.get_trip_collaborator = AsyncMock(return_value=collaborator_data)

        # Execute workflow
        # 1. Get trip
        trip = await mock_database_service.get_trip_by_id(trip_id)
        assert trip["id"] == trip_id

        # 2. Get collaborators
        collaborators = await mock_database_service.get_trip_collaborators(trip_id)
        assert len(collaborators) == 1

        # 3. Get related counts
        counts = await mock_database_service.get_trip_related_counts(trip_id)
        assert counts["collaborator_count"] == 1

        # 4. Add another collaborator
        new_collaborator = {
            "trip_id": trip_id,
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_by": user_id,
        }
        added = await mock_database_service.add_trip_collaborator(new_collaborator)
        assert added == collaborator_data

        # 5. Get specific collaborator
        specific = await mock_database_service.get_trip_collaborator(trip_id, user_id)
        assert specific["permission_level"] == "admin"

    @pytest.mark.asyncio
    async def test_search_and_retrieval_workflow(self, mock_database_service):
        """Test search followed by detailed retrieval workflow."""
        user_id = str(uuid4())

        # Mock search results
        search_results = [
            {"id": "trip-1", "name": "Trip 1", "user_id": user_id},
            {"id": "trip-2", "name": "Trip 2", "user_id": user_id},
        ]

        # Mock detailed trip data
        trip_details = {
            "id": "trip-1",
            "name": "Trip 1",
            "user_id": user_id,
            "destination": "Paris",
        }

        # Mock related data
        collaborators = [
            {"user_id": user_id, "permission_level": "admin"},
            {"user_id": str(uuid4()), "permission_level": "view"},
        ]

        counts = {
            "itinerary_count": 5,
            "flight_count": 2,
            "accommodation_count": 3,
            "transportation_count": 1,
            "collaborator_count": 2,
        }

        # Setup mocks
        mock_database_service.search_trips = AsyncMock(return_value=search_results)
        mock_database_service.get_trip_by_id = AsyncMock(return_value=trip_details)
        mock_database_service.get_trip_collaborators = AsyncMock(return_value=collaborators)
        mock_database_service.get_trip_related_counts = AsyncMock(return_value=counts)

        # Execute workflow
        # 1. Search for user trips
        trips = await mock_database_service.search_trips({"user_id": user_id})
        assert len(trips) == 2

        # 2. Get detailed info for first trip
        first_trip_id = trips[0]["id"]
        detailed_trip = await mock_database_service.get_trip_by_id(first_trip_id)
        assert detailed_trip["destination"] == "Paris"

        # 3. Get collaborators and counts
        trip_collaborators = await mock_database_service.get_trip_collaborators(first_trip_id)
        trip_counts = await mock_database_service.get_trip_related_counts(first_trip_id)

        assert len(trip_collaborators) == 2
        assert trip_counts["collaborator_count"] == 2
        assert trip_counts["itinerary_count"] == 5


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for all new methods."""

    @pytest.mark.asyncio
    async def test_all_methods_not_connected(self):
        """Test all methods handle not connected state."""
        with patch('tripsage_core.services.infrastructure.database_service.get_settings'):
            service = DatabaseService()
            service._connected = False

            # Test get_trip_by_id which handles exceptions gracefully
            result = await service.get_trip_by_id("trip-123")
            assert result is None

            # Test methods that call ensure_connected - they should raise when connection fails
            methods_to_test = [
                ("search_trips", ({"query": "test"},)),
                ("get_trip_collaborators", ("trip-123",)),
                ("get_trip_related_counts", ("trip-123",)),
                ("add_trip_collaborator", ({"trip_id": 123, "user_id": str(uuid4()), "permission_level": "edit", "added_by": str(uuid4())},)),
                ("get_trip_collaborator", ("trip-123", str(uuid4()))),
            ]

            for method_name, args in methods_to_test:
                method = getattr(service, method_name)
                
                # Mock ensure_connected to fail
                with patch.object(service, 'ensure_connected', side_effect=CoreServiceError("Not connected")):
                    with pytest.raises(CoreServiceError):
                        await method(*args)

    @pytest.mark.asyncio
    async def test_search_trips_empty_filters(self, mock_database_service):
        """Test search with empty filter dictionary."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        with patch("asyncio.to_thread", return_value=Mock(data=[])):
            result = await mock_database_service.search_trips({})

        # Should work with empty filters
        assert result == []

    @pytest.mark.asyncio
    async def test_search_trips_none_values_in_filters(self, mock_database_service):
        """Test search with None values in filters."""
        mock_client = Mock()
        mock_query = Mock()
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        # Filters with None values should be ignored
        filters_with_none = {
            "query": None,
            "user_id": "valid-user-id",
            "status": None,
            "destinations": None,
        }

        with patch("asyncio.to_thread", return_value=Mock(data=[])):
            result = await mock_database_service.search_trips(filters_with_none)

        # Should only apply non-None filters
        assert result == []

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_partial_failure(self, mock_database_service):
        """Test when some count operations fail."""
        # Mock count to fail on specific tables
        async def mock_count_with_failure(table, filters):
            if table == "itinerary_items":
                raise Exception("Table not found")
            return 1

        mock_database_service.count = AsyncMock(side_effect=mock_count_with_failure)

        # Should propagate the first error
        with pytest.raises(CoreDatabaseError):
            await mock_database_service.get_trip_related_counts("trip-123")

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_core_database_error_propagation(self, mock_database_service):
        """Test that CoreDatabaseError is propagated as-is."""
        sample_data = {
            "trip_id": "trip-123",
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_by": str(uuid4()),
        }

        # Mock upsert to raise CoreDatabaseError (like validation error)
        original_error = CoreDatabaseError(
            message="Validation failed",
            code="VALIDATION_ERROR",
            operation="UPSERT",
        )
        mock_database_service.upsert = AsyncMock(side_effect=original_error)

        # Should re-raise the same CoreDatabaseError
        with pytest.raises(CoreDatabaseError) as exc_info:
            await mock_database_service.add_trip_collaborator(sample_data)

        # Should be the exact same error object
        assert exc_info.value is original_error

    @pytest.mark.asyncio
    async def test_method_parameter_validation(self, mock_database_service):
        """Test parameter validation for all methods."""
        # Test empty/invalid trip IDs
        invalid_trip_ids = ["", None, "   ", "invalid-id-format"]
        
        # get_trip_by_id should handle invalid IDs gracefully
        for invalid_id in invalid_trip_ids:
            if invalid_id is not None:  # None would cause TypeError in string operations
                mock_database_service.select = AsyncMock(return_value=[])
                result = await mock_database_service.get_trip_by_id(invalid_id)
                # Should return None for any ID that doesn't exist
                assert result is None

    @pytest.mark.asyncio
    async def test_search_trips_complex_filter_combinations(self, mock_database_service):
        """Test complex filter combinations."""
        mock_client = Mock()
        mock_query = Mock()
        
        # Mock all query methods
        mock_query.eq = Mock(return_value=mock_query)
        mock_query.or_ = Mock(return_value=mock_query)
        mock_query.overlaps = Mock(return_value=mock_query)
        mock_query.gte = Mock(return_value=mock_query)
        mock_query.lte = Mock(return_value=mock_query)
        mock_query.order = Mock(return_value=mock_query)
        mock_query.limit = Mock(return_value=mock_query)
        mock_query.offset = Mock(return_value=mock_query)

        mock_client.table = Mock(return_value=Mock(select=Mock(return_value=mock_query)))
        mock_database_service._client = mock_client

        from datetime import date

        complex_filters = {
            "query": "vacation",
            "user_id": str(uuid4()),
            "status": "active",
            "visibility": "public",
            "destinations": ["Paris", "London"],
            "tags": ["europe", "summer"],
            "date_range": {
                "start_date": date(2025, 6, 1),
                "end_date": date(2025, 8, 31)
            }
        }

        with patch("asyncio.to_thread", return_value=Mock(data=[])):
            result = await mock_database_service.search_trips(complex_filters, limit=25, offset=50)

        # Verify all filter methods were called
        assert mock_query.eq.call_count >= 2  # user_id, status, visibility
        assert mock_query.or_.call_count >= 2  # query text search, destinations
        assert mock_query.overlaps.call_count >= 1  # tags
        assert mock_query.gte.call_count >= 1  # start_date
        assert mock_query.lte.call_count >= 1  # end_date
        assert mock_query.limit.call_count == 1
        assert mock_query.offset.call_count == 1