"""Test database connection factory implementation.

Tests the DatabaseConnectionFactory for secure connection handling,
URL validation, and proper asyncpg pool management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from pydantic import SecretStr

from tripsage_core.config import Settings
from tripsage_core.database.factory import (
    DatabaseConnectionFactory,
    get_connection_factory,
    get_database_connection,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Settings(
        postgres_url="postgresql://testuser:testpass@localhost:5432/testdb",
        database_url="https://test.supabase.co",
        database_public_key=SecretStr("test-public-key"),
        database_service_key=SecretStr("test-service-key"),
        _env_file=None,
    )
    return settings


@pytest.fixture
def factory(mock_settings):
    """Create a factory instance with mock settings."""
    return DatabaseConnectionFactory(mock_settings)


class TestDatabaseConnectionFactory:
    """Test DatabaseConnectionFactory class."""

    def test_init_with_custom_settings(self, mock_settings):
        """Test factory initialization with custom settings."""
        factory = DatabaseConnectionFactory(mock_settings)
        assert factory.settings == mock_settings
        assert factory._pool is None

    def test_init_with_default_settings(self):
        """Test factory initialization with default settings."""
        with patch("tripsage_core.database.factory.get_settings") as mock_get_settings:
            mock_get_settings.return_value = MagicMock()
            factory = DatabaseConnectionFactory()
            assert factory.settings == mock_get_settings.return_value
            assert factory._pool is None

    def test_validate_connection_url_valid(self, factory):
        """Test URL validation with valid URLs."""
        # Valid PostgreSQL URLs
        valid_urls = [
            "postgresql://user:pass@localhost:5432/db",
            "postgres://user:pass@localhost:5432/db",
            "postgresql+asyncpg://user:pass@localhost:5432/db",
            "postgresql://user:pass@example.com/mydb",
        ]

        for url in valid_urls:
            # Should not raise any exception
            factory._validate_connection_url(url)

    def test_validate_connection_url_invalid_scheme(self, factory):
        """Test URL validation with invalid schemes."""
        invalid_urls = [
            "mysql://user:pass@localhost:3306/db",
            "mongodb://user:pass@localhost:27017/db",
            "redis://localhost:6379",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError, match="Invalid scheme"):
                factory._validate_connection_url(url)

    def test_validate_connection_url_dangerous_patterns(self, factory):
        """Test URL validation detects dangerous SQL patterns."""
        dangerous_urls = [
            "postgresql://user:pass@localhost:5432/db;DROP TABLE users",
            "postgresql://user:pass@localhost:5432/db--comment",
            "postgresql://user:pass@localhost:5432/db/*comment*/",
            "postgresql://user:pass@localhost:5432/db;CREATE TABLE hack",
        ]

        for url in dangerous_urls:
            with pytest.raises(ValueError, match="dangerous pattern"):
                factory._validate_connection_url(url)

    def test_validate_connection_url_malformed(self, factory):
        """Test URL validation with malformed URLs."""
        malformed_urls = [
            "not-a-url",
            "postgresql://",
            "://missing-scheme",
            "postgresql:missing-slashes",
        ]

        for url in malformed_urls:
            with pytest.raises(ValueError, match="Invalid"):
                factory._validate_connection_url(url)

    def test_get_pool_config(self, factory):
        """Test pool configuration settings."""
        config = factory._get_pool_config()

        assert config["min_size"] == 5
        assert config["max_size"] == 20
        assert config["max_queries"] == 50000
        assert config["max_inactive_connection_lifetime"] == 300.0
        assert config["command_timeout"] == 60.0
        assert config["server_settings"]["application_name"] == "tripsage"
        assert config["server_settings"]["jit"] == "off"

    @pytest.mark.asyncio
    async def test_create_pool_success(self, factory, mock_settings):
        """Test successful pool creation."""
        # Create a proper mock for the connection
        mock_connection = AsyncMock()
        mock_connection.fetchval = AsyncMock(return_value=1)

        # Create a proper mock for pool.acquire() context manager
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context

        with patch(
            "asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool
        ) as mock_create:
            pool = await factory.create_pool()

            assert pool == mock_pool
            assert factory._pool == mock_pool

            # Verify pool was created with correct URL
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert "postgres://" in call_args[0][0]
            assert "testuser:testpass@localhost:5432/testdb" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_pool_returns_existing(self, factory):
        """Test create_pool returns existing pool if already created."""
        mock_pool = AsyncMock()
        factory._pool = mock_pool

        with patch("asyncpg.create_pool") as mock_create:
            pool = await factory.create_pool()

            assert pool == mock_pool
            # Should not create a new pool
            mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_pool_url_conversion(self, factory):
        """Test pool creation properly converts URL for asyncpg."""
        # Create a proper mock for the connection
        mock_connection = AsyncMock()
        mock_connection.fetchval = AsyncMock(return_value=1)

        # Create a proper mock for pool.acquire() context manager
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context

        # Test with URL that needs conversion
        factory.settings.postgres_url = "postgresql+asyncpg://user:pass@host/db"

        with patch(
            "asyncpg.create_pool", new_callable=AsyncMock, return_value=mock_pool
        ) as mock_create:
            await factory.create_pool()

            # Should convert to plain postgres:// for asyncpg
            call_args = mock_create.call_args[0][0]
            assert call_args == "postgres://user:pass@host/db"

    @pytest.mark.asyncio
    async def test_create_pool_validation_failure(self, factory):
        """Test pool creation fails on URL validation."""
        factory.settings.postgres_url = (
            "postgresql://user:pass@host/db;DROP TABLE users"
        )

        with pytest.raises(ValueError, match="dangerous pattern"):
            await factory.create_pool()

    @pytest.mark.asyncio
    async def test_create_pool_connection_failure(self, factory):
        """Test pool creation handles connection failures."""
        with (
            patch(
                "asyncpg.create_pool",
                side_effect=asyncpg.PostgresError("Connection failed"),
            ),
            pytest.raises(asyncpg.PostgresError),
        ):
            await factory.create_pool()

    @pytest.mark.asyncio
    async def test_get_connection(self, factory):
        """Test getting a connection from the pool."""
        mock_connection = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_connection)
        factory._pool = mock_pool

        conn = await factory.get_connection()

        assert conn == mock_connection
        mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_creates_pool_if_needed(self, factory):
        """Test get_connection creates pool if not initialized."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_connection)

        async def mock_create_pool():
            factory._pool = mock_pool
            return mock_pool

        with patch.object(
            factory, "create_pool", side_effect=mock_create_pool
        ) as mock_create:
            conn = await factory.get_connection()

            assert conn == mock_connection
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, factory):
        """Test closing the connection pool."""
        mock_pool = AsyncMock()
        factory._pool = mock_pool

        await factory.close()

        mock_pool.close.assert_called_once()
        assert factory._pool is None

    @pytest.mark.asyncio
    async def test_close_no_pool(self, factory):
        """Test closing when no pool exists."""
        # Should not raise any exception
        await factory.close()
        assert factory._pool is None

    @pytest.mark.asyncio
    async def test_test_connection_success(self, factory):
        """Test successful connection test."""
        mock_connection = AsyncMock()
        mock_connection.fetchval = AsyncMock(return_value=1)

        # Create a proper mock for pool.acquire() context manager
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context

        with patch.object(factory, "create_pool", return_value=mock_pool):
            result = await factory.test_connection()

            assert result is True
            mock_connection.fetchval.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, factory):
        """Test failed connection test."""
        with patch.object(
            factory, "create_pool", side_effect=Exception("Connection failed")
        ):
            result = await factory.test_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_execute_query(self, factory):
        """Test executing a query."""
        mock_result = [{"id": 1, "name": "test"}]
        mock_connection = AsyncMock()
        mock_connection.fetch = AsyncMock(return_value=mock_result)

        # Create a proper mock for pool.acquire() context manager
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context
        factory._pool = mock_pool

        result = await factory.execute_query("SELECT * FROM users WHERE id = $1", 1)

        assert str(mock_result) in result
        mock_connection.fetch.assert_called_once_with(
            "SELECT * FROM users WHERE id = $1", 1, timeout=None
        )

    @pytest.mark.asyncio
    async def test_execute_query_with_timeout(self, factory):
        """Test executing a query with timeout."""
        mock_connection = AsyncMock()
        mock_connection.fetch = AsyncMock(return_value=[])

        # Create a proper mock for pool.acquire() context manager
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context
        factory._pool = mock_pool

        await factory.execute_query("SELECT 1", timeout=30.0)

        mock_connection.fetch.assert_called_once_with("SELECT 1", timeout=30.0)

    @pytest.mark.asyncio
    async def test_execute_query_creates_pool(self, factory):
        """Test execute_query creates pool if needed."""
        mock_connection = AsyncMock()
        mock_connection.fetch = AsyncMock(return_value=[])

        # Create a proper mock for pool.acquire() context manager
        mock_acquire_context = AsyncMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_connection)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)

        # Create mock pool
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = mock_acquire_context

        async def mock_create_pool():
            factory._pool = mock_pool
            return mock_pool

        with patch.object(
            factory, "create_pool", side_effect=mock_create_pool
        ) as mock_create:
            await factory.execute_query("SELECT 1")

            mock_create.assert_called_once()


class TestModuleLevelFunctions:
    """Test module-level factory functions."""

    def test_get_connection_factory_singleton(self):
        """Test get_connection_factory returns singleton."""
        factory1 = get_connection_factory()
        factory2 = get_connection_factory()

        assert factory1 is factory2

    @pytest.mark.asyncio
    async def test_get_database_connection(self):
        """Test get_database_connection function."""
        mock_connection = AsyncMock()
        mock_factory = AsyncMock()
        mock_factory.get_connection = AsyncMock(return_value=mock_connection)

        with patch(
            "tripsage_core.database.factory.get_connection_factory",
            return_value=mock_factory,
        ):
            conn = await get_database_connection()

            assert conn == mock_connection
            mock_factory.get_connection.assert_called_once()


class TestSecurityPatterns:
    """Test security validation patterns."""

    def test_dangerous_patterns_comprehensive(self):
        """Test comprehensive dangerous pattern detection."""
        # Create a factory instance
        factory = DatabaseConnectionFactory()

        # Test various SQL injection attempts
        dangerous_inputs = [
            # Basic SQL commands
            "DROP TABLE users",
            "ALTER TABLE accounts",
            "CREATE DATABASE hack",
            "DELETE FROM customers",
            "TRUNCATE TABLE orders",
            # With different casing
            "drop table users",
            "DrOp TaBlE users",
            # With semicolons
            "; DROP TABLE users",
            "valid_input; DELETE FROM data",
            # SQL comments
            "-- DROP TABLE users",
            "/* DELETE FROM users */",
            # Complex patterns
            "';DROP TABLE users--",
            "1'; DROP DATABASE main; --",
        ]

        for pattern in dangerous_inputs:
            url = f"postgresql://user:pass@localhost:5432/db?options={pattern}"
            with pytest.raises(ValueError, match="dangerous pattern"):
                factory._validate_connection_url(url)
