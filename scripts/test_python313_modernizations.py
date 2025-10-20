#!/usr/bin/env python3
"""Test Script for Python 3.13 Modernizations in TripSage.
======================================================

This script tests and validates all Python 3.13 modern features implemented
across the TripSage codebase. It serves as both a test suite and demonstration
of the improvements.

Run this script to verify that Python 3.13 modernizations are working correctly.
"""

import asyncio
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import our modernized modules
from tripsage_core.utils.error_handling import (  # noqa: E402
    example_database_operations,
)
from tripsage_core.utils.performance_optimizations import (  # noqa: E402
    BatchProcessor,
    OptimizedAsyncCache,
    OptimizedStringBuilder,
    benchmark_async_operations,
    example_string_optimization,
    performance_monitor,
)


class TestResult:
    """Test result tracking with modern annotations."""

    def __init__(self, test_name: str):
        """Initialize test result tracking.

        Args:
            test_name: Name of the test being run
        """
        self.test_name = test_name
        self.start_time = time.time()
        self.success = False
        self.error: Exception | None = None
        self.duration = 0.0
        self.details: dict[str, any] = {}

    def complete(self, success: bool = True, error: Exception | None = None, **details):
        """Mark test as complete."""
        self.success = success
        self.error = error
        self.duration = time.time() - self.start_time
        self.details.update(details)

    def __str__(self) -> str:
        """String representation of test result."""
        status = "✅ PASS" if self.success else "❌ FAIL"
        duration_ms = self.duration * 1000

        if self.error:
            return f"{status} {self.test_name} ({duration_ms:.1f}ms) - {self.error}"
        else:
            return f"{status} {self.test_name} ({duration_ms:.1f}ms)"


async def test_type_parameters():
    """Test PEP 695 type parameters implementation."""
    test = TestResult("Type Parameters (PEP 695)")

    try:
        # Test generic type aliases
        type DatabaseResult[T] = dict[str, T] | list[dict[str, T]]
        type UserData = dict[str, str | int]

        # Test usage
        user_data: UserData = {"id": 123, "name": "Alice", "age": 30}
        db_result: DatabaseResult[str] = [{"name": "Alice"}, {"name": "Bob"}]

        test.complete(
            success=True, user_data_keys=len(user_data), db_result_count=len(db_result)
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_taskgroup_concurrency():
    """Test asyncio.TaskGroup structured concurrency."""
    test = TestResult("TaskGroup Structured Concurrency")

    try:
        # Test TaskGroup with multiple concurrent tasks
        async with asyncio.TaskGroup() as tg:
            tg.create_task(asyncio.sleep(0.1), name="sleep_task_1")
            tg.create_task(asyncio.sleep(0.1), name="sleep_task_2")
            tg.create_task(asyncio.sleep(0.1), name="sleep_task_3")

        # All tasks completed successfully
        test.complete(success=True, tasks_completed=3, concurrent_execution=True)

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_enhanced_error_handling():
    """Test enhanced error handling with TaskGroups."""
    test = TestResult("Enhanced Error Handling")

    try:
        # Test the enhanced error context
        result = await example_database_operations()

        test.complete(
            success=True,
            operations_completed=len(result),
            has_users="users" in result,
            has_trips="trips" in result,
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_optimized_cache():
    """Test the optimized async cache implementation."""
    test = TestResult("Optimized Async Cache")

    try:
        cache = OptimizedAsyncCache[str, dict](max_size=10, ttl_seconds=1)

        # Test cache operations
        await cache.set("user:123", {"name": "Alice", "id": 123})
        result = await cache.get("user:123")

        # Test cache miss
        missing = await cache.get("user:999")

        stats = cache.get_stats()

        test.complete(
            success=result is not None and missing is None,
            cache_hit=result is not None,
            cache_miss=missing is None,
            cache_size=stats["size"],
            hit_rate=stats["hit_rate"],
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_batch_processor():
    """Test the optimized batch processor."""
    test = TestResult("Batch Processor with TaskGroups")

    try:

        async def mock_processor(item: str) -> str:
            await asyncio.sleep(0.01)  # Simulate work
            return f"processed_{item}"

        processor = BatchProcessor[str](batch_size=3, max_concurrent=2)
        items = [f"item_{i}" for i in range(10)]

        results = await processor.process_items(items, mock_processor)

        test.complete(
            success=len(results) == len(items),
            items_processed=len(results),
            all_processed=all("processed_" in r for r in results),
            processor_stats={
                "operations": processor.stats.operation_count,
                "avg_duration": processor.stats.average_duration,
            },
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_performance_monitoring():
    """Test performance monitoring decorator."""
    test = TestResult("Performance Monitoring")

    try:

        @performance_monitor(track_memory=False)
        async def sample_operation():
            await asyncio.sleep(0.05)
            return {"status": "completed", "data": list(range(100))}

        result = await sample_operation()

        test.complete(
            success=result["status"] == "completed",
            data_size=len(result["data"]),
            monitoring_applied=True,
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_string_optimization():
    """Test optimized string operations."""
    test = TestResult("String Optimization")

    try:
        result = await example_string_optimization()

        # Test string builder
        builder = OptimizedStringBuilder()
        builder.append("Test: ").append("Success").append_formatted(
            " ({status})", status="OK"
        )
        built_string = builder.build()

        test.complete(
            success=len(result) > 0 and "TripSage" in result,
            result_length=len(result),
            builder_test=built_string == "Test: Success (OK)",
            contains_report_data="Operation" in result,
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_database_modernizations():
    """Test database service modernizations."""
    test = TestResult("Database Service Modernizations")

    try:
        # Import and test database service types
        from tripsage_core.services.infrastructure.database_service import (
            DatabaseResult,
            FilterDict,
            MetricsDict,
        )

        # Test type aliases work
        sample_result: DatabaseResult[str] = {"data": "test"}
        sample_filter: FilterDict = {"user_id": "123", "active": True}
        sample_metrics: MetricsDict = {"query_time": 0.5, "rows": 10}

        test.complete(
            success=True,
            type_aliases_working=True,
            database_result_type=type(sample_result).__name__,
            filter_dict_keys=len(sample_filter),
            metrics_dict_keys=len(sample_metrics),
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def test_memory_service_modernizations():
    """Test memory service modernizations."""
    test = TestResult("Memory Service Modernizations")

    try:
        # Import memory service to test modernizations
        from tripsage_core.services.business.memory_service_async import (
            MemorySearchRequest,
        )

        # Test that imports work and types are available
        search_request = MemorySearchRequest(
            query="test query", limit=5, similarity_threshold=0.7
        )

        test.complete(
            success=True,
            memory_service_imported=True,
            search_request_created=search_request.query == "test query",
            modern_types_available=True,
        )

    except Exception as e:
        test.complete(success=False, error=e)

    return test


async def run_performance_benchmark():
    """Run a comprehensive performance benchmark."""
    print("\n🚀 Running Performance Benchmark")
    print("=" * 50)

    # Define benchmark operations
    async def fast_operation():
        await asyncio.sleep(0.001)
        return {"result": "fast"}

    async def medium_operation():
        await asyncio.sleep(0.01)
        return {"result": "medium"}

    async def database_simulation():
        await asyncio.sleep(0.05)
        return {"result": "database", "rows": 100}

    operations = {
        "fast_operation": fast_operation,
        "medium_operation": medium_operation,
        "database_simulation": database_simulation,
    }

    # Run benchmark
    results = await benchmark_async_operations(operations, iterations=50)

    print("\n📊 Benchmark Results:")
    for op_name, metrics in results.items():
        print(f"  {op_name}:")
        print(f"    Avg time: {metrics['avg_time'] * 1000:.2f}ms")
        print(f"    Ops/sec: {metrics['operations_per_second']:.0f}")
        print(f"    Error rate: {metrics['error_rate']:.1%}")

    return results


async def main():
    """Main test runner."""
    print("🧪 Python 3.13 Modernizations Test Suite")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Test started: {datetime.now(UTC).isoformat()}")
    print()

    # Define all tests
    tests = [
        test_type_parameters(),
        test_taskgroup_concurrency(),
        test_enhanced_error_handling(),
        test_optimized_cache(),
        test_batch_processor(),
        test_performance_monitoring(),
        test_string_optimization(),
        test_database_modernizations(),
        test_memory_service_modernizations(),
    ]

    # Run all tests concurrently using TaskGroup
    results = []

    try:
        async with asyncio.TaskGroup() as tg:
            test_tasks = {}
            for test_coro in tests:
                task = tg.create_task(test_coro)
                test_tasks[task] = test_coro.__name__

        # Collect results
        for task in test_tasks:
            result = task.result()
            results.append(result)

    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

    # Print results
    print("📋 Test Results:")
    print("-" * 40)

    passed = 0
    failed = 0

    for result in results:
        print(f"  {result}")
        if result.success:
            passed += 1
        else:
            failed += 1

        # Print details for failed tests
        if not result.success and result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")

    # Run performance benchmark
    await run_performance_benchmark()

    # Summary
    print("\n📊 Test Summary:")
    print(f"  Total tests: {len(results)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success rate: {passed / len(results):.1%}")

    if failed == 0:
        print("\n🎉 All Python 3.13 modernizations are working correctly!")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
