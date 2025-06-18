"""
Tests for the simple round-robin read replica manager functionality.

Tests cover basic round-robin load balancing, simple health monitoring,
failover logic, and connection management.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import CoreServiceError
from tripsage_core.services.infrastructure.replica_manager import (
    QueryType,
    ReplicaConfig,
    ReplicaHealth,
    ReplicaManager,
    ReplicaStatus,
    close_replica_manager,
    get_replica_manager,
)

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.database_url = "https://test.supabase.co"

    # Mock SecretStr attributes properly with longer keys
    # (Supabase requires longer keys)
    mock_public_key = MagicMock()
    mock_public_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-key-value-for-testing-only"
    )
    settings.database_public_key = mock_public_key

    # Mock read_replicas property
    settings.read_replicas = {
        "west": {
            "url": "https://west.supabase.co",
            "api_key": "west-key",
            "enabled": True,
        },
        "eu": {
            "url": "https://eu.supabase.co",
            "api_key": "eu-key",
            "enabled": True,
        },
        "disabled": {
            "url": "https://disabled.supabase.co",
            "api_key": "disabled-key",
            "enabled": False,
        },
    }

    return settings

@pytest.fixture
def replica_config():
    """Create a test replica configuration."""
    return ReplicaConfig(
        id="test-replica",
        url="https://test.supabase.co",
        api_key="test-key",
        enabled=True,
    )

@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = MagicMock()
    table_mock = MagicMock()
    query_mock = MagicMock()

    # Chain method calls
    client.table.return_value = table_mock
    table_mock.select.return_value = query_mock
    query_mock.limit.return_value = query_mock
    query_mock.execute.return_value = MagicMock(data=[{"id": "test"}])

    return client

class TestReplicaManager:
    """Test cases for the simplified ReplicaManager class."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_settings):
        """Set up test fixtures."""
        self.settings = mock_settings
        self.replica_manager = ReplicaManager(self.settings)

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_initialization(self, mock_create_client, mock_supabase_client):
        """Test replica manager initialization."""
        mock_create_client.return_value = mock_supabase_client

        await self.replica_manager.initialize()

        assert self.replica_manager._enabled
        assert len(self.replica_manager._replicas) >= 1  # Primary + enabled replicas
        assert "primary" in self.replica_manager._replicas
        assert "west" in self.replica_manager._replicas
        assert "eu" in self.replica_manager._replicas
        assert "disabled" not in self.replica_manager._replicas  # Should be excluded

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_initialization_failure_handling(self, mock_create_client):
        """Test handling of replica initialization failures."""
        # Mock failure for one replica
        mock_create_client.side_effect = [
            MagicMock(),  # Primary succeeds
            Exception("Connection failed"),  # First replica fails
            MagicMock(),  # Second replica succeeds
        ]

        await self.replica_manager.initialize()

        # Should still be enabled despite one failure
        assert self.replica_manager._enabled

        # Should have health status for failed replica marked as unhealthy
        failed_replica_health = None
        for health in self.replica_manager._health.values():
            if health.status == ReplicaStatus.UNHEALTHY and health.error_count > 0:
                failed_replica_health = health
                break

        assert failed_replica_health is not None

    def test_round_robin_selection(self):
        """Test basic round-robin replica selection."""
        # Set up test replicas and health
        self.replica_manager._replicas = {
            "primary": ReplicaConfig(
                id="primary",
                url="https://primary.supabase.co",
                api_key="primary-key",
            ),
            "replica1": ReplicaConfig(
                id="replica1",
                url="https://r1.supabase.co",
                api_key="key1",
            ),
            "replica2": ReplicaConfig(
                id="replica2",
                url="https://r2.supabase.co",
                api_key="key2",
            ),
        }

        self.replica_manager._health = {
            "primary": ReplicaHealth(
                replica_id="primary",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=10.0,
            ),
            "replica1": ReplicaHealth(
                replica_id="replica1",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=15.0,
            ),
            "replica2": ReplicaHealth(
                replica_id="replica2",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=20.0,
            ),
        }

        # Test multiple selections to verify round-robin behavior
        selections = []
        for _ in range(6):  # 3 cycles through 2 replicas
            replica_id = self.replica_manager.get_replica_for_query(QueryType.READ)
            selections.append(replica_id)

        # Should cycle through available read replicas (excluding primary)
        healthy_read_replicas = ["replica1", "replica2"]
        for i, selection in enumerate(selections):
            expected = healthy_read_replicas[i % len(healthy_read_replicas)]
            assert selection == expected

    def test_query_type_routing(self):
        """Test query type-based routing (write vs read)."""
        # Set up healthy replicas
        self.replica_manager._replicas = {
            "primary": ReplicaConfig(
                id="primary",
                url="https://primary.supabase.co",
                api_key="primary-key",
            ),
            "replica1": ReplicaConfig(
                id="replica1",
                url="https://r1.supabase.co",
                api_key="key1",
            ),
        }

        self.replica_manager._health = {
            "primary": ReplicaHealth(
                replica_id="primary",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=10.0,
            ),
            "replica1": ReplicaHealth(
                replica_id="replica1",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=15.0,
            ),
        }

        # Write queries should always use primary
        replica_id = self.replica_manager.get_replica_for_query(QueryType.WRITE)
        assert replica_id == "primary"

        # Read queries should use replicas
        replica_id = self.replica_manager.get_replica_for_query(QueryType.READ)
        assert replica_id == "replica1"

    def test_fallback_to_primary(self):
        """Test fallback to primary when no healthy replicas available."""
        # Set up primary as healthy but replicas as unhealthy
        self.replica_manager._replicas = {
            "primary": ReplicaConfig(
                id="primary",
                url="https://primary.supabase.co",
                api_key="primary-key",
            ),
            "replica1": ReplicaConfig(
                id="replica1",
                url="https://r1.supabase.co",
                api_key="key1",
            ),
        }

        self.replica_manager._health = {
            "primary": ReplicaHealth(
                replica_id="primary",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=10.0,
            ),
            "replica1": ReplicaHealth(
                replica_id="replica1",
                status=ReplicaStatus.UNHEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=0.0,
                error_count=3,
            ),
        }

        # Read queries should fall back to primary when no healthy replicas
        replica_id = self.replica_manager.get_replica_for_query(QueryType.READ)
        assert replica_id == "primary"

    def test_get_healthy_read_replicas(self):
        """Test filtering of healthy read replicas."""
        # Set up replicas with different health states
        self.replica_manager._replicas = {
            "primary": ReplicaConfig(
                id="primary",
                url="https://primary.supabase.co",
                api_key="primary-key",
            ),
            "healthy": ReplicaConfig(
                id="healthy",
                url="https://healthy.supabase.co",
                api_key="healthy-key",
                enabled=True,
            ),
            "unhealthy": ReplicaConfig(
                id="unhealthy",
                url="https://unhealthy.supabase.co",
                api_key="unhealthy-key",
                enabled=True,
            ),
            "disabled": ReplicaConfig(
                id="disabled",
                url="https://disabled.supabase.co",
                api_key="disabled-key",
                enabled=False,
            ),
        }

        self.replica_manager._health = {
            "primary": ReplicaHealth(
                replica_id="primary",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=10.0,
            ),
            "healthy": ReplicaHealth(
                replica_id="healthy",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=15.0,
            ),
            "unhealthy": ReplicaHealth(
                replica_id="unhealthy",
                status=ReplicaStatus.UNHEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=0.0,
            ),
            "disabled": ReplicaHealth(
                replica_id="disabled",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=12.0,
            ),
        }

        healthy_replicas = self.replica_manager._get_healthy_read_replicas()

        # Should only include healthy, enabled replicas (excluding primary)
        assert "healthy" in healthy_replicas
        assert "primary" not in healthy_replicas  # Excluded for read load balancing
        assert "unhealthy" not in healthy_replicas  # Unhealthy
        assert "disabled" not in healthy_replicas  # Disabled

    async def test_connection_acquisition(self):
        """Test connection acquisition context manager."""
        # Set up test replica
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client

        with patch.object(
            self.replica_manager, "get_replica_for_query", return_value="test"
        ):
            async with self.replica_manager.acquire_connection() as (
                replica_id,
                client,
            ):
                assert replica_id == "test"
                assert client == mock_client

    async def test_connection_acquisition_fallback(self):
        """Test connection acquisition fallback when selected replica unavailable."""
        # Set up primary client but not selected replica
        mock_primary_client = MagicMock()
        self.replica_manager._clients["primary"] = mock_primary_client

        with patch.object(
            self.replica_manager, "get_replica_for_query", return_value="missing"
        ):
            async with self.replica_manager.acquire_connection() as (
                replica_id,
                client,
            ):
                assert replica_id == "primary"
                assert client == mock_primary_client

    async def test_connection_acquisition_no_client_error(self):
        """Test error when no client is available."""
        # No clients available
        self.replica_manager._clients.clear()

        with patch.object(
            self.replica_manager, "get_replica_for_query", return_value="missing"
        ):
            with pytest.raises(CoreServiceError) as exc_info:
                async with self.replica_manager.acquire_connection():
                    pass

            assert exc_info.value.code == "NO_CLIENT_AVAILABLE"

    async def test_connection_error_handling(self):
        """Test error handling during connection usage."""
        # Set up test replica with health tracking
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
            error_count=0,
        )

        with patch.object(
            self.replica_manager, "get_replica_for_query", return_value="test"
        ):
            with pytest.raises(Exception, match="Database error"):
                async with self.replica_manager.acquire_connection():
                    # Simulate an error during connection usage
                    raise Exception("Database error")

            # Should increment error count
            health = self.replica_manager._health["test"]
            assert health.error_count == 1

    async def test_health_check_success(self):
        """Test successful health check."""
        # Set up a test replica with mock client
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.UNHEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=0.0,
            error_count=2,
        )

        # Mock successful health check
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.select.return_value.limit.return_value.execute.return_value = (
            MagicMock()
        )

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = None
            await self.replica_manager._check_replica_health("test")

        health = self.replica_manager._health["test"]
        assert health.status == ReplicaStatus.HEALTHY
        assert health.error_count == 1  # Should be decremented
        assert health.latency_ms > 0

    async def test_health_check_failure(self):
        """Test health check failure handling."""
        # Set up a test replica with mock client
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
            error_count=0,
        )

        # Mock failed health check
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Connection failed")
            await self.replica_manager._check_replica_health("test")

        health = self.replica_manager._health["test"]
        assert health.status == ReplicaStatus.UNHEALTHY
        assert health.error_count == 1

    async def test_health_check_timeout(self):
        """Test health check timeout handling."""
        # Set up a test replica with mock client
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
            error_count=0,
        )

        # Mock timeout
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()
            await self.replica_manager._check_replica_health("test")

        health = self.replica_manager._health["test"]
        assert health.status == ReplicaStatus.UNHEALTHY
        assert health.error_count == 1

    async def test_perform_health_checks(self):
        """Test performing health checks on all replicas."""
        # Set up multiple replicas with both config and clients
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        self.replica_manager._replicas["test1"] = ReplicaConfig(
            id="test1", url="https://test1.supabase.co", api_key="key1"
        )
        self.replica_manager._replicas["test2"] = ReplicaConfig(
            id="test2", url="https://test2.supabase.co", api_key="key2"
        )

        self.replica_manager._clients["test1"] = mock_client1
        self.replica_manager._clients["test2"] = mock_client2

        self.replica_manager._health["test1"] = ReplicaHealth(
            replica_id="test1",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
        )
        self.replica_manager._health["test2"] = ReplicaHealth(
            replica_id="test2",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=15.0,
        )

        with patch.object(self.replica_manager, "_check_replica_health") as mock_check:
            mock_check.return_value = None
            await self.replica_manager._perform_health_checks()

            # Should check health for all replicas
            assert mock_check.call_count == 2

    def test_replica_health_getters(self):
        """Test replica health getters."""
        # Set up test health data
        health = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
        )
        self.replica_manager._health["test"] = health

        # Test getting specific replica health
        result = self.replica_manager.get_replica_health("test")
        assert result == health

        # Test getting all replica health
        all_health = self.replica_manager.get_replica_health()
        assert "test" in all_health
        assert all_health["test"] == health

    def test_replica_configs_getter(self):
        """Test replica configurations getter."""
        config = ReplicaConfig(
            id="test",
            url="https://test.supabase.co",
            api_key="test-key",
        )
        self.replica_manager._replicas["test"] = config

        configs = self.replica_manager.get_replica_configs()
        assert "test" in configs
        assert configs["test"] == config

    async def test_close_cleanup(self):
        """Test proper cleanup when closing replica manager."""
        # Set up some test data
        self.replica_manager._clients["test"] = MagicMock()
        self.replica_manager._replicas["test"] = ReplicaConfig(
            id="test",
            url="https://test.supabase.co",
            api_key="test-key",
        )

        # Create a real asyncio task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)

        mock_task = asyncio.create_task(dummy_task())
        self.replica_manager._health_check_task = mock_task

        await self.replica_manager.close()

        assert not self.replica_manager._enabled
        assert len(self.replica_manager._clients) == 0
        assert len(self.replica_manager._replicas) == 0
        assert len(self.replica_manager._health) == 0
        assert mock_task.cancelled()

    async def test_close_with_cancelled_task(self):
        """Test close handling when background task is cancelled."""

        # Create a real asyncio task and cancel it
        async def dummy_task():
            await asyncio.sleep(10)

        mock_task = asyncio.create_task(dummy_task())
        mock_task.cancel()  # Pre-cancel the task
        self.replica_manager._health_check_task = mock_task

        # Should not raise exception even with a cancelled task
        await self.replica_manager.close()
        assert not self.replica_manager._enabled
        assert mock_task.cancelled()

    async def test_disabled_replica_manager(self):
        """Test replica manager behavior when disabled."""
        self.replica_manager._enabled = False

        await self.replica_manager.initialize()

        # Should remain disabled and not load replicas
        assert not self.replica_manager._enabled
        assert len(self.replica_manager._replicas) == 0

@pytest.mark.asyncio
class TestReplicaManagerGlobalInstance:
    """Test global replica manager instance functions."""

    async def test_get_replica_manager_singleton(self):
        """Test that get_replica_manager returns the same instance."""
        # Reset global instance
        import tripsage_core.services.infrastructure.replica_manager as rm_module

        rm_module._replica_manager = None

        with patch(
            "tripsage_core.services.infrastructure.replica_manager.create_client"
        ):
            manager1 = await get_replica_manager()
            manager2 = await get_replica_manager()

            assert manager1 is manager2

        # Cleanup
        await close_replica_manager()

    async def test_close_replica_manager_global(self):
        """Test closing global replica manager instance."""
        # Reset global instance
        import tripsage_core.services.infrastructure.replica_manager as rm_module

        rm_module._replica_manager = None

        with patch(
            "tripsage_core.services.infrastructure.replica_manager.create_client"
        ):
            manager = await get_replica_manager()
            assert manager is not None

            await close_replica_manager()

            # Should be reset to None
            assert rm_module._replica_manager is None

    async def test_close_replica_manager_when_none(self):
        """Test closing when no global instance exists."""
        # Reset global instance
        import tripsage_core.services.infrastructure.replica_manager as rm_module

        rm_module._replica_manager = None

        # Should not raise exception
        await close_replica_manager()

@pytest.mark.asyncio
class TestReplicaManagerIntegration:
    """Integration tests for replica manager."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_settings):
        """Set up integration test fixtures."""
        self.settings = mock_settings
        self.replica_manager = ReplicaManager(self.settings)

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_full_read_query_lifecycle(
        self, mock_create_client, mock_supabase_client
    ):
        """Test full lifecycle of a read query through the replica manager."""
        mock_create_client.return_value = mock_supabase_client

        # Initialize
        await self.replica_manager.initialize()
        assert self.replica_manager._enabled

        # Simulate a series of read queries to test round-robin
        query_results = []
        for _ in range(4):
            async with self.replica_manager.acquire_connection(QueryType.READ) as (
                replica_id,
                client,
            ):
                query_results.append(replica_id)
                assert client == mock_supabase_client

        # Should see round-robin behavior among healthy replicas
        # (excluding primary for read load balancing)
        healthy_replicas = self.replica_manager._get_healthy_read_replicas()
        if healthy_replicas:
            # Verify round-robin pattern
            for i, result in enumerate(query_results):
                expected = healthy_replicas[i % len(healthy_replicas)]
                assert result == expected
        else:
            # If no healthy replicas, should all be primary
            assert all(result == "primary" for result in query_results)

        # Close
        await self.replica_manager.close()
        assert not self.replica_manager._enabled

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_write_query_always_primary(
        self, mock_create_client, mock_supabase_client
    ):
        """Test that write queries always go to primary."""
        mock_create_client.return_value = mock_supabase_client

        # Initialize
        await self.replica_manager.initialize()

        # Test multiple write queries
        for _ in range(5):
            async with self.replica_manager.acquire_connection(QueryType.WRITE) as (
                replica_id,
                client,
            ):
                assert replica_id == "primary"
                assert client == mock_supabase_client

        await self.replica_manager.close()

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_unhealthy_replica_recovery(
        self, mock_create_client, mock_supabase_client
    ):
        """Test recovery of unhealthy replicas through health checks."""
        mock_create_client.return_value = mock_supabase_client

        await self.replica_manager.initialize()

        # Mark a replica as unhealthy
        if "west" in self.replica_manager._health:
            self.replica_manager._health["west"].status = ReplicaStatus.UNHEALTHY
            self.replica_manager._health["west"].error_count = 2

        # Simulate successful health check
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = None
            await self.replica_manager._check_replica_health("west")

        # Should be marked as healthy again with reduced error count
        health = self.replica_manager._health["west"]
        assert health.status == ReplicaStatus.HEALTHY
        assert health.error_count == 1  # Decremented

        await self.replica_manager.close()

class TestReplicaDataClasses:
    """Test the data classes used by replica manager."""

    def test_replica_config_creation(self):
        """Test ReplicaConfig creation and defaults."""
        config = ReplicaConfig(
            id="test",
            url="https://test.supabase.co",
            api_key="test-key",
        )

        assert config.id == "test"
        assert config.url == "https://test.supabase.co"
        assert config.api_key == "test-key"
        assert config.enabled is True  # Default value

    def test_replica_health_creation(self):
        """Test ReplicaHealth creation and defaults."""
        now = datetime.now(timezone.utc)
        health = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=now,
            latency_ms=10.5,
        )

        assert health.replica_id == "test"
        assert health.status == ReplicaStatus.HEALTHY
        assert health.last_check == now
        assert health.latency_ms == 10.5
        assert health.error_count == 0  # Default value

    def test_query_type_enum(self):
        """Test QueryType enum values."""
        assert QueryType.READ.value == "read"
        assert QueryType.WRITE.value == "write"
        assert QueryType.VECTOR_SEARCH.value == "vector_search"
        assert QueryType.ANALYTICS.value == "analytics"

    def test_replica_status_enum(self):
        """Test ReplicaStatus enum values."""
        assert ReplicaStatus.HEALTHY.value == "healthy"
        assert ReplicaStatus.UNHEALTHY.value == "unhealthy"
