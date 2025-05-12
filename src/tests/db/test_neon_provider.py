"""Tests for the Neon database provider."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.exceptions import ConnectionError, NotConnectedError
from src.db.providers import NeonProvider, NeonQueryResult


class TestNeonProvider:
    """Tests for the NeonProvider class."""

    def test_init(self):
        """Test initialization of the NeonProvider."""
        # Arrange
        connection_string = "postgresql://user:password@test-host:5432/testdb"
        min_size = 2
        max_size = 10
        max_inactive_connection_lifetime = 120.0

        # Act
        provider = NeonProvider(
            connection_string=connection_string,
            min_size=min_size,
            max_size=max_size,
            max_inactive_connection_lifetime=max_inactive_connection_lifetime,
        )

        # Assert
        assert provider.connection_string == connection_string
        assert provider.min_size == min_size
        assert provider.max_size == max_size
        assert (
            provider.max_inactive_connection_lifetime
            == max_inactive_connection_lifetime
        )
        assert provider.pool is None
        assert provider._connected is False
        assert provider._transaction_connections == {}

    async def test_connect_success(self, mock_asyncpg_pool):
        """Test successful connection to Neon."""
        # Arrange
        provider = NeonProvider("postgresql://user:password@test-host:5432/testdb")

        # Act
        with patch("asyncpg.create_pool", return_value=mock_asyncpg_pool):
            await provider.connect()

        # Assert
        assert provider.is_connected is True
        assert provider.pool is mock_asyncpg_pool

    async def test_connect_failure(self):
        """Test connection failure to Neon."""
        # Arrange
        provider = NeonProvider("postgresql://user:password@test-host:5432/testdb")

        # Act and Assert
        with patch("asyncpg.create_pool", side_effect=Exception("Connection failed")):
            with pytest.raises(ConnectionError) as excinfo:
                await provider.connect()

            assert "Failed to connect to Neon" in str(excinfo.value)
            assert provider.is_connected is False
            assert provider.pool is None

    async def test_disconnect(self, mock_neon_provider):
        """Test disconnection from Neon."""
        # Act
        await mock_neon_provider.disconnect()

        # Assert
        assert mock_neon_provider.is_connected is False
        assert mock_neon_provider.pool is None

    def test_table(self, mock_neon_provider):
        """Test getting a table query builder."""
        # Act
        table_builder = mock_neon_provider.table("users")

        # Assert
        assert table_builder is not None
        assert table_builder.table_name == "users"
        assert table_builder.pool is mock_neon_provider.pool

    def test_table_not_connected(self):
        """Test getting a table query builder when not connected."""
        # Arrange
        provider = NeonProvider("postgresql://user:password@test-host:5432/testdb")

        # Act and Assert
        with pytest.raises(NotConnectedError):
            provider.table("users")

    async def test_execute_sql(self, mock_neon_provider):
        """Test executing a SQL query."""
        # Arrange
        query = "SELECT * FROM users"
        params = {"user_id": 1}

        # Act
        result = await mock_neon_provider.execute_sql(query, params)

        # Assert
        mock_neon_provider.pool.acquire.assert_called_once()
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1

    async def test_execute_sql_not_connected(self):
        """Test executing a SQL query when not connected."""
        # Arrange
        provider = NeonProvider("postgresql://user:password@test-host:5432/testdb")

        # Act and Assert
        with pytest.raises(NotConnectedError):
            await provider.execute_sql("SELECT * FROM users")

    async def test_execute_prepared_sql(self, mock_neon_provider):
        """Test executing a prepared SQL statement."""
        # Arrange
        query = "SELECT * FROM users WHERE id = $1"
        params = [1]

        # Act
        result = await mock_neon_provider.execute_prepared_sql(query, params)

        # Assert
        mock_neon_provider.pool.acquire.assert_called_once()
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 1

    async def test_tables_exist(self, mock_neon_provider):
        """Test checking if tables exist."""
        # Arrange
        tables = ["users", "posts"]
        # The fetchrow method is already mocked in mock_asyncpg_pool 
        # to return {"exists": True}

        # Act
        result = await mock_neon_provider.tables_exist(tables)

        # Assert
        assert len(result) == 2
        assert result["users"] is True
        assert result["posts"] is True

    async def test_rpc(self, mock_neon_provider):
        """Test calling an RPC function."""
        # Arrange
        function_name = "get_user"
        params = {"id": 1}

        # Mock the execute_prepared_sql method
        mock_neon_provider.execute_prepared_sql = AsyncMock(
            return_value=NeonQueryResult(data=[{"id": 1, "name": "test"}])
        )

        # Act
        result = await mock_neon_provider.rpc(function_name, params)

        # Assert
        mock_neon_provider.execute_prepared_sql.assert_called_once()
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1

    async def test_exec_sql_rpc(self, mock_neon_provider):
        """Test calling the exec_sql RPC function."""
        # Arrange
        params = {"query": "SELECT 1", "param1": "value1"}

        # Mock the execute_sql method
        mock_neon_provider.execute_sql = AsyncMock(
            return_value=NeonQueryResult(data=[{"result": 1}])
        )

        # Act
        result = await mock_neon_provider.rpc("exec_sql", params)

        # Assert
        mock_neon_provider.execute_sql.assert_called_once_with(
            "SELECT 1", {"param1": "value1"}
        )
        assert isinstance(result, NeonQueryResult)

    async def test_transaction_success(self, mock_neon_provider):
        """Test successful transaction."""
        # Arrange
        mock_conn = mock_neon_provider.pool.acquire.return_value.__aenter__.return_value

        # Act
        async with mock_neon_provider.transaction():
            # Transaction is started
            pass

        # Assert
        mock_conn.execute.assert_any_call("BEGIN")
        mock_conn.execute.assert_any_call("COMMIT")
        assert len(mock_neon_provider._transaction_connections) == 0

    async def test_transaction_failure(self, mock_neon_provider):
        """Test transaction failure and rollback."""
        # Arrange
        mock_conn = mock_neon_provider.pool.acquire.return_value.__aenter__.return_value

        # Act and Assert
        try:
            async with mock_neon_provider.transaction():
                raise Exception("Transaction failed")
        except Exception:
            pass

        # Assert
        mock_conn.execute.assert_any_call("BEGIN")
        mock_conn.execute.assert_any_call("ROLLBACK")
        assert len(mock_neon_provider._transaction_connections) == 0

    async def test_get_connection_no_transaction(self, mock_neon_provider):
        """Test getting a connection when not in a transaction."""
        # Act
        conn = await mock_neon_provider._get_connection()

        # Assert
        assert conn is None

    async def test_begin_transaction_already_in_transaction(self, mock_neon_provider):
        """Test beginning a transaction when already in a transaction."""
        # Arrange
        task_id = id(asyncio.current_task())
        mock_neon_provider._transaction_connections[task_id] = MagicMock()

        # Act and Assert
        with pytest.raises(Exception) as excinfo:
            await mock_neon_provider._begin_transaction()

        assert "Transaction already in progress" in str(excinfo.value)
