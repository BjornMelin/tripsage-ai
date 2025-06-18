#!/usr/bin/env python3
"""
Performance benchmark script for database services.

Compares performance between old and new database services across various operations:
- Connection establishment
- Query execution (SELECT, INSERT, UPDATE, DELETE)
- Vector search operations
- Connection pooling efficiency
- Query caching performance
- Concurrent request handling
"""

import asyncio
import json
import statistics
import time
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from tabulate import tabulate

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.consolidated_database_service import (
    ConnectionMode,
    ConsolidatedDatabaseService,
)

# Try to import old services for comparison (if they still exist)
try:
    from tripsage_core.services.infrastructure.database_service import DatabaseService

    OLD_SERVICE_AVAILABLE = True
except ImportError:
    OLD_SERVICE_AVAILABLE = False
    print("Warning: Old DatabaseService not available for comparison")


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str):
        self.name = name
        self.durations: List[float] = []
        self.errors = 0
        self.metadata: Dict[str, Any] = {}

    @property
    def avg_duration(self) -> float:
        """Average duration in milliseconds."""
        return statistics.mean(self.durations) if self.durations else 0

    @property
    def min_duration(self) -> float:
        """Minimum duration in milliseconds."""
        return min(self.durations) if self.durations else 0

    @property
    def max_duration(self) -> float:
        """Maximum duration in milliseconds."""
        return max(self.durations) if self.durations else 0

    @property
    def p95_duration(self) -> float:
        """95th percentile duration in milliseconds."""
        if not self.durations:
            return 0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * 0.95)
        return sorted_durations[index]

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        total = len(self.durations) + self.errors
        return (len(self.durations) / total * 100) if total > 0 else 0

    def add_result(self, duration_ms: float, success: bool = True):
        """Add a benchmark result."""
        if success:
            self.durations.append(duration_ms)
        else:
            self.errors += 1


class DatabaseBenchmark:
    """Database service benchmark runner."""

    def __init__(self, iterations: int = 100, concurrent_users: int = 10):
        self.iterations = iterations
        self.concurrent_users = concurrent_users
        self.settings = get_settings()
        self.results: Dict[str, BenchmarkResult] = {}

    async def run_all_benchmarks(self):
        """Run all benchmarks."""
        print(f"Running database benchmarks with {self.iterations} iterations...")
        print(f"Concurrent users: {self.concurrent_users}\n")

        # Test new consolidated service
        print("Testing Consolidated Database Service...")
        await self.benchmark_consolidated_service()

        # Test old service if available
        if OLD_SERVICE_AVAILABLE:
            print("\nTesting Old Database Service...")
            await self.benchmark_old_service()

        # Generate report
        self.generate_report()

    async def benchmark_consolidated_service(self):
        """Benchmark the new consolidated service."""
        service = ConsolidatedDatabaseService(
            settings=self.settings,
            enable_monitoring=True,
            enable_query_cache=True,
        )

        try:
            # Test connection establishment
            await self._benchmark_connection(service, "Consolidated - Connect All")

            # Test different connection modes
            for mode in ConnectionMode:
                await self._benchmark_queries_by_mode(service, mode)

            # Test caching performance
            await self._benchmark_caching(service)

            # Test concurrent operations
            await self._benchmark_concurrent_operations(service)

            # Test vector search
            await self._benchmark_vector_search(service)

        finally:
            await service.close()

    async def benchmark_old_service(self):
        """Benchmark the old database service."""
        if not OLD_SERVICE_AVAILABLE:
            return

        service = DatabaseService(settings=self.settings)

        try:
            # Test connection establishment
            result = BenchmarkResult("Old Service - Connect")
            start = time.time()

            try:
                await service.connect()
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception as e:
                result.add_result(0, success=False)
                print(f"Old service connection failed: {e}")

            self.results[result.name] = result

            # Test basic queries
            await self._benchmark_old_service_queries(service)

        finally:
            await service.close()

    async def _benchmark_connection(
        self, service: ConsolidatedDatabaseService, name: str
    ):
        """Benchmark connection establishment."""
        result = BenchmarkResult(name)

        for _ in range(
            min(10, self.iterations)
        ):  # Connection test doesn't need many iterations
            # Close existing connections
            await service.close()

            start = time.time()
            try:
                await service.connect()
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception as e:
                result.add_result(0, success=False)
                print(f"Connection failed: {e}")

        self.results[name] = result

    async def _benchmark_queries_by_mode(
        self, service: ConsolidatedDatabaseService, mode: ConnectionMode
    ):
        """Benchmark queries for a specific connection mode."""
        # Ensure connected
        await service.connect(mode)

        # SELECT benchmark
        result = BenchmarkResult(f"Consolidated ({mode.value}) - SELECT")
        for _ in range(self.iterations):
            start = time.time()
            try:
                await service.select("users", columns="id,email", limit=10, mode=mode)
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception:
                result.add_result(0, success=False)

        self.results[result.name] = result

        # INSERT benchmark (fewer iterations to avoid spam)
        result = BenchmarkResult(f"Consolidated ({mode.value}) - INSERT")
        for i in range(min(10, self.iterations)):
            start = time.time()
            try:
                await service.insert(
                    "test_benchmark",
                    {
                        "name": f"Benchmark {i}",
                        "created_at": datetime.utcnow().isoformat(),
                    },
                    mode=mode,
                )
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception:
                result.add_result(0, success=False)

        self.results[result.name] = result

    async def _benchmark_caching(self, service: ConsolidatedDatabaseService):
        """Benchmark query caching performance."""
        await service.connect()

        # First, run without cache
        result_no_cache = BenchmarkResult("Consolidated - SELECT (No Cache)")
        for i in range(self.iterations):
            start = time.time()
            try:
                await service.select(
                    "users",
                    columns=["id", "email"],
                    filters={"id": f"user_{i % 10}"},  # Vary queries slightly
                )
                duration = (time.time() - start) * 1000
                result_no_cache.add_result(duration)
            except Exception:
                result_no_cache.add_result(0, success=False)

        self.results[result_no_cache.name] = result_no_cache

        # Then with cache
        result_with_cache = BenchmarkResult("Consolidated - SELECT (With Cache)")
        for i in range(self.iterations):
            start = time.time()
            try:
                await service.select(
                    "users",
                    columns=["id", "email"],
                    filters={"id": f"user_{i % 10}"},  # Same queries to test cache hits
                )
                duration = (time.time() - start) * 1000
                result_with_cache.add_result(duration)
            except Exception:
                result_with_cache.add_result(0, success=False)

        self.results[result_with_cache.name] = result_with_cache

        # Calculate cache hit rate
        cache_speedup = (
            result_no_cache.avg_duration / result_with_cache.avg_duration
            if result_with_cache.avg_duration > 0
            else 0
        )
        result_with_cache.metadata["cache_speedup"] = f"{cache_speedup:.2f}x"

    async def _benchmark_concurrent_operations(self, service: DatabaseService):
        """Benchmark concurrent operations."""
        # Service is already connected

        result = BenchmarkResult(
            f"Consolidated - Concurrent SELECT ({self.concurrent_users} users)"
        )

        async def concurrent_select(user_id: int):
            """Simulate a user making queries."""
            durations = []
            for _ in range(10):  # Each user makes 10 queries
                start = time.time()
                try:
                    await service.select(
                        "users",
                        columns=["id", "email"],
                        filters={"id": f"user_{user_id}"},
                    )
                    duration = (time.time() - start) * 1000
                    durations.append(duration)
                except Exception:
                    pass
            return durations

        # Run concurrent users
        start_total = time.time()
        tasks = [concurrent_select(i) for i in range(self.concurrent_users)]
        all_durations = await asyncio.gather(*tasks)
        total_time = (time.time() - start_total) * 1000

        # Flatten and add all durations
        for user_durations in all_durations:
            for duration in user_durations:
                result.add_result(duration)

        result.metadata["total_time_ms"] = f"{total_time:.2f}"
        result.metadata["queries_per_second"] = (
            f"{len(result.durations) / (total_time / 1000):.2f}"
        )

        self.results[result.name] = result

    async def _benchmark_vector_search(self, service: DatabaseService):
        """Benchmark vector search operations."""
        # Service is already connected

        result = BenchmarkResult("Consolidated - Vector Search")

        # Generate random vectors for testing
        vector_dim = 384  # Common embedding dimension

        for _ in range(min(20, self.iterations)):  # Vector search is typically slower
            query_vector = np.random.rand(vector_dim).tolist()

            start = time.time()
            try:
                await service.vector_search(
                    "embeddings",
                    "embedding",
                    query_vector,
                    limit=10,
                    similarity_threshold=0.7,
                )
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception as e:
                # Vector table might not exist in test environment
                result.add_result(0, success=False)
                if "embeddings" in str(e):
                    result.metadata["note"] = "Vector table not found - skipping"
                    break

        self.results[result.name] = result

    async def _benchmark_old_service_queries(self, service):
        """Benchmark queries for old service."""
        if not hasattr(service, "is_connected") or not service.is_connected:
            return

        # SELECT benchmark
        result = BenchmarkResult("Old Service - SELECT")
        for _ in range(self.iterations):
            start = time.time()
            try:
                await service.select("users", columns="id,email", limit=10)
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception:
                result.add_result(0, success=False)

        self.results[result.name] = result

    def generate_report(self):
        """Generate and display benchmark report."""
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80 + "\n")

        # Prepare data for table
        table_data = []
        for name, result in self.results.items():
            row = [
                name,
                f"{result.avg_duration:.2f}",
                f"{result.min_duration:.2f}",
                f"{result.max_duration:.2f}",
                f"{result.p95_duration:.2f}",
                f"{result.success_rate:.1f}%",
                len(result.durations) + result.errors,
            ]

            # Add metadata if available
            if result.metadata:
                metadata_str = ", ".join(
                    f"{k}: {v}" for k, v in result.metadata.items()
                )
                row.append(metadata_str)
            else:
                row.append("")

            table_data.append(row)

        headers = [
            "Operation",
            "Avg (ms)",
            "Min (ms)",
            "Max (ms)",
            "P95 (ms)",
            "Success",
            "Count",
            "Notes",
        ]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Performance comparison if both services tested
        if OLD_SERVICE_AVAILABLE:
            print("\n" + "=" * 80)
            print("PERFORMANCE COMPARISON")
            print("=" * 80 + "\n")

            comparisons = []

            # Compare SELECT performance
            old_select = self.results.get("Old Service - SELECT")
            new_select_transaction = self.results.get("Consolidated - SELECT")

            if old_select and new_select_transaction:
                improvement = (
                    (old_select.avg_duration - new_select_transaction.avg_duration)
                    / old_select.avg_duration
                    * 100
                )
                comparisons.append(
                    [
                        "SELECT Performance",
                        f"{old_select.avg_duration:.2f} ms",
                        f"{new_select_transaction.avg_duration:.2f} ms",
                        f"{improvement:.1f}% improvement"
                        if improvement > 0
                        else f"{-improvement:.1f}% slower",
                    ]
                )

            if comparisons:
                headers = ["Metric", "Old Service", "Consolidated Service", "Change"]
                print(tabulate(comparisons, headers=headers, tablefmt="grid"))

        # Save detailed results to file
        self.save_results()

    def save_results(self):
        """Save detailed results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"

        results_data = {
            "timestamp": timestamp,
            "configuration": {
                "iterations": self.iterations,
                "concurrent_users": self.concurrent_users,
            },
            "results": {},
        }

        for name, result in self.results.items():
            results_data["results"][name] = {
                "avg_duration_ms": result.avg_duration,
                "min_duration_ms": result.min_duration,
                "max_duration_ms": result.max_duration,
                "p95_duration_ms": result.p95_duration,
                "success_rate": result.success_rate,
                "total_operations": len(result.durations) + result.errors,
                "errors": result.errors,
                "metadata": result.metadata,
            }

        with open(filename, "w") as f:
            json.dump(results_data, f, indent=2)

        print(f"\nDetailed results saved to: {filename}")


async def main():
    """Main benchmark runner."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark database services")
    parser.add_argument(
        "--iterations", type=int, default=100, help="Number of iterations per test"
    )
    parser.add_argument(
        "--concurrent", type=int, default=10, help="Number of concurrent users"
    )

    args = parser.parse_args()

    benchmark = DatabaseBenchmark(
        iterations=args.iterations, concurrent_users=args.concurrent
    )

    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())
