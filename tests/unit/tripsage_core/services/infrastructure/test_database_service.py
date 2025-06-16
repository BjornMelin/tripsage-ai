"""
Comprehensive tests for TripSage Core Database Service.

This module provides comprehensive test coverage for database service functionality
including connection management, CRUD operations, transaction support, vector
operations, health monitoring, and error handling scenarios.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    get_database_service,
)


class TestDatabaseService:
    """Comprehensive test suite for DatabaseService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.database = Mock()
        settings.database.supabase_url = "https://test.supabase.co"
        settings.database.supabase_anon_key = Mock(
            get_secret_value=Mock(return_value="test_key_1234567890123456789012")
        )
        settings.database.supabase_auto_refresh_token = True
        settings.database.supabase_persist_session = True
        settings.database.supabase_timeout = 10
        return settings

    @pytest.fixture
    def mock_supabase_client(self):
        """Create a comprehensive mock Supabase client."""
        client = MagicMock()

        # Setup chain-able API methods
        client.table.return_value = client
        client.select.return_value = client
        client.insert.return_value = client
        client.update.return_value = client
        client.upsert.return_value = client
        client.delete.return_value = client
        client.eq.return_value = client
        client.neq.return_value = client
        client.gt.return_value = client
        client.gte.return_value = client
        client.lt.return_value = client
        client.lte.return_value = client
        client.like.return_value = client
        client.ilike.return_value = client
        client.in_.return_value = client
        client.is_.return_value = client
        client.order.return_value = client
        client.limit.return_value = client
        client.offset.return_value = client
        client.single.return_value = client
        client.on_conflict.return_value = client
        client.rpc.return_value = client

        # Default successful execution
        client.execute.return_value = Mock(data=[{"id": "test-id"}], count=1)

        return client

    @pytest.fixture
    def database_service(self, mock_settings, mock_supabase_client):
        """Create a DatabaseService instance with mocked dependencies."""
        mock_options = Mock()
        with (
            patch(
                "tripsage_core.services.infrastructure.database_service.ClientOptions",
                return_value=mock_options,
            ),
            patch(
                "tripsage_core.services.infrastructure.database_service.create_client",
                return_value=mock_supabase_client,
            ),
            patch(
                "tripsage_core.services.infrastructure.database_service.asyncio.to_thread",
                side_effect=lambda func: asyncio.create_task(
                    asyncio.coroutine(lambda: func())()
                ),
            ),
        ):
            service = DatabaseService(settings=mock_settings)
            service._client = mock_supabase_client
            service._connected = True
            return service

    # Connection Management Tests

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_settings, mock_supabase_client):
        """Test successful database connection."""
        mock_options = Mock()
        with (
            patch(
                "tripsage_core.services.infrastructure.database_service.ClientOptions",
                return_value=mock_options,
            ),
            patch(
                "tripsage_core.services.infrastructure.database_service.create_client",
                return_value=mock_supabase_client,
            ),
            patch(
                "tripsage_core.services.infrastructure.database_service.asyncio.to_thread",
                side_effect=lambda func: asyncio.create_task(
                    asyncio.coroutine(lambda: func())()
                ),
            ),
        ):
            service = DatabaseService(settings=mock_settings)

            await service.connect()

            assert service.is_connected
            assert service._client is not None

    @pytest.mark.asyncio
    async def test_connect_invalid_url(self, mock_settings):
        """Test connection with invalid URL."""
        mock_settings.database.supabase_url = "invalid-url"
        service = DatabaseService(settings=mock_settings)

        with pytest.raises(CoreDatabaseError, match="Invalid Supabase URL format"):
            await service.connect()

    @pytest.mark.asyncio
    async def test_connect_invalid_key(self, mock_settings):
        """Test connection with invalid API key."""
        mock_settings.database.supabase_anon_key.get_secret_value.return_value = "short"
        service = DatabaseService(settings=mock_settings)

        with pytest.raises(CoreDatabaseError, match="Invalid Supabase API key"):
            await service.connect()

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, database_service):
        """Test connecting when already connected."""
        initial_client = database_service._client

        await database_service.connect()

        # Should not change the client
        assert database_service._client is initial_client

    @pytest.mark.asyncio
    async def test_close_connection(self, database_service):
        """Test closing database connection."""
        await database_service.close()

        assert not database_service.is_connected
        assert database_service._client is None

    @pytest.mark.asyncio
    async def test_ensure_connected_when_not_connected(self, database_service):
        """Test ensure_connected when not connected."""
        database_service._connected = False

        with patch.object(
            database_service, "connect", new_callable=AsyncMock
        ) as mock_connect:
            await database_service.ensure_connected()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_property_when_not_connected(self, mock_settings):
        """Test accessing client property when not connected."""
        service = DatabaseService(settings=mock_settings)

        with pytest.raises(CoreServiceError, match="Database service not connected"):
            _ = service.client

    # Core CRUD Operations Tests

    @pytest.mark.asyncio
    async def test_insert_single_record(self, database_service, mock_supabase_client):
        """Test inserting a single record."""
        test_data = {"name": "Test Item", "value": 123}
        expected_result = [{"id": "new-id", **test_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.insert("test_table", test_data)

        assert result == expected_result
        mock_supabase_client.table.assert_called_with("test_table")
        mock_supabase_client.insert.assert_called_with(test_data)

    @pytest.mark.asyncio
    async def test_insert_multiple_records(
        self, database_service, mock_supabase_client
    ):
        """Test inserting multiple records."""
        test_data = [
            {"name": "Item 1", "value": 123},
            {"name": "Item 2", "value": 456},
        ]
        expected_result = [
            {"id": "id1", **test_data[0]},
            {"id": "id2", **test_data[1]},
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.insert("test_table", test_data)

        assert result == expected_result
        mock_supabase_client.insert.assert_called_with(test_data)

    @pytest.mark.asyncio
    async def test_select_basic(self, database_service, mock_supabase_client):
        """Test basic select operation."""
        expected_data = [{"id": "1", "name": "Test"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        result = await database_service.select("test_table")

        assert result == expected_data
        mock_supabase_client.table.assert_called_with("test_table")
        mock_supabase_client.select.assert_called_with("*")

    @pytest.mark.asyncio
    async def test_select_with_columns(self, database_service, mock_supabase_client):
        """Test select with specific columns."""
        expected_data = [{"name": "Test"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        result = await database_service.select("test_table", columns="name,value")

        assert result == expected_data
        mock_supabase_client.select.assert_called_with("name,value")

    @pytest.mark.asyncio
    async def test_select_with_filters(self, database_service, mock_supabase_client):
        """Test select with various filter types."""
        expected_data = [{"id": "1", "status": "active"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        # Test simple equality filter
        result = await database_service.select(
            "test_table", filters={"status": "active"}
        )

        assert result == expected_data
        mock_supabase_client.eq.assert_called_with("status", "active")

    @pytest.mark.asyncio
    async def test_select_with_complex_filters(
        self, database_service, mock_supabase_client
    ):
        """Test select with complex filters."""
        expected_data = [{"id": "1", "age": 25}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        # Test complex filters
        result = await database_service.select(
            "test_table", filters={"age": {"gte": 18, "lt": 65}, "status": "active"}
        )

        assert result == expected_data
        # Check that complex operators were called
        mock_supabase_client.gte.assert_called_with("age", 18)
        mock_supabase_client.lt.assert_called_with("age", 65)
        mock_supabase_client.eq.assert_called_with("status", "active")

    @pytest.mark.asyncio
    async def test_select_with_ordering(self, database_service, mock_supabase_client):
        """Test select with ordering."""
        expected_data = [{"id": "1"}, {"id": "2"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        # Test ascending order
        await database_service.select("test_table", order_by="created_at")
        mock_supabase_client.order.assert_called_with("created_at")

        # Test descending order
        await database_service.select("test_table", order_by="-created_at")
        mock_supabase_client.order.assert_called_with("created_at", desc=True)

    @pytest.mark.asyncio
    async def test_select_with_pagination(self, database_service, mock_supabase_client):
        """Test select with pagination."""
        expected_data = [{"id": "1"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        result = await database_service.select("test_table", limit=10, offset=20)

        assert result == expected_data
        mock_supabase_client.limit.assert_called_with(10)
        mock_supabase_client.offset.assert_called_with(20)

    @pytest.mark.asyncio
    async def test_update_success(self, database_service, mock_supabase_client):
        """Test successful record update."""
        updates = {"name": "Updated Name"}
        expected_result = [{"id": "test-id", **updates}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.update(
            "test_table", updates, filters={"id": "test-id"}
        )

        assert result == expected_result
        mock_supabase_client.update.assert_called_with(updates)
        mock_supabase_client.eq.assert_called_with("id", "test-id")

    @pytest.mark.asyncio
    async def test_upsert_success(self, database_service, mock_supabase_client):
        """Test successful upsert operation."""
        data = {"email": "test@example.com", "name": "Test User"}
        expected_result = [{"id": "test-id", **data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.upsert("users", data, on_conflict="email")

        assert result == expected_result
        mock_supabase_client.upsert.assert_called_with(data)
        mock_supabase_client.on_conflict.assert_called_with("email")

    @pytest.mark.asyncio
    async def test_delete_success(self, database_service, mock_supabase_client):
        """Test successful record deletion."""
        deleted_data = [{"id": "test-id"}]
        mock_supabase_client.execute.return_value = Mock(data=deleted_data)

        result = await database_service.delete("test_table", filters={"id": "test-id"})

        assert result == deleted_data
        mock_supabase_client.delete.assert_called_once()
        mock_supabase_client.eq.assert_called_with("id", "test-id")

    @pytest.mark.asyncio
    async def test_count_success(self, database_service, mock_supabase_client):
        """Test successful count operation."""
        mock_supabase_client.execute.return_value = Mock(count=5)

        result = await database_service.count(
            "test_table", filters={"status": "active"}
        )

        assert result == 5
        mock_supabase_client.select.assert_called_with("*", count="exact")
        mock_supabase_client.eq.assert_called_with("status", "active")

    # High-level Business Operations Tests

    @pytest.mark.asyncio
    async def test_create_trip_success(self, database_service, mock_supabase_client):
        """Test successful trip creation."""
        trip_data = {
            "user_id": str(uuid4()),
            "title": "Europe Trip",
            "destination": "Paris",
            "start_date": datetime.now(timezone.utc).isoformat(),
        }
        expected_result = [{"id": str(uuid4()), **trip_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.create_trip(trip_data)

        assert result == expected_result[0]
        mock_supabase_client.table.assert_called_with("trips")
        mock_supabase_client.insert.assert_called_with(trip_data)

    @pytest.mark.asyncio
    async def test_get_trip_success(self, database_service, mock_supabase_client):
        """Test successful trip retrieval."""
        trip_id = str(uuid4())
        expected_trip = {"id": trip_id, "title": "My Trip"}
        mock_supabase_client.execute.return_value = Mock(data=[expected_trip])

        result = await database_service.get_trip(trip_id)

        assert result == expected_trip
        mock_supabase_client.eq.assert_called_with("id", trip_id)

    @pytest.mark.asyncio
    async def test_get_trip_not_found(self, database_service, mock_supabase_client):
        """Test trip retrieval when trip doesn't exist."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[])

        with pytest.raises(CoreResourceNotFoundError, match="Trip .* not found"):
            await database_service.get_trip(trip_id)

    @pytest.mark.asyncio
    async def test_update_trip_success(self, database_service, mock_supabase_client):
        """Test successful trip update."""
        trip_id = str(uuid4())
        updates = {"title": "Updated Trip"}
        expected_result = [{"id": trip_id, **updates}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.update_trip(trip_id, updates)

        assert result == expected_result[0]
        mock_supabase_client.table.assert_called_with("trips")
        mock_supabase_client.update.assert_called_with(updates)

    @pytest.mark.asyncio
    async def test_update_trip_not_found(self, database_service, mock_supabase_client):
        """Test trip update when trip doesn't exist."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[])

        with pytest.raises(CoreResourceNotFoundError, match="Trip .* not found"):
            await database_service.update_trip(trip_id, {"title": "Updated"})

    @pytest.mark.asyncio
    async def test_delete_trip_success(self, database_service, mock_supabase_client):
        """Test successful trip deletion."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[{"id": trip_id}])

        result = await database_service.delete_trip(trip_id)

        assert result is True
        mock_supabase_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_trip_not_found(self, database_service, mock_supabase_client):
        """Test trip deletion when trip doesn't exist."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[])

        result = await database_service.delete_trip(trip_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_create_user_success(self, database_service, mock_supabase_client):
        """Test successful user creation."""
        user_data = {
            "email": "test@example.com",
            "full_name": "Test User",
            "username": "testuser",
        }
        expected_result = [{"id": str(uuid4()), **user_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.create_user(user_data)

        assert result == expected_result[0]
        mock_supabase_client.table.assert_called_with("users")

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful user retrieval by email."""
        email = "test@example.com"
        expected_user = {"id": str(uuid4()), "email": email}
        mock_supabase_client.execute.return_value = Mock(data=[expected_user])

        result = await database_service.get_user_by_email(email)

        assert result == expected_user
        mock_supabase_client.eq.assert_called_with("email", email)

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(
        self, database_service, mock_supabase_client
    ):
        """Test user retrieval by email when user doesn't exist."""
        email = "nonexistent@example.com"
        mock_supabase_client.execute.return_value = Mock(data=[])

        result = await database_service.get_user_by_email(email)

        assert result is None

    # Chat Operations Tests

    @pytest.mark.asyncio
    async def test_create_chat_session_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful chat session creation."""
        session_data = {
            "user_id": str(uuid4()),
            "title": "Travel Planning",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        expected_result = [{"id": str(uuid4()), **session_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.create_chat_session(session_data)

        assert result == expected_result[0]
        mock_supabase_client.table.assert_called_with("chat_sessions")

    @pytest.mark.asyncio
    async def test_save_chat_message_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful chat message save."""
        message_data = {
            "session_id": str(uuid4()),
            "role": "user",
            "content": "Hello",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        expected_result = [{"id": str(uuid4()), **message_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.save_chat_message(message_data)

        assert result == expected_result[0]
        mock_supabase_client.table.assert_called_with("chat_messages")

    @pytest.mark.asyncio
    async def test_get_chat_history_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful chat history retrieval."""
        session_id = str(uuid4())
        expected_messages = [
            {"id": "1", "session_id": session_id, "content": "Hello"},
            {"id": "2", "session_id": session_id, "content": "Hi there!"},
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_messages)

        result = await database_service.get_chat_history(session_id, limit=10)

        assert result == expected_messages
        mock_supabase_client.eq.assert_called_with("session_id", session_id)
        mock_supabase_client.order.assert_called_with("created_at")
        mock_supabase_client.limit.assert_called_with(10)

    # API Key Operations Tests

    @pytest.mark.asyncio
    async def test_save_api_key_success(self, database_service, mock_supabase_client):
        """Test successful API key save."""
        key_data = {
            "user_id": str(uuid4()),
            "service_name": "openai",
            "encrypted_key": "encrypted_key_value",
        }
        expected_result = [{"id": str(uuid4()), **key_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.save_api_key(key_data)

        assert result == expected_result[0]
        mock_supabase_client.upsert.assert_called_with(key_data)
        mock_supabase_client.on_conflict.assert_called_with("user_id,service_name")

    @pytest.mark.asyncio
    async def test_get_user_api_keys_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful user API keys retrieval."""
        user_id = str(uuid4())
        expected_keys = [
            {"id": "1", "user_id": user_id, "service_name": "openai"},
            {"id": "2", "user_id": user_id, "service_name": "google"},
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_keys)

        result = await database_service.get_user_api_keys(user_id)

        assert result == expected_keys
        mock_supabase_client.eq.assert_called_with("user_id", user_id)

    @pytest.mark.asyncio
    async def test_delete_api_key_success(self, database_service, mock_supabase_client):
        """Test successful API key deletion."""
        user_id = str(uuid4())
        service_name = "openai"
        mock_supabase_client.execute.return_value = Mock(data=[{"id": "1"}])

        result = await database_service.delete_api_key(user_id, service_name)

        assert result is True
        mock_supabase_client.delete.assert_called_once()

    # Vector Operations Tests

    @pytest.mark.asyncio
    async def test_vector_search_success(self, database_service, mock_supabase_client):
        """Test successful vector similarity search."""
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected_results = [
            {"id": "1", "content": "Similar content", "distance": 0.1},
            {"id": "2", "content": "Another similar content", "distance": 0.2},
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_results)

        result = await database_service.vector_search(
            table="documents",
            vector_column="embedding",
            query_vector=query_vector,
            limit=5,
            similarity_threshold=0.8,
        )

        assert result == expected_results
        mock_supabase_client.table.assert_called_with("documents")

    @pytest.mark.asyncio
    async def test_vector_search_destinations(
        self, database_service, mock_supabase_client
    ):
        """Test vector search for destinations."""
        query_vector = [0.1, 0.2, 0.3]
        expected_results = [{"id": "1", "name": "Paris", "distance": 0.1}]
        mock_supabase_client.execute.return_value = Mock(data=expected_results)

        result = await database_service.vector_search_destinations(
            query_vector, limit=10, similarity_threshold=0.7
        )

        assert result == expected_results

    @pytest.mark.asyncio
    async def test_save_destination_embedding(
        self, database_service, mock_supabase_client
    ):
        """Test saving destination with embedding."""
        destination_data = {"name": "Paris", "country": "France"}
        embedding = [0.1, 0.2, 0.3]
        expected_result = [{"id": "dest-1", **destination_data, "embedding": embedding}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.save_destination_embedding(
            destination_data, embedding
        )

        assert result == expected_result[0]
        expected_data = {**destination_data, "embedding": embedding}
        mock_supabase_client.upsert.assert_called_with(expected_data)

    # Advanced Operations Tests

    @pytest.mark.asyncio
    async def test_execute_sql_success(self, database_service, mock_supabase_client):
        """Test successful raw SQL execution."""
        sql = "SELECT COUNT(*) FROM users WHERE active = true"
        params = {"active": True}
        expected_result = [{"count": 5}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.execute_sql(sql, params)

        assert result == expected_result
        mock_supabase_client.rpc.assert_called_with(
            "execute_sql", {"sql": sql, "params": params}
        )

    @pytest.mark.asyncio
    async def test_call_function_success(self, database_service, mock_supabase_client):
        """Test successful database function call."""
        function_name = "get_user_stats"
        params = {"user_id": str(uuid4())}
        expected_result = {"trip_count": 5, "total_distance": 1000}
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.call_function(function_name, params)

        assert result == expected_result
        mock_supabase_client.rpc.assert_called_with(function_name, params)

    # Transaction Tests

    @pytest.mark.asyncio
    async def test_transaction_context(self, database_service, mock_supabase_client):
        """Test transaction context manager."""
        mock_supabase_client.execute.return_value = Mock(data=[{"id": "1"}])

        async with database_service.transaction() as tx:
            tx.insert("users", {"name": "Test User"})
            tx.update("users", {"active": True}, {"id": "1"})
            tx.delete("logs", {"old": True})

            results = await tx.execute()

        assert len(results) == 3
        assert len(tx.operations) == 3

    # Analytics and Reporting Tests

    @pytest.mark.asyncio
    async def test_get_user_stats_success(self, database_service, mock_supabase_client):
        """Test successful user statistics retrieval."""
        user_id = str(uuid4())

        # Mock multiple count operations
        mock_supabase_client.execute.side_effect = [
            Mock(count=5),  # trip count
            Mock(count=10),  # flight searches
            Mock(count=8),  # accommodation searches
        ]

        result = await database_service.get_user_stats(user_id)

        assert result["trip_count"] == 5
        assert result["flight_searches"] == 10
        assert result["accommodation_searches"] == 8
        assert result["total_searches"] == 18

    @pytest.mark.asyncio
    async def test_get_popular_destinations(
        self, database_service, mock_supabase_client
    ):
        """Test popular destinations retrieval."""
        expected_destinations = [
            {"destination": "Paris", "search_count": 50},
            {"destination": "London", "search_count": 35},
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_destinations)

        result = await database_service.get_popular_destinations(limit=10)

        assert result == expected_destinations

    # Health and Monitoring Tests

    @pytest.mark.asyncio
    async def test_health_check_success(self, database_service, mock_supabase_client):
        """Test successful health check."""
        mock_supabase_client.execute.return_value = Mock(data=[{"id": "test"}])

        result = await database_service.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, database_service, mock_supabase_client):
        """Test health check failure."""
        mock_supabase_client.execute.side_effect = Exception("Connection failed")

        result = await database_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_table_info_success(self, database_service, mock_supabase_client):
        """Test successful table info retrieval."""
        expected_columns = [
            {
                "column_name": "id",
                "data_type": "uuid",
                "is_nullable": "NO",
                "column_default": "gen_random_uuid()",
            },
            {
                "column_name": "name",
                "data_type": "text",
                "is_nullable": "YES",
                "column_default": None,
            },
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_columns)

        result = await database_service.get_table_info("users")

        assert result["columns"] == expected_columns

    @pytest.mark.asyncio
    async def test_get_database_stats_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful database statistics retrieval."""
        table_stats = [
            {"tablename": "users", "n_tup_ins": 100, "n_tup_upd": 50, "n_tup_del": 5},
            {"tablename": "trips", "n_tup_ins": 200, "n_tup_upd": 30, "n_tup_del": 10},
        ]
        connection_stats = [{"active_connections": 5}]

        mock_supabase_client.execute.side_effect = [
            Mock(data=table_stats),
            Mock(data=connection_stats),
        ]

        result = await database_service.get_database_stats()

        assert result["tables"] == table_stats
        assert result["connections"] == connection_stats

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_database_error_handling(
        self, database_service, mock_supabase_client
    ):
        """Test database error handling."""
        mock_supabase_client.execute.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(CoreDatabaseError, match="Failed to select from table"):
            await database_service.select("test_table")

    @pytest.mark.asyncio
    async def test_insert_error_handling(self, database_service, mock_supabase_client):
        """Test insert error handling."""
        mock_supabase_client.execute.side_effect = Exception("Constraint violation")

        with pytest.raises(CoreDatabaseError, match="Failed to insert into table"):
            await database_service.insert("test_table", {"invalid": "data"})

    @pytest.mark.asyncio
    async def test_update_error_handling(self, database_service, mock_supabase_client):
        """Test update error handling."""
        mock_supabase_client.execute.side_effect = Exception("Update failed")

        with pytest.raises(CoreDatabaseError, match="Failed to update table"):
            await database_service.update("test_table", {"name": "New"}, {"id": "1"})

    @pytest.mark.asyncio
    async def test_delete_error_handling(self, database_service, mock_supabase_client):
        """Test delete error handling."""
        mock_supabase_client.execute.side_effect = Exception("Delete failed")

        with pytest.raises(CoreDatabaseError, match="Failed to delete from table"):
            await database_service.delete("test_table", {"id": "1"})

    @pytest.mark.asyncio
    async def test_vector_search_error_handling(
        self, database_service, mock_supabase_client
    ):
        """Test vector search error handling."""
        mock_supabase_client.execute.side_effect = Exception("Vector search failed")

        with pytest.raises(CoreDatabaseError, match="Failed to perform vector search"):
            await database_service.vector_search(
                "documents", "embedding", [0.1, 0.2, 0.3]
            )

    @pytest.mark.asyncio
    async def test_sql_execution_error_handling(
        self, database_service, mock_supabase_client
    ):
        """Test SQL execution error handling."""
        mock_supabase_client.execute.side_effect = Exception("SQL error")

        with pytest.raises(CoreDatabaseError, match="Failed to execute SQL query"):
            await database_service.execute_sql("SELECT * FROM invalid_table")

    @pytest.mark.asyncio
    async def test_function_call_error_handling(
        self, database_service, mock_supabase_client
    ):
        """Test function call error handling."""
        mock_supabase_client.execute.side_effect = Exception("Function error")

        with pytest.raises(CoreDatabaseError, match="Failed to call database function"):
            await database_service.call_function("nonexistent_function")

    # Dependency Injection Tests

    @pytest.mark.asyncio
    async def test_get_database_service_function(self):
        """Test the get_database_service dependency function."""
        with patch(
            "tripsage_core.services.infrastructure.database_service.get_settings"
        ):
            service = await get_database_service()
            assert isinstance(service, DatabaseService)

    @pytest.mark.asyncio
    async def test_get_database_service_singleton(self):
        """Test that get_database_service returns singleton instance."""
        with (
            patch(
                "tripsage_core.services.infrastructure.database_service.get_settings"
            ),
            patch(
                "tripsage_core.services.infrastructure.database_service._database_service",
                None,
            ),
        ):
            service1 = await get_database_service()
            service2 = await get_database_service()
            assert service1 is service2

    # Performance and Concurrency Tests

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, database_service, mock_supabase_client):
        """Test concurrent database operations."""
        mock_supabase_client.execute.return_value = Mock(data=[{"id": "test"}])

        # Execute multiple operations concurrently
        tasks = [
            database_service.select("table1"),
            database_service.select("table2"),
            database_service.select("table3"),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert all(result == [{"id": "test"}] for result in results)

    @pytest.mark.asyncio
    async def test_large_batch_insert(self, database_service, mock_supabase_client):
        """Test inserting large batch of records."""
        large_data = [{"name": f"Item {i}", "value": i} for i in range(1000)]
        expected_result = [
            {"id": f"id{i}", **item} for i, item in enumerate(large_data)
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.insert("test_table", large_data)

        assert len(result) == 1000
        mock_supabase_client.insert.assert_called_with(large_data)

    # Edge Cases Tests

    @pytest.mark.asyncio
    async def test_empty_result_handling(self, database_service, mock_supabase_client):
        """Test handling of empty results."""
        mock_supabase_client.execute.return_value = Mock(data=[])

        result = await database_service.select("empty_table")

        assert result == []

    @pytest.mark.asyncio
    async def test_null_value_handling(self, database_service, mock_supabase_client):
        """Test handling of null values."""
        data_with_nulls = [{"id": "1", "name": "Test", "optional_field": None}]
        mock_supabase_client.execute.return_value = Mock(data=data_with_nulls)

        result = await database_service.select("test_table")

        assert result == data_with_nulls
        assert result[0]["optional_field"] is None

    @pytest.mark.asyncio
    async def test_special_characters_handling(
        self, database_service, mock_supabase_client
    ):
        """Test handling of special characters in data."""
        special_data = {
            "name": "Test with 'quotes' and \"double quotes\"",
            "description": "Text with unicode: émojis 🎉 and symbols ±∞",
        }
        expected_result = [{"id": "1", **special_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.insert("test_table", special_data)

        assert result == expected_result
        mock_supabase_client.insert.assert_called_with(special_data)

    # Tests for the 6 new database service methods

    # Tests for get_trip_by_id

    @pytest.mark.asyncio
    async def test_get_trip_by_id_success(self, database_service, mock_supabase_client):
        """Test successful trip retrieval by ID."""
        trip_id = str(uuid4())
        expected_trip = {"id": trip_id, "name": "Test Trip"}
        mock_supabase_client.execute.return_value = Mock(data=[expected_trip])

        result = await database_service.get_trip_by_id(trip_id)

        assert result == expected_trip

    @pytest.mark.asyncio
    async def test_get_trip_by_id_not_found(
        self, database_service, mock_supabase_client
    ):
        """Test trip retrieval when trip doesn't exist."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[])

        result = await database_service.get_trip_by_id(trip_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_trip_by_id_database_error(
        self, database_service, mock_supabase_client
    ):
        """Test trip retrieval with database error (should return None)."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.side_effect = Exception("Database error")

        result = await database_service.get_trip_by_id(trip_id)

        assert result is None

    # Tests for search_trips

    @pytest.mark.asyncio
    async def test_search_trips_basic_success(
        self, database_service, mock_supabase_client
    ):
        """Test basic trip search functionality."""
        user_id = str(uuid4())
        search_filters = {"user_id": user_id}
        expected_trips = [{"id": str(uuid4()), "user_id": user_id}]
        mock_supabase_client.execute.return_value = Mock(data=expected_trips)

        result = await database_service.search_trips(search_filters)

        assert result == expected_trips

    @pytest.mark.asyncio
    async def test_search_trips_with_query_text(
        self, database_service, mock_supabase_client
    ):
        """Test trip search with text query."""
        search_filters = {"query": "Paris"}
        expected_trips = [{"id": str(uuid4()), "destination": "Paris"}]

        # Reset the mock to ensure clean state
        mock_supabase_client.reset_mock()

        # Set up the chain for search_trips which includes order and limit
        final_mock = Mock()
        final_mock.execute.return_value = Mock(data=expected_trips)
        (
            mock_supabase_client.table.return_value.select.return_value.or_.return_value.order.return_value.limit.return_value
        ) = final_mock

        result = await database_service.search_trips(search_filters)

        assert result == expected_trips
        mock_supabase_client.table.assert_called_with("trips")
        mock_supabase_client.table.return_value.select.assert_called_with("*")

    @pytest.mark.asyncio
    async def test_search_trips_with_status_filter(
        self, database_service, mock_supabase_client
    ):
        """Test trip search with status filter."""
        search_filters = {"status": "planning"}
        expected_trips = [{"id": str(uuid4()), "status": "planning"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_trips)

        result = await database_service.search_trips(search_filters)

        assert result == expected_trips

    @pytest.mark.asyncio
    async def test_search_trips_with_date_range(
        self, database_service, mock_supabase_client
    ):
        """Test trip search with date range filter."""
        start_date = datetime(2024, 7, 1)
        end_date = datetime(2024, 7, 31)
        search_filters = {
            "date_range": {"start_date": start_date, "end_date": end_date}
        }
        expected_trips = [{"id": str(uuid4())}]
        mock_supabase_client.execute.return_value = Mock(data=expected_trips)

        result = await database_service.search_trips(search_filters)

        assert result == expected_trips

    @pytest.mark.asyncio
    async def test_search_trips_database_error(
        self, database_service, mock_supabase_client
    ):
        """Test trip search with database error."""
        search_filters = {"user_id": str(uuid4())}
        mock_supabase_client.execute.side_effect = Exception("Database error")

        with pytest.raises(CoreDatabaseError, match="Failed to search trips"):
            await database_service.search_trips(search_filters)

    # Tests for get_trip_collaborators

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful trip collaborators retrieval."""
        trip_id = str(uuid4())
        expected_collaborators = [
            {"trip_id": trip_id, "user_id": str(uuid4()), "permission_level": "edit"}
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_collaborators)

        result = await database_service.get_trip_collaborators(trip_id)

        assert result == expected_collaborators

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_empty_result(
        self, database_service, mock_supabase_client
    ):
        """Test trip collaborators retrieval with no collaborators."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[])

        result = await database_service.get_trip_collaborators(trip_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_trip_collaborators_database_error(
        self, database_service, mock_supabase_client
    ):
        """Test trip collaborators retrieval with database error."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.side_effect = Exception("Database error")

        with pytest.raises(CoreDatabaseError, match="Failed to get collaborators"):
            await database_service.get_trip_collaborators(trip_id)

    # Tests for get_trip_related_counts

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful trip related counts retrieval."""
        trip_id = str(uuid4())

        # Mock multiple count operations with different return values
        mock_supabase_client.execute.side_effect = [
            Mock(count=5),  # itinerary_count
            Mock(count=3),  # flight_count
            Mock(count=2),  # accommodation_count
            Mock(count=1),  # transportation_count
            Mock(count=4),  # collaborator_count
        ]

        result = await database_service.get_trip_related_counts(trip_id)

        expected_result = {
            "itinerary_count": 5,
            "flight_count": 3,
            "accommodation_count": 2,
            "transportation_count": 1,
            "collaborator_count": 4,
        }
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_zero_counts(
        self, database_service, mock_supabase_client
    ):
        """Test trip related counts with all zero counts."""
        trip_id = str(uuid4())

        # Mock all count operations returning 0
        mock_supabase_client.execute.side_effect = [
            Mock(count=0),  # itinerary_count
            Mock(count=0),  # flight_count
            Mock(count=0),  # accommodation_count
            Mock(count=0),  # transportation_count
            Mock(count=0),  # collaborator_count
        ]

        result = await database_service.get_trip_related_counts(trip_id)

        expected_result = {
            "itinerary_count": 0,
            "flight_count": 0,
            "accommodation_count": 0,
            "transportation_count": 0,
            "collaborator_count": 0,
        }
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_trip_related_counts_database_error(
        self, database_service, mock_supabase_client
    ):
        """Test trip related counts with database error."""
        trip_id = str(uuid4())
        mock_supabase_client.execute.side_effect = Exception("Database error")

        with pytest.raises(CoreDatabaseError, match="Failed to get related counts"):
            await database_service.get_trip_related_counts(trip_id)

    # Tests for add_trip_collaborator

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful trip collaborator addition."""
        collaborator_data = {
            "trip_id": str(uuid4()),
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_by": str(uuid4()),
        }
        expected_result = [{"id": str(uuid4()), **collaborator_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.add_trip_collaborator(collaborator_data)

        assert result == expected_result[0]

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_missing_required_field(self, database_service):
        """Test trip collaborator addition with missing required field."""
        incomplete_data = {
            "trip_id": str(uuid4()),
            "user_id": str(uuid4()),
            # Missing permission_level and added_by
        }

        with pytest.raises(CoreDatabaseError, match="Missing required field"):
            await database_service.add_trip_collaborator(incomplete_data)

    @pytest.mark.asyncio
    async def test_add_trip_collaborator_database_error(
        self, database_service, mock_supabase_client
    ):
        """Test trip collaborator addition with database error."""
        collaborator_data = {
            "trip_id": str(uuid4()),
            "user_id": str(uuid4()),
            "permission_level": "edit",
            "added_by": str(uuid4()),
        }
        mock_supabase_client.execute.side_effect = Exception("Database error")

        with pytest.raises(CoreDatabaseError, match="Failed to upsert into table"):
            await database_service.add_trip_collaborator(collaborator_data)

    # Tests for get_trip_collaborator

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_success(
        self, database_service, mock_supabase_client
    ):
        """Test successful specific trip collaborator retrieval."""
        trip_id = str(uuid4())
        user_id = str(uuid4())
        expected_collaborator = {
            "trip_id": trip_id,
            "user_id": user_id,
            "permission_level": "edit",
        }
        mock_supabase_client.execute.return_value = Mock(data=[expected_collaborator])

        result = await database_service.get_trip_collaborator(trip_id, user_id)

        assert result == expected_collaborator

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_not_found(
        self, database_service, mock_supabase_client
    ):
        """Test trip collaborator retrieval when collaborator doesn't exist."""
        trip_id = str(uuid4())
        user_id = str(uuid4())
        mock_supabase_client.execute.return_value = Mock(data=[])

        result = await database_service.get_trip_collaborator(trip_id, user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_trip_collaborator_database_error(
        self, database_service, mock_supabase_client
    ):
        """Test trip collaborator retrieval with database error."""
        trip_id = str(uuid4())
        user_id = str(uuid4())
        mock_supabase_client.execute.side_effect = Exception("Database error")

        with pytest.raises(CoreDatabaseError, match="Failed to get collaborator"):
            await database_service.get_trip_collaborator(trip_id, user_id)
