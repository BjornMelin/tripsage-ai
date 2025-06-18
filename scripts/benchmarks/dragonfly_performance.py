#!/usr/bin/env python3
"""
DragonflyDB Performance Benchmark Script

This script validates the performance improvements of DragonflyDB over Redis
by running various cache operations and measuring throughput.
"""

import asyncio
import statistics
import time

from tripsage_core.config import get_settings
from tripsage_core.services.infrastructure.cache_service import CacheService

class DragonflyBenchmark:
    """Benchmark suite for DragonflyDB performance testing."""

    def __init__(self):
        self.settings = get_settings()
        self.cache_service = CacheService(self.settings)
        self.results: dict[str, list[float]] = {}

    async def setup(self):
        """Connect to DragonflyDB."""
        await self.cache_service.connect()
        print(f"✅ Connected to DragonflyDB at {self.settings.redis_url}")

    async def teardown(self):
        """Disconnect from DragonflyDB."""
        await self.cache_service.disconnect()

    async def benchmark_set_operations(self, iterations: int = 10000):
        """Benchmark SET operations."""
        print(f"\n📊 Benchmarking SET operations ({iterations} iterations)...")
        times = []

        for i in range(iterations):
            data = {"id": i, "value": f"test_value_{i}", "timestamp": time.time()}
            start = time.perf_counter()
            await self.cache_service.set_json(f"bench:set:{i}", data, ttl=300)
            times.append(time.perf_counter() - start)

        self.results["set"] = times
        ops_per_sec = iterations / sum(times)
        avg_ms = statistics.mean(times) * 1000
        print(f"✅ SET: {ops_per_sec:,.0f} ops/sec (avg: {avg_ms:.3f}ms)")

    async def benchmark_get_operations(self, iterations: int = 10000):
        """Benchmark GET operations."""
        print(f"\n📊 Benchmarking GET operations ({iterations} iterations)...")

        # First, populate cache
        for i in range(min(1000, iterations)):
            await self.cache_service.set_json(
                f"bench:get:{i}", {"id": i, "value": f"test_value_{i}"}, ttl=300
            )

        times = []
        for i in range(iterations):
            key = f"bench:get:{i % 1000}"  # Cycle through keys
            start = time.perf_counter()
            await self.cache_service.get_json(key)
            times.append(time.perf_counter() - start)

        self.results["get"] = times
        ops_per_sec = iterations / sum(times)
        avg_ms = statistics.mean(times) * 1000
        print(f"✅ GET: {ops_per_sec:,.0f} ops/sec (avg: {avg_ms:.3f}ms)")

    async def benchmark_mixed_operations(self, iterations: int = 10000):
        """Benchmark mixed SET/GET operations."""
        print(f"\n📊 Benchmarking mixed operations ({iterations} iterations)...")
        times = []

        for i in range(iterations):
            start = time.perf_counter()

            if i % 3 == 0:  # 33% writes
                await self.cache_service.set_json(
                    f"bench:mixed:{i}", {"id": i, "value": f"test_value_{i}"}, ttl=300
                )
            else:  # 67% reads
                await self.cache_service.get_json(f"bench:mixed:{i % 1000}")

            times.append(time.perf_counter() - start)

        self.results["mixed"] = times
        ops_per_sec = iterations / sum(times)
        avg_ms = statistics.mean(times) * 1000
        print(f"✅ MIXED: {ops_per_sec:,.0f} ops/sec (avg: {avg_ms:.3f}ms)")

    async def benchmark_bulk_operations(
        self, batch_size: int = 100, batches: int = 100
    ):
        """Benchmark bulk operations."""
        print(
            f"\n📊 Benchmarking bulk operations "
            f"({batch_size} items × {batches} batches)..."
        )
        times = []

        for batch in range(batches):
            # Prepare batch data
            batch_data = {
                f"bench:bulk:{batch}:{i}": {
                    "id": i,
                    "batch": batch,
                    "data": f"value_{i}",
                }
                for i in range(batch_size)
            }

            # Time bulk set
            start = time.perf_counter()
            tasks = [
                self.cache_service.set_json(key, value, ttl=300)
                for key, value in batch_data.items()
            ]
            await asyncio.gather(*tasks)
            times.append(time.perf_counter() - start)

        self.results["bulk"] = times
        total_ops = batch_size * batches
        ops_per_sec = total_ops / sum(times)
        avg_batch_ms = statistics.mean(times) * 1000
        print(f"✅ BULK: {ops_per_sec:,.0f} ops/sec (avg batch: {avg_batch_ms:.3f}ms)")

    def print_summary(self):
        """Print benchmark summary."""
        print("\n" + "=" * 60)
        print("📈 DRAGONFLY PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)

        total_ops = 0
        total_time = 0

        for operation, times in self.results.items():
            ops = len(times)
            total = sum(times)
            avg = statistics.mean(times) * 1000  # Convert to ms
            p50 = statistics.median(times) * 1000
            p99 = sorted(times)[int(len(times) * 0.99)] * 1000

            total_ops += ops
            total_time += total

            print(f"\n{operation.upper()} Operations:")
            print(f"  Total: {ops:,} ops in {total:.2f}s")
            print(f"  Throughput: {ops / total:,.0f} ops/sec")
            print(f"  Latency - Avg: {avg:.3f}ms, P50: {p50:.3f}ms, P99: {p99:.3f}ms")

        if total_ops > 0:
            print("\n🎯 OVERALL PERFORMANCE:")
            print(f"  Total Operations: {total_ops:,}")
            print(f"  Total Time: {total_time:.2f}s")
            print(f"  Average Throughput: {total_ops / total_time:,.0f} ops/sec")

            # Compare with Redis baseline (typical Redis: ~100k ops/sec)
            redis_baseline = 100_000
            dragonfly_throughput = total_ops / total_time
            improvement = dragonfly_throughput / redis_baseline

            print("\n🚀 Performance vs Redis Baseline:")
            print(f"  Redis (typical): ~{redis_baseline:,} ops/sec")
            print(f"  DragonflyDB: ~{dragonfly_throughput:,.0f} ops/sec")
            print(f"  Improvement: {improvement:.1f}x")

    async def run(self):
        """Run all benchmarks."""
        try:
            await self.setup()

            # Run benchmarks
            await self.benchmark_set_operations(10000)
            await self.benchmark_get_operations(10000)
            await self.benchmark_mixed_operations(10000)
            await self.benchmark_bulk_operations(100, 100)

            # Print results
            self.print_summary()

        except Exception as e:
            print(f"❌ Benchmark error: {e}")
        finally:
            await self.teardown()

async def main():
    """Run DragonflyDB performance benchmarks."""
    print("🐉 DragonflyDB Performance Benchmark")
    print("=" * 60)

    benchmark = DragonflyBenchmark()
    await benchmark.run()

if __name__ == "__main__":
    asyncio.run(main())
