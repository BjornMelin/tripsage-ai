"""
Enhanced Error Handling for Python 3.13

This module provides modern error handling patterns leveraging Python 3.13 improvements:
- Improved traceback formatting with colored output
- Structured exception handling with TaskGroups
- Enhanced error context and debugging information
- Modern async error propagation patterns
"""

import asyncio
import sys
import traceback
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

# Python 3.13 type parameters for error handling
type ErrorHandler[T] = Callable[[Exception], T]
type AsyncErrorHandler[T] = Callable[[Exception], Awaitable[T]]
type ErrorContext = dict[str, Any]

T = TypeVar("T")
E = TypeVar("E", bound=Exception)


class EnhancedErrorInfo(Generic[E]):
    """Enhanced error information with modern typing and context."""

    def __init__(
        self,
        exception: E,
        context: ErrorContext | None = None,
        task_name: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ):
        self.exception = exception
        self.context = context or {}
        self.task_name = task_name
        self.user_id = user_id
        self.request_id = request_id
        self.timestamp = datetime.now(timezone.utc)
        self.python_version = sys.version_info

    def format_enhanced_traceback(self, use_colors: bool = True) -> str:
        """Format traceback with Python 3.13 enhanced features."""
        # Get the traceback
        tb_lines = traceback.format_exception(
            type(self.exception), self.exception, self.exception.__traceback__
        )

        if (
            not use_colors
            or not hasattr(sys.stderr, "isatty")
            or not sys.stderr.isatty()
        ):
            return "".join(tb_lines)

        # Enhanced colored traceback formatting (Python 3.13 style)
        colored_lines = []
        for line in tb_lines:
            if line.strip().startswith("File"):
                # File paths in blue
                colored_lines.append(f"\033[94m{line}\033[0m")
            elif line.strip().startswith("Traceback"):
                # Header in bold
                colored_lines.append(f"\033[1m{line}\033[0m")
            elif "Error:" in line or "Exception:" in line:
                # Exception names in red
                colored_lines.append(f"\033[91m{line}\033[0m")
            else:
                # Code lines in default color
                colored_lines.append(line)

        return "".join(colored_lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert error info to dictionary for logging/serialization."""
        return {
            "exception_type": type(self.exception).__name__,
            "exception_message": str(self.exception),
            "context": self.context,
            "task_name": self.task_name,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "python_version": (
                f"{self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}"
            ),
            "traceback": traceback.format_exception(
                type(self.exception), self.exception, self.exception.__traceback__
            ),
        }


class TaskGroupErrorCollector:
    """Collect and manage errors from TaskGroup operations."""

    def __init__(self):
        self.errors: list[EnhancedErrorInfo] = []
        self.successful_tasks: list[str] = []
        self.failed_tasks: list[str] = []

    def add_error(
        self, exception: Exception, task_name: str, context: ErrorContext | None = None
    ) -> None:
        """Add an error with enhanced context."""
        error_info = EnhancedErrorInfo(
            exception=exception, context=context, task_name=task_name
        )
        self.errors.append(error_info)
        self.failed_tasks.append(task_name)

    def add_success(self, task_name: str) -> None:
        """Record successful task completion."""
        self.successful_tasks.append(task_name)

    def has_errors(self) -> bool:
        """Check if any errors were collected."""
        return len(self.errors) > 0

    def get_summary(self) -> dict[str, Any]:
        """Get error summary for reporting."""
        return {
            "total_tasks": len(self.successful_tasks) + len(self.failed_tasks),
            "successful_tasks": len(self.successful_tasks),
            "failed_tasks": len(self.failed_tasks),
            "success_rate": len(self.successful_tasks)
            / (len(self.successful_tasks) + len(self.failed_tasks))
            if (len(self.successful_tasks) + len(self.failed_tasks)) > 0
            else 0.0,
            "error_types": [type(err.exception).__name__ for err in self.errors],
            "failed_task_names": self.failed_tasks,
        }


@asynccontextmanager
async def enhanced_error_context(
    operation_name: str,
    user_id: str | None = None,
    request_id: str | None = None,
    context: ErrorContext | None = None,
):
    """
    Enhanced async context manager for error handling with Python 3.13 features.

    Provides structured error handling with detailed context and improved
    traceback formatting.
    """
    error_collector = TaskGroupErrorCollector()
    start_time = datetime.now(timezone.utc)

    try:
        yield error_collector

        # Operation completed successfully
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        if error_collector.has_errors():
            # Some tasks failed but operation didn't crash
            summary = error_collector.get_summary()
            print(f"⚠️  Operation '{operation_name}' completed with errors:")
            print(f"   Success rate: {summary['success_rate']:.1%}")
            print(f"   Failed tasks: {summary['failed_tasks']}")
        else:
            print(
                f"✅ Operation '{operation_name}' completed successfully "
                f"in {duration:.3f}s"
            )

    except Exception as e:
        # Handle single exceptions
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        error_info = EnhancedErrorInfo(
            exception=e,
            context=context,
            task_name=operation_name,
            user_id=user_id,
            request_id=request_id,
        )

        print(f"❌ Operation '{operation_name}' failed after {duration:.3f}s")
        print(f"🔍 Error: {type(e).__name__}: {e}")

        if context:
            print(f"📋 Context: {context}")

        # Print enhanced traceback
        print("\n📋 Traceback:")
        print(error_info.format_enhanced_traceback())

        raise


async def safe_task_execution[T](
    tasks: dict[str, Awaitable[T]],
    operation_name: str = "batch_operation",
    fail_fast: bool = False,
    max_concurrent: int | None = None,
) -> dict[str, T]:
    """
    Execute tasks safely using TaskGroup with enhanced error handling.

    Args:
        tasks: Dictionary mapping task names to awaitable tasks
        operation_name: Name of the operation for logging
        fail_fast: If True, stop on first error; if False, collect all errors
        max_concurrent: Maximum number of concurrent tasks (None for unlimited)

    Returns:
        Dictionary of successful results
    """
    results: dict[str, T] = {}

    async with enhanced_error_context(operation_name) as error_collector:
        if fail_fast:
            # Use TaskGroup for fail-fast behavior
            async with asyncio.TaskGroup() as tg:
                running_tasks = {}
                for task_name, awaitable in tasks.items():
                    task = tg.create_task(awaitable, name=task_name)
                    running_tasks[task] = task_name

            # Collect results if all succeeded
            for task, task_name in running_tasks.items():
                results[task_name] = task.result()
                error_collector.add_success(task_name)

        else:
            # Manual task management for partial success
            if max_concurrent:
                # Process in batches
                task_items = list(tasks.items())
                for i in range(0, len(task_items), max_concurrent):
                    batch = task_items[i : i + max_concurrent]
                    await _process_task_batch(batch, results, error_collector)
            else:
                # Process all at once
                await _process_task_batch(list(tasks.items()), results, error_collector)

    return results


async def _process_task_batch[T](
    batch: list[tuple[str, Awaitable[T]]],
    results: dict[str, T],
    error_collector: TaskGroupErrorCollector,
) -> None:
    """Process a batch of tasks with individual error handling."""
    running_tasks = {}

    # Start all tasks in the batch
    for task_name, awaitable in batch:
        task = asyncio.create_task(awaitable, name=task_name)
        running_tasks[task] = task_name

    # Wait for all tasks to complete
    completed_tasks = await asyncio.gather(
        *running_tasks.keys(), return_exceptions=True
    )

    # Process results
    for task, result in zip(running_tasks.keys(), completed_tasks, strict=False):
        task_name = running_tasks[task]

        if isinstance(result, Exception):
            error_collector.add_error(result, task_name)
        else:
            results[task_name] = result
            error_collector.add_success(task_name)


# Example usage functions for demonstration
async def example_database_operations() -> dict[str, Any]:
    """Example of using enhanced error handling for database operations."""

    async def fetch_users() -> list[dict[str, Any]]:
        await asyncio.sleep(0.1)
        return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    async def fetch_trips() -> list[dict[str, Any]]:
        await asyncio.sleep(0.2)
        return [{"id": 101, "destination": "Paris"}]

    async def fetch_memories() -> list[dict[str, Any]]:
        await asyncio.sleep(0.1)
        # Simulate occasional failure
        import random

        if random.random() < 0.3:
            raise ConnectionError("Memory service temporarily unavailable")
        return [{"id": 201, "memory": "Great trip to Paris"}]

    # Execute with enhanced error handling
    tasks = {
        "users": fetch_users(),
        "trips": fetch_trips(),
        "memories": fetch_memories(),
    }

    return await safe_task_execution(
        tasks,
        operation_name="fetch_user_data",
        fail_fast=False,  # Continue even if some tasks fail
    )


async def example_batch_processing() -> dict[str, str]:
    """Example of batch processing with error handling."""

    async def process_item(item_id: str) -> str:
        await asyncio.sleep(0.05)
        if item_id == "error_item":
            raise ValueError(f"Cannot process {item_id}")
        return f"Processed {item_id}"

    # Create tasks for batch processing
    item_ids = ["item_1", "item_2", "error_item", "item_3", "item_4"]
    tasks = {item_id: process_item(item_id) for item_id in item_ids}

    return await safe_task_execution(
        tasks, operation_name="batch_item_processing", fail_fast=False, max_concurrent=3
    )
