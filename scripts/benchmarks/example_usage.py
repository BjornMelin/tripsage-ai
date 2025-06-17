"""
Example usage scripts for TripSage PGVector Performance Benchmark Suite.

This module demonstrates various ways to use the benchmark framework
for different scenarios and use cases.
"""

import asyncio
import logging
from pathlib import Path

from pgvector_benchmark import BenchmarkConfig, PGVectorBenchmark, run_benchmark
from regression_detector import BaselineManager, RegressionDetector


async def example_basic_benchmark():
    """Example: Basic benchmark execution."""
    print("🚀 Running basic benchmark...")

    # Run with default settings
    results = await run_benchmark(
        output_dir="./example_results",
        quick_test=True,  # Use quick mode for demonstration
        verbose=True,
    )

    print(f"✅ Benchmark completed in {results.total_duration_seconds:.1f} seconds")

    # Print key results
    if results.optimized_query_metrics:
        best_metric = min(
            results.optimized_query_metrics, key=lambda x: x.avg_latency_ms
        )
        print("🎯 Best performance:")
        print(f"   - Latency: {best_metric.avg_latency_ms:.2f}ms")
        print(f"   - Throughput: {best_metric.queries_per_second:.1f} QPS")
        print(f"   - Success rate: {best_metric.success_rate:.1%}")

    # Performance improvements
    improvements = results.performance_improvements
    if improvements:
        print("📈 Performance improvements:")
        for metric, value in improvements.items():
            print(f"   - {metric.replace('_', ' ').title()}: {value:.2f}x")

    return results


async def example_custom_benchmark():
    """Example: Custom benchmark configuration."""
    print("🔧 Running custom benchmark...")

    # Create custom configuration
    config = BenchmarkConfig(
        # Focus on speed optimization
        small_dataset_size=500,
        medium_dataset_size=2000,
        large_dataset_size=5000,
        # Test specific ef_search values
        ef_search_values=[40, 100],
        # Stricter performance targets
        target_query_latency_ms=5.0,
        target_performance_improvement_x=40.0,
        # Custom output location
        output_directory="./custom_results",
    )

    # Run benchmark with custom config
    benchmark = PGVectorBenchmark(config)
    results = await benchmark.run_full_benchmark()

    print("✅ Custom benchmark completed")
    print("🎯 Validation results:")
    for test, passed in results.validation_results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {test.replace('_', ' ').title()}")

    return results


def example_baseline_management():
    """Example: Managing performance baselines."""
    print("📊 Managing performance baselines...")

    # Initialize baseline manager
    manager = BaselineManager("./example_baselines")

    # Save a performance baseline
    performance_data = {
        "avg_latency_ms": 6.8,
        "p95_latency_ms": 11.2,
        "queries_per_second": 147.3,
        "memory_usage_mb": 334.5,
        "success_rate": 1.0,
        "index_creation_time_s": 12.5,
    }

    manager.save_baseline("example_test", performance_data, "v2.1.0")
    print("✅ Baseline saved")

    # Load the latest baseline
    baseline = manager.get_latest_baseline("example_test")
    if baseline:
        print(f"📋 Latest baseline (v{baseline.test_version}):")
        print(f"   - Latency: {baseline.avg_latency_ms:.2f}ms")
        print(f"   - Throughput: {baseline.queries_per_second:.1f} QPS")
        print(f"   - Memory: {baseline.memory_usage_mb:.1f} MB")

    # Get historical baselines
    historical = manager.get_historical_baselines("example_test", days_back=30)
    print(f"📈 Found {len(historical)} historical baselines")

    return manager


def example_regression_detection():
    """Example: Detecting performance regressions."""
    print("🔍 Detecting performance regressions...")

    # Setup baseline manager with test data
    manager = BaselineManager("./example_baselines")

    # Save a good baseline
    baseline_data = {
        "avg_latency_ms": 8.0,
        "p95_latency_ms": 12.0,
        "queries_per_second": 125.0,
        "memory_usage_mb": 400.0,
        "success_rate": 1.0,
    }
    manager.save_baseline("regression_test", baseline_data, "baseline")

    # Create regression detector
    detector = RegressionDetector(manager)

    # Test 1: No regression (performance is similar)
    current_results_good = {
        "avg_latency_ms": 7.8,  # Slightly better
        "queries_per_second": 128.0,  # Slightly better
        "memory_usage_mb": 395.0,  # Slightly better
        "success_rate": 1.0,
    }

    analysis = detector.analyze_performance("regression_test", current_results_good)
    print("📊 Test 1 - Good performance:")
    print(f"   Status: {'✅ PASS' if not analysis.overall_regression else '❌ FAIL'}")
    print(f"   Severity: {analysis.severity}")

    # Test 2: Latency regression
    current_results_bad = {
        "avg_latency_ms": 15.0,  # Much worse (87% increase)
        "queries_per_second": 120.0,  # Slightly worse
        "memory_usage_mb": 410.0,  # Slightly worse
        "success_rate": 1.0,
    }

    analysis = detector.analyze_performance("regression_test", current_results_bad)
    print("📊 Test 2 - Latency regression:")
    print(f"   Status: {'✅ PASS' if not analysis.overall_regression else '❌ FAIL'}")
    print(f"   Severity: {analysis.severity}")
    print(f"   Latency change: {analysis.latency_change_pct:+.1f}%")

    if analysis.recommendations:
        print("   Recommendations:")
        for rec in analysis.recommendations[:2]:  # Show first 2
            print(f"     - {rec}")

    return detector


async def example_development_workflow():
    """Example: Development workflow with performance validation."""
    print("🔄 Development workflow example...")

    # Step 1: Run quick benchmark for current changes
    print("1️⃣ Running quick benchmark for current changes...")
    results = await run_benchmark(
        output_dir="./dev_results", quick_test=True, verbose=False
    )

    # Step 2: Check against baseline (if exists)
    print("2️⃣ Checking for performance regressions...")
    manager = BaselineManager("./dev_baselines")
    detector = RegressionDetector(manager)

    # Extract results for analysis
    if results.optimized_query_metrics:
        current_perf = results.optimized_query_metrics[0]  # Use first optimized metric
        current_data = {
            "avg_latency_ms": current_perf.avg_latency_ms,
            "queries_per_second": current_perf.queries_per_second,
            "memory_usage_mb": current_perf.memory_usage_mb,
            "success_rate": current_perf.success_rate,
        }

        analysis = detector.analyze_performance("dev_test", current_data)

        if analysis.overall_regression:
            print("   ❌ Performance regression detected!")
            print(f"   Severity: {analysis.severity}")
            if analysis.recommendations:
                print(f"   Action needed: {analysis.recommendations[0]}")
        else:
            print("   ✅ No performance regression detected")

        # Step 3: Update baseline if performance is good
        if not analysis.overall_regression:
            print("3️⃣ Updating development baseline...")
            manager.save_baseline("dev_test", current_data, "latest")
            print("   ✅ Baseline updated")

    return results


def example_ci_simulation():
    """Example: Simulate CI/CD performance validation."""
    print("🤖 Simulating CI/CD performance validation...")

    # This would typically be run in CI/CD pipeline
    import sys

    try:
        # Simulate CI command execution
        print("1️⃣ Running CI performance check...")

        # In real CI, this would be:
        # python ci_performance_check.py full-pipeline --git-commit $COMMIT_SHA --quick

        # For example, we'll just show the command structure
        ci_command = [
            sys.executable,
            "ci_performance_check.py",
            "full-pipeline",
            "--git-commit",
            "example-commit-123",
            "--quick",
            "--output-dir",
            "./ci_example_results",
        ]

        print(f"   Command: {' '.join(ci_command)}")
        print("   (Note: This is a simulation - actual CI integration would run this)")

        # Simulate CI status
        print("2️⃣ CI Performance Validation Results:")
        print("   ✅ Benchmark execution: PASSED")
        print("   ✅ Performance targets: MET")
        print("   ✅ Regression check: PASSED")
        print("   📊 Artifacts generated: YES")

        print("3️⃣ CI pipeline would continue with deployment...")

    except Exception as e:
        print(f"   ❌ CI simulation failed: {e}")
        return False

    return True


async def main():
    """Run all example scenarios."""
    print("🎯 TripSage PGVector Benchmark Examples")
    print("=" * 50)

    # Configure logging for examples
    logging.basicConfig(level=logging.WARNING)  # Reduce noise for examples

    try:
        # Basic benchmark
        await example_basic_benchmark()
        print()

        # Custom benchmark
        await example_custom_benchmark()
        print()

        # Baseline management
        example_baseline_management()
        print()

        # Regression detection
        example_regression_detection()
        print()

        # Development workflow
        await example_development_workflow()
        print()

        # CI simulation
        example_ci_simulation()
        print()

        print("✅ All examples completed successfully!")
        print("\n📚 Next steps:")
        print("   - Review generated reports in example_results/")
        print("   - Integrate with your CI/CD pipeline")
        print("   - Set up regular performance monitoring")
        print("   - Customize thresholds for your requirements")

    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Create output directories
    for directory in [
        "./example_results",
        "./custom_results",
        "./dev_results",
        "./ci_example_results",
    ]:
        Path(directory).mkdir(exist_ok=True)

    # Run examples
    asyncio.run(main())
