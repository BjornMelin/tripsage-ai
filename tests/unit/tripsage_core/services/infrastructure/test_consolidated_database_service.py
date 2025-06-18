"""
Comprehensive test suite for the consolidated database service.

Tests all features including:
- Connection modes (direct, session, transaction)
- Query operations (CRUD, vector search)
- Performance monitoring and metrics
- Retry logic and circuit breaker
- Query caching
- Health checks
- Compatibility with old API
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from supabase.lib.client_options import ClientOptions

from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError,
    CoreResourceNotFoundError,
)
from tripsage_core.services.infrastructure.consolidated_database_service import (
    ConnectionMode,
    ConnectionStats,
    ConsolidatedDatabaseService,
    HealthStatus,
    QueryMetrics,
    QueryType,
    get_database_service,
    close_database_service,
)


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.database_url = "https://test-project.supabase.co"
    settings.database_public_key.get_secret_value.return_value = "test-api-key"
    settings.supabase_region = "us-east-1"
    return settings


@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    client = MagicMock()
    
    # Mock table operations
    table_mock = MagicMock()
    client.table.return_value = table_mock
    
    # Mock query chain
    query_mock = MagicMock()
    table_mock.select.return_value = query_mock
    table_mock.insert.return_value = query_mock
    table_mock.update.return_value = query_mock
    table_mock.delete.return_value = query_mock
    table_mock.upsert.return_value = query_mock
    
    # Mock query modifiers
    query_mock.eq.return_value = query_mock
    query_mock.lt.return_value = query_mock
    query_mock.gt.return_value = query_mock
    query_mock.gte.return_value = query_mock
    query_mock.lte.return_value = query_mock
    query_mock.order.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.offset.return_value = query_mock
    query_mock.on_conflict.return_value = query_mock
    
    # Mock execute
    result_mock = MagicMock()
    result_mock.data = []
    result_mock.count = 0
    query_mock.execute.return_value = result_mock
    
    # Mock RPC
    client.rpc.return_value = query_mock
    
    return client


@pytest.fixture
async def database_service(mock_settings, mock_supabase_client):
    """Create database service instance for testing."""
    with patch("tripsage_core.services.infrastructure.consolidated_database_service.create_client") as mock_create:
        mock_create.return_value = mock_supabase_client
        
        service = ConsolidatedDatabaseService(
            settings=mock_settings,
            enable_monitoring=True,
            enable_query_cache=True,
        )
        
        yield service
        
        # Cleanup
        await service.close()


class TestConnectionManagement:
    """Test connection management functionality."""
    
    async def test_connect_all_modes(self, database_service, mock_supabase_client):
        """Test connecting in all modes."""
        await database_service.connect()
        
        # Verify all connections established
        assert database_service._connected is True
        assert all(
            database_service._clients[mode] is not None
            for mode in ConnectionMode
        )
    
    async def test_connect_specific_mode(self, database_service, mock_supabase_client):
        """Test connecting in specific mode."""
        await database_service.connect(ConnectionMode.TRANSACTION)
        
        # Verify only transaction mode connected
        assert database_service._clients[ConnectionMode.TRANSACTION] is not None
        assert database_service._clients[ConnectionMode.DIRECT] is None
        assert database_service._clients[ConnectionMode.SESSION] is None
    
    async def test_connection_url_generation(self, database_service):
        """Test connection URL generation for different modes."""
        # Direct mode should use original URL
        direct_url = database_service._get_connection_url(ConnectionMode.DIRECT)
        assert direct_url == "https://test-project.supabase.co"
        
        # Transaction mode should use Supavisor with port 6543
        transaction_url = database_service._get_connection_url(ConnectionMode.TRANSACTION)
        assert "pooler.supabase.com:6543" in transaction_url
        assert "aws-0-us-east-1" in transaction_url
        
        # Session mode should use Supavisor with port 5432
        session_url = database_service._get_connection_url(ConnectionMode.SESSION)
        assert "pooler.supabase.com:5432" in session_url
    
    async def test_client_options_configuration(self, database_service):
        """Test client options for different modes."""
        # Transaction mode options
        transaction_opts = database_service._create_client_options(ConnectionMode.TRANSACTION)
        assert transaction_opts.auto_refresh_token is False
        assert transaction_opts.persist_session is False
        
        # Session mode options
        session_opts = database_service._create_client_options(ConnectionMode.SESSION)
        assert session_opts.auto_refresh_token is True
        assert session_opts.persist_session is True
    
    async def test_connection_failure_handling(self, database_service, mock_settings):
        """Test handling of connection failures."""
        with patch("tripsage_core.services.infrastructure.consolidated_database_service.create_client") as mock_create:
            mock_create.side_effect = Exception("Connection failed")
            
            # Should raise error when specific mode requested
            with pytest.raises(CoreDatabaseError) as exc_info:
                await database_service.connect(ConnectionMode.DIRECT)
            
            assert "Failed to connect" in str(exc_info.value)
            assert database_service._connection_stats.connection_errors == 1
    
    async def test_close_connections(self, database_service, mock_supabase_client):
        """Test closing connections."""
        await database_service.connect()
        await database_service.close()
        
        # Verify all connections closed
        assert database_service._connected is False
        assert all(
            database_service._clients[mode] is None
            for mode in ConnectionMode
        )


class TestQueryOperations:
    """Test database query operations."""
    
    async def test_select_operation(self, database_service, mock_supabase_client):
        """Test SELECT operation."""
        # Setup mock response
        mock_data = [{"id": 1, "name": "Test"}]
        mock_supabase_client.table().select().execute.return_value.data = mock_data
        
        await database_service.connect()
        result = await database_service.select(
            "test_table",
            columns="id,name",
            filters={"active": True},
            order_by="-created_at",
            limit=10,
            offset=0
        )
        
        assert result == mock_data
        
        # Verify query construction
        mock_supabase_client.table.assert_called_with("test_table")
        mock_supabase_client.table().select.assert_called_with("id,name")
        mock_supabase_client.table().select().eq.assert_called_with("active", True)
        mock_supabase_client.table().select().order.assert_called_with("created_at", desc=True)
        mock_supabase_client.table().select().limit.assert_called_with(10)
        mock_supabase_client.table().select().offset.assert_called_with(0)
    
    async def test_insert_operation(self, database_service, mock_supabase_client):
        """Test INSERT operation."""
        mock_data = {"name": "New Item"}
        mock_response = [{"id": 1, **mock_data}]
        mock_supabase_client.table().insert().execute.return_value.data = mock_response
        
        await database_service.connect()
        result = await database_service.insert("test_table", mock_data)
        
        assert result == mock_response
        mock_supabase_client.table().insert.assert_called_with(mock_data)
    
    async def test_update_operation(self, database_service, mock_supabase_client):
        """Test UPDATE operation."""
        update_data = {"name": "Updated"}
        filters = {"id": 1}
        mock_response = [{"id": 1, **update_data}]
        mock_supabase_client.table().update().execute.return_value.data = mock_response
        
        await database_service.connect()
        result = await database_service.update("test_table", update_data, filters)
        
        assert result == mock_response
        mock_supabase_client.table().update.assert_called_with(update_data)
        mock_supabase_client.table().update().eq.assert_called_with("id", 1)
    
    async def test_delete_operation(self, database_service, mock_supabase_client):
        """Test DELETE operation."""
        filters = {"id": 1}
        mock_response = [{"id": 1}]
        mock_supabase_client.table().delete().execute.return_value.data = mock_response
        
        await database_service.connect()
        result = await database_service.delete("test_table", filters)
        
        assert result == mock_response
        mock_supabase_client.table().delete().eq.assert_called_with("id", 1)
    
    async def test_upsert_operation(self, database_service, mock_supabase_client):
        """Test UPSERT operation."""
        upsert_data = {"id": 1, "name": "Upserted"}
        mock_response = [upsert_data]
        mock_supabase_client.table().upsert().execute.return_value.data = mock_response
        
        await database_service.connect()
        result = await database_service.upsert(
            "test_table",
            upsert_data,
            on_conflict="id"
        )
        
        assert result == mock_response
        mock_supabase_client.table().upsert.assert_called_with(upsert_data)
        mock_supabase_client.table().upsert().on_conflict.assert_called_with("id")
    
    async def test_count_operation(self, database_service, mock_supabase_client):
        """Test COUNT operation."""
        mock_supabase_client.table().select().execute.return_value.count = 42
        
        await database_service.connect()
        result = await database_service.count("test_table", {"active": True})
        
        assert result == 42
        mock_supabase_client.table().select.assert_called_with("*", count="exact")


class TestVectorOperations:
    """Test vector search operations."""
    
    async def test_vector_search(self, database_service, mock_supabase_client):
        """Test vector similarity search."""
        query_vector = [0.1, 0.2, 0.3]
        mock_results = [
            {"id": 1, "name": "Item 1", "distance": 0.1},
            {"id": 2, "name": "Item 2", "distance": 0.2},
        ]
        mock_supabase_client.table().select().execute.return_value.data = mock_results
        
        await database_service.connect()
        result = await database_service.vector_search(
            "embeddings_table",
            "embedding",
            query_vector,
            limit=5,
            similarity_threshold=0.8
        )
        
        assert result == mock_results
        
        # Verify vector query construction
        expected_vector_str = "[0.1,0.2,0.3]"
        mock_supabase_client.table().select.assert_called_with(
            f"*, embedding <-> '{expected_vector_str}' as distance"
        )


class TestConnectionModeSelection:
    """Test automatic connection mode selection."""
    
    async def test_mode_selection_for_queries(self, database_service):
        """Test connection mode selection based on query type."""
        # Read queries should use transaction mode
        assert database_service._select_connection_mode(QueryType.SELECT) == ConnectionMode.TRANSACTION
        assert database_service._select_connection_mode(QueryType.COUNT) == ConnectionMode.TRANSACTION
        assert database_service._select_connection_mode(QueryType.VECTOR_SEARCH) == ConnectionMode.TRANSACTION
        
        # Write queries should use session mode
        assert database_service._select_connection_mode(QueryType.INSERT) == ConnectionMode.SESSION
        assert database_service._select_connection_mode(QueryType.UPDATE) == ConnectionMode.SESSION
        assert database_service._select_connection_mode(QueryType.DELETE) == ConnectionMode.SESSION
        
        # Complex operations should use direct connection
        assert database_service._select_connection_mode(QueryType.TRANSACTION) == ConnectionMode.DIRECT
        assert database_service._select_connection_mode(QueryType.RAW_SQL) == ConnectionMode.DIRECT
        assert database_service._select_connection_mode(QueryType.FUNCTION_CALL) == ConnectionMode.DIRECT
    
    async def test_preferred_mode_override(self, database_service):
        """Test that preferred mode overrides automatic selection."""
        preferred = ConnectionMode.DIRECT
        
        # Preferred mode should always be used
        assert database_service._select_connection_mode(
            QueryType.SELECT, preferred
        ) == preferred


class TestQueryCaching:
    """Test query result caching."""
    
    async def test_cache_hit(self, database_service, mock_supabase_client):
        """Test cache hit for repeated queries."""
        mock_data = [{"id": 1, "name": "Cached"}]
        mock_supabase_client.table().select().execute.return_value.data = mock_data
        
        await database_service.connect()
        
        # First call should hit database
        result1 = await database_service.select("test_table", use_cache=True)
        assert result1 == mock_data
        assert mock_supabase_client.table().select().execute.call_count == 1
        
        # Second call should use cache
        result2 = await database_service.select("test_table", use_cache=True)
        assert result2 == mock_data
        assert mock_supabase_client.table().select().execute.call_count == 1  # No additional call
    
    async def test_cache_invalidation_on_write(self, database_service, mock_supabase_client):
        """Test cache invalidation on write operations."""
        mock_data = [{"id": 1, "name": "Original"}]
        mock_supabase_client.table().select().execute.return_value.data = mock_data
        
        await database_service.connect()
        
        # Cache the result
        await database_service.select("test_table", use_cache=True)
        
        # Insert should invalidate cache
        await database_service.insert("test_table", {"name": "New"})
        
        # Next select should hit database again
        mock_supabase_client.table().select().execute.return_value.data = [{"id": 2, "name": "Updated"}]
        result = await database_service.select("test_table", use_cache=True)
        
        assert mock_supabase_client.table().select().execute.call_count == 2
    
    async def test_cache_ttl(self, database_service, mock_supabase_client):
        """Test cache TTL expiration."""
        database_service.set_cache_ttl(0.1)  # 100ms TTL
        
        mock_data = [{"id": 1, "name": "TTL Test"}]
        mock_supabase_client.table().select().execute.return_value.data = mock_data
        
        await database_service.connect()
        
        # First call
        await database_service.select("test_table", use_cache=True)
        
        # Wait for TTL to expire
        await asyncio.sleep(0.2)
        
        # Should hit database again
        await database_service.select("test_table", use_cache=True)
        assert mock_supabase_client.table().select().execute.call_count == 2


class TestRetryLogic:
    """Test retry logic and circuit breaker."""
    
    async def test_retry_on_transient_error(self, database_service, mock_supabase_client):
        """Test retry on transient errors."""
        database_service.max_retries = 3
        database_service.retry_delay = 0.01  # Fast retry for tests
        
        # Fail twice, then succeed
        mock_supabase_client.table().select().execute.side_effect = [
            Exception("Transient error"),
            Exception("Another transient error"),
            MagicMock(data=[{"id": 1}])
        ]
        
        await database_service.connect()
        result = await database_service.select("test_table")
        
        assert result == [{"id": 1}]
        assert mock_supabase_client.table().select().execute.call_count == 3
    
    async def test_no_retry_on_permanent_error(self, database_service, mock_supabase_client):
        """Test no retry on permanent errors."""
        mock_supabase_client.table().select().execute.side_effect = ValueError("Invalid input")
        
        await database_service.connect()
        
        with pytest.raises(ValueError):
            await database_service.select("test_table")
        
        # Should not retry
        assert mock_supabase_client.table().select().execute.call_count == 1
    
    async def test_circuit_breaker_opens(self, database_service, mock_supabase_client):
        """Test circuit breaker opens after repeated failures."""
        database_service.max_retries = 3
        database_service.retry_delay = 0.01
        
        # Always fail
        mock_supabase_client.table().select().execute.side_effect = Exception("Persistent error")
        
        await database_service.connect()
        
        # First attempt should exhaust retries and open circuit breaker
        with pytest.raises(Exception):
            await database_service.select("test_table")
        
        assert database_service._circuit_breaker_open is True
        
        # Subsequent calls should fail immediately
        with pytest.raises(CoreDatabaseError) as exc_info:
            await database_service.select("test_table")
        
        assert "Circuit breaker is open" in str(exc_info.value)


class TestMonitoringAndMetrics:
    """Test monitoring and metrics collection."""
    
    async def test_query_metrics_collection(self, database_service, mock_supabase_client):
        """Test query metrics are collected."""
        mock_supabase_client.table().select().execute.return_value.data = [{"id": 1}]
        
        await database_service.connect()
        await database_service.select("test_table")
        
        metrics = database_service.get_query_metrics()
        assert len(metrics) == 1
        
        metric = metrics[0]
        assert metric.query_type == QueryType.SELECT
        assert metric.table == "test_table"
        assert metric.success is True
        assert metric.rows_affected == 1
        assert metric.duration_ms > 0
    
    async def test_connection_stats(self, database_service, mock_supabase_client):
        """Test connection statistics tracking."""
        await database_service.connect()
        
        # Execute some queries
        await database_service.select("test_table")
        await database_service.insert("test_table", {"name": "Test"})
        
        stats = database_service.get_connection_stats()
        assert stats.queries_executed == 2
        assert stats.avg_query_time_ms > 0
        assert stats.uptime_seconds > 0
        assert stats.active_connections > 0
    
    async def test_health_check(self, database_service, mock_supabase_client):
        """Test health check functionality."""
        await database_service.connect()
        
        health = await database_service.health_check()
        
        # Should have health status for each mode
        assert len(health) == len(ConnectionMode)
        
        # Connected modes should be healthy
        for mode in ConnectionMode:
            if database_service._clients[mode] is not None:
                assert health[mode.value]["status"] == HealthStatus.HEALTHY.value
                assert "response_time_ms" in health[mode.value]
    
    async def test_monitor_connections(self, database_service, mock_supabase_client):
        """Test connection monitoring."""
        await database_service.connect()
        
        monitor_data = await database_service.monitor_connections()
        
        assert "stats" in monitor_data
        assert "health" in monitor_data
        assert "circuit_breaker_open" in monitor_data
        assert "cache_size" in monitor_data


class TestBusinessOperations:
    """Test high-level business operations."""
    
    async def test_trip_operations(self, database_service, mock_supabase_client):
        """Test trip CRUD operations."""
        trip_data = {"name": "Test Trip", "user_id": "user123"}
        trip_id = "trip123"
        
        # Mock responses
        mock_supabase_client.table().insert().execute.return_value.data = [
            {"id": trip_id, **trip_data}
        ]
        mock_supabase_client.table().select().execute.return_value.data = [
            {"id": trip_id, **trip_data}
        ]
        
        await database_service.connect()
        
        # Create trip
        created = await database_service.create_trip(trip_data)
        assert created["id"] == trip_id
        
        # Get trip
        retrieved = await database_service.get_trip(trip_id)
        assert retrieved["id"] == trip_id
        
        # Get user trips
        user_trips = await database_service.get_user_trips("user123")
        assert isinstance(user_trips, list)
    
    async def test_user_operations(self, database_service, mock_supabase_client):
        """Test user CRUD operations."""
        user_data = {"email": "test@example.com", "name": "Test User"}
        user_id = "user123"
        
        # Mock responses
        mock_supabase_client.table().insert().execute.return_value.data = [
            {"id": user_id, **user_data}
        ]
        mock_supabase_client.table().select().execute.return_value.data = [
            {"id": user_id, **user_data}
        ]
        
        await database_service.connect()
        
        # Create user
        created = await database_service.create_user(user_data)
        assert created["id"] == user_id
        
        # Get user
        retrieved = await database_service.get_user(user_id)
        assert retrieved["id"] == user_id
        
        # Get user by email
        by_email = await database_service.get_user_by_email("test@example.com")
        assert by_email["email"] == "test@example.com"


class TestGlobalServiceInstance:
    """Test global service instance management."""
    
    async def test_get_database_service(self, mock_settings, mock_supabase_client):
        """Test getting global service instance."""
        with patch("tripsage_core.services.infrastructure.consolidated_database_service.create_client") as mock_create:
            mock_create.return_value = mock_supabase_client
            
            # First call should create instance
            service1 = await get_database_service()
            assert service1 is not None
            
            # Second call should return same instance
            service2 = await get_database_service()
            assert service2 is service1
            
            # Cleanup
            await close_database_service()
    
    async def test_close_database_service(self, mock_settings, mock_supabase_client):
        """Test closing global service instance."""
        with patch("tripsage_core.services.infrastructure.consolidated_database_service.create_client") as mock_create:
            mock_create.return_value = mock_supabase_client
            
            service = await get_database_service()
            await close_database_service()
            
            # Should create new instance after close
            new_service = await get_database_service()
            assert new_service is not service
            
            # Cleanup
            await close_database_service()


class TestErrorHandling:
    """Test error handling scenarios."""
    
    async def test_resource_not_found(self, database_service, mock_supabase_client):
        """Test resource not found handling."""
        mock_supabase_client.table().select().execute.return_value.data = []
        
        await database_service.connect()
        
        with pytest.raises(CoreResourceNotFoundError) as exc_info:
            await database_service.get_trip("nonexistent")
        
        assert "Trip nonexistent not found" in str(exc_info.value)
    
    async def test_database_error_details(self, database_service, mock_supabase_client):
        """Test database error includes details."""
        error_msg = "Database constraint violation"
        mock_supabase_client.table().insert().execute.side_effect = Exception(error_msg)
        
        await database_service.connect()
        
        with pytest.raises(CoreDatabaseError) as exc_info:
            await database_service.insert("test_table", {"invalid": "data"})
        
        error = exc_info.value
        assert error.code == "INSERT_FAILED"
        assert error.operation == "INSERT"
        assert error.table == "test_table"
        assert error_msg in str(error.details["error"])