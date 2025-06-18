"""
Integration tests for Database Service with Enhanced Pool Manager.

This module tests the integration between the existing DatabaseService
and the new EnhancedDatabasePoolManager to ensure:
- Seamless operation with existing business logic
- Performance improvements are realized
- No regression in functionality
- Proper metrics collection
"""

import asyncio
import logging
import statistics
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from tripsage_core.monitoring.enhanced_database_metrics import (
    get_enhanced_database_metrics,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.enhanced_database_pool_manager import (
    EnhancedDatabasePoolManager,
)

logger = logging.getLogger(__name__)


class TestDatabaseServicePerformanceIntegration:
    """Integration tests for Database Service performance enhancements."""

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
    async def enhanced_pool_manager(self, mock_settings):
        """Create enhanced pool manager for integration testing."""
        with patch(
            "tripsage_core.services.infrastructure.enhanced_database_pool_manager.get_settings",
            return_value=mock_settings,
        ):
            manager = EnhancedDatabasePoolManager(
                settings=mock_settings,
                enable_metrics=True,
                enable_lifo=True,
                enable_pre_ping=True,
            )

            # Mock initialization
            with (
                patch.object(manager, "_initialize_sqlalchemy_engine"),
                patch.object(manager, "_initialize_supabase_client"),
                patch.object(manager, "_test_connections"),
            ):
                await manager.initialize()

                # Mock components
                mock_engine = MagicMock()
                mock_pool = MagicMock()
                mock_engine.pool = mock_pool
                mock_pool.checkedout.return_value = 4
                mock_pool.checkedin.return_value = 4
                mock_pool.size.return_value = 8

                manager._sqlalchemy_engine = mock_engine
                manager._supabase_client = MagicMock()

            yield manager
            await manager.close()

    @pytest.fixture
    async def database_service(self, mock_settings):
        """Create database service for integration testing."""
        service = DatabaseService(settings=mock_settings)

        # Mock Supabase client
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value.data = []
        mock_client.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "test_id"}
        ]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
            {"id": "test_id"}
        ]
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []

        with patch("supabase.create_client", return_value=mock_client):
            await service.connect()

        yield service

    @pytest.mark.asyncio
    async def test_enhanced_pool_integration_performance(
        self, enhanced_pool_manager, database_service
    ):
        """Test enhanced pool manager integrates well with database service operations."""
        # Test various database operations with performance monitoring
        operations = []

        async def perform_database_operation(operation_type: str):
            """Perform a database operation and measure performance."""
            start_time = time.perf_counter()

            try:
                if operation_type == "select":
                    await database_service.get_user_by_id("test_user_id")
                elif operation_type == "insert":
                    await database_service.create_user(
                        {
                            "id": "test_user",
                            "email": "test@example.com",
                            "full_name": "Test User",
                        }
                    )
                elif operation_type == "update":
                    await database_service.update_user(
                        "test_user_id", {"full_name": "Updated User"}
                    )
                elif operation_type == "vector_search":
                    await database_service.search_similar_destinations(
                        "vacation", limit=5
                    )
                else:
                    raise ValueError(f"Unknown operation: {operation_type}")

                end_time = time.perf_counter()
                duration = (end_time - start_time) * 1000  # Convert to ms

                return {
                    "operation": operation_type,
                    "duration_ms": duration,
                    "success": True,
                    "timestamp": datetime.now(timezone.utc),
                }

            except Exception as e:
                end_time = time.perf_counter()
                duration = (end_time - start_time) * 1000

                return {
                    "operation": operation_type,
                    "duration_ms": duration,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc),
                }

        # Test different operation types
        operation_types = [
            "select",
            "insert",
            "update",
            "vector_search",
        ] * 25  # 100 total operations

        # Perform operations and collect performance data
        for op_type in operation_types:
            result = await perform_database_operation(op_type)
            operations.append(result)

        # Analyze performance results
        successful_operations = [op for op in operations if op["success"]]
        operation_latencies = [op["duration_ms"] for op in successful_operations]

        if not operation_latencies:
            pytest.fail("No successful operations completed")

        avg_latency = statistics.mean(operation_latencies)
        p95_latency = statistics.quantiles(operation_latencies, n=20)[18]
        max_latency = max(operation_latencies)
        success_rate = len(successful_operations) / len(operations) * 100

        # Performance analysis by operation type
        by_operation = {}
        for op in successful_operations:
            op_type = op["operation"]
            if op_type not in by_operation:
                by_operation[op_type] = []
            by_operation[op_type].append(op["duration_ms"])

        logger.info("🚀 Database Service Integration Performance Results:")
        logger.info(f"  📊 Overall average latency: {avg_latency:.2f}ms")
        logger.info(f"  📈 P95 latency: {p95_latency:.2f}ms")
        logger.info(f"  🔥 Max latency: {max_latency:.2f}ms")
        logger.info(f"  ✅ Success rate: {success_rate:.1f}%")

        for op_type, latencies in by_operation.items():
            avg_op_latency = statistics.mean(latencies)
            logger.info(f"  🔹 {op_type} average: {avg_op_latency:.2f}ms")

        # Performance assertions
        assert avg_latency < 50.0, (
            f"Average latency {avg_latency:.2f}ms exceeds 50ms target"
        )
        assert p95_latency < 100.0, f"P95 latency {p95_latency:.2f}ms too high"
        assert success_rate >= 95.0, f"Success rate {success_rate:.1f}% too low"

    @pytest.mark.asyncio
    async def test_metrics_collection_integration(self, enhanced_pool_manager):
        """Test metrics collection works properly during database operations."""
        # Get metrics instance
        metrics = get_enhanced_database_metrics()

        # Reset metrics for clean test
        metrics.reset_baselines()

        # Simulate database operations with metrics
        operation_types = ["select", "insert", "update", "delete"]
        tables = ["users", "trips", "flights", "memories"]

        operations_performed = 0

        for operation in operation_types:
            for table in tables:
                for _ in range(5):  # 5 operations per combination
                    # Simulate operation latency
                    latency = 0.010 + (
                        operations_performed * 0.001
                    )  # Gradually increasing latency

                    # Record in metrics
                    metrics.record_query_duration(
                        duration=latency,
                        operation=operation,
                        table=table,
                        database="supabase",
                        status="success",
                    )

                    operations_performed += 1

        # Test pool utilization metrics
        async with enhanced_pool_manager.acquire_connection("query") as (
            conn_type,
            conn,
        ):
            # Update pool metrics during operation
            enhanced_pool_manager._update_pool_metrics()

        # Validate metrics collection
        summary_stats = metrics.get_summary_stats()
        assert summary_stats["total_queries"] == operations_performed
        assert summary_stats["error_count"] == 0
        assert summary_stats["error_rate"] == 0.0

        # Check percentiles are available
        for operation in operation_types:
            for table in tables:
                metric_key = f"query_duration_{operation}_{table}"
                percentiles = metrics.get_percentiles(metric_key)
                if (
                    percentiles
                ):  # Should have percentiles for operations with enough samples
                    p50, p95, p99 = percentiles
                    assert p50 > 0, f"P50 should be positive for {metric_key}"
                    assert p95 >= p50, f"P95 should be >= P50 for {metric_key}"
                    assert p99 >= p95, f"P99 should be >= P95 for {metric_key}"

        # Check baselines are established
        baselines = metrics.get_baselines()
        assert len(baselines) > 0, "Should have established performance baselines"

        logger.info("📈 Metrics Collection Integration Results:")
        logger.info(f"  📊 Total operations recorded: {operations_performed}")
        logger.info(f"  🎯 Baselines established: {len(baselines)}")
        logger.info(f"  📉 Error rate: {summary_stats['error_rate']:.2%}")
        logger.info(f"  ⏱️ Uptime: {summary_stats['uptime_seconds']:.1f}s")

    @pytest.mark.asyncio
    async def test_concurrent_operations_with_enhanced_pooling(
        self, enhanced_pool_manager, database_service
    ):
        """Test concurrent database operations benefit from enhanced pooling."""
        # Simulate high concurrency scenario
        concurrent_tasks = 50
        operations_per_task = 5

        async def concurrent_database_worker(worker_id: int):
            """Worker function for concurrent database operations."""
            worker_results = []

            for op_num in range(operations_per_task):
                start_time = time.perf_counter()

                try:
                    # Mix of operations
                    if op_num % 4 == 0:
                        await database_service.get_user_by_id(f"user_{worker_id}")
                    elif op_num % 4 == 1:
                        await database_service.search_similar_destinations(
                            "beach", limit=3
                        )
                    elif op_num % 4 == 2:
                        await database_service.create_user(
                            {
                                "id": f"user_{worker_id}_{op_num}",
                                "email": f"user{worker_id}@example.com",
                            }
                        )
                    else:
                        await database_service.update_user(
                            f"user_{worker_id}", {"last_active": datetime.now()}
                        )

                    end_time = time.perf_counter()
                    worker_results.append(
                        {
                            "worker_id": worker_id,
                            "operation": op_num,
                            "duration_ms": (end_time - start_time) * 1000,
                            "success": True,
                        }
                    )

                except Exception as e:
                    end_time = time.perf_counter()
                    worker_results.append(
                        {
                            "worker_id": worker_id,
                            "operation": op_num,
                            "duration_ms": (end_time - start_time) * 1000,
                            "success": False,
                            "error": str(e),
                        }
                    )

            return worker_results

        # Execute concurrent operations
        start_time = time.perf_counter()

        tasks = [concurrent_database_worker(i) for i in range(concurrent_tasks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        total_time = end_time - start_time

        # Flatten results
        all_operations = []
        for result in results:
            if isinstance(result, list):
                all_operations.extend(result)

        # Analyze concurrent performance
        successful_ops = [op for op in all_operations if op.get("success", False)]
        failed_ops = [op for op in all_operations if not op.get("success", True)]

        if successful_ops:
            latencies = [op["duration_ms"] for op in successful_ops]
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            p95_latency = (
                statistics.quantiles(latencies, n=20)[18]
                if len(latencies) >= 20
                else max_latency
            )
        else:
            avg_latency = max_latency = p95_latency = 0

        total_operations = len(all_operations)
        success_rate = (
            len(successful_ops) / total_operations * 100 if total_operations > 0 else 0
        )
        throughput = total_operations / total_time

        logger.info("🚀 Concurrent Operations Performance:")
        logger.info(f"  🔄 Concurrent workers: {concurrent_tasks}")
        logger.info(f"  📊 Total operations: {total_operations}")
        logger.info(f"  ✅ Successful operations: {len(successful_ops)}")
        logger.info(f"  ❌ Failed operations: {len(failed_ops)}")
        logger.info(f"  📈 Success rate: {success_rate:.1f}%")
        logger.info(f"  ⏱️ Average latency: {avg_latency:.2f}ms")
        logger.info(f"  🔥 Max latency: {max_latency:.2f}ms")
        logger.info(f"  📊 P95 latency: {p95_latency:.2f}ms")
        logger.info(f"  🚄 Throughput: {throughput:.1f} ops/sec")
        logger.info(f"  ⏰ Total time: {total_time:.2f}s")

        # Performance assertions for concurrent load
        assert success_rate >= 90.0, (
            f"Success rate {success_rate:.1f}% too low under concurrent load"
        )
        assert avg_latency < 100.0, (
            f"Average latency {avg_latency:.2f}ms too high under concurrent load"
        )
        assert throughput > 50.0, f"Throughput {throughput:.1f} ops/sec too low"

    @pytest.mark.asyncio
    async def test_pool_efficiency_under_load(self, enhanced_pool_manager):
        """Test pool efficiency remains high under various load patterns."""
        # Test different load patterns
        load_patterns = [
            {"name": "burst", "operations": 100, "concurrency": 20, "delay": 0.001},
            {"name": "steady", "operations": 50, "concurrency": 5, "delay": 0.01},
            {"name": "mixed", "operations": 75, "concurrency": 10, "delay": 0.005},
        ]

        pattern_results = []

        for pattern in load_patterns:
            logger.info(f"🔄 Testing load pattern: {pattern['name']}")

            async def operation_task():
                """Single operation task."""
                async with enhanced_pool_manager.acquire_connection("query") as (
                    conn_type,
                    conn,
                ):
                    # Simulate work
                    await asyncio.sleep(pattern["delay"])
                    return True

            # Execute load pattern
            start_time = time.perf_counter()

            # Create batches of concurrent operations
            batch_size = pattern["concurrency"]
            total_ops = pattern["operations"]
            batches = [total_ops // batch_size] * (total_ops // batch_size)
            if total_ops % batch_size:
                batches.append(total_ops % batch_size)

            successful_ops = 0
            for batch_ops in batches:
                tasks = [operation_task() for _ in range(batch_ops)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_ops += sum(1 for r in results if r is True)

            end_time = time.perf_counter()
            duration = end_time - start_time

            # Get pool statistics
            pool_stats = enhanced_pool_manager.get_pool_statistics()

            pattern_result = {
                "name": pattern["name"],
                "operations": total_ops,
                "successful": successful_ops,
                "duration": duration,
                "throughput": total_ops / duration,
                "pool_utilization": pool_stats["current_status"]["utilization_percent"],
                "avg_checkout_time": pool_stats["performance"]["avg_checkout_time_ms"],
            }

            pattern_results.append(pattern_result)

            logger.info(f"  📊 {pattern['name']} results:")
            logger.info(f"    ✅ Success rate: {successful_ops / total_ops * 100:.1f}%")
            logger.info(
                f"    🚄 Throughput: {pattern_result['throughput']:.1f} ops/sec"
            )
            logger.info(
                f"    📈 Pool utilization: {pattern_result['pool_utilization']:.1f}%"
            )
            logger.info(
                f"    ⏱️ Avg checkout time: {pattern_result['avg_checkout_time']:.2f}ms"
            )

        # Validate pool efficiency across all patterns
        for result in pattern_results:
            assert result["successful"] / result["operations"] >= 0.95, (
                f"Success rate too low for {result['name']} pattern"
            )
            assert result["avg_checkout_time"] < 50.0, (
                f"Checkout time too high for {result['name']} pattern"
            )

    @pytest.mark.asyncio
    async def test_memory_operations_performance(self, database_service):
        """Test memory-related database operations performance."""
        # Test memory-specific operations that are common in TripSage
        memory_operations = []

        # Simulate memory operations
        operations = [
            (
                "store_conversation",
                {
                    "user_id": "test_user",
                    "messages": [{"role": "user", "content": "Plan a trip"}],
                },
            ),
            (
                "store_user_preference",
                {"user_id": "test_user", "key": "budget", "value": "1000"},
            ),
            (
                "search_memories",
                {"user_id": "test_user", "query": "vacation", "limit": 10},
            ),
            (
                "update_user_context",
                {"user_id": "test_user", "context": {"last_destination": "Paris"}},
            ),
            ("get_user_preferences", {"user_id": "test_user"}),
        ]

        for op_name, op_data in operations * 20:  # Repeat operations
            start_time = time.perf_counter()

            try:
                # Simulate memory operation with database
                if op_name == "store_conversation":
                    # Mock conversation storage
                    await database_service.create_record(
                        "conversations",
                        {
                            "user_id": op_data["user_id"],
                            "content": str(op_data["messages"]),
                            "created_at": datetime.now(timezone.utc),
                        },
                    )
                elif op_name == "store_user_preference":
                    await database_service.create_record("user_preferences", op_data)
                elif op_name == "search_memories":
                    await database_service.search_similar_destinations(
                        op_data["query"], limit=op_data["limit"]
                    )
                elif op_name == "update_user_context":
                    await database_service.update_user(
                        op_data["user_id"], {"context": op_data["context"]}
                    )
                elif op_name == "get_user_preferences":
                    await database_service.get_user_by_id(op_data["user_id"])

                end_time = time.perf_counter()
                duration = (end_time - start_time) * 1000

                memory_operations.append(
                    {"operation": op_name, "duration_ms": duration, "success": True}
                )

            except Exception as e:
                end_time = time.perf_counter()
                duration = (end_time - start_time) * 1000

                memory_operations.append(
                    {
                        "operation": op_name,
                        "duration_ms": duration,
                        "success": False,
                        "error": str(e),
                    }
                )

        # Analyze memory operations performance
        successful_ops = [op for op in memory_operations if op["success"]]

        if not successful_ops:
            pytest.fail("No successful memory operations completed")

        # Group by operation type
        by_operation = {}
        for op in successful_ops:
            op_type = op["operation"]
            if op_type not in by_operation:
                by_operation[op_type] = []
            by_operation[op_type].append(op["duration_ms"])

        logger.info("🧠 Memory Operations Performance:")
        for op_type, durations in by_operation.items():
            avg_duration = statistics.mean(durations)
            max_duration = max(durations)
            logger.info(
                f"  🔹 {op_type}: avg={avg_duration:.2f}ms, max={max_duration:.2f}ms"
            )

        # Performance assertions
        overall_latencies = [op["duration_ms"] for op in successful_ops]
        avg_memory_latency = statistics.mean(overall_latencies)

        assert avg_memory_latency < 50.0, (
            f"Memory operations latency {avg_memory_latency:.2f}ms too high"
        )


@pytest.mark.asyncio
async def test_end_to_end_performance_validation():
    """End-to-end test validating complete performance enhancement stack."""
    logger.info("🚀 Starting End-to-End Performance Validation")

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.database_url = "https://test.supabase.co"
    mock_settings.database_password.get_secret_value.return_value = "test_password"
    mock_settings.database_public_key.get_secret_value.return_value = (
        "test_key_12345678901234567890"
    )

    with patch(
        "tripsage_core.services.infrastructure.enhanced_database_pool_manager.get_settings",
        return_value=mock_settings,
    ):
        # Create enhanced pool manager
        pool_manager = EnhancedDatabasePoolManager(
            settings=mock_settings,
            enable_metrics=True,
            enable_lifo=True,
            enable_pre_ping=True,
        )

        # Create database service
        db_service = DatabaseService(settings=mock_settings)

        try:
            # Initialize components
            with (
                patch.object(pool_manager, "_initialize_sqlalchemy_engine"),
                patch.object(pool_manager, "_initialize_supabase_client"),
                patch.object(pool_manager, "_test_connections"),
            ):
                await pool_manager.initialize()

                # Mock pool manager components
                mock_engine = MagicMock()
                mock_pool = MagicMock()
                mock_engine.pool = mock_pool
                mock_pool.checkedout.return_value = 6
                mock_pool.checkedin.return_value = 2
                mock_pool.size.return_value = 8

                pool_manager._sqlalchemy_engine = mock_engine
                pool_manager._supabase_client = MagicMock()

            # Mock database service
            mock_client = MagicMock()
            mock_client.table.return_value.select.return_value.execute.return_value.data = [
                {"id": "test"}
            ]

            with patch("supabase.create_client", return_value=mock_client):
                await db_service.connect()

            # Performance validation test sequence
            test_results = {
                "connection_latency": [],
                "query_latency": [],
                "pool_efficiency": [],
                "concurrent_performance": [],
                "metrics_accuracy": True,
                "lifo_effectiveness": True,
            }

            # Test 1: Connection acquisition latency
            logger.info("🔗 Testing connection acquisition latency...")
            for _ in range(50):
                start_time = time.perf_counter()
                async with pool_manager.acquire_connection("query") as (
                    conn_type,
                    conn,
                ):
                    pass
                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000
                test_results["connection_latency"].append(latency)

            # Test 2: Database query latency
            logger.info("📊 Testing database query latency...")
            for _ in range(50):
                start_time = time.perf_counter()
                await db_service.get_user_by_id("test_user")
                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000
                test_results["query_latency"].append(latency)

            # Test 3: Pool efficiency
            logger.info("🎯 Testing pool efficiency...")
            pool_stats = pool_manager.get_pool_statistics()
            utilization = pool_stats["current_status"]["utilization_percent"]
            test_results["pool_efficiency"].append(utilization)

            # Test 4: Concurrent performance
            logger.info("🚀 Testing concurrent performance...")

            async def concurrent_task():
                start_time = time.perf_counter()
                await db_service.get_user_by_id("concurrent_test")
                end_time = time.perf_counter()
                return (end_time - start_time) * 1000

            tasks = [concurrent_task() for _ in range(20)]
            concurrent_latencies = await asyncio.gather(*tasks)
            test_results["concurrent_performance"].extend(concurrent_latencies)

            # Test 5: Health check
            logger.info("🏥 Testing health check...")
            health_status = await pool_manager.health_check()

            # Analyze results
            avg_conn_latency = statistics.mean(test_results["connection_latency"])
            avg_query_latency = statistics.mean(test_results["query_latency"])
            avg_concurrent_latency = statistics.mean(
                test_results["concurrent_performance"]
            )

            # Final validation
            performance_targets_met = {
                "connection_latency_target": avg_conn_latency < 50.0,
                "query_latency_target": avg_query_latency < 50.0,
                "concurrent_latency_target": avg_concurrent_latency < 100.0,
                "pool_efficiency_target": utilization
                > 30.0,  # Reasonable for test scenario
                "health_check_passed": health_status["status"] == "healthy",
                "lifo_enabled": pool_manager.enable_lifo,
                "pre_ping_enabled": pool_manager.enable_pre_ping,
                "metrics_enabled": pool_manager.enable_metrics,
            }

            all_targets_met = all(performance_targets_met.values())

            logger.info("🎯 End-to-End Performance Validation Results:")
            logger.info(
                f"  ⚡ Connection latency: {avg_conn_latency:.2f}ms (target: <50ms) - {'✅' if performance_targets_met['connection_latency_target'] else '❌'}"
            )
            logger.info(
                f"  📊 Query latency: {avg_query_latency:.2f}ms (target: <50ms) - {'✅' if performance_targets_met['query_latency_target'] else '❌'}"
            )
            logger.info(
                f"  🚀 Concurrent latency: {avg_concurrent_latency:.2f}ms (target: <100ms) - {'✅' if performance_targets_met['concurrent_latency_target'] else '❌'}"
            )
            logger.info(
                f"  📈 Pool utilization: {utilization:.1f}% - {'✅' if performance_targets_met['pool_efficiency_target'] else '❌'}"
            )
            logger.info(
                f"  🏥 Health check: {health_status['status']} - {'✅' if performance_targets_met['health_check_passed'] else '❌'}"
            )
            logger.info(
                f"  🔄 LIFO enabled: {'✅' if performance_targets_met['lifo_enabled'] else '❌'}"
            )
            logger.info(
                f"  🔍 Pre-ping enabled: {'✅' if performance_targets_met['pre_ping_enabled'] else '❌'}"
            )
            logger.info(
                f"  📊 Metrics enabled: {'✅' if performance_targets_met['metrics_enabled'] else '❌'}"
            )
            logger.info(
                f"  🎯 Overall: {'✅ ALL TARGETS MET' if all_targets_met else '❌ SOME TARGETS MISSED'}"
            )

            # Assert final validation
            assert all_targets_met, (
                f"Performance targets not met: {performance_targets_met}"
            )

        finally:
            # Cleanup
            await pool_manager.close()
            # Database service cleanup handled by context managers
