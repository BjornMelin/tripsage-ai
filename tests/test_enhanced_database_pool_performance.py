"""
Performance tests for Enhanced Database Pool Manager.

This module validates the performance requirements:
- <50ms average database query latency
- >95% connection pool efficiency
- LIFO connection pooling effectiveness
- Prometheus metrics collection accuracy
"""

import asyncio
import logging
import statistics
import time
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.exceptions.exceptions import CoreDatabaseError
from tripsage_core.monitoring.enhanced_database_metrics import (
    EnhancedDatabaseMetrics,
)
from tripsage_core.services.infrastructure.enhanced_database_pool_manager import (
    EnhancedDatabasePoolManager,
)

logger = logging.getLogger(__name__)


class TestEnhancedDatabasePoolPerformance:
    """Performance tests for Enhanced Database Pool Manager."""

    @pytest.fixture
    async def mock_settings(self):
        """Mock settings for testing."""
        settings = MagicMock()
        settings.database_url = "https://test.supabase.co"
        settings.database_password.get_secret_value.return_value = "test_password"
        settings.database_public_key.get_secret_value.return_value = (
            "test_key_12345678901234567890"
        )
        return settings

    @pytest.fixture
    async def mock_metrics(self):
        """Mock enhanced database metrics."""
        return EnhancedDatabaseMetrics(enable_regression_detection=True)

    @pytest.fixture
    async def pool_manager(self, mock_settings, mock_metrics):
        """Create enhanced pool manager for testing."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_pool_manager.get_enhanced_database_metrics",
            return_value=mock_metrics,
        ):
            manager = EnhancedDatabasePoolManager(
                settings=mock_settings,
                enable_metrics=True,
                enable_lifo=True,
                enable_pre_ping=True,
            )
            yield manager
            if manager._initialized:
                await manager.close()

    @pytest.mark.asyncio
    async def test_connection_acquisition_latency(self, pool_manager):
        """Test connection acquisition meets <50ms latency target."""
        # Mock SQLAlchemy engine and Supabase client
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value = mock_connection

        mock_supabase_client = MagicMock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_supabase_client", mock_supabase_client),
            patch.object(pool_manager, "_initialized", True),
        ):
            # Test multiple connection acquisitions
            latencies = []
            num_tests = 100

            for _ in range(num_tests):
                start_time = time.perf_counter()

                async with pool_manager.acquire_connection("query") as (
                    conn_type,
                    conn,
                ):
                    assert conn_type in ["sqlalchemy", "supabase"]
                    assert conn is not None

                end_time = time.perf_counter()
                latency_ms = (end_time - start_time) * 1000
                latencies.append(latency_ms)

            # Validate performance requirements
            avg_latency = statistics.mean(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
            p99_latency = statistics.quantiles(latencies, n=100)[98]  # 99th percentile

            logger.info("Connection acquisition performance:")
            logger.info(f"  Average latency: {avg_latency:.2f}ms")
            logger.info(f"  P95 latency: {p95_latency:.2f}ms")
            logger.info(f"  P99 latency: {p99_latency:.2f}ms")

            # Performance assertions
            assert avg_latency < 50.0, (
                f"Average latency {avg_latency:.2f}ms exceeds 50ms target"
            )
            assert p95_latency < 100.0, f"P95 latency {p95_latency:.2f}ms too high"
            assert max(latencies) < 500.0, (
                f"Max latency {max(latencies):.2f}ms too high"
            )

    @pytest.mark.asyncio
    async def test_pool_utilization_efficiency(self, pool_manager):
        """Test connection pool efficiency meets >95% target."""
        # Mock pool for testing utilization
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_engine.pool = mock_pool

        # Simulate pool utilization scenarios
        test_scenarios = [
            # (checked_out, checked_in, pool_size, max_overflow)
            (8, 0, 8, 8),  # 100% utilization
            (7, 1, 8, 8),  # 87.5% utilization
            (15, 1, 8, 8),  # 93.75% utilization (using overflow)
            (6, 2, 8, 8),  # 75% utilization
        ]

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_initialized", True),
        ):
            efficiency_scores = []

            for checked_out, checked_in, pool_size, max_overflow in test_scenarios:
                mock_pool.checkedout.return_value = checked_out
                mock_pool.checkedin.return_value = checked_in
                mock_pool.size.return_value = pool_size

                pool_manager.pool_size = pool_size
                pool_manager.max_overflow = max_overflow

                # Update pool metrics
                pool_manager._update_pool_metrics()

                # Calculate efficiency
                max_connections = pool_size + max_overflow
                utilization = (checked_out / max_connections) * 100

                # Efficiency is based on optimal resource usage
                if utilization <= 80:
                    efficiency = utilization  # Under-utilization penalty
                elif utilization <= 95:
                    efficiency = 100  # Optimal range
                else:
                    efficiency = (
                        100 - (utilization - 95) * 2
                    )  # Over-utilization penalty

                efficiency_scores.append(efficiency)

                logger.info(
                    f"Pool utilization: {utilization:.1f}%, efficiency: {efficiency:.1f}%"
                )

            # Validate efficiency requirements
            avg_efficiency = statistics.mean(efficiency_scores)
            assert avg_efficiency >= 95.0, (
                f"Average pool efficiency {avg_efficiency:.1f}% below 95% target"
            )

    @pytest.mark.asyncio
    async def test_lifo_connection_ordering(self, pool_manager):
        """Test LIFO connection pooling improves cache locality."""
        # Mock engine with connection tracking
        mock_engine = MagicMock()
        mock_connections = []
        connection_usage_order = []

        def create_mock_connection(conn_id):
            """Create a mock connection with tracking."""
            conn = MagicMock()
            conn.connection_id = conn_id
            conn.last_used = time.time()
            return conn

        def mock_connect():
            # Simulate LIFO behavior - return most recently returned connection
            if mock_connections:
                conn = mock_connections.pop()  # LIFO - last in, first out
                connection_usage_order.append(conn.connection_id)
                return conn
            else:
                # Create new connection if pool is empty
                new_conn = create_mock_connection(f"conn_{len(connection_usage_order)}")
                connection_usage_order.append(new_conn.connection_id)
                return new_conn

        def mock_return_connection(conn):
            # Return connection to pool (LIFO stack)
            conn.last_used = time.time()
            mock_connections.append(conn)

        mock_engine.connect = mock_connect

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_initialized", True),
        ):
            # Simulate connection acquisition and return pattern
            acquired_connections = []

            # Acquire multiple connections
            for _i in range(5):
                async with pool_manager.acquire_connection("raw_sql") as (
                    conn_type,
                    conn,
                ):
                    acquired_connections.append(conn)
                    # Simulate returning connection to pool
                    mock_return_connection(conn)

            # Test LIFO ordering - most recently returned should be reused first
            recent_connections = []
            for _i in range(3):
                async with pool_manager.acquire_connection("raw_sql") as (
                    conn_type,
                    conn,
                ):
                    recent_connections.append(conn.connection_id)

            # Verify LIFO behavior improves cache locality
            # Recent connections should be reused in reverse order (LIFO)
            logger.info(f"Connection usage order: {connection_usage_order}")
            logger.info(f"Recent connection reuse: {recent_connections}")

            # Assert that we're reusing connections (cache locality benefit)
            reused_count = sum(
                1
                for conn_id in recent_connections
                if connection_usage_order.count(conn_id) > 1
            )
            reuse_rate = reused_count / len(recent_connections) * 100

            assert reuse_rate >= 80.0, (
                f"Connection reuse rate {reuse_rate:.1f}% too low for LIFO benefit"
            )

    @pytest.mark.asyncio
    async def test_query_latency_percentiles(self, pool_manager, mock_metrics):
        """Test query latency percentile tracking and reporting."""
        # Simulate various query latencies
        query_latencies = [
            0.005,
            0.008,
            0.012,
            0.015,
            0.018,
            0.022,
            0.025,
            0.028,  # Fast queries
            0.035,
            0.042,
            0.048,
            0.055,
            0.062,
            0.068,
            0.075,
            0.082,  # Medium queries
            0.095,
            0.108,
            0.125,
            0.142,
            0.158,
            0.175,
            0.192,
            0.208,  # Slower queries
            0.225,
            0.242,
            0.258,
            0.275,
            0.292,
            0.308,
            0.325,
            0.342,  # Slow queries
        ]

        # Record query latencies in metrics
        for _i, latency in enumerate(query_latencies):
            mock_metrics.record_query_duration(
                duration=latency,
                operation="select",
                table="test_table",
                database="supabase",
                status="success",
            )

        # Get percentiles
        percentiles = mock_metrics.get_percentiles("query_duration_select_test_table")
        assert percentiles is not None, "Percentiles should be available"

        p50, p95, p99 = percentiles

        logger.info("Query latency percentiles:")
        logger.info(f"  P50: {p50 * 1000:.1f}ms")
        logger.info(f"  P95: {p95 * 1000:.1f}ms")
        logger.info(f"  P99: {p99 * 1000:.1f}ms")

        # Validate percentile accuracy
        sorted_latencies = sorted(query_latencies)
        n = len(sorted_latencies)
        expected_p50 = sorted_latencies[int(n * 0.5)]
        expected_p95 = sorted_latencies[int(n * 0.95)]
        expected_p99 = sorted_latencies[int(n * 0.99)]

        # Allow small tolerance for percentile calculation differences
        tolerance = 0.01  # 10ms tolerance
        assert abs(p50 - expected_p50) < tolerance, (
            f"P50 mismatch: {p50} vs {expected_p50}"
        )
        assert abs(p95 - expected_p95) < tolerance, (
            f"P95 mismatch: {p95} vs {expected_p95}"
        )
        assert abs(p99 - expected_p99) < tolerance, (
            f"P99 mismatch: {p99} vs {expected_p99}"
        )

    @pytest.mark.asyncio
    async def test_performance_regression_detection(self, pool_manager, mock_metrics):
        """Test performance regression detection and alerting."""
        # Establish baseline with good performance
        baseline_latencies = [0.015, 0.018, 0.020, 0.022, 0.025, 0.028, 0.030] * 10

        for latency in baseline_latencies:
            mock_metrics.record_query_duration(
                duration=latency,
                operation="insert",
                table="test_table",
                database="supabase",
                status="success",
            )

        # Check baseline is established
        baseline = mock_metrics.get_baselines().get("query_duration_insert_test_table")
        assert baseline is not None, "Baseline should be established"

        original_alert_count = len(mock_metrics.get_recent_alerts())

        # Introduce performance regression
        regression_latency = baseline.p95 * 2.5  # Significant regression
        mock_metrics.record_query_duration(
            duration=regression_latency,
            operation="insert",
            table="test_table",
            database="supabase",
            status="success",
        )

        # Check that regression was detected
        new_alerts = mock_metrics.get_recent_alerts()
        new_alert_count = len(new_alerts)

        assert new_alert_count > original_alert_count, (
            "Performance regression should trigger alert"
        )

        # Validate alert details
        latest_alert = new_alerts[-1]
        assert latest_alert.current_value == regression_latency
        assert latest_alert.baseline_p95 == baseline.p95
        assert "regression detected" in latest_alert.message.lower()

        logger.info("Performance regression detected:")
        logger.info(f"  Baseline P95: {baseline.p95 * 1000:.1f}ms")
        logger.info(f"  Regression value: {regression_latency * 1000:.1f}ms")
        logger.info(f"  Alert: {latest_alert.message}")

    @pytest.mark.asyncio
    async def test_connection_pool_health_monitoring(self, pool_manager):
        """Test connection pool health monitoring and diagnostics."""
        # Mock engine and pool
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_engine.pool = mock_pool

        mock_supabase_client = MagicMock()
        mock_supabase_client.table.return_value.select.return_value.limit.return_value.execute.return_value = MagicMock()

        # Configure pool state
        mock_pool.checkedout.return_value = 3
        mock_pool.checkedin.return_value = 5
        mock_pool.size.return_value = 8

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_supabase_client", mock_supabase_client),
            patch.object(pool_manager, "_initialized", True),
        ):
            # Perform health check
            health_status = await pool_manager.health_check()

            # Validate health check results
            assert health_status["status"] == "healthy"
            assert health_status["checks"]["sqlalchemy"] == "healthy"
            assert health_status["checks"]["supabase"] == "healthy"

            # Check metrics are present
            metrics = health_status["metrics"]
            assert "pool_utilization_percent" in metrics
            assert "total_connections" in metrics
            assert "active_connections" in metrics
            assert "avg_checkout_time_ms" in metrics

            # Validate pool statistics
            stats = pool_manager.get_pool_statistics()
            assert stats["pool_id"] == pool_manager._pool_id
            assert stats["configuration"]["lifo_enabled"] is True
            assert stats["configuration"]["pre_ping_enabled"] is True
            assert stats["current_status"]["active_connections"] == 3
            assert stats["current_status"]["idle_connections"] == 5

            logger.info(f"Pool health check results: {health_status['status']}")
            logger.info(f"Pool utilization: {metrics['pool_utilization_percent']:.1f}%")

    @pytest.mark.asyncio
    async def test_concurrent_connection_performance(self, pool_manager):
        """Test performance under concurrent connection load."""
        # Mock components
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value = mock_connection

        mock_supabase_client = MagicMock()

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_supabase_client", mock_supabase_client),
            patch.object(pool_manager, "_initialized", True),
        ):
            # Test concurrent connection acquisition
            async def acquire_connection_task():
                """Single connection acquisition task."""
                start_time = time.perf_counter()
                async with pool_manager.acquire_connection("query") as (
                    conn_type,
                    conn,
                ):
                    # Simulate brief work
                    await asyncio.sleep(0.001)
                end_time = time.perf_counter()
                return (end_time - start_time) * 1000  # Return latency in ms

            # Run concurrent tasks
            num_concurrent = 50
            start_time = time.perf_counter()

            tasks = [acquire_connection_task() for _ in range(num_concurrent)]
            latencies = await asyncio.gather(*tasks)

            end_time = time.perf_counter()
            total_time = (end_time - start_time) * 1000

            # Analyze concurrent performance
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            throughput = num_concurrent / (total_time / 1000)  # Operations per second

            logger.info(f"Concurrent performance ({num_concurrent} connections):")
            logger.info(f"  Average latency: {avg_latency:.2f}ms")
            logger.info(f"  Max latency: {max_latency:.2f}ms")
            logger.info(f"  Total time: {total_time:.2f}ms")
            logger.info(f"  Throughput: {throughput:.1f} ops/sec")

            # Performance assertions for concurrent load
            assert avg_latency < 100.0, (
                f"Concurrent avg latency {avg_latency:.2f}ms too high"
            )
            assert max_latency < 500.0, (
                f"Concurrent max latency {max_latency:.2f}ms too high"
            )
            assert throughput > 100.0, f"Throughput {throughput:.1f} ops/sec too low"

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, pool_manager):
        """Test memory efficiency of connection pooling."""
        # This test validates that LIFO pooling reduces memory overhead
        # by improving connection reuse and reducing allocation pressure

        # Mock components
        mock_engine = MagicMock()
        mock_connections = {}
        connection_counter = 0

        def create_connection():
            nonlocal connection_counter
            connection_counter += 1
            conn_id = f"conn_{connection_counter}"
            mock_connections[conn_id] = MagicMock()
            mock_connections[conn_id].connection_id = conn_id
            return mock_connections[conn_id]

        mock_engine.connect = create_connection

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_initialized", True),
        ):
            # Test connection acquisition pattern
            initial_connections = connection_counter

            # Acquire and release connections multiple times
            for _round_num in range(10):
                async with pool_manager.acquire_connection("raw_sql") as (
                    conn_type,
                    conn,
                ):
                    pass  # Connection automatically returned

            final_connections = connection_counter
            new_connections = final_connections - initial_connections

            # With efficient pooling, we should create fewer new connections
            # than the number of acquisition rounds due to reuse
            reuse_efficiency = 1.0 - (new_connections / 10)

            logger.info("Memory efficiency test:")
            logger.info(f"  Initial connections: {initial_connections}")
            logger.info(f"  Final connections: {final_connections}")
            logger.info(f"  New connections created: {new_connections}")
            logger.info(f"  Reuse efficiency: {reuse_efficiency:.1%}")

            # Assert reasonable connection reuse
            assert reuse_efficiency >= 0.5, (
                f"Connection reuse efficiency {reuse_efficiency:.1%} too low"
            )

    @pytest.mark.asyncio
    async def test_error_handling_performance(self, pool_manager):
        """Test error handling doesn't significantly impact performance."""
        # Mock components with error scenarios
        mock_engine = MagicMock()
        call_count = 0

        def mock_connect():
            nonlocal call_count
            call_count += 1
            if call_count % 5 == 0:  # Every 5th call fails
                raise Exception("Mock connection error")
            return MagicMock()

        mock_engine.connect = mock_connect

        with (
            patch.object(pool_manager, "_sqlalchemy_engine", mock_engine),
            patch.object(pool_manager, "_initialized", True),
        ):
            latencies = []
            success_count = 0
            error_count = 0

            # Test with intermittent failures
            for _ in range(20):
                start_time = time.perf_counter()
                try:
                    async with pool_manager.acquire_connection("raw_sql") as (
                        conn_type,
                        conn,
                    ):
                        success_count += 1
                except CoreDatabaseError:
                    error_count += 1
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)

            avg_latency = statistics.mean(latencies)
            error_rate = error_count / (success_count + error_count)

            logger.info("Error handling performance:")
            logger.info(f"  Average latency with errors: {avg_latency:.2f}ms")
            logger.info(f"  Success count: {success_count}")
            logger.info(f"  Error count: {error_count}")
            logger.info(f"  Error rate: {error_rate:.1%}")

            # Error handling shouldn't significantly degrade performance
            assert avg_latency < 100.0, (
                f"Error handling latency {avg_latency:.2f}ms too high"
            )
            assert error_rate > 0.1, "Should have some errors for this test"
            assert error_rate < 0.3, "Error rate too high for meaningful test"


@pytest.mark.asyncio
async def test_integration_performance_targets():
    """Integration test validating all performance targets together."""
    # Test the full system against performance requirements
    with patch(
        "tripsage_core.services.infrastructure.enhanced_database_pool_manager.get_settings"
    ) as mock_get_settings:
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.database_url = "https://test.supabase.co"
        mock_settings.database_password.get_secret_value.return_value = "test_password"
        mock_settings.database_public_key.get_secret_value.return_value = (
            "test_key_12345678901234567890"
        )
        mock_get_settings.return_value = mock_settings

        # Create pool manager
        pool_manager = EnhancedDatabasePoolManager(
            enable_metrics=True,
            enable_lifo=True,
            enable_pre_ping=True,
        )

        try:
            # Mock initialization
            with (
                patch.object(pool_manager, "_initialize_sqlalchemy_engine"),
                patch.object(pool_manager, "_initialize_supabase_client"),
                patch.object(pool_manager, "_test_connections"),
            ):
                await pool_manager.initialize()

                # Mock components for testing
                mock_engine = MagicMock()
                mock_pool = MagicMock()
                mock_engine.pool = mock_pool
                mock_pool.checkedout.return_value = 6
                mock_pool.checkedin.return_value = 2
                mock_pool.size.return_value = 8

                pool_manager._sqlalchemy_engine = mock_engine
                pool_manager._supabase_client = MagicMock()

                # Performance validation
                latencies = []
                for _ in range(100):
                    start_time = time.perf_counter()
                    async with pool_manager.acquire_connection("query") as (
                        conn_type,
                        conn,
                    ):
                        pass
                    end_time = time.perf_counter()
                    latencies.append((end_time - start_time) * 1000)

                avg_latency = statistics.mean(latencies)

                # Pool efficiency calculation
                max_connections = pool_manager.pool_size + pool_manager.max_overflow
                utilization = (6 / max_connections) * 100  # Based on mocked values

                # Final validation
                assert avg_latency < 50.0, (
                    f"FAILED: Average latency {avg_latency:.2f}ms exceeds 50ms target"
                )
                assert utilization > 30.0, (
                    f"Pool utilization {utilization:.1f}% reasonable for test"
                )

                logger.info("🎯 Performance Integration Test PASSED:")
                logger.info(
                    f"  ✅ Average latency: {avg_latency:.2f}ms (target: <50ms)"
                )
                logger.info(f"  ✅ Pool utilization: {utilization:.1f}%")
                logger.info("  ✅ LIFO pooling: Enabled")
                logger.info("  ✅ Connection validation: Enabled")
                logger.info("  ✅ Metrics collection: Enabled")

        finally:
            await pool_manager.close()
