#!/usr/bin/env python3
"""Python 3.13 Modern Features Demonstration for TripSage with Pydantic models."""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ProcessedItem(BaseModel):
    """Single processed item produced by ModernAsyncProcessor."""

    processed_item: Any
    processor: str
    count: int
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the item was processed.",
    )


class BatchProcessingResult(BaseModel):
    """Collection of processed items keyed by an item identifier."""

    items: dict[str, ProcessedItem]

    @property
    def processed_count(self) -> int:
        """Return the number of processed items."""
        return len(self.items)


class TaskGroupRunMetrics(BaseModel):
    """Stores batch processing output together with the elapsed duration."""

    result: BatchProcessingResult
    duration_seconds: float


class TaskGroupDemoResult(BaseModel):
    """Comparison of TaskGroup and traditional asyncio approaches."""

    structured: TaskGroupRunMetrics
    traditional: TaskGroupRunMetrics
    performance_difference_seconds: float


class TaskExecutionRecord(BaseModel):
    """Successful task execution details."""

    task_id: str
    message: str


class TaskFailure(BaseModel):
    """Failed task metadata captured from an exception group."""

    task_id: str
    error_type: str
    detail: str


class ErrorHandlingResult(BaseModel):
    """Summary of successful and failed task outcomes."""

    successful_tasks: list[TaskExecutionRecord]
    failures: list[TaskFailure]

    @property
    def success_count(self) -> int:
        """Return the number of successful tasks."""
        return len(self.successful_tasks)


class DatabaseOperationResult(BaseModel):
    """Single simulated database operation result."""

    query_type: str
    execution_time_ms: float
    rows_affected: int
    success: bool
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp representing when the operation finished.",
    )


class DatabaseOperationsSummary(BaseModel):
    """Aggregated metrics for concurrent database operations."""

    operations: dict[str, DatabaseOperationResult]
    total_duration_seconds: float
    sequential_time_seconds: float
    speedup: float


class UserDataModel(BaseModel):
    """Typed representation of demo user data."""

    id: int
    name: str
    age: int


class SearchFiltersModel(BaseModel):
    """Typed representation of demo search filters."""

    destinations: list[str]
    min_budget: int
    max_budget: int
    active: bool


class TypeSafetyResult(BaseModel):
    """Container that holds typed user data and filters."""

    user: UserDataModel
    filters: SearchFiltersModel


class ModernAsyncProcessor:
    """Demonstration of Python 3.13 generic type syntax with PEP 695."""

    def __init__(self, name: str) -> None:
        """Initialize modern data processor."""
        self.name = name
        self.processed_count = 0

    async def process_item(self, item: Any) -> ProcessedItem:
        """Process a single item with modern type annotations."""
        await asyncio.sleep(0.1)
        self.processed_count += 1

        return ProcessedItem(
            processed_item=item,
            processor=self.name,
            count=self.processed_count,
        )

    async def process_batch_taskgroup(
        self, items: Sequence[Any]
    ) -> BatchProcessingResult:
        """Process items using Python 3.13 TaskGroup for structured concurrency."""
        results: dict[str, ProcessedItem] = {}

        tasks: dict[asyncio.Task[ProcessedItem], str] = {}
        async with asyncio.TaskGroup() as tg:
            for index, item in enumerate(items):
                task = tg.create_task(
                    self.process_item(item),
                    name=f"process_item_{index}",
                )
                tasks[task] = f"item_{index}"

        for task, item_key in tasks.items():
            results[item_key] = task.result()

        return BatchProcessingResult(items=results)

    async def process_batch_traditional(
        self, items: Sequence[Any]
    ) -> BatchProcessingResult:
        """Process items using traditional asyncio.gather() for comparison."""
        tasks = [self.process_item(item) for item in items]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, ProcessedItem] = {}
        for index, result in enumerate(results_list):
            if isinstance(result, BaseException):
                logger.exception("Task %s failed: %s", index, result)
                continue
            results[f"item_{index}"] = result

        return BatchProcessingResult(items=results)


async def demonstrate_taskgroup_benefits() -> TaskGroupDemoResult:
    """Demonstrate the benefits of TaskGroup over traditional approaches."""
    logger.info("Demonstrating Python 3.13 TaskGroup benefits")

    test_items = ["trip_1", "trip_2", "trip_3", "trip_4", "trip_5"]
    processor = ModernAsyncProcessor("TripSage-Processor")

    start_time = time.time()
    taskgroup_items = await processor.process_batch_taskgroup(test_items)
    taskgroup_duration = time.time() - start_time
    structured_metrics = TaskGroupRunMetrics(
        result=taskgroup_items,
        duration_seconds=taskgroup_duration,
    )

    processor.processed_count = 0

    start_time = time.time()
    traditional_items = await processor.process_batch_traditional(test_items)
    traditional_duration = time.time() - start_time
    traditional_metrics = TaskGroupRunMetrics(
        result=traditional_items,
        duration_seconds=traditional_duration,
    )

    performance_diff = abs(taskgroup_duration - traditional_duration)

    logger.info(
        "TaskGroup processed %s items in %.3fs",
        structured_metrics.result.processed_count,
        structured_metrics.duration_seconds,
    )
    logger.info(
        "Traditional processed %s items in %.3fs",
        traditional_metrics.result.processed_count,
        traditional_metrics.duration_seconds,
    )
    logger.info("Performance difference: %.3fs", performance_diff)

    return TaskGroupDemoResult(
        structured=structured_metrics,
        traditional=traditional_metrics,
        performance_difference_seconds=performance_diff,
    )


async def demonstrate_enhanced_error_handling() -> ErrorHandlingResult:
    """Demonstrate enhanced error handling with TaskGroups."""
    logger.info("Demonstrating enhanced error handling")

    async def failing_task(task_id: str) -> str:
        await asyncio.sleep(0.1)
        if task_id == "fail_me":
            raise ValueError(f"Intentional failure in {task_id}")
        return f"Success: {task_id}"

    failures: list[TaskFailure] = []
    first_run_tasks: dict[asyncio.Task[str], str] = {}
    try:
        async with asyncio.TaskGroup() as tg:
            for task_id in ["task_1", "task_2", "fail_me", "task_3"]:
                task = tg.create_task(failing_task(task_id), name=task_id)
                first_run_tasks[task] = task_id
    except ExceptionGroup as exception_group:
        logger.exception(
            "TaskGroup caught %s exceptions:",
            len(exception_group.exceptions),
        )
        for task, task_id in first_run_tasks.items():
            if not task.done():
                continue
            exception = task.exception()
            if exception is None:
                continue
            failures.append(
                TaskFailure(
                    task_id=task_id,
                    error_type=type(exception).__name__,
                    detail=str(exception),
                )
            )

    successful_records: list[TaskExecutionRecord] = []
    try:
        safe_task_mapping: dict[asyncio.Task[str], str] = {}
        async with asyncio.TaskGroup() as tg:
            for task_id in ["task_1", "task_2", "task_3", "task_4"]:
                task = tg.create_task(failing_task(task_id), name=task_id)
                safe_task_mapping[task] = task_id

        for task, task_id in safe_task_mapping.items():
            successful_records.append(
                TaskExecutionRecord(task_id=task_id, message=task.result())
            )
    except Exception:  # pragma: no cover - safeguard for demo script
        logger.exception("Unexpected error during safe task processing")

    logger.info("Successfully processed %s safe tasks", len(successful_records))

    return ErrorHandlingResult(
        successful_tasks=successful_records,
        failures=failures,
    )


async def demonstrate_concurrent_database_operations() -> DatabaseOperationsSummary:
    """Simulate concurrent database operations using modern patterns."""
    logger.info("Demonstrating concurrent database operations")

    async def simulate_db_query(
        query_type: str,
        delay: float = 0.1,
    ) -> DatabaseOperationResult:
        await asyncio.sleep(delay)
        return DatabaseOperationResult(
            query_type=query_type,
            execution_time_ms=delay * 1000,
            rows_affected=42,
            success=True,
        )

    start_time = time.time()
    async with asyncio.TaskGroup() as tg:
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

    operations = {
        "users": user_task.result(),
        "trips": trips_task.result(),
        "memories": memories_task.result(),
        "health": health_task.result(),
    }

    sequential_time = (
        sum(operation.execution_time_ms for operation in operations.values()) / 1000
    )
    speedup = sequential_time / total_duration if total_duration else 0.0

    logger.info(
        "Completed %s concurrent DB operations in %.3fs",
        len(operations),
        total_duration,
    )
    logger.info("Speedup: %.2fx (Sequential: %.3fs)", speedup, sequential_time)

    return DatabaseOperationsSummary(
        operations=operations,
        total_duration_seconds=total_duration,
        sequential_time_seconds=sequential_time,
        speedup=speedup,
    )


def demonstrate_type_safety() -> TypeSafetyResult:
    """Demonstrate improved type safety with Python 3.13 features."""
    logger.info("Demonstrating enhanced type safety")

    user = UserDataModel(id=12345, name="Alice", age=30)
    filters = SearchFiltersModel(
        destinations=["Paris", "Tokyo", "New York"],
        min_budget=1000,
        max_budget=5000,
        active=True,
    )

    logger.info("User %s", user.model_dump())
    logger.info("Search filters: %s", filters.model_dump())

    return TypeSafetyResult(user=user, filters=filters)


async def main() -> None:
    """Main demonstration function showcasing Python 3.13 modernizations."""
    logger.info("=" * 60)
    logger.info("Python 3.13 Modern Features Demo for TripSage")
    logger.info("=" * 60)

    print(f"Python version: {sys.version}")
    print(f"Demo started at: {datetime.now(UTC).isoformat()}")
    print()

    try:
        taskgroup_demo = await demonstrate_taskgroup_benefits()
        print("TaskGroup comparison:")
        print(taskgroup_demo.model_dump_json(indent=2))
        print()

        error_handling_result = await demonstrate_enhanced_error_handling()
        print("Error handling summary:")
        print(error_handling_result.model_dump_json(indent=2))
        print()

        db_summary = await demonstrate_concurrent_database_operations()
        print("Database operations summary:")
        print(db_summary.model_dump_json(indent=2))
        print()

        type_safety_result = demonstrate_type_safety()
        print("Type safety result:")
        print(type_safety_result.model_dump_json(indent=2))
        print()

        logger.info("All demonstrations completed successfully")

    except Exception:  # pragma: no cover - safeguard for demo script
        logger.exception("Demo failed")
        raise


if __name__ == "__main__":
    asyncio.run(main())
