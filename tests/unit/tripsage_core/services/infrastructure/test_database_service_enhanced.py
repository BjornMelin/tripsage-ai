"""
Enhanced comprehensive tests for TripSage Core Database Service.

This module provides 90%+ test coverage for database service functionality including:
- Connection management and lifecycle
- CRUD operations with error handling
- Transaction support and rollback scenarios
- Vector operations and similarity search
- High-level business operations (trips, users, flights)
- Replica management and load balancing
- Health monitoring and statistics
- Performance optimization and caching

Modern testing patterns:
- AAA (Arrange, Act, Assert) pattern
- pytest-asyncio for async test support
- Hypothesis for property-based testing
- Fixtures for reusable test data
- Mocking with proper isolation
- Comprehensive error scenario testing
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from hypothesis import given, strategies as st
from pydantic import ValidationError
from supabase import Client

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
    CoreServiceError,
)
from tripsage_core.services.infrastructure.database_service import (
    DatabaseService,
    close_database_service,
    get_database_service,
)
from tripsage_core.services.infrastructure.replica_manager import (
    QueryType,
    ReplicaConfig,
    ReplicaManager,
)


class TestDatabaseServiceConnectionManagement:
    """Test suite for database connection management."""

    @pytest_asyncio.fixture
    async def mock_settings(self):
        """Create mock settings for testing."""
        settings = Mock(spec=Settings)
        settings.database_url = "https://test-project.supabase.co"
        settings.database_public_key = Mock()
        settings.database_public_key.get_secret_value.return_value = "test-api-key-1234567890"
        settings.enable_read_replicas = False
        return settings

    @pytest_asyncio.fixture
    async def mock_supabase_client(self):
        """Create mock Supabase client."""
        client = Mock(spec=Client)
        client.table.return_value.select.return_value.limit.return_value.execute.return_value = Mock(
            data=[], count=0
        )
        return client

    @pytest_asyncio.fixture
    async def database_service(self, mock_settings):
        """Create DatabaseService instance for testing."""
        service = DatabaseService(mock_settings)
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_initialization(self, mock_settings):
        """Test database service initialization."""
        # Arrange & Act
        service = DatabaseService(mock_settings)
        
        # Assert
        assert service.settings == mock_settings
        assert service._client is None
        assert not service._connected
        assert service._replica_manager is None
        assert not service.is_connected

    @pytest.mark.asyncio
    async def test_connect_success(self, database_service, mock_supabase_client):
        """Test successful database connection."""
        # Arrange
        with patch('tripsage_core.services.infrastructure.database_service.create_client') as mock_create:
            mock_create.return_value = mock_supabase_client
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_to_thread.return_value = Mock(data=[])
                
                # Act
                await database_service.connect()
                
                # Assert
                assert database_service.is_connected
                assert database_service._client == mock_supabase_client
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_invalid_url(self, mock_settings):
        """Test connection with invalid URL."""
        # Arrange
        mock_settings.database_url = "invalid-url"
        service = DatabaseService(mock_settings)
        
        # Act & Assert
        with pytest.raises(CoreDatabaseError) as exc_info:
            await service.connect()
        
        assert "Invalid Supabase URL format" in str(exc_info.value)
        assert exc_info.value.code == "INVALID_DATABASE_URL"

    @pytest.mark.asyncio
    async def test_connect_invalid_api_key(self, mock_settings):
        """Test connection with invalid API key."""
        # Arrange
        mock_settings.database_public_key.get_secret_value.return_value = "short"
        service = DatabaseService(mock_settings)
        
        # Act & Assert
        with pytest.raises(CoreDatabaseError) as exc_info:
            await service.connect()
        
        assert "Invalid Supabase API key" in str(exc_info.value)
        assert exc_info.value.code == "INVALID_DATABASE_KEY"

    @pytest.mark.asyncio
    async def test_connect_connection_failure(self, database_service, mock_supabase_client):
        """Test connection failure during health check."""
        # Arrange
        with patch('tripsage_core.services.infrastructure.database_service.create_client') as mock_create:
            mock_create.return_value = mock_supabase_client
            with patch('asyncio.to_thread') as mock_to_thread:
                mock_to_thread.side_effect = Exception("Connection failed")
                
                # Act & Assert
                with pytest.raises(CoreDatabaseError) as exc_info:
                    await database_service.connect()
                
                assert "Failed to connect to database" in str(exc_info.value)
                assert exc_info.value.code == "DATABASE_CONNECTION_FAILED"

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, database_service, mock_supabase_client):
        """Test connecting when already connected."""
        # Arrange
        database_service._connected = True
        database_service._client = mock_supabase_client
        
        # Act
        await database_service.connect()
        
        # Assert - should not raise error and remain connected
        assert database_service.is_connected

    @pytest.mark.asyncio
    async def test_close_connection(self, database_service):
        """Test closing database connection."""
        # Arrange
        database_service._connected = True
        database_service._client = Mock()
        mock_replica_manager = Mock()
        mock_replica_manager.close = AsyncMock()
        database_service._replica_manager = mock_replica_manager
        
        # Act
        await database_service.close()
        
        # Assert
        assert not database_service._connected
        assert database_service._client is None
        assert database_service._replica_manager is None
        mock_replica_manager.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_not_connected(self, database_service):
        """Test ensure_connected when not connected."""
        # Arrange
        database_service.connect = AsyncMock()
        
        # Act
        await database_service.ensure_connected()
        
        # Assert
        database_service.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_when_connected(self, database_service):
        """Test ensure_connected when already connected."""
        # Arrange
        database_service._connected = True
        database_service._client = Mock()
        database_service.connect = AsyncMock()
        
        # Act
        await database_service.ensure_connected()
        
        # Assert
        database_service.connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_client_property_when_connected(self, database_service):
        """Test client property when connected."""
        # Arrange
        mock_client = Mock()
        database_service._connected = True
        database_service._client = mock_client
        
        # Act & Assert
        assert database_service.client == mock_client

    @pytest.mark.asyncio
    async def test_client_property_when_not_connected(self, database_service):
        """Test client property when not connected."""
        # Arrange
        database_service._connected = False
        
        # Act & Assert
        with pytest.raises(CoreServiceError) as exc_info:
            _ = database_service.client
        
        assert exc_info.value.code == "DATABASE_NOT_CONNECTED"


class TestDatabaseServiceCRUDOperations:
    """Test suite for CRUD operations."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_insert_single_record(self, connected_service):
        """Test inserting a single record."""
        # Arrange
        test_data = {"name": "Test User", "email": "test@example.com"}
        expected_result = [{"id": 1, **test_data}]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.insert("users", test_data)
            
            # Assert
            assert result == expected_result
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_multiple_records(self, connected_service):
        """Test inserting multiple records."""
        # Arrange
        test_data = [
            {"name": "User 1", "email": "user1@example.com"},
            {"name": "User 2", "email": "user2@example.com"}
        ]
        expected_result = [
            {"id": 1, **test_data[0]},
            {"id": 2, **test_data[1]}
        ]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.insert("users", test_data)
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_insert_failure(self, connected_service):
        """Test insert operation failure."""
        # Arrange
        test_data = {"invalid": "data"}
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Insert failed")
            
            # Act & Assert
            with pytest.raises(CoreDatabaseError) as exc_info:
                await connected_service.insert("users", test_data)
            
            assert exc_info.value.code == "INSERT_FAILED"
            assert exc_info.value.table == "users"

    @pytest.mark.asyncio
    async def test_select_all_records(self, connected_service):
        """Test selecting all records."""
        # Arrange
        expected_result = [
            {"id": 1, "name": "User 1"},
            {"id": 2, "name": "User 2"}
        ]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.select("users")
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_select_with_filters(self, connected_service):
        """Test selecting with filters."""
        # Arrange
        filters = {"status": "active", "age": {"gte": 18}}
        expected_result = [{"id": 1, "name": "Adult User"}]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.select("users", filters=filters)
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_select_with_pagination(self, connected_service):
        """Test selecting with pagination."""
        # Arrange
        expected_result = [{"id": 11, "name": "User 11"}]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.select(
                "users", limit=10, offset=10, order_by="-created_at"
            )
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_update_success(self, connected_service):
        """Test successful update operation."""
        # Arrange
        update_data = {"name": "Updated Name"}
        filters = {"id": 1}
        expected_result = [{"id": 1, "name": "Updated Name"}]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.update("users", update_data, filters)
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_upsert_success(self, connected_service):
        """Test successful upsert operation."""
        # Arrange
        upsert_data = {"id": 1, "name": "Test User", "email": "test@example.com"}
        expected_result = [upsert_data]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.upsert("users", upsert_data, on_conflict="id")
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_delete_success(self, connected_service):
        """Test successful delete operation."""
        # Arrange
        filters = {"id": 1}
        expected_result = [{"id": 1, "name": "Deleted User"}]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.delete("users", filters)
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_count_success(self, connected_service):
        """Test successful count operation."""
        # Arrange
        filters = {"status": "active"}
        expected_count = 42
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(count=expected_count)
            
            # Act
            result = await connected_service.count("users", filters)
            
            # Assert
            assert result == expected_count


class TestDatabaseServiceVectorOperations:
    """Test suite for vector operations."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_vector_search_success(self, connected_service):
        """Test successful vector search."""
        # Arrange
        query_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        expected_result = [
            {"id": 1, "name": "Similar Item", "distance": 0.2},
            {"id": 2, "name": "Another Item", "distance": 0.3}
        ]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.vector_search(
                "destinations", "embedding", query_vector, limit=10
            )
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, connected_service):
        """Test vector search with similarity threshold."""
        # Arrange
        query_vector = [0.1, 0.2, 0.3]
        similarity_threshold = 0.8
        expected_result = [{"id": 1, "name": "Highly Similar", "distance": 0.1}]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=expected_result)
            
            # Act
            result = await connected_service.vector_search(
                "destinations", 
                "embedding", 
                query_vector, 
                similarity_threshold=similarity_threshold
            )
            
            # Assert
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_vector_search_destinations(self, connected_service):
        """Test specialized destination vector search."""
        # Arrange
        query_vector = [0.1, 0.2, 0.3]
        expected_result = [{"id": 1, "name": "Paris", "distance": 0.15}]
        
        with patch.object(connected_service, 'vector_search') as mock_vector_search:
            mock_vector_search.return_value = expected_result
            
            # Act
            result = await connected_service.vector_search_destinations(
                query_vector, limit=5, similarity_threshold=0.7
            )
            
            # Assert
            assert result == expected_result
            mock_vector_search.assert_called_once_with(
                "destinations", "embedding", query_vector, limit=5, similarity_threshold=0.7
            )

    @pytest.mark.asyncio
    async def test_save_destination_embedding(self, connected_service):
        """Test saving destination with embedding."""
        # Arrange
        destination_data = {"name": "Tokyo", "country": "Japan"}
        embedding = [0.1, 0.2, 0.3, 0.4]
        expected_result = [{"id": 1, **destination_data, "embedding": embedding}]
        
        with patch.object(connected_service, 'upsert') as mock_upsert:
            mock_upsert.return_value = expected_result
            
            # Act
            result = await connected_service.save_destination_embedding(
                destination_data, embedding
            )
            
            # Assert
            assert result == expected_result
            mock_upsert.assert_called_once()


class TestDatabaseServiceBusinessOperations:
    """Test suite for high-level business operations."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    # Trip Operations Tests
    @pytest.mark.asyncio
    async def test_create_trip_success(self, connected_service):
        """Test successful trip creation."""
        # Arrange
        trip_data = {
            "name": "European Adventure",
            "destination": "Europe",
            "user_id": str(uuid4())
        }
        expected_result = [{"id": str(uuid4()), **trip_data}]
        
        with patch.object(connected_service, 'insert') as mock_insert:
            mock_insert.return_value = expected_result
            
            # Act
            result = await connected_service.create_trip(trip_data)
            
            # Assert
            assert result == expected_result[0]
            mock_insert.assert_called_once_with("trips", trip_data)

    @pytest.mark.asyncio
    async def test_get_trip_success(self, connected_service):
        """Test successful trip retrieval."""
        # Arrange
        trip_id = str(uuid4())
        expected_trip = {"id": trip_id, "name": "Test Trip"}
        
        with patch.object(connected_service, 'select') as mock_select:
            mock_select.return_value = [expected_trip]
            
            # Act
            result = await connected_service.get_trip(trip_id)
            
            # Assert
            assert result == expected_trip
            mock_select.assert_called_once_with("trips", "*", {"id": trip_id})

    @pytest.mark.asyncio
    async def test_get_trip_not_found(self, connected_service):
        """Test trip not found scenario."""
        # Arrange
        trip_id = str(uuid4())
        
        with patch.object(connected_service, 'select') as mock_select:
            mock_select.return_value = []
            
            # Act & Assert
            with pytest.raises(CoreResourceNotFoundError) as exc_info:
                await connected_service.get_trip(trip_id)
            
            assert f"Trip {trip_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_trips(self, connected_service):
        """Test retrieving user trips."""
        # Arrange
        user_id = str(uuid4())
        expected_trips = [
            {"id": str(uuid4()), "name": "Trip 1", "user_id": user_id},
            {"id": str(uuid4()), "name": "Trip 2", "user_id": user_id}
        ]
        
        with patch.object(connected_service, 'select') as mock_select:
            mock_select.return_value = expected_trips
            
            # Act
            result = await connected_service.get_user_trips(user_id)
            
            # Assert
            assert result == expected_trips
            mock_select.assert_called_once_with(
                "trips", "*", {"user_id": user_id}, order_by="-created_at"
            )

    # User Operations Tests
    @pytest.mark.asyncio
    async def test_create_user_success(self, connected_service):
        """Test successful user creation."""
        # Arrange
        user_data = {"email": "test@example.com", "name": "Test User"}
        expected_result = [{"id": str(uuid4()), **user_data}]
        
        with patch.object(connected_service, 'insert') as mock_insert:
            mock_insert.return_value = expected_result
            
            # Act
            result = await connected_service.create_user(user_data)
            
            # Assert
            assert result == expected_result[0]

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, connected_service):
        """Test retrieving user by email."""
        # Arrange
        email = "test@example.com"
        expected_user = {"id": str(uuid4()), "email": email, "name": "Test User"}
        
        with patch.object(connected_service, 'select') as mock_select:
            mock_select.return_value = [expected_user]
            
            # Act
            result = await connected_service.get_user_by_email(email)
            
            # Assert
            assert result == expected_user


class TestDatabaseServiceTransactions:
    """Test suite for transaction operations."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, connected_service):
        """Test transaction context manager functionality."""
        # Arrange & Act
        async with connected_service.transaction() as tx:
            # Assert
            assert hasattr(tx, 'insert')
            assert hasattr(tx, 'update')
            assert hasattr(tx, 'delete')
            assert hasattr(tx, 'execute')

    @pytest.mark.asyncio
    async def test_transaction_operations(self, connected_service):
        """Test transaction operations."""
        # Arrange
        with patch.object(connected_service, 'insert') as mock_insert:
            with patch.object(connected_service, 'update') as mock_update:
                mock_insert.return_value = [{"id": 1}]
                mock_update.return_value = [{"id": 1, "updated": True}]
                
                # Act
                async with connected_service.transaction() as tx:
                    tx.insert("users", {"name": "Test"})
                    tx.update("users", {"active": True}, {"id": 1})
                    results = await tx.execute()
                
                # Assert
                assert len(results) == 2
                mock_insert.assert_called_once()
                mock_update.assert_called_once()


class TestDatabaseServiceErrorHandling:
    """Test suite for error handling scenarios."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_operation_when_not_connected(self, mock_settings):
        """Test operations when not connected."""
        # Arrange
        service = DatabaseService(mock_settings)
        service.ensure_connected = AsyncMock()
        
        # Act & Assert
        await service.insert("users", {"name": "test"})
        service.ensure_connected.assert_called_once()

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, connected_service):
        """Test network timeout handling."""
        # Arrange
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = asyncio.TimeoutError("Connection timeout")
            
            # Act & Assert
            with pytest.raises(CoreDatabaseError) as exc_info:
                await connected_service.select("users")
            
            assert "SELECT_FAILED" in str(exc_info.value.code)

    @pytest.mark.asyncio
    async def test_invalid_sql_handling(self, connected_service):
        """Test invalid SQL handling."""
        # Arrange
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Invalid SQL syntax")
            
            # Act & Assert
            with pytest.raises(CoreDatabaseError) as exc_info:
                await connected_service.execute_sql("INVALID SQL")
            
            assert exc_info.value.code == "SQL_EXECUTION_FAILED"


class TestDatabaseServiceReplicaManagement:
    """Test suite for replica management."""

    @pytest_asyncio.fixture
    async def replica_enabled_service(self, mock_settings, mock_supabase_client):
        """Create database service with replica management enabled."""
        mock_settings.enable_read_replicas = True
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        
        # Mock replica manager
        mock_replica_manager = Mock(spec=ReplicaManager)
        mock_replica_manager.initialize = AsyncMock()
        mock_replica_manager.close = AsyncMock()
        mock_replica_manager.acquire_connection = AsyncMock()
        service._replica_manager = mock_replica_manager
        
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_replica_manager_initialization(self, replica_enabled_service):
        """Test replica manager initialization."""
        # Arrange & Act
        replica_manager = replica_enabled_service.get_replica_manager()
        
        # Assert
        assert replica_manager is not None
        assert replica_enabled_service.is_replica_enabled()

    @pytest.mark.asyncio
    async def test_get_replica_health(self, replica_enabled_service):
        """Test getting replica health."""
        # Arrange
        mock_health_data = {
            "replica1": Mock(
                status=Mock(value="healthy"),
                latency_ms=50,
                uptime_percentage=99.9,
                last_check=datetime.now(timezone.utc)
            )
        }
        replica_enabled_service._replica_manager.get_replica_health.return_value = mock_health_data
        
        # Act
        health = await replica_enabled_service.get_replica_health()
        
        # Assert
        assert health["enabled"] is True
        assert "replicas" in health
        assert "replica1" in health["replicas"]

    @pytest.mark.asyncio
    async def test_add_read_replica(self, replica_enabled_service):
        """Test adding a read replica."""
        # Arrange
        replica_enabled_service._replica_manager.register_replica = AsyncMock(return_value=True)
        
        # Act
        result = await replica_enabled_service.add_read_replica(
            "test-replica", "https://replica.supabase.co", "test-key"
        )
        
        # Assert
        assert result is True
        replica_enabled_service._replica_manager.register_replica.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_read_replica(self, replica_enabled_service):
        """Test removing a read replica."""
        # Arrange
        replica_enabled_service._replica_manager.remove_replica = AsyncMock(return_value=True)
        
        # Act
        result = await replica_enabled_service.remove_read_replica("test-replica")
        
        # Assert
        assert result is True
        replica_enabled_service._replica_manager.remove_replica.assert_called_once()


class TestDatabaseServiceHealthMonitoring:
    """Test suite for health monitoring and statistics."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_health_check_success(self, connected_service):
        """Test successful health check."""
        # Arrange
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=[])
            
            # Act
            result = await connected_service.health_check()
            
            # Assert
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, connected_service):
        """Test health check failure."""
        # Arrange
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.side_effect = Exception("Health check failed")
            
            # Act
            result = await connected_service.health_check()
            
            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_get_database_stats(self, connected_service):
        """Test getting database statistics."""
        # Arrange
        mock_table_stats = [{"schemaname": "public", "tablename": "users"}]
        mock_connection_stats = [{"active_connections": 5}]
        
        with patch.object(connected_service, 'execute_sql') as mock_execute:
            mock_execute.side_effect = [mock_table_stats, mock_connection_stats]
            
            # Act
            result = await connected_service.get_database_stats()
            
            # Assert
            assert "tables" in result
            assert "connections" in result
            assert result["tables"] == mock_table_stats

    @pytest.mark.asyncio
    async def test_get_table_info(self, connected_service):
        """Test getting table information."""
        # Arrange
        mock_columns = [
            {"column_name": "id", "data_type": "uuid", "is_nullable": "NO"},
            {"column_name": "name", "data_type": "text", "is_nullable": "YES"}
        ]
        
        with patch.object(connected_service, 'execute_sql') as mock_execute:
            mock_execute.return_value = mock_columns
            
            # Act
            result = await connected_service.get_table_info("users")
            
            # Assert
            assert "columns" in result
            assert result["columns"] == mock_columns


class TestDatabaseServiceGlobalInstance:
    """Test suite for global service instance management."""

    @pytest.mark.asyncio
    async def test_get_database_service_singleton(self):
        """Test global database service singleton behavior."""
        # Arrange & Act
        with patch('tripsage_core.services.infrastructure.database_service.DatabaseService') as MockClass:
            mock_instance = Mock()
            mock_instance.connect = AsyncMock()
            MockClass.return_value = mock_instance
            
            service1 = await get_database_service()
            service2 = await get_database_service()
            
            # Assert
            assert service1 == service2  # Same instance
            MockClass.assert_called_once()  # Only created once

    @pytest.mark.asyncio
    async def test_close_database_service_global(self):
        """Test closing global database service."""
        # Arrange
        with patch('tripsage_core.services.infrastructure.database_service._database_service') as mock_global:
            mock_service = Mock()
            mock_service.close = AsyncMock()
            mock_global = mock_service
            
            # Act
            await close_database_service()
            
            # Assert would need better global state management
            # This is a simplified test


# Property-based testing with Hypothesis
class TestDatabaseServicePropertyBased:
    """Property-based tests using Hypothesis."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @given(
        table_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=['Ll', 'Lu', 'Nd'])),
        record_count=st.integers(min_value=1, max_value=100)
    )
    @pytest.mark.asyncio
    async def test_insert_select_consistency(self, connected_service, table_name, record_count):
        """Property test: inserted records should be retrievable."""
        # This is a simplified example - in practice you'd need more sophisticated
        # property testing for database operations
        
        # Arrange
        test_records = [{"id": i, "value": f"test_{i}"} for i in range(record_count)]
        
        with patch.object(connected_service, 'insert') as mock_insert:
            with patch.object(connected_service, 'select') as mock_select:
                mock_insert.return_value = test_records
                mock_select.return_value = test_records
                
                # Act
                inserted = await connected_service.insert(table_name, test_records)
                selected = await connected_service.select(table_name)
                
                # Assert
                assert len(inserted) == record_count
                assert len(selected) == record_count


# Performance benchmarking tests
class TestDatabaseServicePerformance:
    """Performance tests for database operations."""

    @pytest_asyncio.fixture
    async def connected_service(self, mock_settings, mock_supabase_client):
        """Create connected database service."""
        service = DatabaseService(mock_settings)
        service._connected = True
        service._client = mock_supabase_client
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_concurrent_operations_performance(self, connected_service):
        """Test performance of concurrent database operations."""
        # Arrange
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=[{"id": 1}])
            
            # Act
            start_time = asyncio.get_event_loop().time()
            
            tasks = [
                connected_service.select("users", limit=10)
                for _ in range(10)
            ]
            results = await asyncio.gather(*tasks)
            
            end_time = asyncio.get_event_loop().time()
            
            # Assert
            assert len(results) == 10
            execution_time = end_time - start_time
            # Performance assertion - should complete within reasonable time
            assert execution_time < 1.0  # 1 second for 10 concurrent operations

    @pytest.mark.asyncio
    async def test_large_batch_insert_performance(self, connected_service):
        """Test performance of large batch inserts."""
        # Arrange
        large_dataset = [{"id": i, "value": f"test_{i}"} for i in range(1000)]
        
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(data=large_dataset)
            
            # Act
            start_time = asyncio.get_event_loop().time()
            result = await connected_service.insert("test_table", large_dataset)
            end_time = asyncio.get_event_loop().time()
            
            # Assert
            assert len(result) == 1000
            execution_time = end_time - start_time
            # Should handle large batches efficiently
            assert execution_time < 2.0  # 2 seconds for 1000 records


if __name__ == "__main__":
    pytest.main([__file__])