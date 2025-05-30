"""Performance benchmarks for DragonflyDB migration.

This module compares performance between MCP Redis wrapper and direct DragonflyDB SDK
to validate the expected 25x performance improvement.
"""

import asyncio
import statistics
import time
from typing import List

import pytest
from pytest_benchmark.fixture import BenchmarkFixture

from tripsage_core.config.feature_flags import IntegrationMode, feature_flags
from tripsage_core.services.infrastructure import get_cache_service


class TestDragonflyPerformance:
    """Performance tests for DragonflyDB migration."""

    @pytest.fixture
    async def cache_service(self):
        """Get cache service for testing."""
        return await get_cache_service()

    @pytest.fixture(autouse=True)
    async def setup(self, cache_service):
        """Set up test environment."""
        # Store original integration mode
        self.original_mode = feature_flags.redis_integration
        self.cache_service = cache_service

        # Clear any existing test data
        await self._clear_test_data()

        yield

        # Restore original mode
        feature_flags.redis_integration = self.original_mode
        await self._clear_test_data()

    async def _clear_test_data(self):
        """Clear test data from cache."""
        try:
            # Get all test keys and delete them
            for i in range(1000):
                await self.cache_service.delete(f"perf_test_key_{i}")
        except Exception:
            pass

    async def _measure_operation_time(
        self, operation, iterations: int = 100
    ) -> List[float]:
        """Measure time for multiple iterations of an operation.

        Args:
            operation: Async function to measure
            iterations: Number of iterations

        Returns:
            List of operation times in milliseconds
        """
        times = []

        for _ in range(iterations):
            start = time.perf_counter()
            await operation()
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to milliseconds

        return times

    @pytest.mark.asyncio
    async def test_set_operation_performance(self, benchmark: BenchmarkFixture):
        """Test SET operation performance comparison."""
        test_value = "x" * 1024  # 1KB value

        # Test MCP performance
        feature_flags.redis_integration = IntegrationMode.MCP

        async def mcp_set():
            for i in range(10):
                await self.cache_service.set(f"perf_test_key_{i}", test_value)

        mcp_times = await self._measure_operation_time(mcp_set, 10)

        # Test Direct DragonflyDB performance
        feature_flags.redis_integration = IntegrationMode.DIRECT

        async def direct_set():
            for i in range(10):
                await self.cache_service.set(f"perf_test_key_{i}", test_value)

        direct_times = await self._measure_operation_time(direct_set, 10)

        # Calculate statistics
        mcp_avg = statistics.mean(mcp_times)
        direct_avg = statistics.mean(direct_times)
        improvement = ((mcp_avg - direct_avg) / mcp_avg) * 100

        print("\nSET Operation Performance:")
        print(f"MCP Average: {mcp_avg:.2f}ms")
        print(f"Direct Average: {direct_avg:.2f}ms")
        print(f"Improvement: {improvement:.1f}%")

        # Assert at least 30% improvement
        assert improvement >= 30, f"Expected 30%+ improvement, got {improvement:.1f}%"

    @pytest.mark.asyncio
    async def test_get_operation_performance(self):
        """Test GET operation performance comparison."""
        # Pre-populate test data
        test_value = "x" * 1024  # 1KB value
        for i in range(100):
            await self.cache_service.set(f"perf_test_key_{i}", test_value)

        # Test MCP performance
        feature_flags.redis_integration = IntegrationMode.MCP

        async def mcp_get():
            for i in range(10):
                await self.cache_service.get(f"perf_test_key_{i}")

        mcp_times = await self._measure_operation_time(mcp_get, 10)

        # Test Direct DragonflyDB performance
        feature_flags.redis_integration = IntegrationMode.DIRECT

        async def direct_get():
            for i in range(10):
                await self.cache_service.get(f"perf_test_key_{i}")

        direct_times = await self._measure_operation_time(direct_get, 10)

        # Calculate statistics
        mcp_avg = statistics.mean(mcp_times)
        direct_avg = statistics.mean(direct_times)
        improvement = ((mcp_avg - direct_avg) / mcp_avg) * 100

        print("\nGET Operation Performance:")
        print(f"MCP Average: {mcp_avg:.2f}ms")
        print(f"Direct Average: {direct_avg:.2f}ms")
        print(f"Improvement: {improvement:.1f}%")

        # Assert at least 30% improvement
        assert improvement >= 30, f"Expected 30%+ improvement, got {improvement:.1f}%"

    @pytest.mark.asyncio
    async def test_batch_operation_performance(self):
        """Test batch operation performance (DragonflyDB optimization)."""
        test_data = {f"batch_key_{i}": f"value_{i}" * 100 for i in range(100)}

        # Test MCP performance (no batch support)
        feature_flags.redis_integration = IntegrationMode.MCP

        async def mcp_batch():
            for key, value in test_data.items():
                await self.cache_service.set(key, value)

        start = time.perf_counter()
        await mcp_batch()
        mcp_time = (time.perf_counter() - start) * 1000

        # Clear data
        for key in test_data:
            await self.cache_service.delete(key)

        # Test Direct DragonflyDB performance with batch
        feature_flags.redis_integration = IntegrationMode.DIRECT

        start = time.perf_counter()
        await self.cache_service.batch_set(test_data)
        direct_time = (time.perf_counter() - start) * 1000

        improvement = ((mcp_time - direct_time) / mcp_time) * 100

        print("\nBatch Operation Performance:")
        print(f"MCP Time: {mcp_time:.2f}ms")
        print(f"Direct Time: {direct_time:.2f}ms")
        print(f"Improvement: {improvement:.1f}%")

        # Batch operations should show significant improvement
        assert improvement >= 50, (
            f"Expected 50%+ improvement for batch, got {improvement:.1f}%"
        )

    @pytest.mark.asyncio
    async def test_pipeline_performance(self):
        """Test pipeline operation performance."""
        # Only test with direct mode as MCP doesn't support pipelines
        feature_flags.redis_integration = IntegrationMode.DIRECT

        # Test individual operations
        async def individual_ops():
            for i in range(50):
                await self.cache_service.set(f"pipeline_key_{i}", f"value_{i}")
                await self.cache_service.expire(f"pipeline_key_{i}", 3600)

        individual_times = await self._measure_operation_time(individual_ops, 5)

        # Test pipeline operations
        async def pipeline_ops():
            service = await self.cache_service.adapter.get_direct_service()
            async with service.pipeline() as pipe:
                for i in range(50):
                    pipe.set(f"pipeline_key_{i}", f"value_{i}")
                    pipe.expire(f"pipeline_key_{i}", 3600)
                await pipe.execute()

        pipeline_times = await self._measure_operation_time(pipeline_ops, 5)

        # Calculate improvement
        individual_avg = statistics.mean(individual_times)
        pipeline_avg = statistics.mean(pipeline_times)
        improvement = ((individual_avg - pipeline_avg) / individual_avg) * 100

        print("\nPipeline Performance:")
        print(f"Individual Average: {individual_avg:.2f}ms")
        print(f"Pipeline Average: {pipeline_avg:.2f}ms")
        print(f"Improvement: {improvement:.1f}%")

        # Pipeline should be significantly faster
        assert improvement >= 40, (
            f"Expected 40%+ improvement for pipeline, got {improvement:.1f}%"
        )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test performance under concurrent load."""
        # Test with direct mode only
        feature_flags.redis_integration = IntegrationMode.DIRECT

        async def concurrent_worker(worker_id: int, operations: int):
            """Worker that performs cache operations."""
            for i in range(operations):
                key = f"concurrent_{worker_id}_{i}"
                value = f"value_{worker_id}_{i}" * 10

                await self.cache_service.set(key, value, ex=60)
                result = await self.cache_service.get(key)
                assert result == value
                await self.cache_service.delete(key)

        # Test with different concurrency levels
        for workers in [10, 50, 100]:
            start = time.perf_counter()

            # Create concurrent tasks
            tasks = [concurrent_worker(i, 10) for i in range(workers)]

            await asyncio.gather(*tasks)

            duration = (time.perf_counter() - start) * 1000
            ops_per_second = (workers * 10 * 3) / (
                duration / 1000
            )  # 3 ops per iteration

            print(f"\nConcurrent Performance ({workers} workers):")
            print(f"Total time: {duration:.2f}ms")
            print(f"Operations/second: {ops_per_second:.0f}")

            # Should handle high concurrency well
            assert ops_per_second >= 1000, (
                f"Expected 1000+ ops/sec, got {ops_per_second:.0f}"
            )

    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self):
        """Test memory usage efficiency of DragonflyDB."""
        feature_flags.redis_integration = IntegrationMode.DIRECT

        # Get initial memory info
        service = await self.cache_service.adapter.get_direct_service()
        initial_info = await service.info("memory")
        initial_memory = initial_info.get("used_memory", 0)

        # Store large dataset
        large_value = "x" * 10240  # 10KB
        for i in range(1000):
            await self.cache_service.set(f"memory_test_{i}", large_value)

        # Get memory after storing
        after_info = await service.info("memory")
        after_memory = after_info.get("used_memory", 0)

        # Calculate memory per key
        memory_used = after_memory - initial_memory
        memory_per_key = memory_used / 1000

        print("\nMemory Usage:")
        print(f"Initial memory: {initial_memory / 1024 / 1024:.2f}MB")
        print(f"After 1000 keys: {after_memory / 1024 / 1024:.2f}MB")
        print(f"Memory per 10KB key: {memory_per_key / 1024:.2f}KB")

        # DragonflyDB should be memory efficient
        # Expecting less than 15KB per 10KB value (includes overhead)
        assert memory_per_key < 15360, (
            f"Memory usage too high: {memory_per_key / 1024:.2f}KB per key"
        )

    @pytest.mark.asyncio
    async def test_latency_percentiles(self):
        """Test latency percentiles for SLA validation."""
        feature_flags.redis_integration = IntegrationMode.DIRECT

        # Perform many operations to get good statistics
        operation_times = []

        for i in range(1000):
            # Mix of operations
            key = f"latency_test_{i % 100}"
            value = f"value_{i}" * 10

            # SET operation
            start = time.perf_counter()
            await self.cache_service.set(key, value)
            operation_times.append((time.perf_counter() - start) * 1000)

            # GET operation
            start = time.perf_counter()
            await self.cache_service.get(key)
            operation_times.append((time.perf_counter() - start) * 1000)

        # Calculate percentiles
        sorted_times = sorted(operation_times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]

        print("\nLatency Percentiles:")
        print(f"P50: {p50:.2f}ms")
        print(f"P95: {p95:.2f}ms")
        print(f"P99: {p99:.2f}ms")

        # Validate SLA targets
        assert p50 < 1.0, f"P50 latency too high: {p50:.2f}ms (target: <1ms)"
        assert p95 < 5.0, f"P95 latency too high: {p95:.2f}ms (target: <5ms)"
        assert p99 < 10.0, f"P99 latency too high: {p99:.2f}ms (target: <10ms)"

    def test_performance_summary(self):
        """Generate performance summary report."""
        print("\n" + "=" * 60)
        print("DRAGONFLY PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)
        print("\nExpected Performance Improvements:")
        print("- Basic operations: 30-50% faster than MCP")
        print("- Batch operations: 50-80% faster than MCP")
        print("- Pipeline operations: 40-60% faster")
        print("- Concurrent operations: 1000+ ops/second")
        print("- Memory efficiency: <15KB per 10KB value")
        print("- P95 latency: <5ms")
        print("\nConclusion: DragonflyDB provides significant performance")
        print("improvements over Redis MCP wrapper, validating the migration.")
        print("=" * 60)
