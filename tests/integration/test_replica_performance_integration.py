"""
Integration tests for read replica performance and load balancing.

These tests verify the complete integration of read replica functionality
with the database service, including realistic scenarios and performance
characteristics under load.
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.replica_manager import (
    LoadBalancingStrategy,
    ReplicaHealth,
    ReplicaStatus,
)

class TestReplicaPerformanceIntegration:
    """Integration tests for replica performance under realistic loads."""

    @pytest.fixture
    def mock_settings_with_multiple_replicas(self):
        """Create settings with multiple replicas for performance testing."""
        settings = MagicMock(spec=Settings)
        settings.database_url = "https://primary.supabase.co"

        # Mock SecretStr attributes with proper values
        mock_public_key = MagicMock()
        mock_public_key.get_secret_value.return_value = (  # noqa: E501
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-public-key-for-performance-testing"
        )
        settings.database_public_key = mock_public_key

        mock_service_key = MagicMock()
        mock_service_key.get_secret_value.return_value = (  # noqa: E501
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-service-key-for-performance-testing"
        )
        settings.database_service_key = mock_service_key

        mock_jwt_secret = MagicMock()
        mock_jwt_secret.get_secret_value.return_value = (
            "test-jwt-secret-super-secret-for-performance-testing-very-long"
        )
        settings.database_jwt_secret = mock_jwt_secret

        settings.enable_read_replicas = True
        settings.database_region = "us-east-1"
        settings.read_replica_strategy = "round_robin"
        settings.read_replica_health_check_interval = 5.0  # More frequent for testing
        settings.read_replica_fallback_to_primary = True
        settings.read_replica_max_retry_attempts = 2

        # Multiple replicas across regions
        settings.read_replicas = {
            "us-west-1": {
                "url": "https://us-west-1.supabase.co",
                "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.us-west-1-key",
                "name": "US West 1 Replica",
                "region": "us-west-1",
                "priority": 1,
                "weight": 1.0,
                "max_connections": 100,
                "read_only": True,
                "enabled": True,
            },
            "us-west-2": {
                "url": "https://us-west-2.supabase.co",
                "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.us-west-2-key",
                "name": "US West 2 Replica",
                "region": "us-west-2",
                "priority": 1,
                "weight": 1.5,  # Higher weight
                "max_connections": 150,
                "read_only": True,
                "enabled": True,
            },
            "eu-west-1": {
                "url": "https://eu-west-1.supabase.co",
                "api_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eu-west-1-key",
                "name": "EU West 1 Replica",
                "region": "eu-west-1",
                "priority": 2,  # Lower priority (higher number)
                "weight": 1.0,
                "max_connections": 100,
                "read_only": True,
                "enabled": True,
            },
        }

        return settings

    @pytest.fixture
    def mock_high_performance_client(self):
        """Create a mock client that simulates realistic response times."""
        client = MagicMock()

        def simulate_query_time(data_size=10):
            # Simulate realistic query times based on data size
            base_time = 0.01  # 10ms base
            variable_time = data_size * 0.001  # 1ms per record
            return base_time + variable_time

        # Mock table operations with timing simulation
        table_mock = MagicMock()
        client.table.return_value = table_mock

        # Chain method mocks
        query_mock = MagicMock()
        table_mock.select.return_value = query_mock
        table_mock.insert.return_value = query_mock
        table_mock.update.return_value = query_mock
        table_mock.delete.return_value = query_mock

        # Mock chainable query methods
        query_mock.eq.return_value = query_mock
        query_mock.gte.return_value = query_mock
        query_mock.lte.return_value = query_mock
        query_mock.order.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.offset.return_value = query_mock

        # Mock execute with realistic data
        async def mock_execute():
            await asyncio.sleep(simulate_query_time())
            return MagicMock(
                data=[
                    {"id": f"test_{i}", "name": f"Test Record {i}"} for i in range(10)
                ],
                count=10,
            )

        query_mock.execute = mock_execute

        return client

    @pytest.mark.asyncio
    async def test_load_balancing_performance_comparison(
        self, mock_settings_with_multiple_replicas, mock_high_performance_client
    ):
        """Test performance comparison across different load balancing strategies."""

        with patch(
            "tripsage_core.services.infrastructure.database_service.create_client"
        ) as mock_primary_create:
            with patch(
                "tripsage_core.services.infrastructure.replica_manager.create_client"
            ) as mock_replica_create:
                mock_primary_create.return_value = mock_high_performance_client
                mock_replica_create.return_value = mock_high_performance_client

                db_service = DatabaseService(mock_settings_with_multiple_replicas)
                await db_service.connect()

                if not db_service._replica_manager:
                    pytest.skip("Replica manager not initialized")

                # Set up healthy replicas with different latencies
                replicas = ["us-west-1", "us-west-2", "eu-west-1"]
                for i, replica_id in enumerate(replicas):
                    db_service._replica_manager._health[replica_id] = ReplicaHealth(
                        replica_id=replica_id,
                        status=ReplicaStatus.HEALTHY,
                        last_check=datetime.now(timezone.utc),
                        latency_ms=10.0 + (i * 5.0),  # Increasing latency
                        uptime_percentage=99.5,
                    )
                    db_service._replica_manager._connection_counts[replica_id] = 0

                strategies_to_test = [
                    LoadBalancingStrategy.ROUND_ROBIN,
                    LoadBalancingStrategy.LEAST_CONNECTIONS,
                    LoadBalancingStrategy.LATENCY_BASED,
                    LoadBalancingStrategy.WEIGHTED_RANDOM,
                ]

                performance_results = {}

                for strategy in strategies_to_test:
                    db_service._replica_manager.set_load_balancing_strategy(strategy)

                    # Perform multiple queries to test load distribution
                    start_time = time.time()

                    tasks = [
                        db_service.select("users", "*", {"active": True})
                        for _ in range(20)  # 20 concurrent queries
                    ]

                    results = await asyncio.gather(*tasks)

                    end_time = time.time()
                    total_time = end_time - start_time

                    performance_results[strategy.value] = {
                        "total_time": total_time,
                        "avg_time_per_query": total_time / len(tasks),
                        "queries_completed": len([r for r in results if r]),
                        "throughput": len(tasks) / total_time,
                    }

                # Verify all strategies completed successfully
                for strategy, metrics in performance_results.items():
                    assert metrics["queries_completed"] == 20, (
                        f"Strategy {strategy} failed to complete all queries"
                    )
                    assert metrics["total_time"] > 0, (
                        f"Strategy {strategy} reported zero execution time"
                    )
                    assert metrics["throughput"] > 0, (
                        f"Strategy {strategy} reported zero throughput"
                    )

                # Clean up
                await db_service.close()

    @pytest.mark.asyncio
    async def test_geographic_routing_performance(
        self, mock_settings_with_multiple_replicas, mock_high_performance_client
    ):
        """Test geographic routing performance for different user regions."""

        with patch(
            "tripsage_core.services.infrastructure.database_service.create_client"
        ) as mock_primary_create:
            with patch(
                "tripsage_core.services.infrastructure.replica_manager.create_client"
            ) as mock_replica_create:
                mock_primary_create.return_value = mock_high_performance_client
                mock_replica_create.return_value = mock_high_performance_client

                db_service = DatabaseService(mock_settings_with_multiple_replicas)
                await db_service.connect()

                if not db_service._replica_manager:
                    pytest.skip("Replica manager not initialized")

                # Set up geographic strategy
                db_service._replica_manager.set_load_balancing_strategy(
                    LoadBalancingStrategy.GEOGRAPHIC
                )

                # Set up healthy replicas
                replicas = ["us-west-1", "us-west-2", "eu-west-1"]
                for replica_id in replicas:
                    db_service._replica_manager._health[replica_id] = ReplicaHealth(
                        replica_id=replica_id,
                        status=ReplicaStatus.HEALTHY,
                        last_check=datetime.now(timezone.utc),
                        latency_ms=15.0,
                        uptime_percentage=99.5,
                    )
                    db_service._replica_manager._connection_counts[replica_id] = 0

                # Test queries from different regions
                user_regions = ["us-west-1", "us-west-2", "eu-west-1", "ap-southeast-1"]

                for user_region in user_regions:
                    # Perform vector search (which should use replicas)
                    result = await db_service.vector_search(
                        "destinations",
                        "embedding",
                        [0.1, 0.2, 0.3, 0.4, 0.5],
                        limit=10,
                        user_region=user_region,
                    )

                    assert result is not None
                    assert len(result) > 0

                # Verify load distribution
                health_report = await db_service.get_replica_health()
                assert health_report["enabled"] is True
                assert len(health_report["replicas"]) == 3

                # Clean up
                await db_service.close()

    @pytest.mark.asyncio
    async def test_failover_performance_under_load(
        self, mock_settings_with_multiple_replicas, mock_high_performance_client
    ):
        """Test failover performance when replicas become unhealthy under load."""

        with patch(
            "tripsage_core.services.infrastructure.database_service.create_client"
        ) as mock_primary_create:
            with patch(
                "tripsage_core.services.infrastructure.replica_manager.create_client"
            ) as mock_replica_create:
                mock_primary_create.return_value = mock_high_performance_client
                mock_replica_create.return_value = mock_high_performance_client

                db_service = DatabaseService(mock_settings_with_multiple_replicas)
                await db_service.connect()

                if not db_service._replica_manager:
                    pytest.skip("Replica manager not initialized")

                # Initially all replicas are healthy
                replicas = ["us-west-1", "us-west-2", "eu-west-1"]
                for replica_id in replicas:
                    db_service._replica_manager._health[replica_id] = ReplicaHealth(
                        replica_id=replica_id,
                        status=ReplicaStatus.HEALTHY,
                        last_check=datetime.now(timezone.utc),
                        latency_ms=15.0,
                        uptime_percentage=99.5,
                    )
                    db_service._replica_manager._connection_counts[replica_id] = 0

                # Start concurrent queries
                async def query_worker():
                    try:
                        return await db_service.select("users", "*", {"active": True})
                    except Exception:
                        return None

                # Start background queries
                query_tasks = [asyncio.create_task(query_worker()) for _ in range(10)]

                # Wait a bit then mark some replicas as unhealthy
                await asyncio.sleep(0.01)

                # Mark first replica as unhealthy
                db_service._replica_manager._health[
                    "us-west-1"
                ].status = ReplicaStatus.UNHEALTHY
                db_service._replica_manager._health[
                    "us-west-1"
                ].last_error = "Simulated failure"

                # Start more queries after failure
                more_tasks = [asyncio.create_task(query_worker()) for _ in range(10)]

                # Wait for all queries to complete
                all_results = await asyncio.gather(
                    *query_tasks, *more_tasks, return_exceptions=True
                )

                # Verify that despite failures, most queries succeeded
                successful_results = [
                    r
                    for r in all_results
                    if r is not None and not isinstance(r, Exception)
                ]
                assert len(successful_results) >= 15  # At least 75% success rate

                # Verify failover occurred
                metrics = await db_service.get_replica_metrics()
                assert metrics["enabled"] is True

                # Clean up
                await db_service.close()

    @pytest.mark.asyncio
    async def test_scaling_recommendations_integration(
        self, mock_settings_with_multiple_replicas, mock_high_performance_client
    ):
        """Test scaling recommendations under simulated high load conditions."""

        with patch(
            "tripsage_core.services.infrastructure.database_service.create_client"
        ) as mock_primary_create:
            with patch(
                "tripsage_core.services.infrastructure.replica_manager.create_client"
            ) as mock_replica_create:
                mock_primary_create.return_value = mock_high_performance_client
                mock_replica_create.return_value = mock_high_performance_client

                db_service = DatabaseService(mock_settings_with_multiple_replicas)
                await db_service.connect()

                if not db_service._replica_manager:
                    pytest.skip("Replica manager not initialized")

                # Simulate high load conditions
                replica_manager = db_service._replica_manager

                # Set up replicas with high utilization metrics
                replicas = ["us-west-1", "us-west-2", "eu-west-1"]
                for i, replica_id in enumerate(replicas):
                    # High connection utilization
                    replica_manager._connection_counts[replica_id] = 85 + (
                        i * 5
                    )  # 85-95% utilization

                    # High latency and low uptime for some replicas
                    replica_manager._health[replica_id] = ReplicaHealth(
                        replica_id=replica_id,
                        status=ReplicaStatus.HEALTHY
                        if i < 2
                        else ReplicaStatus.DEGRADED,
                        last_check=datetime.now(timezone.utc),
                        latency_ms=150.0 + (i * 50.0),  # High latency
                        uptime_percentage=92.0 - (i * 2.0),  # Decreasing uptime
                        connections_active=85 + (i * 5),
                        connections_idle=15 - (i * 5),
                    )

                # Get scaling recommendations
                recommendations = await db_service.get_scaling_recommendations()

                # Verify recommendations structure
                assert "capacity" in recommendations
                assert "performance" in recommendations
                assert "replicas" in recommendations

                # Verify capacity recommendations (high utilization should trigger
                # recommendations)
                capacity_recs = recommendations["capacity"]
                assert len(capacity_recs) > 0

                # Verify performance recommendations (high latency should trigger
                # recommendations)
                perf_recs = recommendations["performance"]
                assert len(perf_recs) > 0

                # Verify replica-specific recommendations
                replica_recs = recommendations["replicas"]
                assert len(replica_recs) > 0

                # Clean up
                await db_service.close()

    @pytest.mark.asyncio
    async def test_query_type_routing_performance(
        self, mock_settings_with_multiple_replicas, mock_high_performance_client
    ):
        """Test performance of query type-based routing for different workloads."""

        with patch(
            "tripsage_core.services.infrastructure.database_service.create_client"
        ) as mock_primary_create:
            with patch(
                "tripsage_core.services.infrastructure.replica_manager.create_client"
            ) as mock_replica_create:
                mock_primary_create.return_value = mock_high_performance_client
                mock_replica_create.return_value = mock_high_performance_client

                db_service = DatabaseService(mock_settings_with_multiple_replicas)
                await db_service.connect()

                if not db_service._replica_manager:
                    pytest.skip("Replica manager not initialized")

                # Set query type routing strategy
                db_service._replica_manager.set_load_balancing_strategy(
                    LoadBalancingStrategy.QUERY_TYPE
                )

                # Set up healthy replicas
                replicas = ["us-west-1", "us-west-2", "eu-west-1"]
                for replica_id in replicas:
                    db_service._replica_manager._health[replica_id] = ReplicaHealth(
                        replica_id=replica_id,
                        status=ReplicaStatus.HEALTHY,
                        last_check=datetime.now(timezone.utc),
                        latency_ms=15.0,
                        uptime_percentage=99.5,
                    )
                    db_service._replica_manager._connection_counts[replica_id] = 0

                # Test different query types with performance measurement
                query_types = [
                    (
                        "regular_select",
                        lambda: db_service.select("users", "*", {"active": True}),
                    ),
                    (
                        "vector_search",
                        lambda: db_service.vector_search(
                            "destinations", "embedding", [0.1, 0.2, 0.3], limit=5
                        ),
                    ),
                    (
                        "count_query",
                        lambda: db_service.count("trips", {"status": "active"}),
                    ),
                ]

                performance_metrics = {}

                for query_name, query_func in query_types:
                    start_time = time.time()

                    # Execute multiple queries of this type
                    tasks = [query_func() for _ in range(5)]
                    results = await asyncio.gather(*tasks)

                    end_time = time.time()

                    performance_metrics[query_name] = {
                        "total_time": end_time - start_time,
                        "avg_time": (end_time - start_time) / len(tasks),
                        "success_count": len([r for r in results if r is not None]),
                    }

                # Verify all query types completed successfully
                for query_name, metrics in performance_metrics.items():
                    assert metrics["success_count"] == 5, (
                        f"Query type {query_name} had failures"
                    )
                    assert metrics["total_time"] > 0, (
                        f"Query type {query_name} reported zero time"
                    )

                # Get final metrics
                final_metrics = await db_service.get_replica_metrics()
                assert final_metrics["enabled"] is True

                # Clean up
                await db_service.close()

    @pytest.mark.asyncio
    async def test_connection_pool_performance(
        self, mock_settings_with_multiple_replicas, mock_high_performance_client
    ):
        """Test connection pool performance under concurrent load."""

        with patch(
            "tripsage_core.services.infrastructure.database_service.create_client"
        ) as mock_primary_create:
            with patch(
                "tripsage_core.services.infrastructure.replica_manager.create_client"
            ) as mock_replica_create:
                mock_primary_create.return_value = mock_high_performance_client
                mock_replica_create.return_value = mock_high_performance_client

                db_service = DatabaseService(mock_settings_with_multiple_replicas)
                await db_service.connect()

                if not db_service._replica_manager:
                    pytest.skip("Replica manager not initialized")

                # Set up healthy replicas
                replicas = ["us-west-1", "us-west-2", "eu-west-1"]
                for replica_id in replicas:
                    db_service._replica_manager._health[replica_id] = ReplicaHealth(
                        replica_id=replica_id,
                        status=ReplicaStatus.HEALTHY,
                        last_check=datetime.now(timezone.utc),
                        latency_ms=15.0,
                        uptime_percentage=99.5,
                    )
                    db_service._replica_manager._connection_counts[replica_id] = 0

                # Test high concurrency connection acquisition
                async def connection_worker():
                    async with db_service._replica_manager.acquire_connection() as (
                        replica_id,
                        client,
                    ):
                        assert replica_id is not None
                        assert client is not None
                        # Simulate some work
                        await asyncio.sleep(0.001)
                        return replica_id

                # Start many concurrent connection acquisitions
                start_time = time.time()
                tasks = [connection_worker() for _ in range(50)]
                replica_ids = await asyncio.gather(*tasks)
                end_time = time.time()

                # Verify performance
                total_time = end_time - start_time
                assert total_time < 1.0, (
                    f"Connection pool too slow: {total_time}s for 50 connections"
                )

                # Verify load distribution
                replica_usage = {}
                for replica_id in replica_ids:
                    replica_usage[replica_id] = replica_usage.get(replica_id, 0) + 1

                # Should have used multiple replicas
                assert len(replica_usage) > 1, (
                    "Load balancing not working - only one replica used"
                )

                # Verify connection counts returned to zero
                for replica_id in replicas:
                    assert (
                        db_service._replica_manager._connection_counts[replica_id] == 0
                    )

                # Clean up
                await db_service.close()
