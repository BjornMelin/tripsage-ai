"""
Unit tests for TripSage Core Database Service.

Tests the database service functionality with mocked Supabase client.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from tripsage_core.config.base_app_settings import CoreAppSettings
from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    get_database_service,
)


class TestDatabaseService:
    """Test suite for DatabaseService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=CoreAppSettings)
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
        """Create a mock Supabase client."""
        client = MagicMock()
        # Setup chain-able API
        client.table = Mock(return_value=client)
        client.select = Mock(return_value=client)
        client.insert = Mock(return_value=client)
        client.update = Mock(return_value=client)
        client.upsert = Mock(return_value=client)
        client.delete = Mock(return_value=client)
        client.eq = Mock(return_value=client)
        client.single = Mock(return_value=client)
        client.limit = Mock(return_value=client)
        client.offset = Mock(return_value=client)
        client.execute = Mock(return_value=Mock(data=[{"id": "test-id"}]))
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
        ):
            service = DatabaseService(settings=mock_settings)
            service._client = mock_supabase_client
            service._connected = True
            return service

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
    async def test_ensure_connected_when_not_connected(self, database_service):
        """Test ensure_connected when not connected."""
        database_service._connected = False

        with patch.object(
            database_service, "connect", new_callable=AsyncMock
        ) as mock_connect:
            await database_service.ensure_connected()
            mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_success(self, database_service, mock_supabase_client):
        """Test successful record insertion."""
        test_data = {"name": "Test Item", "value": 123}
        expected_result = [{"id": "new-id", **test_data}]
        mock_supabase_client.execute.return_value = Mock(data=expected_result)

        result = await database_service.insert("test_table", test_data)

        assert result == expected_result
        mock_supabase_client.table.assert_called_with("test_table")
        mock_supabase_client.insert.assert_called_with(test_data)

    @pytest.mark.asyncio
    async def test_select_with_filters(self, database_service, mock_supabase_client):
        """Test select with filters."""
        expected_data = [{"id": "1", "status": "active"}]
        mock_supabase_client.execute.return_value = Mock(data=expected_data)

        result = await database_service.select(
            "test_table", filters={"status": "active"}, limit=10
        )

        assert result == expected_data
        mock_supabase_client.eq.assert_called_with("status", "active")
        mock_supabase_client.limit.assert_called_with(10)

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

    @pytest.mark.asyncio
    async def test_delete_success(self, database_service, mock_supabase_client):
        """Test successful record deletion."""
        deleted_data = [{"id": "test-id"}]
        mock_supabase_client.execute.return_value = Mock(data=deleted_data)

        result = await database_service.delete("test_table", filters={"id": "test-id"})

        assert result == deleted_data
        mock_supabase_client.delete.assert_called_once()

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
    async def test_get_user_trips_success(self, database_service, mock_supabase_client):
        """Test successful user trips retrieval."""
        user_id = str(uuid4())
        expected_trips = [
            {"id": "1", "user_id": user_id, "title": "Trip 1"},
            {"id": "2", "user_id": user_id, "title": "Trip 2"},
        ]
        mock_supabase_client.execute.return_value = Mock(data=expected_trips)

        result = await database_service.get_user_trips(user_id)

        assert result == expected_trips
        mock_supabase_client.eq.assert_called_with("user_id", user_id)

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
    async def test_database_error_handling(
        self, database_service, mock_supabase_client
    ):
        """Test database error handling."""
        mock_supabase_client.execute.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(CoreDatabaseError, match="Database operation failed"):
            await database_service.select("test_table")

    @pytest.mark.asyncio
    async def test_close_connection(self, database_service):
        """Test closing database connection."""
        await database_service.close()

        assert not database_service.is_connected
        assert database_service._client is None

    def test_get_database_service_function(self):
        """Test the get_database_service dependency function."""
        with patch(
            "tripsage_core.services.infrastructure.database_service.get_settings"
        ):
            service = get_database_service()
            assert isinstance(service, DatabaseService)

    @pytest.mark.asyncio
    async def test_health_check_success(self, database_service, mock_supabase_client):
        """Test successful health check."""
        mock_supabase_client.execute.return_value = Mock(data=[{"count": 5}])

        result = await database_service.health_check()

        assert result["status"] == "healthy"
        assert result["connected"] is True
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_health_check_failure(self, database_service, mock_supabase_client):
        """Test health check failure."""
        mock_supabase_client.execute.side_effect = Exception("Connection failed")

        result = await database_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["connected"] is False
        assert "error" in result
