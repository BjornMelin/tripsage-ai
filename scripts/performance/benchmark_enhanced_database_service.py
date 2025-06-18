#!/usr/bin/env python3
"""
Performance benchmark script for Enhanced Database Service.

This script validates the performance improvements of the enhanced database service
with LIFO connection pooling and comprehensive monitoring.

Features tested:
- LIFO vs FIFO connection pool performance
- Query latency percentiles under load
- Connection pool utilization efficiency
- Performance regression detection accuracy
- Resource utilization optimization
- Concurrent operation throughput
"""

import asyncio
import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json

from tripsage_core.services.infrastructure.enhanced_database_service_with_monitoring import (
    EnhancedDatabaseService,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark."""
    
    test_name: str
    service_type: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    total_duration_seconds: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    operations_per_second: float
    error_rate_percent: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    additional_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "service_type": self.service_type,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "total_duration_seconds": self.total_duration_seconds,
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "operations_per_second": self.operations_per_second,
            "error_rate_percent": self.error_rate_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "cpu_usage_percent": self.cpu_usage_percent,
            "additional_metrics": self.additional_metrics,
        }


class DatabaseServiceBenchmark:
    """Performance benchmark for database services."""
    
    def __init__(self, settings=None):
        """Initialize benchmark."""
        self.settings = settings or get_settings()
        self.results: List[BenchmarkResult] = []
    
    async def run_all_benchmarks(self) -> List[BenchmarkResult]:
        """Run all performance benchmarks."""
        logger.info("Starting comprehensive database service benchmarks")
        
        # Test configurations
        test_configs = [
            {"name": "light_load", "concurrent_ops": 5, "operations_per_worker": 50},
            {"name": "medium_load", "concurrent_ops": 10, "operations_per_worker": 100},
            {"name": "heavy_load", "concurrent_ops": 20, "operations_per_worker": 150},
        ]
        
        for config in test_configs:
            logger.info(f"Running benchmark: {config['name']}")
            
            # Test enhanced service with LIFO
            enhanced_result = await self._benchmark_service(
                service_type="enhanced_lifo",
                test_name=config["name"],
                concurrent_operations=config["concurrent_ops"],
                operations_per_worker=config["operations_per_worker"],
                use_enhanced=True,
                lifo_enabled=True,
            )
            self.results.append(enhanced_result)
            
            # Test enhanced service with FIFO for comparison
            enhanced_fifo_result = await self._benchmark_service(
                service_type="enhanced_fifo",
                test_name=config["name"],
                concurrent_operations=config["concurrent_ops"],
                operations_per_worker=config["operations_per_worker"],
                use_enhanced=True,
                lifo_enabled=False,
            )
            self.results.append(enhanced_fifo_result)
            
            # Test original service for baseline
            original_result = await self._benchmark_service(
                service_type="original",
                test_name=config["name"],
                concurrent_operations=config["concurrent_ops"],
                operations_per_worker=config["operations_per_worker"],
                use_enhanced=False,
            )
            self.results.append(original_result)
        
        # Run specialized tests
        await self._benchmark_lifo_vs_fifo()
        await self._benchmark_connection_validation()
        await self._benchmark_regression_detection()
        
        return self.results
    
    async def _benchmark_service(
        self,
        service_type: str,
        test_name: str,
        concurrent_operations: int,
        operations_per_worker: int,
        use_enhanced: bool,
        lifo_enabled: bool = True,
    ) -> BenchmarkResult:
        """Benchmark a specific service configuration."""
        logger.info(f"Benchmarking {service_type} service with {concurrent_operations} concurrent operations")
        
        # Create service
        if use_enhanced:
            service = EnhancedDatabaseService(
                settings=self.settings,
                pool_size=max(10, concurrent_operations),
                max_overflow=concurrent_operations * 2,
                lifo_enabled=lifo_enabled,
                enable_regression_detection=True,
            )
        else:
            service = DatabaseService(self.settings)
        
        try:
            await service.connect()
            
            # Warm up the service
            await self._warmup_service(service, 10)
            
            # Run benchmark
            start_time = time.perf_counter()
            latencies, successes, failures = await self._run_concurrent_operations(
                service, concurrent_operations, operations_per_worker
            )
            end_time = time.perf_counter()
            
            # Calculate metrics
            total_duration = end_time - start_time
            total_operations = len(latencies) + failures
            successful_operations = len(latencies)
            
            if latencies:
                latencies_ms = [l * 1000 for l in latencies]  # Convert to ms
                latencies_ms.sort()
                
                avg_latency = statistics.mean(latencies_ms)
                p50_latency = latencies_ms[int(len(latencies_ms) * 0.5)]
                p95_latency = latencies_ms[int(len(latencies_ms) * 0.95)]
                p99_latency = latencies_ms[int(len(latencies_ms) * 0.99)]
            else:
                avg_latency = p50_latency = p95_latency = p99_latency = 0.0
            
            operations_per_second = total_operations / total_duration if total_duration > 0 else 0
            error_rate = (failures / total_operations * 100) if total_operations > 0 else 0
            
            # Get additional metrics for enhanced service
            additional_metrics = {}
            if use_enhanced and hasattr(service, 'get_performance_metrics'):
                performance_metrics = service.get_performance_metrics()
                if "pool" in performance_metrics:
                    pool_stats = performance_metrics["pool"]["statistics"]
                    additional_metrics.update({
                        "pool_utilization": pool_stats.get("pool_utilization", 0),
                        "avg_checkout_time": pool_stats.get("avg_checkout_time", 0),
                        "peak_active_connections": pool_stats.get("peak_active", 0),
                    })
            
            result = BenchmarkResult(
                test_name=test_name,
                service_type=service_type,
                total_operations=total_operations,
                successful_operations=successful_operations,
                failed_operations=failures,
                total_duration_seconds=total_duration,
                avg_latency_ms=avg_latency,
                p50_latency_ms=p50_latency,
                p95_latency_ms=p95_latency,
                p99_latency_ms=p99_latency,
                operations_per_second=operations_per_second,
                error_rate_percent=error_rate,
                additional_metrics=additional_metrics,
            )
            
            logger.info(f"Completed {service_type} benchmark: {operations_per_second:.2f} ops/sec, "
                       f"P95: {p95_latency:.2f}ms, Error rate: {error_rate:.2f}%")
            
            return result
            
        finally:
            await service.close()
    
    async def _warmup_service(self, service, num_operations: int):
        """Warm up the service with some operations."""
        logger.debug(f"Warming up service with {num_operations} operations")
        
        for _ in range(num_operations):
            try:
                await service.select("users", columns="id", limit=1)
            except Exception:
                pass  # Ignore warmup errors
    
    async def _run_concurrent_operations(
        self, service, concurrent_operations: int, operations_per_worker: int
    ) -> tuple[List[float], int, int]:
        """Run concurrent database operations."""
        
        async def worker(worker_id: int) -> tuple[List[float], int, int]:
            """Worker function to perform database operations."""
            latencies = []
            successes = 0
            failures = 0
            
            for i in range(operations_per_worker):
                start_time = time.perf_counter()
                
                try:
                    # Mix different types of operations
                    operation_type = i % 4
                    
                    if operation_type == 0:
                        await service.select("users", columns="id,name", limit=10)
                    elif operation_type == 1:
                        await service.count("users")
                    elif operation_type == 2:
                        await service.select("posts", columns="id,title", limit=5)
                    else:
                        await service.select("users", filters={"active": True}, limit=3)
                    
                    latency = time.perf_counter() - start_time
                    latencies.append(latency)
                    successes += 1
                    
                except Exception as e:
                    logger.debug(f"Worker {worker_id} operation {i} failed: {e}")
                    failures += 1
            
            return latencies, successes, failures
        
        # Run workers concurrently
        tasks = [worker(i) for i in range(concurrent_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        all_latencies = []
        total_successes = 0
        total_failures = 0
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Worker failed: {result}")
                total_failures += operations_per_worker
            else:
                latencies, successes, failures = result
                all_latencies.extend(latencies)
                total_successes += successes
                total_failures += failures
        
        return all_latencies, total_successes, total_failures
    
    async def _benchmark_lifo_vs_fifo(self):
        """Benchmark LIFO vs FIFO connection pool behavior."""
        logger.info("Benchmarking LIFO vs FIFO connection pool behavior")
        
        test_config = {"concurrent_ops": 15, "operations_per_worker": 100}
        
        # Test LIFO
        lifo_result = await self._benchmark_service(
            service_type="lifo_comparison",
            test_name="lifo_vs_fifo",
            concurrent_operations=test_config["concurrent_ops"],
            operations_per_worker=test_config["operations_per_worker"],
            use_enhanced=True,
            lifo_enabled=True,
        )
        
        # Test FIFO
        fifo_result = await self._benchmark_service(
            service_type="fifo_comparison",
            test_name="lifo_vs_fifo",
            concurrent_operations=test_config["concurrent_ops"],
            operations_per_worker=test_config["operations_per_worker"],
            use_enhanced=True,
            lifo_enabled=False,
        )
        
        # Calculate improvement
        if fifo_result.p95_latency_ms > 0:
            latency_improvement = ((fifo_result.p95_latency_ms - lifo_result.p95_latency_ms) 
                                 / fifo_result.p95_latency_ms * 100)
            logger.info(f"LIFO vs FIFO P95 latency improvement: {latency_improvement:.2f}%")
        
        self.results.extend([lifo_result, fifo_result])
    
    async def _benchmark_connection_validation(self):
        """Benchmark connection validation overhead."""
        logger.info("Benchmarking connection validation overhead")
        
        # Test with validation enabled
        with_validation = await self._benchmark_service(
            service_type="with_validation",
            test_name="connection_validation",
            concurrent_operations=10,
            operations_per_worker=50,
            use_enhanced=True,
            lifo_enabled=True,
        )
        
        # Note: Would need to modify service to disable validation for fair comparison
        # For now, we just record the validation enabled result
        self.results.append(with_validation)
    
    async def _benchmark_regression_detection(self):
        """Benchmark performance regression detection overhead."""
        logger.info("Benchmarking regression detection overhead")
        
        # Create service with regression detection
        service = EnhancedDatabaseService(
            settings=self.settings,
            pool_size=10,
            enable_regression_detection=True,
        )
        
        try:
            await service.connect()
            
            # Record baseline performance
            logger.info("Establishing baseline performance")
            for _ in range(100):
                await service.select("users", columns="id", limit=1)
            
            # Get regression detection metrics
            metrics = service.get_performance_metrics()
            if "regression_detection" in metrics:
                regression_metrics = metrics["regression_detection"]
                logger.info(f"Regression detection tracked metrics: {regression_metrics.get('tracked_metrics', 0)}")
            
            # Test alert generation with slow query simulation
            # (In real scenario, this would be a genuinely slow query)
            start_time = time.perf_counter()
            await service.select("users", columns="id", limit=1)
            end_time = time.perf_counter()
            
            # Check for any performance alerts
            alerts = service.get_recent_performance_alerts(limit=5)
            logger.info(f"Recent performance alerts: {len(alerts)}")
            
        finally:
            await service.close()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive benchmark report."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "test_configurations": list(set(r.test_name for r in self.results)),
                "service_types": list(set(r.service_type for r in self.results)),
            },
            "results": [result.to_dict() for result in self.results],
            "analysis": self._analyze_results(),
        }
        
        return report
    
    def _analyze_results(self) -> Dict:
        """Analyze benchmark results for insights."""
        analysis = {
            "performance_comparison": {},
            "recommendations": [],
        }
        
        # Group results by test name
        by_test = {}
        for result in self.results:
            if result.test_name not in by_test:
                by_test[result.test_name] = []
            by_test[result.test_name].append(result)
        
        # Compare enhanced vs original performance
        for test_name, results in by_test.items():
            enhanced_lifo = next((r for r in results if r.service_type == "enhanced_lifo"), None)
            enhanced_fifo = next((r for r in results if r.service_type == "enhanced_fifo"), None)
            original = next((r for r in results if r.service_type == "original"), None)
            
            if enhanced_lifo and original:
                throughput_improvement = ((enhanced_lifo.operations_per_second - original.operations_per_second) 
                                        / original.operations_per_second * 100)
                latency_improvement = ((original.p95_latency_ms - enhanced_lifo.p95_latency_ms) 
                                     / original.p95_latency_ms * 100)
                
                analysis["performance_comparison"][test_name] = {
                    "throughput_improvement_percent": throughput_improvement,
                    "p95_latency_improvement_percent": latency_improvement,
                    "enhanced_ops_per_sec": enhanced_lifo.operations_per_second,
                    "original_ops_per_sec": original.operations_per_second,
                    "enhanced_p95_ms": enhanced_lifo.p95_latency_ms,
                    "original_p95_ms": original.p95_latency_ms,
                }
            
            if enhanced_lifo and enhanced_fifo:
                lifo_vs_fifo_latency = ((enhanced_fifo.p95_latency_ms - enhanced_lifo.p95_latency_ms) 
                                       / enhanced_fifo.p95_latency_ms * 100)
                analysis["performance_comparison"][f"{test_name}_lifo_vs_fifo"] = {
                    "lifo_p95_latency_improvement_percent": lifo_vs_fifo_latency,
                    "lifo_p95_ms": enhanced_lifo.p95_latency_ms,
                    "fifo_p95_ms": enhanced_fifo.p95_latency_ms,
                }
        
        # Generate recommendations
        avg_improvements = []
        for test_data in analysis["performance_comparison"].values():
            if "throughput_improvement_percent" in test_data:
                avg_improvements.append(test_data["throughput_improvement_percent"])
        
        if avg_improvements:
            avg_improvement = statistics.mean(avg_improvements)
            if avg_improvement > 10:
                analysis["recommendations"].append(
                    f"Enhanced database service shows significant performance improvement "
                    f"({avg_improvement:.1f}% average throughput increase)"
                )
            elif avg_improvement > 0:
                analysis["recommendations"].append(
                    f"Enhanced database service shows modest performance improvement "
                    f"({avg_improvement:.1f}% average throughput increase)"
                )
        
        return analysis
    
    def print_summary(self):
        """Print benchmark summary to console."""
        print("\n" + "="*80)
        print("DATABASE SERVICE PERFORMANCE BENCHMARK SUMMARY")
        print("="*80)
        
        # Group by test name for comparison
        by_test = {}
        for result in self.results:
            if result.test_name not in by_test:
                by_test[result.test_name] = []
            by_test[result.test_name].append(result)
        
        for test_name, results in by_test.items():
            print(f"\n{test_name.upper()} TEST RESULTS:")
            print("-" * 50)
            
            for result in results:
                print(f"  {result.service_type}:")
                print(f"    Throughput: {result.operations_per_second:.2f} ops/sec")
                print(f"    P95 Latency: {result.p95_latency_ms:.2f}ms")
                print(f"    Error Rate: {result.error_rate_percent:.2f}%")
                if result.additional_metrics:
                    for key, value in result.additional_metrics.items():
                        print(f"    {key}: {value:.2f}")
                print()


async def main():
    """Run the benchmark suite."""
    print("Starting Enhanced Database Service Performance Benchmark")
    print("="*60)
    
    # Create benchmark instance
    benchmark = DatabaseServiceBenchmark()
    
    try:
        # Run all benchmarks
        results = await benchmark.run_all_benchmarks()
        
        # Generate and save report
        report = benchmark.generate_report()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"benchmark_report_{timestamp}.json"
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nBenchmark completed. Report saved to: {report_file}")
        
        # Print summary
        benchmark.print_summary()
        
        # Print analysis
        analysis = report["analysis"]
        if analysis["performance_comparison"]:
            print("\nPERFORMANCE ANALYSIS:")
            print("-" * 30)
            for test, data in analysis["performance_comparison"].items():
                if "throughput_improvement_percent" in data:
                    print(f"{test}: {data['throughput_improvement_percent']:.1f}% throughput improvement")
        
        if analysis["recommendations"]:
            print("\nRECOMMENDATIONS:")
            print("-" * 20)
            for rec in analysis["recommendations"]:
                print(f"• {rec}")
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())