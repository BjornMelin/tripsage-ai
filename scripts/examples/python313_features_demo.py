#!/usr/bin/env python3
"""Python 3.13 Modern Features Demonstration for TripSage.
===================================================

This script demonstrates the Python 3.13 modern features implemented
across the TripSage codebase:

1. PEP 695: Type Parameter Syntax
2. TaskGroups for structured concurrency
3. Enhanced error handling with improved tracebacks
4. Modern async patterns
5. Performance optimizations

Run this script to see the benefits of Python 3.13 modernization.
"""

import asyncio
import logging
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, TypeVar


# Python 3.13 type parameters (PEP 695) - Modern syntax
type ProcessingResult[T] = dict[str, T] | list[T]
type TaskResult[T] = tuple[str, T, float]  # (task_name, result, duration)
type BatchResults[T] = Mapping[str, Sequence[T]]

# Traditional type variables for comparison
T = TypeVar("T")
ResultT = TypeVar("ResultT")

# Configure logging for demonstration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModernAsyncProcessor[T]:
    """Demonstration of Python 3.13 generic type syntax with PEP 695.

    This class shows how the new type parameter syntax provides better
    type safety and readability compared to traditional TypeVar usage.
    """

    def __init__(self, name: str):
        self.name = name
        self.processed_count = 0

    async def process_item(self, item: T) -> ProcessingResult[T]:
        """Process a single item with modern type annotations."""
        await asyncio.sleep(0.1)  # Simulate processing
        self.processed_count += 1

        return {
            "processed_item": item,
            "processor": self.name,
            "timestamp": datetime.now(UTC).isoformat(),
            "count": self.processed_count,
        }

    async def process_batch_taskgroup(
        self, items: Sequence[T]
    ) -> BatchResults[ProcessingResult[T]]:
        """Process items using Python 3.13 TaskGroup for structured concurrency.

        TaskGroup provides better error handling and automatic cleanup
        compared to asyncio.gather() or manual task management.
        """
        results: dict[str, ProcessingResult[T]] = {}

        # Python 3.13 TaskGroup - structured concurrency
        async with asyncio.TaskGroup() as tg:
            tasks = {}
            for i, item in enumerate(items):
                task = tg.create_task(self.process_item(item), name=f"process_item_{i}")
                tasks[task] = f"item_{i}"

        # Collect results after all tasks complete successfully
        for task, item_key in tasks.items():
            results[item_key] = task.result()

        return results

    async def process_batch_traditional(
        self, items: Sequence[T]
    ) -> BatchResults[ProcessingResult[T]]:
        """Process items using traditional asyncio.gather() for comparison.

        This method demonstrates the old approach for comparison purposes.
        """
        tasks = [self.process_item(item) for item in items]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, ProcessingResult[T]] = {}
        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                logger.exception("Task %s failed: %s", i, result)
                continue
            results[f"item_{i}"] = result

        return results


async def demonstrate_taskgroup_benefits():
    """Demonstrate the benefits of TaskGroup over traditional approaches."""
    logger.info("🚀 Demonstrating Python 3.13 TaskGroup benefits")

    # Test data
    test_items = ["trip_1", "trip_2", "trip_3", "trip_4", "trip_5"]
    processor = ModernAsyncProcessor[str]("TripSage-Processor")

    # Test TaskGroup approach
    start_time = time.time()
    taskgroup_results = await processor.process_batch_taskgroup(test_items)
    taskgroup_duration = time.time() - start_time

    logger.info(
        "✅ TaskGroup processed %s items in %.3fs",
        len(taskgroup_results),
        taskgroup_duration,
    )

    # Reset processor state
    processor.processed_count = 0

    # Test traditional approach
    start_time = time.time()
    traditional_results = await processor.process_batch_traditional(test_items)
    traditional_duration = time.time() - start_time

    logger.info(
        "⚡ Traditional processed %s items in %.3fs",
        len(traditional_results),
        traditional_duration,
    )

    # Compare results
    performance_diff = abs(taskgroup_duration - traditional_duration)
    logger.info("📊 Performance difference: %.3fs", performance_diff)

    return taskgroup_results, traditional_results


async def demonstrate_enhanced_error_handling():
    """Demonstrate enhanced error handling with TaskGroups."""
    logger.info("🛡️ Demonstrating enhanced error handling")

    async def failing_task(task_id: str) -> str:
        """A task that may fail to demonstrate error handling."""
        await asyncio.sleep(0.1)
        if task_id == "fail_me":
            raise ValueError(f"Intentional failure in {task_id}")
        return f"Success: {task_id}"

    # TaskGroup with error handling
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = []
            for task_id in ["task_1", "task_2", "fail_me", "task_3"]:
                task = tg.create_task(failing_task(task_id), name=task_id)
                tasks.append((task_id, task))

        # This won't be reached due to the failure
        logger.info("All tasks completed successfully")

    except* ValueError as eg:
        # Python 3.11+ exception groups - works great with TaskGroup
        logger.exception("TaskGroup caught %s exceptions:", len(eg.exceptions))
        for exc in eg.exceptions:
            logger.exception(" - %s", type(exc).__name__)

    # Demonstrate that partial results can still be processed
    results = {}
    try:
        async with asyncio.TaskGroup() as tg:
            # Process non-failing tasks separately
            safe_tasks = ["task_1", "task_2", "task_3", "task_4"]
            task_map = {}
            for task_id in safe_tasks:
                task = tg.create_task(failing_task(task_id), name=task_id)
                task_map[task] = task_id

        # Collect successful results
        for task, task_id in task_map.items():
            results[task_id] = task.result()

        logger.info("✅ Successfully processed %s safe tasks", len(results))

    except Exception:
        logger.exception("Unexpected error")

    return results


async def demonstrate_concurrent_database_operations():
    """Simulate concurrent database operations using modern patterns."""
    logger.info("🗄️ Demonstrating concurrent database operations")

    async def simulate_db_query(query_type: str, delay: float = 0.1) -> dict[str, Any]:
        """Simulate a database query with varying delays."""
        await asyncio.sleep(delay)
        return {
            "query_type": query_type,
            "execution_time_ms": delay * 1000,
            "rows_affected": 42,
            "success": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Concurrent database operations using TaskGroup
    start_time = time.time()

    async with asyncio.TaskGroup() as tg:
        # Simulate multiple database operations
        user_task = tg.create_task(
            simulate_db_query("SELECT_USERS", 0.15), name="fetch_users"
        )
        trips_task = tg.create_task(
            simulate_db_query("SELECT_TRIPS", 0.12), name="fetch_trips"
        )
        memories_task = tg.create_task(
            simulate_db_query("VECTOR_SEARCH", 0.08), name="search_memories"
        )
        health_task = tg.create_task(
            simulate_db_query("HEALTH_CHECK", 0.05), name="health_check"
        )

    total_duration = time.time() - start_time

    # Collect results
    operations = {
        "users": user_task.result(),
        "trips": trips_task.result(),
        "memories": memories_task.result(),
        "health": health_task.result(),
    }

    logger.info(
        "🎯 Completed %s concurrent DB operations in %.3fs",
        len(operations),
        total_duration,
    )

    # Calculate sequential time for comparison
    sequential_time = sum(op["execution_time_ms"] for op in operations.values()) / 1000
    speedup = sequential_time / total_duration

    logger.info("📈 Speedup: %.2fx (Sequential: %.3fs)", speedup, sequential_time)

    return operations


def demonstrate_type_safety():
    """Demonstrate improved type safety with Python 3.13 features."""
    logger.info("🔒 Demonstrating enhanced type safety")

    # Modern type aliases with type statement
    type UserData = dict[str, str | int | float]
    type SearchFilters = dict[str, str | list[str]]

    def process_user_data(data: UserData) -> str:
        """Process user data with strict typing."""
        return f"User: {data.get('name', 'Unknown')} (ID: {data.get('id', 'N/A')})"

    def create_search_filters(
        destinations: Sequence[str], budget_range: tuple[int, int]
    ) -> SearchFilters:
        """Create search filters with modern type annotations."""
        return {
            "destinations": list(destinations),
            "min_budget": str(budget_range[0]),
            "max_budget": str(budget_range[1]),
            "active": "true",
        }

    # Example usage
    user: UserData = {"id": 12345, "name": "Alice", "age": 30}
    filters: SearchFilters = create_search_filters(
        ["Paris", "Tokyo", "New York"], (1000, 5000)
    )

    logger.info("👤 %s", process_user_data(user))
    logger.info("🔍 Search filters: %s", filters)

    return user, filters


async def main():
    """Main demonstration function showcasing Python 3.13 modernizations."""
    logger.info("=" * 60)
    logger.info("🎉 Python 3.13 Modern Features Demo for TripSage")
    logger.info("=" * 60)

    print(f"Python version: {sys.version}")
    print(f"Demo started at: {datetime.now(UTC).isoformat()}")
    print()

    try:
        # 1. TaskGroup benefits
        await demonstrate_taskgroup_benefits()
        print()

        # 2. Enhanced error handling
        await demonstrate_enhanced_error_handling()
        print()

        # 3. Concurrent operations
        await demonstrate_concurrent_database_operations()
        print()

        # 4. Type safety
        demonstrate_type_safety()
        print()

        logger.info("✨ All demonstrations completed successfully!")

    except Exception:
        logger.exception("Demo failed")
        raise


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
