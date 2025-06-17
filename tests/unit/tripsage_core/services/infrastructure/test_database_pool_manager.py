"""
Comprehensive tests for the simplified DatabasePoolManager.

Tests the Supavisor-based implementation that leverages built-in connection pooling
instead of custom pooling logic. Validates that the simplified design maintains
compatibility while removing redundant functionality.
"""

from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.services.infrastructure.database_pool_manager import (
    DatabasePoolManager,
    close_pool_manager,
    get_pool_manager,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    return Settings(
        environment="testing",
        debug=True,
        database_url="https://test-project.supabase.co",
        database_public_key="test-anon-key-that-is-long-enough-for-validation",
        database_service_key="test-service-key-that-is-long-enough-for-validation",
        _env_file=None,
    )


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # Mock query chain
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select

    mock_limit = MagicMock()
    mock_select.limit.return_value = mock_limit

    mock_execute = MagicMock()
    mock_limit.execute.return_value = mock_execute
    mock_execute.data = [{"id": "test_user"}]

    return mock_client


class TestDatabasePoolManager:
    """Test the simplified DatabasePoolManager class."""

    def test_init(self, mock_settings):
        """Test pool manager initialization."""
        manager = DatabasePoolManager(mock_settings)

        assert manager.settings == mock_settings
        assert manager._client is None
        assert not manager._initialized

    def test_init_with_default_settings(self):
        """Test pool manager initialization with default settings."""
        with patch(
            "tripsage_core.services.infrastructure.database_pool_manager.get_settings"
        ) as mock_get_settings:
            mock_get_settings.return_value = MagicMock()
            manager = DatabasePoolManager()
            assert manager.settings is not None

    def test_get_supavisor_url(self, mock_settings):
        """Test Supavisor URL conversion."""
        manager = DatabasePoolManager(mock_settings)

        # Test standard Supabase URL conversion
        supavisor_url = manager._get_supavisor_url()
        assert "pooler.supabase.com" in supavisor_url
        assert (
            ".supabase.co" not in supavisor_url
            or ".pooler.supabase.com" in supavisor_url
        )

    def test_get_supavisor_url_non_supabase(self, mock_settings):
        """Test URL handling for non-Supabase URLs."""
        mock_settings.database_url = "https://custom-db.example.com"
        manager = DatabasePoolManager(mock_settings)

        supavisor_url = manager._get_supavisor_url()
        assert supavisor_url == "https://custom-db.example.com"

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    def test_create_supavisor_client_success(
        self, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test successful Supavisor client creation."""
        mock_create_client.return_value = mock_supabase_client

        manager = DatabasePoolManager(mock_settings)
        client = manager._create_supavisor_client()

        assert client == mock_supabase_client
        mock_create_client.assert_called_once()

        # Verify client options
        call_args = mock_create_client.call_args
        options = call_args[1]["options"]
        assert not options.auto_refresh_token
        assert not options.persist_session
        assert options.postgrest_client_timeout == 30.0

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    def test_create_supavisor_client_failure(self, mock_create_client, mock_settings):
        """Test Supavisor client creation failure."""
        mock_create_client.side_effect = Exception("Connection failed")

        manager = DatabasePoolManager(mock_settings)

        with pytest.raises(
            CoreDatabaseError, match="Failed to create Supavisor client"
        ):
            manager._create_supavisor_client()

    @patch("asyncio.to_thread")
    async def test_test_connection_success(
        self, mock_to_thread, mock_settings, mock_supabase_client
    ):
        """Test successful connection test."""
        mock_to_thread.return_value = None  # Success

        manager = DatabasePoolManager(mock_settings)
        manager._client = mock_supabase_client

        # Should not raise exception
        await manager._test_connection()
        mock_to_thread.assert_called_once()

    @patch("asyncio.to_thread")
    async def test_test_connection_failure(
        self, mock_to_thread, mock_settings, mock_supabase_client
    ):
        """Test connection test failure."""
        mock_to_thread.side_effect = Exception("Query failed")

        manager = DatabasePoolManager(mock_settings)
        manager._client = mock_supabase_client

        with pytest.raises(CoreDatabaseError, match="Connection test failed"):
            await manager._test_connection()

    async def test_test_connection_no_client(self, mock_settings):
        """Test connection test without client."""
        manager = DatabasePoolManager(mock_settings)

        with pytest.raises(CoreDatabaseError, match="No client available"):
            await manager._test_connection()

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_initialize_success(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test successful initialization."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None  # Successful connection test

        manager = DatabasePoolManager(mock_settings)
        await manager.initialize()

        assert manager._initialized
        assert manager._client == mock_supabase_client

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    async def test_initialize_already_initialized(
        self, mock_create_client, mock_settings
    ):
        """Test initialization when already initialized."""
        manager = DatabasePoolManager(mock_settings)
        manager._initialized = True

        await manager.initialize()

        # Should not create client if already initialized
        mock_create_client.assert_not_called()

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    async def test_initialize_failure(self, mock_create_client, mock_settings):
        """Test initialization failure."""
        mock_create_client.side_effect = Exception("Failed to create client")

        manager = DatabasePoolManager(mock_settings)

        with pytest.raises(
            CoreDatabaseError, match="Failed to initialize database connection"
        ):
            await manager.initialize()

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_acquire_connection_success(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test successful connection acquisition."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)

        async with manager.acquire_connection() as client:
            assert client == mock_supabase_client

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_acquire_connection_with_params(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test connection acquisition with parameters (should be ignored)."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)

        # These parameters should be ignored as Supavisor handles them
        async with manager.acquire_connection(
            pool_type="session", timeout=10.0
        ) as client:
            assert client == mock_supabase_client

    async def test_acquire_connection_not_initialized(self, mock_settings):
        """Test connection acquisition when not initialized."""
        manager = DatabasePoolManager(mock_settings)

        # Should raise error during initialization due to invalid settings
        with pytest.raises(CoreDatabaseError):
            async with manager.acquire_connection():
                pass

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_health_check_success(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test successful health check."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)
        await manager.initialize()

        health = await manager.health_check()
        assert health is True

    async def test_health_check_not_initialized(self, mock_settings):
        """Test health check when not initialized."""
        manager = DatabasePoolManager(mock_settings)

        health = await manager.health_check()
        assert health is False

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_health_check_failure(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test health check failure."""
        mock_create_client.return_value = mock_supabase_client
        # First call succeeds for initialization, second fails for health check
        mock_to_thread.side_effect = [None, Exception("Health check failed")]

        manager = DatabasePoolManager(mock_settings)
        await manager.initialize()

        health = await manager.health_check()
        assert health is False

    def test_get_metrics_not_connected(self, mock_settings):
        """Test metrics when not connected."""
        manager = DatabasePoolManager(mock_settings)

        metrics = manager.get_metrics()
        assert metrics["status"] == "disconnected"
        assert metrics["pool_type"] == "supavisor_transaction_mode"
        assert metrics["port"] == "6543"

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_get_metrics_connected(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test metrics when connected."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)
        await manager.initialize()

        metrics = manager.get_metrics()
        assert metrics["status"] == "connected"
        assert metrics["pool_type"] == "supavisor_transaction_mode"
        assert metrics["port"] == "6543"
        assert "Detailed metrics available in Supabase dashboard" in metrics["note"]

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_close(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test closing the pool manager."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)
        await manager.initialize()

        assert manager._initialized
        assert manager._client is not None

        await manager.close()

        assert not manager._initialized
        assert manager._client is None


class TestGlobalPoolManager:
    """Test global pool manager functions."""

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_get_pool_manager_singleton(
        self, mock_to_thread, mock_create_client, mock_supabase_client
    ):
        """Test that get_pool_manager returns singleton instance."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        # Clear any existing global instance
        await close_pool_manager()

        # First call should create instance
        manager1 = await get_pool_manager()
        assert manager1 is not None
        assert manager1._initialized

        # Second call should return same instance
        manager2 = await get_pool_manager()
        assert manager1 is manager2

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_close_pool_manager(
        self, mock_to_thread, mock_create_client, mock_supabase_client
    ):
        """Test closing global pool manager."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        # Create instance
        manager = await get_pool_manager()
        assert manager._initialized

        # Close it
        await close_pool_manager()

        # Should be cleaned up
        assert not manager._initialized
        assert manager._client is None

    async def test_close_pool_manager_none(self):
        """Test closing when no global manager exists."""
        # Clear any existing instance first
        await close_pool_manager()

        # Should not raise error
        await close_pool_manager()


class TestSupavisorIntegration:
    """Test Supavisor-specific functionality."""

    def test_supavisor_url_conversion_formats(self, mock_settings):
        """Test various Supabase URL formats are converted correctly."""
        manager = DatabasePoolManager(mock_settings)

        test_cases = [
            (
                "https://abcdef123456.supabase.co",
                "https://abcdef123456.pooler.supabase.com",
            ),
            (
                "https://project-name.supabase.co/rest/v1",
                "https://project-name.pooler.supabase.com/rest/v1",
            ),
            (
                "https://test.supabase.co?key=value",
                "https://test.pooler.supabase.com?key=value",
            ),
        ]

        for input_url, expected_url in test_cases:
            mock_settings.database_url = input_url
            result = manager._get_supavisor_url()
            assert result == expected_url

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    def test_supavisor_client_options(
        self, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test that client is configured correctly for Supavisor."""
        mock_create_client.return_value = mock_supabase_client

        manager = DatabasePoolManager(mock_settings)
        manager._create_supavisor_client()

        # Verify create_client was called with correct parameters
        call_args = mock_create_client.call_args
        url, key = call_args[0]
        options = call_args[1]["options"]

        # URL should be pooler format
        assert "pooler.supabase.com" in url

        # Options should be optimized for Supavisor transaction mode
        assert not options.auto_refresh_token
        assert not options.persist_session
        assert options.postgrest_client_timeout == 30.0

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_multiple_concurrent_connections(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test that multiple concurrent connections work with Supavisor."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)
        await manager.initialize()

        # Simulate multiple concurrent connection acquisitions
        async def get_connection():
            async with manager.acquire_connection() as client:
                assert client == mock_supabase_client
                return "success"

        # All should use the same client (Supavisor handles pooling)
        import asyncio

        results = await asyncio.gather(*[get_connection() for _ in range(10)])
        assert all(result == "success" for result in results)

    @patch("tripsage_core.services.infrastructure.database_pool_manager.create_client")
    @patch("asyncio.to_thread")
    async def test_compatibility_with_existing_interface(
        self, mock_to_thread, mock_create_client, mock_settings, mock_supabase_client
    ):
        """Test that the simplified interface is compatible with existing code."""
        mock_create_client.return_value = mock_supabase_client
        mock_to_thread.return_value = None

        manager = DatabasePoolManager(mock_settings)

        # These methods should exist and work (for backward compatibility)
        await manager.initialize()

        async with manager.acquire_connection("transaction", timeout=5.0) as client:
            assert client is not None

        metrics = manager.get_metrics()
        assert isinstance(metrics, dict)

        health = await manager.health_check()
        assert isinstance(health, bool)

        await manager.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
