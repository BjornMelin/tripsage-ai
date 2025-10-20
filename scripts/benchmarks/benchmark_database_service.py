#!/usr/bin/env python3
"""Performance benchmark script for the unified database service.

Benchmarks the consolidated DatabaseService across various operations:
- Connection establishment and pooling
- Query execution (SELECT, INSERT, UPDATE, DELETE)
- Vector search operations (pgvector)
- Query caching performance
- Concurrent request handling
- Performance optimization validation

Validates ULTRATHINK consolidation performance improvements.
"""

import asyncio
import json
import logging
import statistics
import time
from datetime import datetime
from typing import Any

import numpy as np

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.database_service import DatabaseService


# Simple table formatting function if tabulate is not available
def simple_table(data, headers):
    """Simple table formatting without external dependencies."""
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Format rows
    lines = []

    # Header
    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    lines.append(header_line)
    lines.append("-" * len(header_line))

    # Data rows
    for row in data:
        row_line = " | ".join(
            str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
        )
        lines.append(row_line)

    return "\n".join(lines)


# Use simple table formatting without external dependencies
def tabulate(data, headers=None, tablefmt="grid"):
    """Simple table formatting function without external dependencies.

    Args:
        data: List of rows to format
        headers: Optional column headers
        tablefmt: Table format (unused, kept for compatibility)

    Returns:
        Formatted table string
    """
    return simple_table(data, headers)


# Note: We now use the unified DatabaseService (consolidates 7 previous services)
# This benchmark validates the unified service performance


class BenchmarkResult:
    """Container for benchmark results."""

    def __init__(self, name: str):
        """Initialize benchmark result tracking.

        Args:
            name: Name of the benchmark operation
        """
        self.name = name
        self.durations: list[float] = []
        self.errors = 0
        self.metadata: dict[str, Any] = {}

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
        """Initialize database benchmark runner.

        Args:
            iterations: Number of iterations per test
            concurrent_users: Number of concurrent users to simulate
        """
        self.iterations = iterations
        self.concurrent_users = concurrent_users
        self.settings = get_settings()
        self.results: dict[str, BenchmarkResult] = {}

    async def run_all_benchmarks(self):
        """Run all benchmarks."""
        print(f"Running database benchmarks with {self.iterations} iterations...")
        print(f"Concurrent users: {self.concurrent_users}\n")

        # Test unified database service
        print("Testing Database Service...")
        await self.benchmark_database_service()

        # Generate report
        self.generate_report()

    async def benchmark_database_service(self):
        """Benchmark the database service."""
        service = DatabaseService(settings=self.settings)

        try:
            # Test connection establishment
            await self._benchmark_connection(service, "Database - Connection Test")

            # Test different query types
            await self._benchmark_query_types(service)

            # Test transaction performance
            await self._benchmark_transactions(service)

            # Test caching performance
            await self._benchmark_caching(service)

            # Test concurrent operations
            await self._benchmark_concurrent_operations(service)

            # Test vector search if available
            await self._benchmark_vector_search(service)

        finally:
            await service.close()

    async def _benchmark_connection(self, service: DatabaseService, name: str):
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

    async def _benchmark_query_types(self, service: DatabaseService):
        """Benchmark different query types with the unified service."""
        # Ensure connected
        try:
            await service.connect()
        except Exception as e:
            print(f"Failed to connect for query benchmarks: {e}")
            return

        # SELECT benchmark
        result = BenchmarkResult("Database - SELECT")
        for _ in range(self.iterations):
            start = time.time()
            try:
                await service.execute_sql("SELECT 1 as test_column LIMIT 10")
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception:
                result.add_result(0, success=False)

        self.results[result.name] = result

        # Test table operations if available
        try:
            # Create test table for benchmarking
            await service.execute_sql("""
                CREATE TABLE IF NOT EXISTS test_benchmark (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # INSERT benchmark (fewer iterations to avoid spam)
            result = BenchmarkResult("Database - INSERT")
            for i in range(min(10, self.iterations)):
                start = time.time()
                try:
                    await service.execute_sql(
                        "INSERT INTO test_benchmark (name) VALUES ($1)",
                        (f"Benchmark {i}",),
                    )
                    duration = (time.time() - start) * 1000
                    result.add_result(duration)
                except Exception:
                    result.add_result(0, success=False)

            self.results[result.name] = result

            # UPDATE benchmark
            result = BenchmarkResult("Database - UPDATE")
            for i in range(min(5, self.iterations)):
                start = time.time()
                try:
                    await service.execute_sql(
                        "UPDATE test_benchmark SET name = $1 WHERE id = $2",
                        (f"Updated {i}", i + 1),
                    )
                    duration = (time.time() - start) * 1000
                    result.add_result(duration)
                except Exception:
                    result.add_result(0, success=False)

            self.results[result.name] = result

        except Exception as e:
            print(f"Could not run table-based benchmarks: {e}")

    async def _benchmark_transactions(self, service: DatabaseService):
        """Benchmark transaction performance."""
        result = BenchmarkResult("Database - Transactions")

        for _ in range(min(5, self.iterations)):
            start = time.time()
            try:
                async with service.transaction():
                    await service.execute_sql("SELECT 1")
                    await service.execute_sql("SELECT 2")
                duration = (time.time() - start) * 1000
                result.add_result(duration)
            except Exception:
                result.add_result(0, success=False)

        self.results[result.name] = result

    async def _benchmark_caching(self, service: DatabaseService):
        """Benchmark query caching performance."""
        try:
            await service.connect()
        except Exception as e:
            print(f"Failed to connect for caching benchmarks: {e}")
            return

        # Test repeated queries to see if there's any caching benefit
        result_first_run = BenchmarkResult("Database - SELECT (First Run)")
        for i in range(min(20, self.iterations)):
            start = time.time()
            try:
                await service.execute_sql(
                    "SELECT * FROM information_schema.tables WHERE table_name = $1",
                    (f"table_{i % 5}",),  # Vary queries slightly
                )
                duration = (time.time() - start) * 1000
                result_first_run.add_result(duration)
            except Exception:
                result_first_run.add_result(0, success=False)

        self.results[result_first_run.name] = result_first_run

        # Run same queries again to test for any caching
        result_repeat_run = BenchmarkResult("Database - SELECT (Repeat Run)")
        for i in range(min(20, self.iterations)):
            start = time.time()
            try:
                await service.execute_sql(
                    "SELECT * FROM information_schema.tables WHERE table_name = $1",
                    (f"table_{i % 5}",),  # Same queries to test cache hits
                )
                duration = (time.time() - start) * 1000
                result_repeat_run.add_result(duration)
            except Exception:
                result_repeat_run.add_result(0, success=False)

        self.results[result_repeat_run.name] = result_repeat_run

        # Calculate potential speedup
        if result_repeat_run.avg_duration > 0 and result_first_run.avg_duration > 0:
            speedup = result_first_run.avg_duration / result_repeat_run.avg_duration
            result_repeat_run.metadata["potential_speedup"] = f"{speedup:.2f}x"

    async def _benchmark_concurrent_operations(self, service: DatabaseService):
        """Benchmark concurrent operations."""
        # Service is already connected

        result = BenchmarkResult(
            f"Database - Concurrent SELECT ({self.concurrent_users} users)"
        )

        async def concurrent_select(user_id: int):
            """Simulate a user making queries."""
            durations = []
            for _ in range(10):  # Each user makes 10 queries
                start = time.time()
                try:
                    await service.execute_sql(
                        "SELECT $1 as user_id, NOW() as timestamp", (user_id,)
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

        result = BenchmarkResult("Database - Vector Search")

        # Check if pgvector extension is available
        try:
            await service.execute_sql(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )

            # Generate random vectors for testing
            vector_dim = 384  # Common embedding dimension

            # Vector search is typically slower
            for _ in range(min(5, self.iterations)):
                # Use numpy for efficient vector generation
                rng = np.random.default_rng(42)  # Reproducible seeding
                query_vector = rng.random(vector_dim).tolist()

                start = time.time()
                try:
                    # Test basic vector operations if available
                    await service.execute_sql(
                        "SELECT $1::vector <-> $2::vector as distance",
                        (query_vector, query_vector),
                    )
                    duration = (time.time() - start) * 1000
                    result.add_result(duration)
                except Exception as e:
                    result.add_result(0, success=False)
                    result.metadata["note"] = f"Vector operation failed: {str(e)[:100]}"
                    break

        except Exception as e:
            result.metadata["note"] = "pgvector extension not available"
            logging.info(f"Vector search benchmark skipped: {e}")

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

        with Path(filename).open("w") as f:
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
