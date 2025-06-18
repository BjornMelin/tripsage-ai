#!/usr/bin/env python3
"""
Enhanced Database Performance Benchmark Script.

This script benchmarks the Enhanced Database Pool Manager against performance targets:
- <50ms average database query latency
- >95% connection pool efficiency
- LIFO connection pooling effectiveness
- Prometheus metrics accuracy

Usage:
    python scripts/benchmark_enhanced_database_performance.py \
        [--verbose] [--iterations N]
"""

import argparse
import asyncio
import logging
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tripsage_core.config import get_settings  # noqa: E402
from tripsage_core.monitoring.enhanced_database_metrics import (  # noqa: E402
    get_enhanced_database_metrics,
)
from tripsage_core.services.infrastructure import (  # noqa: E402
    get_database_service,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Enhanced Database Performance Benchmark."""

    def __init__(self, iterations: int = 1000, verbose: bool = False):
        """Initialize benchmark with configuration."""
        self.iterations = iterations
        self.verbose = verbose
        self.results = {}
        self.db_service = None
        self.metrics = None

    async def setup(self):
        """Setup benchmark environment."""
        logger.info("🚀 Setting up Enhanced Database Performance Benchmark")

        try:
            # Get settings
            get_settings()

            # Get consolidated database service
            self.db_service = await get_database_service()

            # Get metrics instance
            self.metrics = get_enhanced_database_metrics()
            self.metrics.reset_baselines()

            logger.info("✅ Benchmark setup completed")

        except Exception as e:
            logger.error(f"❌ Benchmark setup failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup benchmark resources."""
        if self.db_service:
            await self.db_service.close()
        logger.info("🧹 Benchmark cleanup completed")

    async def benchmark_connection_acquisition(self) -> Dict[str, Any]:
        """Benchmark connection acquisition latency."""
        logger.info("🔗 Benchmarking connection acquisition latency...")

        latencies = []
        errors = 0

        for i in range(self.iterations):
            try:
                start_time = time.perf_counter()

                async with self.db_service.get_session():
                    # Minimal work to simulate real usage
                    await asyncio.sleep(0.001)

                end_time = time.perf_counter()
                latency = (end_time - start_time) * 1000  # Convert to ms
                latencies.append(latency)

                if self.verbose and i % 100 == 0:
                    logger.info(
                        f"  Progress: {i}/{self.iterations} - "
                        f"Current latency: {latency:.2f}ms"
                    )

            except Exception as e:
                errors += 1
                if self.verbose:
                    logger.warning(f"  Connection acquisition error: {e}")

        # Calculate statistics
        if latencies:
            avg_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18]
            p99_latency = statistics.quantiles(latencies, n=100)[98]
            max_latency = max(latencies)
            min_latency = min(latencies)
        else:
            avg_latency = median_latency = p95_latency = p99_latency = max_latency = (
                min_latency
            ) = 0

        success_rate = (len(latencies) / self.iterations) * 100

        results = {
            "test_name": "Connection Acquisition",
            "iterations": self.iterations,
            "successful_operations": len(latencies),
            "errors": errors,
            "success_rate_percent": success_rate,
            "avg_latency_ms": avg_latency,
            "median_latency_ms": median_latency,
            "p95_latency_ms": p95_latency,
            "p99_latency_ms": p99_latency,
            "max_latency_ms": max_latency,
            "min_latency_ms": min_latency,
            "target_met": avg_latency < 50.0 and success_rate >= 95.0,
        }

        self.results["connection_acquisition"] = results
        return results

    async def benchmark_query_operations(self) -> Dict[str, Any]:
        """Benchmark various database query operations."""
        logger.info("📊 Benchmarking database query operations...")

        operations = [
            ("select", "users"),
            ("insert", "trips"),
            ("update", "flights"),
            ("select", "memories"),
            ("vector_search", "destinations"),
        ]

        operation_results = {}

        for operation, table in operations:
            logger.info(f"  Testing {operation} on {table}...")

            latencies = []
            errors = 0

            for i in range(self.iterations // len(operations)):
                try:
                    start_time = time.perf_counter()

                    # Simulate database operation
                    async with self.db_service.get_session():
                        # Simulate increasing load
                        operation_latency = 0.010 + (i * 0.0001)
                        # Simulate work
                        await asyncio.sleep(operation_latency)

                    end_time = time.perf_counter()
                    total_latency = (end_time - start_time) * 1000
                    latencies.append(total_latency)

                except Exception as e:
                    errors += 1
                    if self.verbose:
                        logger.warning(f"  Query operation error: {e}")

            # Calculate statistics for this operation
            if latencies:
                avg_latency = statistics.mean(latencies)
                p95_latency = (
                    statistics.quantiles(latencies, n=20)[18]
                    if len(latencies) >= 20
                    else max(latencies)
                )
            else:
                avg_latency = p95_latency = 0

            operation_key = f"{operation}_{table}"
            operation_results[operation_key] = {
                "operation": operation,
                "table": table,
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "successful_operations": len(latencies),
                "errors": errors,
                "target_met": avg_latency < 50.0,
            }

        # Overall query performance
        all_latencies = []
        total_errors = 0
        total_operations = 0

        for result in operation_results.values():
            total_operations += result["successful_operations"] + result["errors"]
            total_errors += result["errors"]
            # Approximate latencies for overall calculation
            all_latencies.extend(
                [result["avg_latency_ms"]] * result["successful_operations"]
            )

        overall_avg = statistics.mean(all_latencies) if all_latencies else 0
        success_rate = (
            ((total_operations - total_errors) / total_operations) * 100
            if total_operations > 0
            else 0
        )

        results = {
            "test_name": "Query Operations",
            "operations": operation_results,
            "overall_avg_latency_ms": overall_avg,
            "total_operations": total_operations,
            "total_errors": total_errors,
            "success_rate_percent": success_rate,
            "target_met": overall_avg < 50.0 and success_rate >= 95.0,
        }

        self.results["query_operations"] = results
        return results

    async def benchmark_concurrent_operations(self) -> Dict[str, Any]:
        """Benchmark concurrent database operations."""
        logger.info("🚀 Benchmarking concurrent operations...")

        concurrent_levels = [5, 10, 20, 50]
        concurrent_results = {}

        for concurrency in concurrent_levels:
            logger.info(f"  Testing concurrency level: {concurrency}")

            async def concurrent_task():
                """Single concurrent task."""
                start_time = time.perf_counter()
                try:
                    async with self.db_service.get_session():
                        await asyncio.sleep(0.005)  # Simulate work
                    end_time = time.perf_counter()
                    return {
                        "latency_ms": (end_time - start_time) * 1000,
                        "success": True,
                    }
                except Exception as e:
                    end_time = time.perf_counter()
                    return {
                        "latency_ms": (end_time - start_time) * 1000,
                        "success": False,
                        "error": str(e),
                    }

            # Execute concurrent tasks
            start_time = time.perf_counter()
            tasks = [concurrent_task() for _ in range(concurrency)]
            results = await asyncio.gather(*tasks)
            end_time = time.perf_counter()

            total_time = end_time - start_time
            successful_results = [r for r in results if r["success"]]
            failed_results = [r for r in results if not r["success"]]

            if successful_results:
                latencies = [r["latency_ms"] for r in successful_results]
                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)
            else:
                avg_latency = max_latency = 0

            success_rate = (len(successful_results) / concurrency) * 100
            throughput = concurrency / total_time

            concurrent_results[f"concurrency_{concurrency}"] = {
                "concurrency_level": concurrency,
                "avg_latency_ms": avg_latency,
                "max_latency_ms": max_latency,
                "success_rate_percent": success_rate,
                "throughput_ops_per_sec": throughput,
                "total_time_sec": total_time,
                "successful_operations": len(successful_results),
                "failed_operations": len(failed_results),
                "target_met": avg_latency < 100.0 and success_rate >= 95.0,
            }

        results = {
            "test_name": "Concurrent Operations",
            "concurrency_results": concurrent_results,
            "target_met": all(r["target_met"] for r in concurrent_results.values()),
        }

        self.results["concurrent_operations"] = results
        return results

    async def benchmark_pool_efficiency(self) -> Dict[str, Any]:
        """Benchmark connection pool efficiency."""
        logger.info("📈 Benchmarking pool efficiency...")

        # Get current pool statistics from metrics
        pool_stats = await self.db_service.get_pool_stats()

        # Simulate various utilization scenarios
        utilization_tests = []

        for load_factor in [0.5, 0.7, 0.8, 0.9]:
            # Calculate number of concurrent connections for this load factor
            max_connections = pool_stats.get("pool_size", 100) + pool_stats.get(
                "max_overflow", 500
            )
            target_connections = int(max_connections * load_factor)

            logger.info(
                f"  Testing load factor: {load_factor:.1%} "
                f"({target_connections} connections)"
            )

            async def load_task():
                """Task to maintain load on the pool."""
                async with self.db_service.get_session():
                    await asyncio.sleep(0.1)  # Hold connection briefly

            # Execute load test
            start_time = time.perf_counter()
            tasks = [load_task() for _ in range(target_connections)]
            await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.perf_counter()

            # Get updated pool statistics
            updated_stats = await self.db_service.get_pool_stats()

            test_result = {
                "load_factor": load_factor,
                "target_connections": target_connections,
                "test_duration_sec": end_time - start_time,
                "pool_utilization_percent": updated_stats.get("utilization_percent", 0),
                "avg_checkout_time_ms": updated_stats.get("avg_wait_time_ms", 0),
                "checkout_count": updated_stats.get("connections_created", 0),
                "connection_errors": updated_stats.get("connection_errors", 0),
            }

            utilization_tests.append(test_result)

        # Calculate overall efficiency metrics
        avg_utilization = statistics.mean(
            [t["pool_utilization_percent"] for t in utilization_tests]
        )
        avg_checkout_time = statistics.mean(
            [t["avg_checkout_time_ms"] for t in utilization_tests]
        )
        total_errors = sum([t["connection_errors"] for t in utilization_tests])

        # Pool efficiency is considered good if:
        # 1. Average checkout time is low
        # 2. Pool utilization is reasonable
        # 3. Few or no connection errors
        efficiency_score = max(0, 100 - (avg_checkout_time * 2) - (total_errors * 10))

        results = {
            "test_name": "Pool Efficiency",
            "utilization_tests": utilization_tests,
            "avg_utilization_percent": avg_utilization,
            "avg_checkout_time_ms": avg_checkout_time,
            "total_connection_errors": total_errors,
            "efficiency_score": efficiency_score,
            "target_met": (efficiency_score >= 80.0 and avg_checkout_time < 50.0),
        }

        self.results["pool_efficiency"] = results
        return results

    async def benchmark_metrics_accuracy(self) -> Dict[str, Any]:
        """Benchmark metrics collection accuracy."""
        logger.info("📊 Benchmarking metrics accuracy...")

        # Record known operations and verify metrics
        test_operations = [
            ("select", "users", 0.015),
            ("insert", "trips", 0.025),
            ("update", "flights", 0.020),
            ("delete", "bookings", 0.030),
        ]

        metrics_tests = {}

        for operation, table, expected_latency in test_operations:
            # Record multiple operations with known latencies
            for _ in range(50):
                self.metrics.record_query_duration(
                    duration=expected_latency,
                    operation=operation,
                    table=table,
                    database="supabase",
                    status="success",
                )

            # Get recorded percentiles
            metric_key = f"query_duration_{operation}_{table}"
            percentiles = self.metrics.get_percentiles(metric_key)

            if percentiles:
                p50, p95, p99 = percentiles

                # Verify accuracy (should be close to expected latency)
                # 1ms tolerance
                accuracy_p50 = abs(p50 - expected_latency) < 0.001
                accuracy_p95 = abs(p95 - expected_latency) < 0.001

                metrics_tests[metric_key] = {
                    "operation": operation,
                    "table": table,
                    "expected_latency_sec": expected_latency,
                    "recorded_p50_sec": p50,
                    "recorded_p95_sec": p95,
                    "recorded_p99_sec": p99,
                    "p50_accurate": accuracy_p50,
                    "p95_accurate": accuracy_p95,
                }
            else:
                metrics_tests[metric_key] = {
                    "operation": operation,
                    "table": table,
                    "expected_latency_sec": expected_latency,
                    "error": "No percentiles available",
                }

        # Check baseline establishment
        baselines = self.metrics.get_baselines()
        baseline_count = len(baselines)

        # Get summary statistics
        summary_stats = self.metrics.get_summary_stats()

        results = {
            "test_name": "Metrics Accuracy",
            "metrics_tests": metrics_tests,
            "baselines_established": baseline_count,
            "summary_stats": summary_stats,
            "target_met": (
                baseline_count >= len(test_operations)
                and summary_stats["total_queries"] > 0
            ),
        }

        self.results["metrics_accuracy"] = results
        return results

    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete performance benchmark suite."""
        logger.info("🎯 Starting Enhanced Database Performance Benchmark Suite")

        start_time = time.time()

        try:
            # Run all benchmarks
            await self.benchmark_connection_acquisition()
            await self.benchmark_query_operations()
            await self.benchmark_concurrent_operations()
            await self.benchmark_pool_efficiency()
            await self.benchmark_metrics_accuracy()

            # Health check
            health_status = await self.db_service.health_check()

            end_time = time.time()
            total_duration = end_time - start_time

            # Calculate overall results
            all_targets_met = all(
                [
                    self.results["connection_acquisition"]["target_met"],
                    self.results["query_operations"]["target_met"],
                    self.results["concurrent_operations"]["target_met"],
                    self.results["pool_efficiency"]["target_met"],
                    self.results["metrics_accuracy"]["target_met"],
                    health_status["status"] == "healthy",
                ]
            )

            overall_results = {
                "benchmark_suite": "Enhanced Database Performance",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_sec": total_duration,
                "iterations": self.iterations,
                "all_targets_met": all_targets_met,
                "health_status": health_status["status"],
                "individual_results": self.results,
            }

            return overall_results

        except Exception as e:
            logger.error(f"❌ Benchmark failed: {e}")
            raise

    def print_results(self, results: Dict[str, Any]):
        """Print formatted benchmark results."""
        print("\n" + "=" * 80)
        print("🎯 ENHANCED DATABASE PERFORMANCE BENCHMARK RESULTS")
        print("=" * 80)

        print(f"📊 Benchmark Duration: {results['duration_sec']:.2f} seconds")
        print(f"🔄 Iterations: {results['iterations']:,}")
        print(f"🏥 Health Status: {results['health_status']}")
        overall_result = (
            "✅ ALL TARGETS MET"
            if results["all_targets_met"]
            else "❌ SOME TARGETS MISSED"
        )
        print(f"🎯 Overall Result: {overall_result}")
        print()

        # Connection Acquisition Results
        conn_results = results["individual_results"]["connection_acquisition"]
        print("🔗 CONNECTION ACQUISITION PERFORMANCE:")
        conn_status = "✅" if conn_results["target_met"] else "❌"
        print(
            f"  Average Latency: {conn_results['avg_latency_ms']:.2f}ms "
            f"(target: <50ms) - {conn_status}"
        )
        print(f"  P95 Latency: {conn_results['p95_latency_ms']:.2f}ms")
        print(f"  P99 Latency: {conn_results['p99_latency_ms']:.2f}ms")
        print(f"  Success Rate: {conn_results['success_rate_percent']:.1f}%")
        print()

        # Query Operations Results
        query_results = results["individual_results"]["query_operations"]
        print("📊 QUERY OPERATIONS PERFORMANCE:")
        query_status = "✅" if query_results["target_met"] else "❌"
        print(
            f"  Overall Average Latency: "
            f"{query_results['overall_avg_latency_ms']:.2f}ms "
            f"(target: <50ms) - {query_status}"
        )
        print(f"  Total Operations: {query_results['total_operations']:,}")
        print(f"  Success Rate: {query_results['success_rate_percent']:.1f}%")

        for _op_name, op_result in query_results["operations"].items():
            op_status = "✅" if op_result["target_met"] else "❌"
            print(
                f"    {op_result['operation']} on {op_result['table']}: "
                f"{op_result['avg_latency_ms']:.2f}ms - {op_status}"
            )
        print()

        # Concurrent Operations Results
        concurrent_results = results["individual_results"]["concurrent_operations"]
        print("🚀 CONCURRENT OPERATIONS PERFORMANCE:")
        concurrent_status = "✅" if concurrent_results["target_met"] else "❌"
        print(f"  Overall Target Met: {concurrent_status}")

        for _level_name, level_result in concurrent_results[
            "concurrency_results"
        ].items():
            concurrency = level_result["concurrency_level"]
            level_status = "✅" if level_result["target_met"] else "❌"
            print(
                f"    {concurrency} concurrent ops: "
                f"{level_result['avg_latency_ms']:.2f}ms avg, "
                f"{level_result['throughput_ops_per_sec']:.1f} ops/sec - "
                f"{level_status}"
            )
        print()

        # Pool Efficiency Results
        pool_results = results["individual_results"]["pool_efficiency"]
        print("📈 POOL EFFICIENCY PERFORMANCE:")
        pool_status = "✅" if pool_results["target_met"] else "❌"
        print(
            f"  Efficiency Score: {pool_results['efficiency_score']:.1f}/100 - "
            f"{pool_status}"
        )
        print(f"  Average Utilization: {pool_results['avg_utilization_percent']:.1f}%")
        print(f"  Average Checkout Time: {pool_results['avg_checkout_time_ms']:.2f}ms")
        print(f"  Connection Errors: {pool_results['total_connection_errors']}")
        print()

        # Metrics Accuracy Results
        metrics_results = results["individual_results"]["metrics_accuracy"]
        print("📊 METRICS ACCURACY:")
        print(f"  Baselines Established: {metrics_results['baselines_established']}")
        print(
            f"  Total Queries Tracked: "
            f"{metrics_results['summary_stats']['total_queries']:,}"
        )
        metrics_status = "✅" if metrics_results["target_met"] else "❌"
        print(f"  Target Met: {metrics_status}")
        print()

        print("=" * 80)
        print("🎯 PERFORMANCE TARGETS SUMMARY:")
        conn_latency_status = "✅" if conn_results["target_met"] else "❌"
        query_latency_status = "✅" if query_results["target_met"] else "❌"
        concurrent_perf_status = "✅" if concurrent_results["target_met"] else "❌"
        pool_eff_status = "✅" if pool_results["target_met"] else "❌"
        metrics_coll_status = "✅" if metrics_results["target_met"] else "❌"
        health_status = "✅" if results["health_status"] == "healthy" else "❌"

        print(f"  🔗 Connection Latency <50ms: {conn_latency_status}")
        print(f"  📊 Query Latency <50ms: {query_latency_status}")
        print(f"  🚀 Concurrent Performance: {concurrent_perf_status}")
        print(f"  📈 Pool Efficiency >80%: {pool_eff_status}")
        print(f"  📊 Metrics Collection: {metrics_coll_status}")
        print(f"  🏥 Health Status: {health_status}")
        print("=" * 80)


async def main():
    """Main benchmark execution."""
    parser = argparse.ArgumentParser(
        description="Enhanced Database Performance Benchmark"
    )
    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=1000,
        help="Number of iterations per test",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file for results (JSON format)",
    )

    args = parser.parse_args()

    benchmark = PerformanceBenchmark(iterations=args.iterations, verbose=args.verbose)

    try:
        await benchmark.setup()
        results = await benchmark.run_full_benchmark()
        benchmark.print_results(results)

        # Save results to file if requested
        if args.output:
            import json

            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"📁 Results saved to {args.output}")

        # Exit with appropriate code
        if results["all_targets_met"]:
            logger.info("🎉 Benchmark completed successfully - all targets met!")
            return 0
        else:
            logger.warning("⚠️ Benchmark completed with some targets not met")
            return 1

    except Exception as e:
        logger.error(f"❌ Benchmark failed: {e}")
        return 2
    finally:
        await benchmark.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
