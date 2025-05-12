"""Tests for the NeonQueryBuilder class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.providers import NeonProvider, NeonQueryResult


class TestNeonQueryBuilder:
    """Tests for the NeonQueryBuilder inner class."""

    def test_init(self):
        """Test initialization of the NeonQueryBuilder."""
        # Arrange
        mock_pool = MagicMock()
        table_name = "users"

        # Act
        builder = NeonProvider.NeonQueryBuilder(mock_pool, table_name)

        # Assert
        assert builder.pool is mock_pool
        assert builder.table_name == table_name
        assert builder._select_columns == "*"
        assert builder._where_clauses == []
        assert builder._where_params == []
        assert builder._param_counter == 0
        assert builder._order_by is None
        assert builder._limit_val is None
        assert builder._offset_val is None
        assert builder._range_from is None
        assert builder._range_to is None
        assert builder._operation is None
        assert builder._data is None

    def test_select(self):
        """Test the select method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.select("id, name")

        # Assert
        assert result is builder
        assert builder._select_columns == "id, name"

    def test_eq(self):
        """Test the eq method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.eq("id", 1)

        # Assert
        assert result is builder
        assert builder._where_clauses == ["id = $1"]
        assert builder._where_params == [1]
        assert builder._param_counter == 1

    def test_neq(self):
        """Test the neq method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.neq("id", 1)

        # Assert
        assert result is builder
        assert builder._where_clauses == ["id != $1"]
        assert builder._where_params == [1]
        assert builder._param_counter == 1

    def test_gt(self):
        """Test the gt method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.gt("age", 18)

        # Assert
        assert result is builder
        assert builder._where_clauses == ["age > $1"]
        assert builder._where_params == [18]
        assert builder._param_counter == 1

    def test_lt(self):
        """Test the lt method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.lt("age", 65)

        # Assert
        assert result is builder
        assert builder._where_clauses == ["age < $1"]
        assert builder._where_params == [65]
        assert builder._param_counter == 1

    def test_gte(self):
        """Test the gte method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.gte("age", 18)

        # Assert
        assert result is builder
        assert builder._where_clauses == ["age >= $1"]
        assert builder._where_params == [18]
        assert builder._param_counter == 1

    def test_lte(self):
        """Test the lte method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.lte("age", 65)

        # Assert
        assert result is builder
        assert builder._where_clauses == ["age <= $1"]
        assert builder._where_params == [65]
        assert builder._param_counter == 1

    def test_order(self):
        """Test the order method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.order("name")

        # Assert
        assert result is builder
        assert builder._order_by == "name ASC"

    def test_order_descending(self):
        """Test the order method with descending order."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.order("age", ascending=False)

        # Assert
        assert result is builder
        assert builder._order_by == "age DESC"

    def test_limit(self):
        """Test the limit method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.limit(10)

        # Assert
        assert result is builder
        assert builder._limit_val == 10

    def test_offset(self):
        """Test the offset method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.offset(5)

        # Assert
        assert result is builder
        assert builder._offset_val == 5

    def test_range(self):
        """Test the range method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.range(5, 15)

        # Assert
        assert result is builder
        assert builder._range_from == 5
        assert builder._range_to == 15

    def test_insert(self):
        """Test the insert method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        data = {"name": "test", "email": "test@example.com"}

        # Act
        result = builder.insert(data)

        # Assert
        assert result is builder
        assert builder._operation == "INSERT"
        assert builder._data == [data]

    def test_insert_multiple(self):
        """Test the insert method with multiple records."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        data = [
            {"name": "test1", "email": "test1@example.com"},
            {"name": "test2", "email": "test2@example.com"},
        ]

        # Act
        result = builder.insert(data)

        # Assert
        assert result is builder
        assert builder._operation == "INSERT"
        assert builder._data == data

    def test_update(self):
        """Test the update method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        data = {"name": "updated", "email": "updated@example.com"}

        # Act
        result = builder.update(data)

        # Assert
        assert result is builder
        assert builder._operation == "UPDATE"
        assert builder._data == data

    def test_delete(self):
        """Test the delete method."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")

        # Act
        result = builder.delete()

        # Assert
        assert result is builder
        assert builder._operation == "DELETE"

    def test_get_debug_query_select(self):
        """Test the _get_debug_query method for SELECT."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.select("name, email").eq("id", 1).order("name").limit(10)

        # Act
        query = builder._get_debug_query()

        # Assert
        assert "SELECT name, email FROM users" in query
        assert "WHERE id = $1" in query
        assert "ORDER BY name ASC" in query
        assert "LIMIT 10" in query

    def test_get_debug_query_insert(self):
        """Test the _get_debug_query method for INSERT."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.insert({"name": "test"})

        # Act
        query = builder._get_debug_query()

        # Assert
        assert "INSERT INTO users" in query

    def test_get_debug_query_update(self):
        """Test the _get_debug_query method for UPDATE."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.update({"name": "test"}).eq("id", 1)

        # Act
        query = builder._get_debug_query()

        # Assert
        assert "UPDATE users SET" in query
        assert "WHERE id = $1" in query

    def test_get_debug_query_delete(self):
        """Test the _get_debug_query method for DELETE."""
        # Arrange
        mock_pool = MagicMock()
        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.delete().eq("id", 1)

        # Act
        query = builder._get_debug_query()

        # Assert
        assert "DELETE FROM users" in query
        assert "WHERE id = $1" in query

    async def test_execute_select(self):
        """Test the execute method for SELECT."""
        # Arrange
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"id": 1, "name": "test1"},
            {"id": 2, "name": "test2"},
        ]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.select("id, name").eq("id", 1).order("name").limit(10)

        # Act
        result = await builder.execute()

        # Assert
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 2
        assert result.data[0]["id"] == 1
        assert result.data[1]["id"] == 2
        mock_conn.fetch.assert_called_once()

    async def test_execute_insert(self):
        """Test the execute method for INSERT."""
        # Arrange
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{"id": 1, "name": "test"}]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.insert({"name": "test"})

        # Act
        result = await builder.execute()

        # Assert
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 1
        assert result.data[0]["id"] == 1
        mock_conn.fetch.assert_called_once()

    async def test_execute_update(self):
        """Test the execute method for UPDATE."""
        # Arrange
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{"id": 1, "name": "updated"}]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.update({"name": "updated"}).eq("id", 1)

        # Act
        result = await builder.execute()

        # Assert
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 1
        assert result.data[0]["name"] == "updated"
        mock_conn.fetch.assert_called_once()

    async def test_execute_delete(self):
        """Test the execute method for DELETE."""
        # Arrange
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [{"id": 1, "name": "test"}]
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.delete().eq("id", 1)

        # Act
        result = await builder.execute()

        # Assert
        assert isinstance(result, NeonQueryResult)
        assert len(result.data) == 1
        mock_conn.fetch.assert_called_once()

    async def test_execute_error(self):
        """Test error handling in the execute method."""
        # Arrange
        mock_pool = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = Exception("Query execution failed")
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        builder = NeonProvider.NeonQueryBuilder(mock_pool, "users")
        builder.select("id, name")

        # Act and Assert
        with pytest.raises(Exception) as excinfo:
            await builder.execute()

        assert "Query execution error" in str(excinfo.value)
