"""Tests for the Supabase database provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.exceptions import (
    ConnectionError,
    DatabaseError,
    NotConnectedError,
    QueryError,
)
from src.db.providers import SupabaseProvider


class TestSupabaseProvider:
    """Tests for the SupabaseProvider class."""

    def test_init(self):
        """Test initialization of the SupabaseProvider."""
        # Arrange
        url = "https://example.supabase.co"
        key = "test-key"
        options = {"timeout": 5.0}

        # Act
        provider = SupabaseProvider(url, key, options)

        # Assert
        assert provider.url == url
        assert provider.key == key
        assert provider.options == options
        assert provider.client is None
        assert provider._connected is False
        assert provider._in_transaction is False

    async def test_connect_success(self, mock_supabase_client):
        """Test successful connection to Supabase."""
        # Arrange
        provider = SupabaseProvider("https://example.supabase.co", "test-key")

        # Act
        with patch("src.db.providers.create_client", return_value=mock_supabase_client):
            await provider.connect()

        # Assert
        assert provider.is_connected is True
        assert provider.client is mock_supabase_client

    async def test_connect_failure(self):
        """Test connection failure to Supabase."""
        # Arrange
        provider = SupabaseProvider("https://example.supabase.co", "test-key")

        # Act and Assert
        with patch(
            "src.db.providers.create_client", side_effect=Exception("Connection failed")
        ):
            with pytest.raises(ConnectionError) as excinfo:
                await provider.connect()

            assert "Failed to connect to Supabase" in str(excinfo.value)
            assert provider.is_connected is False
            assert provider.client is None

    async def test_disconnect(self, mock_supabase_provider):
        """Test disconnection from Supabase."""
        # Act
        await mock_supabase_provider.disconnect()

        # Assert
        assert mock_supabase_provider.is_connected is False
        assert mock_supabase_provider.client is None

    def test_table(self, mock_supabase_provider):
        """Test getting a table query builder."""
        # Act
        table_builder = mock_supabase_provider.table("users")

        # Assert
        assert table_builder is not None
        mock_supabase_provider.client.table.assert_called_once_with("users")

    def test_table_not_connected(self):
        """Test getting a table query builder when not connected."""
        # Arrange
        provider = SupabaseProvider("https://example.supabase.co", "test-key")

        # Act and Assert
        with pytest.raises(NotConnectedError):
            provider.table("users")

    async def test_execute_sql(self, mock_supabase_provider):
        """Test executing a SQL query."""
        # Arrange
        query = "SELECT * FROM users"
        params = {"limit": 10}
        mock_supabase_provider.client.rpc.return_value.execute.return_value = MagicMock(
            data=[{"id": 1}]
        )

        # Act
        result = await mock_supabase_provider.execute_sql(query, params)

        # Assert
        mock_supabase_provider.client.rpc.assert_called_once_with(
            "exec_sql", {"query": query, "limit": 10}
        )
        assert result.data[0]["id"] == 1

    async def test_execute_sql_not_connected(self):
        """Test executing a SQL query when not connected."""
        # Arrange
        provider = SupabaseProvider("https://example.supabase.co", "test-key")

        # Act and Assert
        with pytest.raises(NotConnectedError):
            await provider.execute_sql("SELECT * FROM users")

    async def test_execute_sql_failure(self, mock_supabase_provider):
        """Test failure when executing a SQL query."""
        # Arrange
        mock_supabase_provider.client.rpc.return_value.execute.side_effect = Exception(
            "Query failed"
        )

        # Act and Assert
        with pytest.raises(QueryError) as excinfo:
            await mock_supabase_provider.execute_sql("SELECT * FROM users")

        assert "Failed to execute SQL query" in str(excinfo.value)

    async def test_execute_prepared_sql(self, mock_supabase_provider):
        """Test executing a prepared SQL statement."""
        # Arrange
        query = "SELECT * FROM users WHERE id = $1"
        params = [1]

        # Mock the execute_sql method
        mock_supabase_provider.execute_sql = AsyncMock()

        # Act
        await mock_supabase_provider.execute_prepared_sql(query, params)

        # Assert
        mock_supabase_provider.execute_sql.assert_called_once()
        # Check that the query was modified to use named parameters
        called_query, called_params = mock_supabase_provider.execute_sql.call_args[0]
        assert ":param_0" in called_query
        assert "param_0" in called_params

    async def test_tables_exist(self, mock_supabase_provider):
        """Test checking if tables exist."""
        # Arrange
        tables = ["users", "posts"]
        mock_response = MagicMock(data=[{"exists": True}])
        mock_supabase_provider.execute_sql = AsyncMock(return_value=mock_response)

        # Act
        result = await mock_supabase_provider.tables_exist(tables)

        # Assert
        assert len(result) == 2
        assert result["users"] is True
        assert result["posts"] is True

    async def test_transaction_success(self, mock_supabase_provider):
        """Test successful transaction."""
        # Arrange
        mock_supabase_provider.execute_sql = AsyncMock()

        # Act
        async with mock_supabase_provider.transaction():
            # Execute some query in the transaction
            await mock_supabase_provider.execute_sql(
                "INSERT INTO users (name) VALUES ('test')"
            )

        # Assert
        assert mock_supabase_provider._in_transaction is False
        # Check that BEGIN and COMMIT were called
        assert mock_supabase_provider.execute_sql.call_args_list[0][0][0] == "BEGIN"
        assert mock_supabase_provider.execute_sql.call_args_list[2][0][0] == "COMMIT"

    async def test_transaction_failure(self, mock_supabase_provider):
        """Test transaction failure and rollback."""
        # Arrange
        mock_supabase_provider.execute_sql = AsyncMock()
        mock_supabase_provider.execute_sql.side_effect = [
            None,  # BEGIN succeeds
            QueryError("Query failed"),  # Query fails
            None,  # ROLLBACK succeeds
        ]

        # Act and Assert
        with pytest.raises(QueryError):
            async with mock_supabase_provider.transaction():
                await mock_supabase_provider.execute_sql(
                    "INSERT INTO users (name) VALUES ('test')"
                )

        # Assert
        assert mock_supabase_provider._in_transaction is False
        # Check that BEGIN and ROLLBACK were called
        assert mock_supabase_provider.execute_sql.call_args_list[0][0][0] == "BEGIN"
        assert mock_supabase_provider.execute_sql.call_args_list[2][0][0] == "ROLLBACK"

    async def test_transaction_rollback(self, mock_supabase_provider):
        """Test transaction rollback."""
        # Arrange
        mock_supabase_provider.execute_sql = AsyncMock()
        mock_supabase_provider.execute_sql.side_effect = [
            None,  # BEGIN succeeds
            None,  # Query succeeds
            None,  # ROLLBACK succeeds
        ]

        # Act and Assert
        with pytest.raises(DatabaseError):
            async with mock_supabase_provider.transaction():
                await mock_supabase_provider.execute_sql(
                    "INSERT INTO users (id, email) VALUES (:id, :email)",
                    {"id": "123", "email": "test@example.com"},
                )
                # Raise an error to cause a rollback
                raise ValueError("Test error")

        # Assert
        assert mock_supabase_provider._in_transaction is False
        # Check that BEGIN and ROLLBACK were called
        assert mock_supabase_provider.execute_sql.call_args_list[0][0][0] == "BEGIN"
        assert mock_supabase_provider.execute_sql.call_args_list[2][0][0] == "ROLLBACK"
