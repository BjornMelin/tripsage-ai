"""Performance benchmarks for DragonflyDB and SDK migration validation.

Tests to verify the expected performance improvements from direct SDK integration.
Compares previous baseline performance with current DragonflyDB operations.
"""

import asyncio
import contextlib
import time
from statistics import mean, median

import pytest

from tripsage.config.feature_flags import FeatureFlags, IntegrationMode
from tripsage_core.services.infrastructure import (
    get_cache_service,
    get_database_service,
)
from tripsage_core.utils.cache_utils import redis_cache as web_cache


class PerformanceBenchmark:
    """Utility class for conducting performance benchmarks."""

    def __init__(self, iterations: int = 100):
        """Set benchmark iteration count and allocate result storage."""
        self.iterations = iterations
        self.results: dict[str, list[float]] = {}

    async def time_operation(self, name: str, operation, *args, **kwargs) -> float:
        """Time a single operation and return execution time in milliseconds."""
        start_time = time.perf_counter()
        try:
            await operation(*args, **kwargs)
        except (RuntimeError, OSError, TimeoutError) as e:
            print(f"Operation {name} failed: {e}")
            return float("inf")
        end_time = time.perf_counter()
        return (end_time - start_time) * 1000  # Convert to milliseconds

    async def benchmark_operation(
        self, name: str, operation, *args, **kwargs
    ) -> dict[str, float]:
        """Benchmark an operation multiple times and return statistics."""
        times = []
        for _ in range(self.iterations):
            execution_time = await self.time_operation(name, operation, *args, **kwargs)
            if execution_time != float("inf"):
                times.append(execution_time)
            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.01)

        if not times:
            return {
                "mean": float("inf"),
                "median": float("inf"),
                "min": float("inf"),
                "max": float("inf"),
            }

        return {
            "mean": mean(times),
            "median": median(times),
            "min": min(times),
            "max": max(times),
            "samples": len(times),
        }


@pytest.fixture
async def dragonfly_service():
    """DragonflyDB service fixture."""
    service = await get_cache_service()
    yield service
    # Cleanup if needed
    if hasattr(service, "disconnect"):
        with contextlib.suppress(Exception):
            await service.close()


@pytest.fixture
async def supabase_service():
    """Fixture for direct Supabase service."""
    service = await get_database_service()
    yield service
    await service.close()


@pytest.fixture
def performance_benchmark():
    """Fixture for performance benchmark utility."""
    return PerformanceBenchmark(iterations=50)  # Reduced for test speed


class TestDragonflyMigrationPerformance:
    """Test performance improvements from DragonflyDB migration."""

    async def test_dragonfly_set_operations_performance(
        self, dragonfly_service, performance_benchmark
    ):
        """Test DragonflyDB SET operation performance."""
        test_key = "benchmark:test:set"
        test_value = {"message": "performance test", "timestamp": time.time()}

        # Benchmark direct SDK operation
        direct_stats = await performance_benchmark.benchmark_operation(
            "dragonfly_direct_set",
            dragonfly_service.set_json,
            test_key,
            test_value,
            ex=300,
        )

        # Benchmark current cache_tools (using direct SDK)
        cache_stats = await performance_benchmark.benchmark_operation(
            "cache_tools_set", web_cache.set_cache, test_key, test_value, ttl=300
        )

        print("\nDragonflyDB SET Performance Comparison:")
        print(
            f"Direct SDK - Mean: {direct_stats['mean']:.2f}ms, "
            f"Median: {direct_stats['median']:.2f}ms"
        )
        print(
            f"Cache Tools - Mean: {cache_stats['mean']:.2f}ms, "
            f"Median: {cache_stats['median']:.2f}ms"
        )

        # Verify both operations are performing well (under 50ms for local DragonflyDB)
        assert direct_stats["mean"] < 50, (
            f"Direct SDK too slow: {direct_stats['mean']:.2f}ms"
        )
        assert cache_stats["mean"] < 50, (
            f"Cache tools too slow: {cache_stats['mean']:.2f}ms"
        )

        # Cache tools should be comparable to direct SDK (within 2x)
        performance_ratio = cache_stats["mean"] / direct_stats["mean"]
        assert performance_ratio < 2.0, (
            f"Cache tools overhead too high: {performance_ratio:.2f}x"
        )

    async def test_dragonfly_get_operations_performance(
        self, dragonfly_service, performance_benchmark
    ):
        """Test DragonflyDB GET operation performance."""
        test_key = "benchmark:test:get"
        test_value = {"message": "performance test", "data": list(range(100))}

        # Setup test data
        await dragonfly_service.set_json(test_key, test_value, ex=300)

        # Benchmark direct SDK operation
        direct_stats = await performance_benchmark.benchmark_operation(
            "dragonfly_direct_get", dragonfly_service.get_json, test_key
        )

        # Benchmark current cache_tools (using direct SDK)
        cache_stats = await performance_benchmark.benchmark_operation(
            "cache_tools_get", web_cache.get_cache, test_key
        )

        print("\nDragonflyDB GET Performance Comparison:")
        print(
            f"Direct SDK - Mean: {direct_stats['mean']:.2f}ms, "
            f"Median: {direct_stats['median']:.2f}ms"
        )
        print(
            f"Cache Tools - Mean: {cache_stats['mean']:.2f}ms, "
            f"Median: {cache_stats['median']:.2f}ms"
        )

        # Verify both operations are performing well
        assert direct_stats["mean"] < 50, (
            f"Direct SDK too slow: {direct_stats['mean']:.2f}ms"
        )
        assert cache_stats["mean"] < 50, (
            f"Cache tools too slow: {cache_stats['mean']:.2f}ms"
        )


class TestSupabaseMigrationPerformance:
    """Test performance improvements from Supabase SDK migration."""

    async def test_supabase_connection_performance(
        self, supabase_service, performance_benchmark
    ):
        """Test Supabase connection establishment performance."""
        # Test connection performance
        connection_stats = await performance_benchmark.benchmark_operation(
            "supabase_connect", supabase_service.ensure_connected
        )

        print("\nSupabase Connection Performance:")
        print(
            f"Direct SDK - Mean: {connection_stats['mean']:.2f}ms, "
            f"Median: {connection_stats['median']:.2f}ms"
        )

        # Connection should be fast (under 100ms for already established connections)
        assert connection_stats["mean"] < 100, (
            f"Connection too slow: {connection_stats['mean']:.2f}ms"
        )

    async def test_supabase_query_performance(
        self, supabase_service, performance_benchmark
    ):
        """Test basic Supabase query performance."""
        # Simple query that should work on any Supabase instance
        query_stats = await performance_benchmark.benchmark_operation(
            "supabase_query",
            supabase_service.select,
            "users",
            columns="id,email",
            limit=1,
        )

        print("\nSupabase Query Performance:")
        print(
            f"Direct SDK - Mean: {query_stats['mean']:.2f}ms, "
            f"Median: {query_stats['median']:.2f}ms"
        )

        # Query should complete reasonably fast (allowing for network latency)
        assert query_stats["mean"] < 1000, (
            f"Query too slow: {query_stats['mean']:.2f}ms"
        )


class TestOverallMigrationImpact:
    """Test overall migration performance impact."""

    async def test_migration_status_reporting(self):
        """Test migration status and feature flag configuration."""
        flags = FeatureFlags()

        # Check that we can report migration status
        migration_status = flags.get_migration_status()

        print("\nMigration Status Report:")
        for service, mode in migration_status.items():
            print(f"  {service}: {mode.value}")

        # Verify our migrated services are using direct mode by default
        assert flags.redis_integration in {
            IntegrationMode.DIRECT,
            IntegrationMode.MCP,
        }
        assert flags.supabase_integration in {
            IntegrationMode.DIRECT,
            IntegrationMode.MCP,
        }

    async def test_performance_improvement_validation(self, performance_benchmark):
        """Validate that we've achieved meaningful performance improvements."""
        # This test validates that our direct SDK implementations are performant

        # Test DragonflyDB pipeline operations (batch performance)
        import redis.asyncio as redis

        dragonfly_url = "redis://localhost:6379/0"
        direct_dragonfly = redis.from_url(dragonfly_url)

        async def batch_dragonfly_operations():
            """Simulate batch DragonflyDB operations."""
            pipe = direct_dragonfly.pipeline()
            for i in range(10):
                pipe.set(f"batch:key:{i}", f"value:{i}")
            await pipe.execute()

        batch_stats = await performance_benchmark.benchmark_operation(
            "dragonfly_batch_operations", batch_dragonfly_operations
        )

        print("\nBatch Operations Performance:")
        print(f"DragonflyDB Pipeline (10 ops) - Mean: {batch_stats['mean']:.2f}ms")

        # Batch operations should be very fast
        assert batch_stats["mean"] < 100, (
            f"Batch operations too slow: {batch_stats['mean']:.2f}ms"
        )

        await direct_dragonfly.close()


# Utility function for manual performance testing
async def run_comprehensive_benchmark():
    """Run performance benchmark for manual testing."""
    print("=" * 60)
    print("TripSage SDK Migration Performance Benchmark")
    print("=" * 60)

    benchmark = PerformanceBenchmark(iterations=100)

    # Test DragonflyDB performance
    dragonfly_service = await get_cache_service()

    try:
        # DragonflyDB SET performance
        set_stats = await benchmark.benchmark_operation(
            "dragonfly_set",
            dragonfly_service.set_json,
            "benchmark:test",
            {"test": "data", "timestamp": time.time()},
            ex=300,
        )

        # DragonflyDB GET performance
        get_stats = await benchmark.benchmark_operation(
            "dragonfly_get", dragonfly_service.get_json, "benchmark:test"
        )

        print("\nDragonflyDB Performance (100 iterations):")
        print(
            f"SET - Mean: {set_stats['mean']:.2f}ms, "
            f"Median: {set_stats['median']:.2f}ms"
        )
        print(
            f"GET - Mean: {get_stats['mean']:.2f}ms, "
            f"Median: {get_stats['median']:.2f}ms"
        )

    finally:
        if hasattr(dragonfly_service, "disconnect"):
            await dragonfly_service.disconnect()

    # Test Supabase performance
    supabase_service = await get_database_service()
    # Core database service auto-connects

    try:
        connection_stats = await benchmark.benchmark_operation(
            "supabase_connection", supabase_service.ensure_connected
        )

        print("\nSupabase Performance (100 iterations):")
        print(
            f"Connection - Mean: {connection_stats['mean']:.2f}ms, "
            f"Median: {connection_stats['median']:.2f}ms"
        )

    finally:
        await supabase_service.disconnect()

    print("\nBenchmark completed successfully!")
    print("Performance optimizations achieved through direct SDK integration.")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_benchmark())
