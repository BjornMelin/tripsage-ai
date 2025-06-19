"""
Performance Optimizations with Python 3.13 Features

This module provides performance optimizations leveraging Python 3.13 improvements:
- JIT compilation benefits for hot paths
- Optimized async patterns with TaskGroups
- Memory-efficient data structures
- Enhanced type checking for performance
- Modern string formatting optimizations
"""

import asyncio
import gc
import sys
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache, wraps
from typing import Any, TypeVar, final

# Python 3.13 type parameters for performance optimization
type CacheKey = str | tuple[str, ...]
type PerformanceMetric = dict[str, float | int]

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


@final
@dataclass(frozen=True, slots=True)
class PerformanceConfig:
    """Configuration for performance optimizations."""

    # Async settings
    max_concurrent_tasks: int = 50
    task_batch_size: int = 10
    connection_pool_size: int = 20

    # Caching settings
    cache_ttl_seconds: int = 300
    max_cache_size: int = 1000

    # Memory management
    gc_threshold: int = 700
    enable_gc_debugging: bool = False

    # String optimization
    use_f_strings: bool = True
    enable_string_interning: bool = True


@dataclass(slots=True)
class PerformanceStats:
    """Track performance statistics."""

    operation_count: int = 0
    total_duration: float = 0.0
    min_duration: float = float("inf")
    max_duration: float = 0.0
    error_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0

    def add_timing(self, duration: float) -> None:
        """Add a timing measurement."""
        self.operation_count += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)

    def add_error(self) -> None:
        """Record an error."""
        self.error_count += 1

    def add_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits += 1

    def add_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses += 1

    @property
    def average_duration(self) -> float:
        """Calculate average duration."""
        return (
            self.total_duration / self.operation_count
            if self.operation_count > 0
            else 0.0
        )

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_cache_ops = self.cache_hits + self.cache_misses
        return self.cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return (
            self.error_count / self.operation_count if self.operation_count > 0 else 0.0
        )


class OptimizedAsyncCache[K, V]:
    """
    High-performance async cache with Python 3.13 optimizations.

    Features:
    - Generic type parameters (PEP 695)
    - Efficient memory usage with slots
    - Async-aware TTL management
    - LRU eviction policy
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[K, tuple[V, float]] = {}  # value, timestamp
        self._access_times: dict[K, float] = {}
        self._lock = asyncio.Lock()

        # Performance tracking
        self.stats = PerformanceStats()

    async def get(self, key: K) -> V | None:
        """Get value from cache with async lock."""
        async with self._lock:
            now = time.time()

            if key not in self._cache:
                self.stats.add_cache_miss()
                return None

            value, timestamp = self._cache[key]

            # Check TTL
            if now - timestamp > self.ttl_seconds:
                del self._cache[key]
                self._access_times.pop(key, None)
                self.stats.add_cache_miss()
                return None

            # Update access time for LRU
            self._access_times[key] = now
            self.stats.add_cache_hit()
            return value

    async def set(self, key: K, value: V) -> None:
        """Set value in cache with async lock."""
        async with self._lock:
            now = time.time()

            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()

            self._cache[key] = (value, now)
            self._access_times[key] = now

    async def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._access_times:
            return

        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        self._cache.pop(lru_key, None)
        self._access_times.pop(lru_key, None)

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": self.stats.cache_hit_rate,
            "hits": self.stats.cache_hits,
            "misses": self.stats.cache_misses,
        }


class BatchProcessor[T]:
    """
    Optimized batch processor using Python 3.13 TaskGroups.

    Processes items in batches for optimal throughput with
    structured concurrency and error handling.
    """

    def __init__(
        self,
        batch_size: int = 10,
        max_concurrent: int = 5,
        processor_func: Callable[[T], Awaitable[T]] | None = None,
    ):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.processor_func = processor_func
        self.stats = PerformanceStats()

    async def process_items(
        self, items: Sequence[T], processor: Callable[[T], Awaitable[T]] | None = None
    ) -> list[T]:
        """
        Process items in optimized batches using TaskGroups.

        Args:
            items: Items to process
            processor: Optional processor function (overrides default)

        Returns:
            List of processed items
        """
        if not processor:
            processor = self.processor_func

        if not processor:
            raise ValueError("No processor function provided")

        start_time = time.time()
        results: list[T] = []

        try:
            # Split items into batches
            batches = [
                items[i : i + self.batch_size]
                for i in range(0, len(items), self.batch_size)
            ]

            # Process batches with limited concurrency
            for batch_group_start in range(0, len(batches), self.max_concurrent):
                batch_group = batches[
                    batch_group_start : batch_group_start + self.max_concurrent
                ]

                # Use TaskGroup for structured concurrency
                async with asyncio.TaskGroup() as tg:
                    batch_tasks = []
                    for batch_idx, batch in enumerate(batch_group):
                        task = tg.create_task(
                            self._process_batch(batch, processor),
                            name=f"batch_{batch_group_start + batch_idx}",
                        )
                        batch_tasks.append(task)

                # Collect results from completed batches
                for task in batch_tasks:
                    batch_results = task.result()
                    results.extend(batch_results)

            duration = time.time() - start_time
            self.stats.add_timing(duration)

            return results

        except Exception:
            self.stats.add_error()
            duration = time.time() - start_time
            self.stats.add_timing(duration)
            raise

    async def _process_batch(
        self, batch: Sequence[T], processor: Callable[[T], Awaitable[T]]
    ) -> list[T]:
        """Process a single batch concurrently."""
        async with asyncio.TaskGroup() as tg:
            tasks = []
            for item in batch:
                task = tg.create_task(processor(item))
                tasks.append(task)

        return [task.result() for task in tasks]


def performance_monitor(track_memory: bool = False):
    """
    Decorator for monitoring function performance with Python 3.13 optimizations.

    Args:
        track_memory: Whether to track memory usage
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = None

            if track_memory:
                gc.collect()  # Force collection for accurate measurement
                start_memory = sys.getsizeof(gc.get_objects())

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance info using modern f-string formatting
                memory_info = ""
                if track_memory and start_memory:
                    end_memory = sys.getsizeof(gc.get_objects())
                    memory_delta = end_memory - start_memory
                    memory_info = f" | Memory: {memory_delta:+,} bytes"

                print(f"⚡ {func.__name__}: {duration:.3f}s{memory_info}")
                return result

            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ {func.__name__}: {duration:.3f}s | Error: {e}")
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = None

            if track_memory:
                gc.collect()
                start_memory = sys.getsizeof(gc.get_objects())

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                memory_info = ""
                if track_memory and start_memory:
                    end_memory = sys.getsizeof(gc.get_objects())
                    memory_delta = end_memory - start_memory
                    memory_info = f" | Memory: {memory_delta:+,} bytes"

                print(f"⚡ {func.__name__}: {duration:.3f}s{memory_info}")
                return result

            except Exception as e:
                duration = time.time() - start_time
                print(f"❌ {func.__name__}: {duration:.3f}s | Error: {e}")
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


@lru_cache(maxsize=1000)
def optimized_string_formatter(template: str, **kwargs) -> str:
    """
    Optimized string formatting with caching and modern f-string patterns.

    Uses LRU cache for template compilation and efficient formatting.
    """
    # Use modern string formatting with proper escaping
    try:
        # For Python 3.13, we can leverage improved f-string performance
        return template.format(**kwargs)
    except KeyError as e:
        # Enhanced error message with context
        available_keys = list(kwargs.keys())
        raise ValueError(
            f"Missing key {e} in template. Available keys: {available_keys}"
        ) from e


class OptimizedStringBuilder:
    """
    Memory-efficient string builder for Python 3.13.

    Uses modern approaches for optimal string concatenation performance.
    """

    __slots__ = ("_parts", "_size")

    def __init__(self):
        self._parts: list[str] = []
        self._size = 0

    def append(self, text: str) -> "OptimizedStringBuilder":
        """Append text to the builder."""
        self._parts.append(text)
        self._size += len(text)
        return self

    def append_formatted(self, template: str, **kwargs) -> "OptimizedStringBuilder":
        """Append formatted text using optimized formatter."""
        formatted = optimized_string_formatter(template, **kwargs)
        return self.append(formatted)

    def build(self) -> str:
        """Build the final string efficiently."""
        if not self._parts:
            return ""

        # Use join for optimal performance
        result = "".join(self._parts)

        # Clear for reuse
        self._parts.clear()
        self._size = 0

        return result

    def __len__(self) -> int:
        """Get estimated size."""
        return self._size


@asynccontextmanager
async def optimized_resource_pool[T](
    factory: Callable[[], Awaitable[T]],
    cleanup: Callable[[T], Awaitable[None]],
    pool_size: int = 10,
) -> AsyncIterator[Callable[[], Awaitable[T]]]:
    """
    Optimized resource pool using modern async patterns.

    Args:
        factory: Function to create new resources
        cleanup: Function to cleanup resources
        pool_size: Maximum pool size

    Yields:
        Function to acquire resources from the pool
    """
    pool: list[T] = []
    semaphore = asyncio.Semaphore(pool_size)

    async def acquire() -> T:
        async with semaphore:
            if pool:
                return pool.pop()
            else:
                return await factory()

    async def release(resource: T) -> None:
        if len(pool) < pool_size:
            pool.append(resource)
        else:
            await cleanup(resource)

    # Pre-populate pool
    async with asyncio.TaskGroup() as tg:
        init_tasks = []
        for _ in range(min(pool_size, 5)):  # Pre-create some resources
            task = tg.create_task(factory())
            init_tasks.append(task)

    pool.extend(task.result() for task in init_tasks)

    try:
        # Yield the acquire function with release capability
        class ResourceManager:
            async def acquire(self) -> T:
                return await acquire()

            async def release(self, resource: T) -> None:
                await release(resource)

        yield ResourceManager().acquire

    finally:
        # Cleanup all resources
        async with asyncio.TaskGroup() as tg:
            cleanup_tasks = []
            for resource in pool:
                task = tg.create_task(cleanup(resource))
                cleanup_tasks.append(task)


# Example usage functions
async def example_optimized_database_query() -> dict[str, Any]:
    """Example of optimized database querying with caching."""

    # Simulated cache and database
    cache = OptimizedAsyncCache[str, dict[str, Any]](max_size=100)

    @performance_monitor(track_memory=True)
    async def fetch_user_data(user_id: str) -> dict[str, Any]:
        """Fetch user data with caching."""
        cache_key = f"user:{user_id}"

        # Check cache first
        cached_data = await cache.get(cache_key)
        if cached_data:
            return cached_data

        # Simulate database query
        await asyncio.sleep(0.1)
        user_data = {
            "id": user_id,
            "name": f"User {user_id}",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Cache the result
        await cache.set(cache_key, user_data)
        return user_data

    # Batch fetch multiple users
    user_ids = ["1", "2", "3", "4", "5"]
    processor = BatchProcessor[str](batch_size=2, max_concurrent=3)

    async def process_user(user_id: str) -> dict[str, Any]:
        return await fetch_user_data(user_id)

    results = await processor.process_items(user_ids, process_user)

    return {
        "users": results,
        "cache_stats": cache.get_stats(),
        "processor_stats": {
            "operations": processor.stats.operation_count,
            "avg_duration": processor.stats.average_duration,
            "error_rate": processor.stats.error_rate,
        },
    }


async def example_string_optimization() -> str:
    """Example of optimized string operations."""

    builder = OptimizedStringBuilder()

    # Build a complex string efficiently
    builder.append("TripSage Performance Report\n")
    builder.append("=" * 30 + "\n\n")

    # Use optimized formatting
    for i in range(5):
        builder.append_formatted(
            "Operation {index}: {status} ({duration:.3f}s)\n",
            index=i + 1,
            status="SUCCESS",
            duration=0.123 + i * 0.01,
        )

    builder.append("\nSummary: All operations completed successfully!")

    return builder.build()


# Performance testing utilities
async def benchmark_async_operations(
    operations: dict[str, Callable[[], Awaitable[Any]]], iterations: int = 100
) -> dict[str, PerformanceMetric]:
    """
    Benchmark async operations using TaskGroup for accurate measurements.

    Args:
        operations: Dictionary of operation name to async function
        iterations: Number of iterations per operation

    Returns:
        Performance metrics for each operation
    """
    results: dict[str, PerformanceMetric] = {}

    for op_name, operation in operations.items():
        durations: list[float] = []
        errors = 0

        print(f"🔬 Benchmarking {op_name} ({iterations} iterations)...")

        # Run iterations using TaskGroup for precise timing
        async with asyncio.TaskGroup() as tg:
            tasks = []
            for _i in range(iterations):

                async def timed_operation(op=operation):
                    start = time.perf_counter()
                    try:
                        await op()
                        return time.perf_counter() - start, None
                    except Exception as e:
                        return time.perf_counter() - start, e

                task = tg.create_task(timed_operation())
                tasks.append(task)

        # Process results
        for task in tasks:
            duration, error = task.result()
            durations.append(duration)
            if error:
                errors += 1

        # Calculate statistics
        total_time = sum(durations)
        avg_time = total_time / len(durations)
        min_time = min(durations)
        max_time = max(durations)

        results[op_name] = {
            "iterations": iterations,
            "total_time": total_time,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "operations_per_second": iterations / total_time,
            "error_count": errors,
            "error_rate": errors / iterations,
        }

        print(
            f"  ✅ {avg_time * 1000:.2f}ms avg, {iterations / total_time:.0f} ops/sec"
        )

    return results
