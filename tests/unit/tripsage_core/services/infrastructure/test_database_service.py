"""
Comprehensive tests for Database Service methods (BJO-120 implementation).

This test suite covers the newly implemented user-specific database methods:
- Activity operations: save_activity_option, get_user_saved_activities, delete_saved_activity
- Search operations: save_user_search, get_user_recent_searches, delete_user_search

Tests follow ULTRATHINK principles:
- ≥90% coverage with actionable assertions
- Zero flaky tests with deterministic mocking  
- Real-world usage patterns and edge cases
- Modern pytest patterns with Pydantic 2.x
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.services.infrastructure.database_service import DatabaseService


class TestActivityDatabaseOperations:
    """Test activity-related database operations."""

    @pytest.fixture
    def database_service(self) -> DatabaseService:
        """Create database service with mocked connection."""
        service = DatabaseService()
        service._connected = True
        service._client = MagicMock()
        return service

    @pytest.fixture
    def sample_activity_option(self) -> Dict[str, Any]:
        """Create sample activity option data."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": "user123",
            "activity_id": "gmp_12345",
            "trip_id": "trip_abc123",
            "activity_data": {
                "id": "gmp_12345",
                "name": "Louvre Museum",
                "type": "museum",
                "location": "Paris, France",
                "price": 17.0,
                "rating": 4.8,
                "coordinates": {"lat": 48.8606, "lng": 2.3376},
            },
            "notes": "Must visit this famous museum",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

    async def test_save_activity_option_success(
        self,
        database_service: DatabaseService,
        sample_activity_option: Dict[str, Any],
    ):
        """Test successful saving of activity option."""
        # Mock the insert method
        with patch.object(database_service, 'insert', return_value=[sample_activity_option]) as mock_insert:
            result = await database_service.save_activity_option(sample_activity_option)

            # Verify result
            assert result == sample_activity_option
            assert result["user_id"] == "user123"
            assert result["activity_id"] == "gmp_12345"
            assert result["activity_data"]["name"] == "Louvre Museum"

            # Verify insert was called correctly
            mock_insert.assert_called_once_with("saved_activities", sample_activity_option)

    async def test_save_activity_option_database_error(
        self,
        database_service: DatabaseService,
        sample_activity_option: Dict[str, Any],
    ):
        """Test saving activity option when database error occurs."""
        with patch.object(database_service, 'insert', side_effect=CoreDatabaseError("Insert failed", code="INSERT_FAILED")):
            with pytest.raises(CoreDatabaseError) as exc_info:
                await database_service.save_activity_option(sample_activity_option)

            # Verify error details
            assert exc_info.value.code == "INSERT_FAILED"

    async def test_get_user_saved_activities_success(
        self,
        database_service: DatabaseService,
        sample_activity_option: Dict[str, Any],
    ):
        """Test successful retrieval of user's saved activities."""
        # Create multiple saved activities
        saved_activities = [
            sample_activity_option,
            {
                **sample_activity_option,
                "id": str(uuid.uuid4()),
                "activity_id": "gmp_67890",
                "trip_id": None,  # General saved activity
                "activity_data": {
                    "id": "gmp_67890",
                    "name": "Eiffel Tower",
                    "type": "landmark",
                    "location": "Paris, France",
                    "price": 29.4,
                    "rating": 4.6,
                },
                "notes": None,
            }
        ]

        with patch.object(database_service, 'select', return_value=saved_activities) as mock_select:
            result = await database_service.get_user_saved_activities("user123")

            # Verify result
            assert len(result) == 2
            assert result[0]["activity_id"] == "gmp_12345"
            assert result[0]["trip_id"] == "trip_abc123"
            assert result[1]["activity_id"] == "gmp_67890"
            assert result[1]["trip_id"] is None

            # Verify select was called correctly
            mock_select.assert_called_once_with(
                "saved_activities", 
                "*", 
                {"user_id": "user123"}, 
                order_by="-created_at"
            )

    async def test_get_user_saved_activities_with_trip_filter(
        self,
        database_service: DatabaseService,
        sample_activity_option: Dict[str, Any],
    ):
        """Test retrieving saved activities filtered by trip ID."""
        trip_activities = [sample_activity_option]

        with patch.object(database_service, 'select', return_value=trip_activities) as mock_select:
            result = await database_service.get_user_saved_activities("user123", "trip_abc123")

            # Verify result
            assert len(result) == 1
            assert result[0]["trip_id"] == "trip_abc123"

            # Verify select was called with trip filter
            mock_select.assert_called_once_with(
                "saved_activities", 
                "*", 
                {"user_id": "user123", "trip_id": "trip_abc123"}, 
                order_by="-created_at"
            )

    async def test_get_user_saved_activities_empty_result(
        self,
        database_service: DatabaseService,
    ):
        """Test retrieving saved activities when user has none."""
        with patch.object(database_service, 'select', return_value=[]) as mock_select:
            result = await database_service.get_user_saved_activities("user123")

            # Verify empty result
            assert isinstance(result, list)
            assert len(result) == 0

    async def test_delete_saved_activity_success(
        self,
        database_service: DatabaseService,
    ):
        """Test successful deletion of saved activity."""
        with patch.object(database_service, 'delete', return_value=[{"id": "deleted_id"}]) as mock_delete:
            result = await database_service.delete_saved_activity("user123", "gmp_12345")

            # Verify deletion success
            assert result is True

            # Verify delete was called correctly
            mock_delete.assert_called_once_with(
                "saved_activities", 
                {"user_id": "user123", "activity_id": "gmp_12345"}
            )

    async def test_delete_saved_activity_not_found(
        self,
        database_service: DatabaseService,
    ):
        """Test deletion when activity is not found."""
        with patch.object(database_service, 'delete', return_value=[]) as mock_delete:
            result = await database_service.delete_saved_activity("user123", "gmp_nonexistent")

            # Verify deletion failed
            assert result is False

    async def test_delete_saved_activity_database_error(
        self,
        database_service: DatabaseService,
    ):
        """Test deletion when database error occurs."""
        with patch.object(database_service, 'delete', side_effect=CoreDatabaseError("Delete failed", code="DELETE_FAILED")):
            with pytest.raises(CoreDatabaseError) as exc_info:
                await database_service.delete_saved_activity("user123", "gmp_12345")

            # Verify error details
            assert exc_info.value.code == "DELETE_FAILED"


class TestSearchDatabaseOperations:
    """Test search-related database operations."""

    @pytest.fixture
    def database_service(self) -> DatabaseService:
        """Create database service with mocked connection."""
        service = DatabaseService()
        service._connected = True
        service._client = MagicMock()
        return service

    @pytest.fixture
    def sample_user_search(self) -> Dict[str, Any]:
        """Create sample user search data."""
        return {
            "id": str(uuid.uuid4()),
            "user_id": "user123",
            "search_type": "unified",
            "query": "best restaurants in Rome",
            "search_params": {
                "query": "best restaurants in Rome",
                "destination": "Rome, Italy",
                "types": ["activity"],
                "adults": 2,
                "filters": {
                    "price_max": 100.0,
                    "rating_min": 4.5,
                }
            },
            "title": "Search: best restaurants in Rome",
            "description": "Unified search for 'best restaurants in Rome'",
            "metadata": {
                "types": ["activity"],
                "destination": "Rome, Italy",
                "has_filters": True,
            },
            "created_at": datetime.now().isoformat(),
        }

    async def test_save_user_search_success(
        self,
        database_service: DatabaseService,
        sample_user_search: Dict[str, Any],
    ):
        """Test successful saving of user search."""
        with patch.object(database_service, 'insert', return_value=[sample_user_search]) as mock_insert:
            result = await database_service.save_user_search(sample_user_search)

            # Verify result
            assert result == sample_user_search
            assert result["user_id"] == "user123"
            assert result["query"] == "best restaurants in Rome"
            assert result["search_type"] == "unified"
            assert result["metadata"]["destination"] == "Rome, Italy"

            # Verify insert was called correctly
            mock_insert.assert_called_once_with("user_searches", sample_user_search)

    async def test_save_user_search_database_error(
        self,
        database_service: DatabaseService,
        sample_user_search: Dict[str, Any],
    ):
        """Test saving user search when database error occurs."""
        with patch.object(database_service, 'insert', side_effect=CoreDatabaseError("Insert failed", code="INSERT_FAILED")):
            with pytest.raises(CoreDatabaseError) as exc_info:
                await database_service.save_user_search(sample_user_search)

            # Verify error details
            assert exc_info.value.code == "INSERT_FAILED"

    async def test_get_user_recent_searches_success(
        self,
        database_service: DatabaseService,
        sample_user_search: Dict[str, Any],
    ):
        """Test successful retrieval of user's recent searches."""
        # Create multiple recent searches
        recent_searches = [
            sample_user_search,
            {
                **sample_user_search,
                "id": str(uuid.uuid4()),
                "query": "hotels in Tokyo",
                "search_params": {
                    "query": "hotels in Tokyo",
                    "destination": "Tokyo, Japan",
                    "types": ["accommodation"],
                },
                "metadata": {
                    "destination": "Tokyo, Japan",
                    "has_filters": False,
                },
                "created_at": "2025-01-09T10:00:00Z",
            },
            {
                **sample_user_search,
                "id": str(uuid.uuid4()),
                "query": "flights to Barcelona",
                "search_params": {
                    "query": "flights to Barcelona",
                    "origin": "Paris, France",
                    "destination": "Barcelona, Spain",
                    "types": ["flight"],
                },
                "metadata": {
                    "destination": "Barcelona, Spain",
                    "has_filters": False,
                },
                "created_at": "2025-01-08T15:30:00Z",
            }
        ]

        with patch.object(database_service, 'select', return_value=recent_searches) as mock_select:
            result = await database_service.get_user_recent_searches("user123", limit=20)

            # Verify result
            assert len(result) == 3
            assert result[0]["query"] == "best restaurants in Rome"
            assert result[1]["query"] == "hotels in Tokyo"
            assert result[2]["query"] == "flights to Barcelona"

            # Verify ordering and metadata
            assert result[0]["metadata"]["has_filters"] is True
            assert result[1]["metadata"]["has_filters"] is False

            # Verify select was called correctly
            mock_select.assert_called_once_with(
                "user_searches",
                "*",
                {"user_id": "user123"},
                order_by="-created_at",
                limit=20,
            )

    async def test_get_user_recent_searches_with_custom_limit(
        self,
        database_service: DatabaseService,
        sample_user_search: Dict[str, Any],
    ):
        """Test retrieving recent searches with custom limit."""
        limited_searches = [sample_user_search]

        with patch.object(database_service, 'select', return_value=limited_searches) as mock_select:
            result = await database_service.get_user_recent_searches("user123", limit=1)

            # Verify limited result
            assert len(result) == 1
            assert result[0]["query"] == "best restaurants in Rome"

            # Verify limit was passed correctly
            mock_select.assert_called_once_with(
                "user_searches",
                "*",
                {"user_id": "user123"},
                order_by="-created_at",
                limit=1,
            )

    async def test_get_user_recent_searches_empty_result(
        self,
        database_service: DatabaseService,
    ):
        """Test retrieving recent searches when user has none."""
        with patch.object(database_service, 'select', return_value=[]):
            result = await database_service.get_user_recent_searches("user123")

            # Verify empty result
            assert isinstance(result, list)
            assert len(result) == 0

    async def test_delete_user_search_success(
        self,
        database_service: DatabaseService,
    ):
        """Test successful deletion of user search."""
        search_id = str(uuid.uuid4())
        
        with patch.object(database_service, 'delete', return_value=[{"id": search_id}]) as mock_delete:
            result = await database_service.delete_user_search("user123", search_id)

            # Verify deletion success
            assert result is True

            # Verify delete was called correctly
            mock_delete.assert_called_once_with(
                "user_searches", 
                {"user_id": "user123", "id": search_id}
            )

    async def test_delete_user_search_not_found(
        self,
        database_service: DatabaseService,
    ):
        """Test deletion when search is not found."""
        search_id = str(uuid.uuid4())
        
        with patch.object(database_service, 'delete', return_value=[]):
            result = await database_service.delete_user_search("user123", search_id)

            # Verify deletion failed
            assert result is False

    async def test_delete_user_search_database_error(
        self,
        database_service: DatabaseService,
    ):
        """Test deletion when database error occurs."""
        search_id = str(uuid.uuid4())
        
        with patch.object(database_service, 'delete', side_effect=CoreDatabaseError("Delete failed", code="DELETE_FAILED")):
            with pytest.raises(CoreDatabaseError) as exc_info:
                await database_service.delete_user_search("user123", search_id)

            # Verify error details
            assert exc_info.value.code == "DELETE_FAILED"


class TestDatabaseServiceIntegration:
    """Test database service integration scenarios."""

    @pytest.fixture
    def database_service(self) -> DatabaseService:
        """Create database service with mocked connection."""
        service = DatabaseService()
        service._connected = True
        service._client = MagicMock()
        return service

    async def test_concurrent_activity_operations(
        self,
        database_service: DatabaseService,
    ):
        """Test concurrent activity save/retrieve operations."""
        import asyncio
        
        # Mock data for concurrent operations
        activity_data = {
            "user_id": "user123",
            "activity_id": "gmp_concurrent",
            "trip_id": "trip_test",
        }
        
        with patch.object(database_service, 'insert', return_value=[activity_data]), \
             patch.object(database_service, 'select', return_value=[activity_data]), \
             patch.object(database_service, 'delete', return_value=[{"id": "deleted"}]):
            
            # Execute concurrent operations
            save_task = database_service.save_activity_option(activity_data)
            get_task = database_service.get_user_saved_activities("user123")
            delete_task = database_service.delete_saved_activity("user123", "gmp_old")

            results = await asyncio.gather(save_task, get_task, delete_task, return_exceptions=True)

            # Verify all operations succeeded
            for result in results:
                assert not isinstance(result, Exception)

            # Verify results
            assert results[0] == activity_data  # Save result
            assert isinstance(results[1], list)  # Get result
            assert isinstance(results[2], bool)  # Delete result

    async def test_user_data_isolation(
        self,
        database_service: DatabaseService,
    ):
        """Test that user data is properly isolated between users."""
        # Mock results for different users
        user1_activities = [
            {"user_id": "user1", "activity_id": "gmp_user1_activity"}
        ]
        user2_activities = [
            {"user_id": "user2", "activity_id": "gmp_user2_activity"}
        ]

        def mock_select_side_effect(table, columns, filters, **kwargs):
            if filters.get("user_id") == "user1":
                return user1_activities
            elif filters.get("user_id") == "user2":
                return user2_activities
            return []

        with patch.object(database_service, 'select', side_effect=mock_select_side_effect):
            # Get activities for both users
            user1_result = await database_service.get_user_saved_activities("user1")
            user2_result = await database_service.get_user_saved_activities("user2")

            # Verify data isolation
            assert len(user1_result) == 1
            assert len(user2_result) == 1
            assert user1_result[0]["user_id"] == "user1"
            assert user2_result[0]["user_id"] == "user2"
            assert user1_result[0]["activity_id"] != user2_result[0]["activity_id"]

    async def test_large_dataset_handling(
        self,
        database_service: DatabaseService,
    ):
        """Test handling of large search history datasets."""
        # Create large dataset of searches
        large_search_set = []
        for i in range(100):
            search_item = {
                "id": str(uuid.uuid4()),
                "user_id": "user123",
                "query": f"search query {i}",
                "created_at": f"2025-01-{(i % 30) + 1:02d}T12:00:00Z",
            }
            large_search_set.append(search_item)

        # Simulate limit behavior
        def mock_select_with_limit(table, columns, filters, order_by=None, limit=None, **kwargs):
            return large_search_set[:limit] if limit else large_search_set
        
        with patch.object(database_service, 'select', side_effect=mock_select_with_limit):
            result = await database_service.get_user_recent_searches("user123", limit=50)

            # Verify large dataset handling
            assert len(result) == 50
            assert all("search query" in item["query"] for item in result)

    async def test_database_connection_handling(
        self,
        database_service: DatabaseService,
    ):
        """Test proper database connection handling."""
        # Test disconnected service
        database_service._connected = False
        database_service._client = None

        with pytest.raises(Exception):  # Should raise connection error
            await database_service.save_activity_option({"test": "data"})

        # Test reconnection
        database_service._client = MagicMock()
        database_service._connected = True

        with patch.object(database_service, 'insert', return_value=[{"test": "data"}]):
            result = await database_service.save_activity_option({"test": "data"})
            assert result == {"test": "data"}

    async def test_json_serialization_edge_cases(
        self,
        database_service: DatabaseService,
    ):
        """Test handling of complex JSON data structures."""
        complex_search_data = {
            "user_id": "user123",
            "search_params": {
                "nested_filters": {
                    "price_range": {"min": 10.5, "max": 100.75},
                    "coordinates": [48.8566, 2.3522],
                    "amenities": ["wifi", "pool", "gym"],
                    "special_chars": "café résümé 日本語",
                },
                "unicode_query": "🏨 hotels in 東京 with 🏊‍♀️",
            },
            "metadata": {
                "null_field": None,
                "empty_array": [],
                "boolean_flags": [True, False, True],
            }
        }

        with patch.object(database_service, 'insert', return_value=[complex_search_data]):
            result = await database_service.save_user_search(complex_search_data)

            # Verify complex data handling
            assert result["search_params"]["unicode_query"] == "🏨 hotels in 東京 with 🏊‍♀️"
            assert result["search_params"]["nested_filters"]["special_chars"] == "café résümé 日本語"
            assert result["metadata"]["null_field"] is None
            assert result["metadata"]["empty_array"] == []
            assert result["metadata"]["boolean_flags"] == [True, False, True]