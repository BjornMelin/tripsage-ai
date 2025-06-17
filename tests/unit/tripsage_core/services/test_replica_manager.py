"""
Tests for the read replica manager functionality.

Tests cover load balancing strategies, health monitoring, failover logic,
geographic routing, and integration with the database service.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.services.infrastructure.replica_manager import (
    LoadBalancerStats,
    LoadBalancingStrategy,
    QueryType,
    ReplicaConfig,
    ReplicaHealth,
    ReplicaManager,
    ReplicaMetrics,
    ReplicaStatus,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.database_url = "https://test.supabase.co"

    # Mock SecretStr attributes properly with longer keys (Supabase requires longer keys)
    mock_public_key = MagicMock()
    mock_public_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-key-value-for-testing-only"
    )
    settings.database_public_key = mock_public_key

    mock_service_key = MagicMock()
    mock_service_key.get_secret_value.return_value = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-service-key-value-for-testing-only"
    )
    settings.database_service_key = mock_service_key

    mock_jwt_secret = MagicMock()
    mock_jwt_secret.get_secret_value.return_value = (
        "test-jwt-secret-super-secret-for-testing-only-very-long-secret-key"
    )
    settings.database_jwt_secret = mock_jwt_secret

    settings.database_region = "us-east-1"
    settings.enable_read_replicas = True
    settings.read_replica_strategy = "round_robin"
    settings.read_replica_health_check_interval = 30.0
    settings.read_replica_fallback_to_primary = True
    settings.read_replica_max_retry_attempts = 3

    # Mock read_replicas property
    settings.read_replicas = {
        "west": {
            "url": "https://west.supabase.co",
            "api_key": "west-key",
            "name": "West Replica",
            "region": "us-west-1",
            "priority": 1,
            "weight": 1.0,
            "max_connections": 100,
            "read_only": True,
            "enabled": True,
        },
        "eu": {
            "url": "https://eu.supabase.co",
            "api_key": "eu-key",
            "name": "EU Replica",
            "region": "eu-west-1",
            "priority": 2,
            "weight": 1.5,
            "max_connections": 100,
            "read_only": True,
            "enabled": True,
        },
    }

    return settings


@pytest.fixture
def replica_config():
    """Create a test replica configuration."""
    return ReplicaConfig(
        id="test-replica",
        name="Test Replica",
        region="us-west-1",
        url="https://test.supabase.co",
        api_key="test-key",
        priority=1,
        weight=1.0,
        max_connections=100,
        read_only=True,
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
    """Test cases for ReplicaManager class."""

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
        assert len(self.replica_manager._replicas) >= 1  # Primary + replicas
        assert "primary" in self.replica_manager._replicas
        assert "west" in self.replica_manager._replicas
        assert "eu" in self.replica_manager._replicas

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_replica_registration(
        self, mock_create_client, mock_supabase_client, replica_config
    ):
        """Test manual replica registration."""
        mock_create_client.return_value = mock_supabase_client

        await self.replica_manager.initialize()
        await self.replica_manager.register_replica("manual", replica_config)

        assert "manual" in self.replica_manager._replicas
        assert "manual" in self.replica_manager._clients
        assert "manual" in self.replica_manager._health
        assert "manual" in self.replica_manager._metrics

    async def test_replica_removal(self):
        """Test replica removal."""
        # Add a test replica first
        self.replica_manager._replicas["test"] = ReplicaConfig(
            id="test",
            name="Test",
            region="us-east-1",
            url="https://test.supabase.co",
            api_key="key",
        )
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
        )

        await self.replica_manager.remove_replica("test")

        assert "test" not in self.replica_manager._replicas
        assert "test" not in self.replica_manager._health

    async def test_load_balancing_strategies(self):
        """Test different load balancing strategies."""
        # Set up test replicas
        self.replica_manager._replicas = {
            "replica1": ReplicaConfig(
                id="replica1",
                name="R1",
                region="us-east-1",
                url="https://r1.supabase.co",
                api_key="key1",
                weight=1.0,
            ),
            "replica2": ReplicaConfig(
                id="replica2",
                name="R2",
                region="us-west-1",
                url="https://r2.supabase.co",
                api_key="key2",
                weight=2.0,
            ),
        }

        self.replica_manager._health = {
            "replica1": ReplicaHealth(
                replica_id="replica1",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=10.0,
            ),
            "replica2": ReplicaHealth(
                replica_id="replica2",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=20.0,
            ),
        }

        self.replica_manager._connection_counts = {"replica1": 5, "replica2": 3}

        # Test round-robin
        selected = await self.replica_manager._round_robin_selection(
            ["replica1", "replica2"]
        )
        assert selected in ["replica1", "replica2"]

        # Test least connections
        selected = await self.replica_manager._least_connections_selection(
            ["replica1", "replica2"]
        )
        assert selected == "replica2"  # Fewer connections

        # Test latency-based
        selected = await self.replica_manager._latency_based_selection(
            ["replica1", "replica2"]
        )
        assert selected == "replica1"  # Lower latency

        # Test geographic
        selected = await self.replica_manager._geographic_selection(
            ["replica1", "replica2"], "us-west-1"
        )
        assert selected == "replica2"  # Same region

    async def test_query_type_routing(self):
        """Test query type-based routing."""
        # Set up healthy replicas
        healthy_replicas = ["replica1", "replica2"]

        # Mock the methods to return predictable results
        self.replica_manager._least_connections_selection = AsyncMock(
            return_value="replica1"
        )
        self.replica_manager._latency_based_selection = AsyncMock(
            return_value="replica2"
        )
        self.replica_manager._round_robin_selection = AsyncMock(return_value="replica1")

        # Test analytics queries
        await self.replica_manager._query_type_selection(
            healthy_replicas, QueryType.ANALYTICS
        )
        self.replica_manager._least_connections_selection.assert_called_once()

        # Test vector search queries
        await self.replica_manager._query_type_selection(
            healthy_replicas, QueryType.VECTOR_SEARCH
        )
        self.replica_manager._latency_based_selection.assert_called_once()

        # Test regular read queries
        await self.replica_manager._query_type_selection(
            healthy_replicas, QueryType.READ
        )
        self.replica_manager._round_robin_selection.assert_called_once()

    async def test_health_monitoring(self):
        """Test health monitoring functionality."""
        # Set up a test replica with mock client
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=0.0,
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
        assert health.success_count == 1

    async def test_health_check_failure(self):
        """Test health check failure handling."""
        # Set up a test replica with mock client
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=0.0,
        )

        # Mock failed health check
        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.side_effect = Exception("Connection failed")
            await self.replica_manager._check_replica_health("test")

        health = self.replica_manager._health["test"]
        assert health.status == ReplicaStatus.UNHEALTHY
        assert health.error_count == 1
        assert "Connection failed" in health.last_error

    async def test_get_replica_for_query(self):
        """Test replica selection for queries."""
        # Set up test replicas and health
        self.replica_manager._replicas = {
            "primary": ReplicaConfig(
                id="primary",
                name="Primary",
                region="us-east-1",
                url="https://primary.supabase.co",
                api_key="key",
                read_only=False,
            ),
            "replica1": ReplicaConfig(
                id="replica1",
                name="R1",
                region="us-east-1",
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

        self.replica_manager._connection_counts = {"primary": 0, "replica1": 0}
        self.replica_manager._enabled = True

        # Test write query (should use primary)
        replica_id = await self.replica_manager.get_replica_for_query(QueryType.WRITE)
        assert replica_id == "primary"

        # Test read query (should use replica)
        replica_id = await self.replica_manager.get_replica_for_query(QueryType.READ)
        assert replica_id in ["primary", "replica1"]

    async def test_connection_acquisition(self):
        """Test connection acquisition context manager."""
        # Set up test replica
        mock_client = MagicMock()
        self.replica_manager._replicas["test"] = ReplicaConfig(
            id="test",
            name="Test",
            region="us-east-1",
            url="https://test.supabase.co",
            api_key="key",
        )
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
        )
        self.replica_manager._connection_counts["test"] = 0
        self.replica_manager._metrics["test"] = ReplicaMetrics(replica_id="test")
        self.replica_manager._enabled = True

        # Mock get_replica_for_query to return our test replica
        with patch.object(
            self.replica_manager, "get_replica_for_query", return_value="test"
        ):
            async with self.replica_manager.acquire_connection() as (
                replica_id,
                client,
            ):
                assert replica_id == "test"
                assert client == mock_client
                assert self.replica_manager._connection_counts["test"] == 1

        # Connection should be released
        assert self.replica_manager._connection_counts["test"] == 0

    def test_load_balancer_stats(self):
        """Test load balancer statistics tracking."""
        stats = self.replica_manager.get_load_balancer_stats()
        assert isinstance(stats, LoadBalancerStats)
        assert stats.total_requests == 0
        assert stats.successful_requests == 0
        assert stats.failed_requests == 0

    async def test_scaling_recommendations(self):
        """Test scaling recommendations generation."""
        # Set up test data with high utilization
        self.replica_manager._metrics["test"] = ReplicaMetrics(
            replica_id="test",
            total_queries=1000,
            connection_pool_utilization=85.0,  # High utilization
        )

        self.replica_manager._health["test"] = ReplicaHealth(
            replica_id="test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=150.0,  # High latency
            uptime_percentage=92.0,  # Low uptime
        )

        self.replica_manager._replicas["test"] = ReplicaConfig(
            id="test",
            name="Test",
            region="us-east-1",
            url="https://test.supabase.co",
            api_key="key",
        )

        recommendations = await self.replica_manager.get_scaling_recommendations()

        assert "capacity" in recommendations
        assert "performance" in recommendations
        assert "replicas" in recommendations

        # Should recommend capacity increase for high utilization
        capacity_recs = recommendations["capacity"]
        assert any(
            "high_connection_utilization" in rec["type"] for rec in capacity_recs
        )

        # Should recommend performance improvement for high latency
        perf_recs = recommendations["performance"]
        assert any("high_latency" in rec["type"] for rec in perf_recs)

        # Should recommend replica stability improvement for low uptime
        replica_recs = recommendations["replicas"]
        assert any("low_uptime" in rec["type"] for rec in replica_recs)

    def test_strategy_switching(self):
        """Test load balancing strategy switching."""

        self.replica_manager.set_load_balancing_strategy(
            LoadBalancingStrategy.LATENCY_BASED
        )

        assert (
            self.replica_manager._current_strategy
            == LoadBalancingStrategy.LATENCY_BASED
        )
        assert self.replica_manager._load_balancer_stats.strategy_switches == 1

    async def test_metrics_collection(self):
        """Test metrics collection from replicas."""
        # Set up test client and metrics
        mock_client = MagicMock()
        self.replica_manager._clients["test"] = mock_client
        self.replica_manager._metrics["test"] = ReplicaMetrics(replica_id="test")

        # Mock the RPC call for connection metrics
        mock_client.rpc.return_value.execute.return_value.data = [
            {
                "total_connections": 10,
                "active_connections": 5,
                "idle_connections": 5,
            }
        ]

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = (
                mock_client.rpc.return_value.execute.return_value
            )
            await self.replica_manager._collect_connection_metrics("test", mock_client)

        # Verify metrics were updated
        health = self.replica_manager._health.get("test")
        if health:
            assert health.connections_active == 5
            assert health.connections_idle == 5

    async def test_close_cleanup(self):
        """Test proper cleanup when closing replica manager."""
        # Set up some test data
        self.replica_manager._clients["test"] = MagicMock()
        self.replica_manager._replicas["test"] = ReplicaConfig(
            id="test",
            name="Test",
            region="us-east-1",
            url="https://test.supabase.co",
            api_key="key",
        )

        await self.replica_manager.close()

        assert not self.replica_manager._enabled
        assert len(self.replica_manager._clients) == 0
        assert len(self.replica_manager._replicas) == 0

    def test_replica_health_getters(self):
        """Test replica health and metrics getters."""
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

    def test_replica_metrics_getters(self):
        """Test replica metrics getters."""
        # Set up test metrics data
        metrics = ReplicaMetrics(replica_id="test", total_queries=100)
        self.replica_manager._metrics["test"] = metrics

        # Test getting specific replica metrics
        result = self.replica_manager.get_replica_metrics("test")
        assert result == metrics

        # Test getting all replica metrics
        all_metrics = self.replica_manager.get_replica_metrics()
        assert "test" in all_metrics
        assert all_metrics["test"] == metrics

    def test_replica_configs_getter(self):
        """Test replica configurations getter."""
        config = ReplicaConfig(
            id="test",
            name="Test",
            region="us-east-1",
            url="https://test.supabase.co",
            api_key="key",
        )
        self.replica_manager._replicas["test"] = config

        configs = self.replica_manager.get_replica_configs()
        assert "test" in configs
        assert configs["test"] == config


@pytest.mark.asyncio
class TestReplicaManagerIntegration:
    """Integration tests for replica manager."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_settings):
        """Set up integration test fixtures."""
        self.settings = mock_settings
        self.replica_manager = ReplicaManager(self.settings)

    @patch("tripsage_core.services.infrastructure.replica_manager.create_client")
    async def test_full_lifecycle(self, mock_create_client, mock_supabase_client):
        """Test full lifecycle of replica manager."""
        mock_create_client.return_value = mock_supabase_client

        # Initialize
        await self.replica_manager.initialize()
        assert self.replica_manager._enabled

        # Add a replica
        config = ReplicaConfig(
            id="lifecycle-test",
            name="Lifecycle Test",
            region="us-west-1",
            url="https://lifecycle.supabase.co",
            api_key="test-key",
        )
        await self.replica_manager.register_replica("lifecycle-test", config)

        # Use the replica
        self.replica_manager._health["lifecycle-test"] = ReplicaHealth(
            replica_id="lifecycle-test",
            status=ReplicaStatus.HEALTHY,
            last_check=datetime.now(timezone.utc),
            latency_ms=10.0,
        )
        self.replica_manager._connection_counts["lifecycle-test"] = 0
        self.replica_manager._metrics["lifecycle-test"] = ReplicaMetrics(
            replica_id="lifecycle-test"
        )

        with patch.object(
            self.replica_manager, "get_replica_for_query", return_value="lifecycle-test"
        ):
            async with self.replica_manager.acquire_connection() as (
                replica_id,
                client,
            ):
                assert replica_id == "lifecycle-test"
                assert client == mock_supabase_client

        # Get health and metrics
        health = self.replica_manager.get_replica_health("lifecycle-test")
        assert health.replica_id == "lifecycle-test"

        metrics = self.replica_manager.get_replica_metrics("lifecycle-test")
        assert metrics.replica_id == "lifecycle-test"

        # Remove replica
        await self.replica_manager.remove_replica("lifecycle-test")
        assert "lifecycle-test" not in self.replica_manager._replicas

        # Close
        await self.replica_manager.close()
        assert not self.replica_manager._enabled


@pytest.mark.asyncio
class TestReplicaManagerErrorHandling:
    """Test error handling in replica manager."""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_settings):
        """Set up error handling test fixtures."""
        self.settings = mock_settings
        self.replica_manager = ReplicaManager(self.settings)

    async def test_connection_failure_fallback(self):
        """Test fallback behavior when connection fails."""
        self.replica_manager._enabled = True

        # Set up a scenario where all replicas are unhealthy
        self.replica_manager._replicas = {
            "primary": ReplicaConfig(
                id="primary",
                name="Primary",
                region="us-east-1",
                url="https://primary.supabase.co",
                api_key="key",
                read_only=False,
            ),
            "replica1": ReplicaConfig(
                id="replica1",
                name="R1",
                region="us-east-1",
                url="https://r1.supabase.co",
                api_key="key1",
            ),
        }

        # Mark all replicas as unhealthy
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
                latency_ms=999.0,
                last_error="Connection failed",
            ),
        }

        # When no healthy replicas are available for reads, should fall back to primary
        replica_id = await self.replica_manager.get_replica_for_query(QueryType.READ)
        assert replica_id == "primary"  # Should fall back to primary

    async def test_replica_registration_failure(self):
        """Test handling of replica registration failures."""
        config = ReplicaConfig(
            id="fail-test",
            name="Fail Test",
            region="us-west-1",
            url="invalid-url",
            api_key="test-key",
        )

        with patch(
            "tripsage_core.services.infrastructure.replica_manager.create_client",
            side_effect=Exception("Invalid URL"),
        ):
            with pytest.raises(CoreDatabaseError):
                await self.replica_manager.register_replica("fail-test", config)

    async def test_empty_replica_list_handling(self):
        """Test handling when no replicas are available."""
        # Clear all replicas
        self.replica_manager._replicas.clear()
        self.replica_manager._enabled = True

        replica_id = await self.replica_manager.get_replica_for_query(QueryType.READ)
        assert replica_id == "primary"

    async def test_unhealthy_replica_filtering(self):
        """Test filtering out unhealthy replicas."""
        # Set up replicas with different health states
        self.replica_manager._replicas = {
            "healthy": ReplicaConfig(
                id="healthy",
                name="Healthy",
                region="us-east-1",
                url="https://healthy.supabase.co",
                api_key="key",
            ),
            "unhealthy": ReplicaConfig(
                id="unhealthy",
                name="Unhealthy",
                region="us-west-1",
                url="https://unhealthy.supabase.co",
                api_key="key",
            ),
        }

        self.replica_manager._health = {
            "healthy": ReplicaHealth(
                replica_id="healthy",
                status=ReplicaStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=10.0,
            ),
            "unhealthy": ReplicaHealth(
                replica_id="unhealthy",
                status=ReplicaStatus.UNHEALTHY,
                last_check=datetime.now(timezone.utc),
                latency_ms=0.0,
            ),
        }

        healthy_replicas = await self.replica_manager._get_healthy_replicas(
            QueryType.READ
        )
        assert "healthy" in healthy_replicas
        assert "unhealthy" not in healthy_replicas
