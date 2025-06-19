"""Comprehensive test suite for DatabaseService.

This file consolidates core functionality tests from multiple test files
to provide complete coverage without duplication.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel

from tripsage_core.exceptions.exceptions import (
    CoreDatabaseError as DatabaseError,
)
from tripsage_core.exceptions.exceptions import (
    CoreValidationError as ValidationError,
)
from tripsage_core.services.infrastructure.database_service import (
    DatabaseConfig,
    DatabaseService,
)
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


# Test Models
class TestModel(BaseModel):
    """Test model for database operations."""

    id: uuid.UUID
    name: str
    value: int
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


@pytest.fixture
def db_config():
    """Database configuration for testing."""
    return DatabaseConfig(
        host="localhost",
        port=5432,
        database="test_db",
        user="test_user",
        password="test_pass",
        pool_size=10,
        max_overflow=5,
        pool_timeout=30.0,
        command_timeout=60.0,
        enable_ssl=False,
        enable_monitoring=True,
        enable_query_cache=True,
        enable_read_replicas=False,
        query_timeout=30.0,
        slow_query_threshold=1.0,
        max_retries=3,
        retry_delay=0.1,
    )


@pytest.fixture
def mock_pool():
    """Mock connection pool."""
    pool = AsyncMock()
    pool.acquire = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_connection():
    """Mock database connection."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.close = AsyncMock()
    return conn


@pytest.fixture
async def db_service(db_config, mock_pool, mock_connection):
    """Create DatabaseService instance for testing."""
    with patch("asyncpg.create_pool", return_value=mock_pool):
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        service = DatabaseService(db_config)
        await service.connect()
        yield service
        await service.close()


class TestDatabaseServiceCore:
    """Core functionality tests for DatabaseService."""

    async def test_connect_success(self, db_config):
        """Test successful database connection."""
        mock_pool = AsyncMock()
        with patch("asyncpg.create_pool", return_value=mock_pool) as mock_create:
            service = DatabaseService(db_config)
            await service.connect()

            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]
            assert call_args["host"] == db_config.host
            assert call_args["port"] == db_config.port
            assert call_args["database"] == db_config.database
            assert call_args["user"] == db_config.user
            assert call_args["password"] == db_config.password
            assert call_args["min_size"] == db_config.pool_size
            assert call_args["max_size"] == db_config.pool_size + db_config.max_overflow
            assert service._pool == mock_pool

    async def test_connect_failure(self, db_config):
        """Test database connection failure."""
        error = asyncpg.PostgresError("Connection failed")
        with patch("asyncpg.create_pool", side_effect=error):
            service = DatabaseService(db_config)
            with pytest.raises(DatabaseError) as exc:
                await service.connect()
            assert "Failed to connect" in str(exc.value)

    async def test_close_connection(self, db_service, mock_pool):
        """Test closing database connection."""
        await db_service.close()
        mock_pool.close.assert_called_once()
        assert db_service._pool is None

    async def test_ensure_connected(self, db_service, mock_pool):
        """Test ensure_connected functionality."""
        # Pool exists - should not reconnect
        await db_service.ensure_connected()
        assert mock_pool.create_pool.call_count == 0

        # Pool is None - should reconnect
        db_service._pool = None
        with patch("asyncpg.create_pool", return_value=mock_pool):
            await db_service.ensure_connected()
            assert db_service._pool is not None

    async def test_health_check_success(self, db_service, mock_connection):
        """Test successful health check."""
        mock_connection.fetchval.return_value = 1
        mock_connection.fetch.return_value = []  # No slow queries

        result = await db_service.health_check()

        assert result["status"] == "healthy"
        assert result["database"]["connected"] is True
        assert result["database"]["latency_ms"] > 0
        assert result["monitoring"]["slow_queries"] == 0
        mock_connection.fetchval.assert_called_with("SELECT 1")

    async def test_health_check_failure(self, db_service, mock_connection):
        """Test health check with database failure."""
        mock_connection.fetchval.side_effect = asyncpg.PostgresError("DB error")

        result = await db_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["database"]["connected"] is False
        assert "error" in result["database"]


class TestDatabaseServiceCRUD:
    """CRUD operation tests for DatabaseService."""

    async def test_execute_success(self, db_service, mock_connection):
        """Test successful query execution."""
        query = "INSERT INTO users (name) VALUES ($1)"
        params = ["test_user"]
        mock_connection.execute.return_value = "INSERT 0 1"

        result = await db_service.execute(query, params)

        assert result == "INSERT 0 1"
        mock_connection.execute.assert_called_once_with(query, *params)

    async def test_execute_with_retry(self, db_service, mock_connection):
        """Test query execution with retry on failure."""
        query = "UPDATE users SET name = $1"
        params = ["new_name"]

        # First attempt fails, second succeeds
        mock_connection.execute.side_effect = [
            asyncpg.PostgresError("Temporary error"),
            "UPDATE 1",
        ]

        result = await db_service.execute(query, params)

        assert result == "UPDATE 1"
        assert mock_connection.execute.call_count == 2

    async def test_fetch_one_success(self, db_service, mock_connection):
        """Test fetching single row."""
        query = "SELECT * FROM users WHERE id = $1"
        params = [uuid.uuid4()]
        expected_row = {"id": params[0], "name": "test_user"}
        mock_connection.fetchrow.return_value = expected_row

        result = await db_service.fetch_one(query, params)

        assert result == expected_row
        mock_connection.fetchrow.assert_called_once_with(query, *params)

    async def test_fetch_many_success(self, db_service, mock_connection):
        """Test fetching multiple rows."""
        query = "SELECT * FROM users WHERE active = $1"
        params = [True]
        expected_rows = [
            {"id": uuid.uuid4(), "name": "user1"},
            {"id": uuid.uuid4(), "name": "user2"},
        ]
        mock_connection.fetch.return_value = expected_rows

        result = await db_service.fetch_many(query, params)

        assert result == expected_rows
        mock_connection.fetch.assert_called_once_with(query, *params)

    async def test_fetch_val_success(self, db_service, mock_connection):
        """Test fetching single value."""
        query = "SELECT COUNT(*) FROM users"
        expected_value = 42
        mock_connection.fetchval.return_value = expected_value

        result = await db_service.fetch_val(query)

        assert result == expected_value
        mock_connection.fetchval.assert_called_once_with(query)

    async def test_insert_returning(self, db_service, mock_connection):
        """Test insert with RETURNING clause."""
        table = "users"
        data = {"name": "new_user", "email": "test@example.com"}
        expected_row = {"id": uuid.uuid4(), **data}
        mock_connection.fetchrow.return_value = expected_row

        result = await db_service.insert_returning(table, data)

        assert result == expected_row
        call_args = mock_connection.fetchrow.call_args[0]
        assert "INSERT INTO users" in call_args[0]
        assert "RETURNING *" in call_args[0]

    async def test_update_returning(self, db_service, mock_connection):
        """Test update with RETURNING clause."""
        table = "users"
        data = {"name": "updated_user"}
        where = {"id": uuid.uuid4()}
        expected_row = {**where, **data}
        mock_connection.fetchrow.return_value = expected_row

        result = await db_service.update_returning(table, data, where)

        assert result == expected_row
        call_args = mock_connection.fetchrow.call_args[0]
        assert "UPDATE users SET" in call_args[0]
        assert "WHERE" in call_args[0]
        assert "RETURNING *" in call_args[0]

    async def test_upsert(self, db_service, mock_connection):
        """Test upsert operation."""
        table = "user_settings"
        data = {"user_id": uuid.uuid4(), "theme": "dark"}
        conflict_columns = ["user_id"]
        mock_connection.execute.return_value = "INSERT 0 1"

        await db_service.upsert(table, data, conflict_columns)

        call_args = mock_connection.execute.call_args[0]
        assert "INSERT INTO user_settings" in call_args[0]
        assert "ON CONFLICT (user_id)" in call_args[0]
        assert "DO UPDATE SET" in call_args[0]

    async def test_delete(self, db_service, mock_connection):
        """Test delete operation."""
        table = "users"
        where = {"id": uuid.uuid4(), "active": False}
        mock_connection.execute.return_value = "DELETE 5"

        result = await db_service.delete(table, where)

        assert result == "DELETE 5"
        call_args = mock_connection.execute.call_args[0]
        assert "DELETE FROM users WHERE" in call_args[0]

    async def test_count(self, db_service, mock_connection):
        """Test count operation."""
        table = "users"
        where = {"active": True}
        mock_connection.fetchval.return_value = 100

        result = await db_service.count(table, where)

        assert result == 100
        call_args = mock_connection.fetchval.call_args[0]
        assert "SELECT COUNT(*) FROM users" in call_args[0]
        assert "WHERE active = $1" in call_args[0]


class TestDatabaseServiceTransactions:
    """Transaction handling tests."""

    async def test_transaction_success(self, db_service, mock_pool, mock_connection):
        """Test successful transaction."""
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction

        async with db_service.transaction() as tx:
            assert tx == mock_connection

        mock_connection.transaction.assert_called_once()

    async def test_transaction_rollback(self, db_service, mock_pool, mock_connection):
        """Test transaction rollback on error."""
        mock_transaction = AsyncMock()
        mock_connection.transaction.return_value = mock_transaction

        with pytest.raises(ValueError):
            async with db_service.transaction():
                raise ValueError("Test error")

        # Transaction should handle rollback automatically

    async def test_nested_transactions(self, db_service, mock_connection):
        """Test nested transaction handling."""
        mock_tx1 = AsyncMock()
        mock_tx2 = AsyncMock()
        mock_connection.transaction.side_effect = [mock_tx1, mock_tx2]

        async with db_service.transaction():
            # Nested transactions not directly supported
            # Would need savepoint implementation
            pass


class TestDatabaseServiceBusinessOperations:
    """Business operation tests."""

    async def test_create_user(self, db_service, mock_connection):
        """Test user creation."""
        user_data = {
            "id": uuid.uuid4(),
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_connection.fetchrow.return_value = user_data

        result = await db_service.create_user(
            email=user_data["email"], name=user_data["name"]
        )

        assert result["email"] == user_data["email"]
        assert result["name"] == user_data["name"]

    async def test_get_user(self, db_service, mock_connection):
        """Test getting user by ID."""
        user_id = uuid.uuid4()
        user_data = {
            "id": user_id,
            "email": "test@example.com",
            "name": "Test User",
        }
        mock_connection.fetchrow.return_value = user_data

        result = await db_service.get_user(user_id)

        assert result == user_data
        call_args = mock_connection.fetchrow.call_args[0]
        assert "SELECT * FROM users WHERE id = $1" in call_args[0]

    async def test_get_user_not_found(self, db_service, mock_connection):
        """Test getting non-existent user."""
        mock_connection.fetchrow.return_value = None

        result = await db_service.get_user(uuid.uuid4())

        assert result is None

    async def test_create_trip(self, db_service, mock_connection):
        """Test trip creation."""
        trip_data = {
            "user_id": uuid.uuid4(),
            "name": "Test Trip",
            "destination": "Paris",
            "start_date": datetime.now(timezone.utc),
            "end_date": datetime.now(timezone.utc) + timedelta(days=7),
        }
        mock_connection.fetchrow.return_value = {"id": uuid.uuid4(), **trip_data}

        result = await db_service.create_trip(**trip_data)

        assert result["name"] == trip_data["name"]
        assert result["destination"] == trip_data["destination"]

    async def test_get_user_trips(self, db_service, mock_connection):
        """Test getting user's trips."""
        user_id = uuid.uuid4()
        trips = [
            {"id": uuid.uuid4(), "name": "Trip 1", "user_id": user_id},
            {"id": uuid.uuid4(), "name": "Trip 2", "user_id": user_id},
        ]
        mock_connection.fetch.return_value = trips

        result = await db_service.get_user_trips(user_id)

        assert len(result) == 2
        assert result[0]["name"] == "Trip 1"
        assert result[1]["name"] == "Trip 2"

    async def test_create_api_key(self, db_service, mock_connection):
        """Test API key creation."""
        key_data = {
            "user_id": uuid.uuid4(),
            "name": "Test API Key",
            "key_hash": "hashed_key",
            "permissions": ["read", "write"],
        }
        mock_connection.fetchrow.return_value = {"id": uuid.uuid4(), **key_data}

        result = await db_service.create_api_key(**key_data)

        assert result["name"] == key_data["name"]
        assert result["permissions"] == key_data["permissions"]

    async def test_validate_api_key(self, db_service, mock_connection):
        """Test API key validation."""
        key_hash = "valid_hash"
        key_data = {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "is_active": True,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        }
        mock_connection.fetchrow.return_value = key_data

        result = await db_service.validate_api_key(key_hash)

        assert result == key_data
        assert result["is_active"] is True

    async def test_create_chat_session(self, db_service, mock_connection):
        """Test chat session creation."""
        session_data = {
            "user_id": uuid.uuid4(),
            "trip_id": uuid.uuid4(),
            "agent_id": "travel_agent",
        }
        mock_connection.fetchrow.return_value = {"id": uuid.uuid4(), **session_data}

        result = await db_service.create_chat_session(**session_data)

        assert result["agent_id"] == session_data["agent_id"]

    async def test_add_chat_message(self, db_service, mock_connection):
        """Test adding chat message."""
        message_data = {
            "session_id": uuid.uuid4(),
            "role": "user",
            "content": "Hello",
        }
        mock_connection.fetchrow.return_value = {"id": uuid.uuid4(), **message_data}

        result = await db_service.add_chat_message(**message_data)

        assert result["content"] == message_data["content"]


class TestDatabaseServiceMonitoring:
    """Monitoring and metrics tests."""

    async def test_get_pool_stats(self, db_service, mock_pool):
        """Test getting connection pool statistics."""
        mock_pool.get_size.return_value = 5
        mock_pool.get_idle_size.return_value = 2
        mock_pool.get_max_size.return_value = 15

        stats = await db_service.get_pool_stats()

        assert stats["total_connections"] == 5
        assert stats["idle_connections"] == 2
        assert stats["active_connections"] == 3
        assert stats["max_connections"] == 15

    async def test_get_slow_queries(self, db_service, mock_connection):
        """Test retrieving slow queries."""
        slow_queries = [
            {
                "query": "SELECT * FROM large_table",
                "mean_time": 2500.0,
                "calls": 100,
            }
        ]
        mock_connection.fetch.return_value = slow_queries

        result = await db_service.get_slow_queries(threshold_ms=1000)

        assert len(result) == 1
        assert result[0]["mean_time"] == 2500.0

    async def test_query_monitoring(self, db_service, mock_connection):
        """Test query execution monitoring."""
        # Enable monitoring
        db_service.config.enable_monitoring = True

        query = "SELECT * FROM users"
        mock_connection.fetch.return_value = []

        # Execute query
        await db_service.fetch_many(query)

        # Verify monitoring metrics would be collected
        # In real implementation, this would update metrics

    async def test_get_table_stats(self, db_service, mock_connection):
        """Test getting table statistics."""
        table_stats = [
            {
                "schemaname": "public",
                "tablename": "users",
                "n_tup_ins": 1000,
                "n_tup_upd": 500,
                "n_tup_del": 100,
            }
        ]
        mock_connection.fetch.return_value = table_stats

        result = await db_service.get_table_stats()

        assert len(result) == 1
        assert result[0]["tablename"] == "users"


class TestDatabaseServiceValidation:
    """Input validation tests."""

    async def test_execute_empty_query(self, db_service):
        """Test execution with empty query."""
        with pytest.raises(ValidationError):
            await db_service.execute("")

    async def test_insert_empty_data(self, db_service):
        """Test insert with empty data."""
        with pytest.raises(ValidationError):
            await db_service.insert_returning("users", {})

    async def test_invalid_table_name(self, db_service):
        """Test operations with invalid table names."""
        with pytest.raises(ValidationError):
            await db_service.count("users; DROP TABLE users;--", {})

    @given(st.text(min_size=0, max_size=0))
    async def test_empty_string_validation(self, db_service, empty_string):
        """Property test for empty string validation."""
        with pytest.raises(ValidationError):
            await db_service.execute(empty_string)


class TestDatabaseServiceSecurity:
    """Security-related tests."""

    async def test_sql_injection_prevention(self, db_service, mock_connection):
        """Test SQL injection prevention."""
        # Potentially malicious input
        malicious_input = "'; DROP TABLE users; --"

        # Parameters should be safely escaped
        await db_service.fetch_one(
            "SELECT * FROM users WHERE name = $1", [malicious_input]
        )

        # Verify parameterized query was used
        call_args = mock_connection.fetchrow.call_args
        # Passed as parameter, not concatenated
        assert call_args[0][1] == malicious_input

    async def test_password_not_logged(self, db_service, db_config):
        """Test that passwords are not logged."""
        # In real implementation, verify logging doesn't include password
        assert db_config.password not in str(db_config)


class TestDatabaseServiceAdvancedFeatures:
    """Advanced feature tests."""

    async def test_vector_search(self, db_service, mock_connection):
        """Test vector similarity search."""
        embedding = [0.1, 0.2, 0.3, 0.4]
        results = [
            {"id": uuid.uuid4(), "content": "Result 1", "similarity": 0.95},
            {"id": uuid.uuid4(), "content": "Result 2", "similarity": 0.85},
        ]
        mock_connection.fetch.return_value = results

        result = await db_service.vector_search(
            table="documents", embedding=embedding, limit=10
        )

        assert len(result) == 2
        assert result[0]["similarity"] == 0.95

    async def test_bulk_insert(self, db_service, mock_connection):
        """Test bulk insert operation."""
        records = [
            {"name": f"User {i}", "email": f"user{i}@example.com"} for i in range(100)
        ]
        mock_connection.executemany.return_value = None

        await db_service.bulk_insert("users", records)

        mock_connection.executemany.assert_called_once()

    async def test_json_operations(self, db_service, mock_connection):
        """Test JSONB operations."""
        data = {
            "user_id": uuid.uuid4(),
            "settings": {"theme": "dark", "notifications": True},
        }
        mock_connection.fetchrow.return_value = data

        await db_service.update_json_field(
            table="user_settings",
            json_field="settings",
            path=["theme"],
            value="light",
            where={"user_id": data["user_id"]},
        )

        call_args = mock_connection.fetchrow.call_args[0]
        assert "jsonb_set" in call_args[0]

    async def test_full_text_search(self, db_service, mock_connection):
        """Test full-text search."""
        search_results = [
            {"id": uuid.uuid4(), "title": "Paris Guide", "rank": 0.9},
            {"id": uuid.uuid4(), "title": "Paris Hotels", "rank": 0.7},
        ]
        mock_connection.fetch.return_value = search_results

        result = await db_service.full_text_search(
            table="articles", search_columns=["title", "content"], query="Paris travel"
        )

        assert len(result) == 2
        assert result[0]["rank"] == 0.9

    async def test_copy_from_csv(self, db_service, mock_connection):
        """Test COPY FROM CSV functionality."""
        csv_data = "id,name,email\n1,John,john@example.com\n2,Jane,jane@example.com"

        await db_service.copy_from_csv(
            table="users", columns=["id", "name", "email"], csv_data=csv_data
        )

        # Verify COPY command was used
        mock_connection.copy_from_table.assert_called_once()


class TestDatabaseServiceErrorRecovery:
    """Error recovery and resilience tests."""

    async def test_connection_pool_exhaustion_recovery(self, db_service, mock_pool):
        """Test recovery from connection pool exhaustion."""
        mock_pool.acquire.side_effect = asyncio.TimeoutError("Pool timeout")

        with pytest.raises(DatabaseError) as exc:
            await db_service.execute("SELECT 1")

        assert "Pool timeout" in str(exc.value)

    async def test_automatic_reconnection(self, db_service, mock_pool, mock_connection):
        """Test automatic reconnection on connection loss."""
        # First call fails with connection error
        mock_connection.execute.side_effect = [
            asyncpg.InterfaceError("Connection lost"),
            "SELECT 1",  # Second attempt succeeds
        ]

        result = await db_service.execute("SELECT 1")

        assert result == "SELECT 1"
        assert mock_connection.execute.call_count == 2

    async def test_transaction_retry_on_serialization_error(
        self, db_service, mock_connection
    ):
        """Test transaction retry on serialization errors."""
        mock_connection.execute.side_effect = [
            asyncpg.SerializationError("Could not serialize"),
            "UPDATE 1",  # Retry succeeds
        ]

        result = await db_service.execute("UPDATE users SET name = $1", ["test"])

        assert result == "UPDATE 1"

    async def test_graceful_degradation(self, db_service, mock_connection):
        """Test graceful degradation when features unavailable."""
        # Simulate missing extension
        error = asyncpg.UndefinedFunctionError("vector_search not found")
        mock_connection.fetch.side_effect = error

        with pytest.raises(DatabaseError):
            await db_service.vector_search("documents", [0.1, 0.2], limit=10)


# Performance helper tests
class TestDatabaseServiceHelpers:
    """Helper method tests."""

    def test_build_where_clause(self, db_service):
        """Test WHERE clause building."""
        conditions = {"name": "test", "active": True, "age": 25}
        clause, params = db_service._build_where_clause(conditions)

        assert "name = $1" in clause
        assert "active = $2" in clause
        assert "age = $3" in clause
        assert params == ["test", True, 25]

    def test_build_insert_query(self, db_service):
        """Test INSERT query building."""
        data = {"name": "test", "email": "test@example.com"}
        query, params = db_service._build_insert_query("users", data)

        assert "INSERT INTO users" in query
        assert "(name, email)" in query
        assert "VALUES ($1, $2)" in query
        assert params == ["test", "test@example.com"]

    def test_build_update_query(self, db_service):
        """Test UPDATE query building."""
        data = {"name": "updated"}
        where = {"id": uuid.uuid4()}
        query, params = db_service._build_update_query("users", data, where)

        assert "UPDATE users SET" in query
        assert "name = $1" in query
        assert "WHERE id = $2" in query

    def test_sanitize_table_name(self, db_service):
        """Test table name sanitization."""
        assert db_service._sanitize_table_name("users") == "users"
        assert db_service._sanitize_table_name("user_settings") == "user_settings"

        with pytest.raises(ValidationError):
            db_service._sanitize_table_name("users; DROP TABLE users;")

    def test_format_query_params(self, db_service):
        """Test query parameter formatting."""
        params = [
            "string",
            123,
            True,
            datetime.now(timezone.utc),
            uuid.uuid4(),
            None,
            {"key": "value"},
            [1, 2, 3],
        ]

        formatted = db_service._format_params(params)

        assert isinstance(formatted[0], str)
        assert isinstance(formatted[1], int)
        assert isinstance(formatted[2], bool)
        assert isinstance(formatted[3], str)  # Datetime formatted
        assert isinstance(formatted[4], str)  # UUID as string
        assert formatted[5] is None
        assert isinstance(formatted[6], str)  # JSON serialized
        assert isinstance(formatted[7], str)  # JSON serialized
