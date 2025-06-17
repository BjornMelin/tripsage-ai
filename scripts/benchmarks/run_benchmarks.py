#!/usr/bin/env python3
"""
Performance Benchmark Execution Script for TripSage Database Optimizations.

This script provides a complete example of running the performance benchmarking
suite to validate database optimization improvements. It demonstrates:

1. Complete benchmark suite execution (baseline vs optimized)
2. Validation of performance claims (3x query, 30x vector, 50% memory)
3. Report generation with visualizations
4. CI/CD integration examples

Usage:
    python run_benchmarks.py --mode comparison --output-dir ./results
    python run_benchmarks.py --mode validate --claims
    python run_benchmarks.py --mode custom --scenario read_heavy --duration 600
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import click
from benchmark_runner import BenchmarkRunner
from benchmark_runner import cli as benchmark_cli
from config import (
    BenchmarkConfig,
    OptimizationLevel,
    PerformanceThresholds,
    WorkloadType,
)

logger = logging.getLogger(__name__)


async def run_complete_validation_suite(
    output_dir: Path, verbose: bool = False
) -> Dict[str, Any]:
    """
    Run the complete validation suite to verify all optimization claims.

    This is the main function for validating the database performance
    optimization framework against the claimed improvements:
    - 3x general query performance improvement
    - 30x pgvector performance improvement
    - 50% memory reduction
    - Improved connection pool efficiency
    - High cache hit ratios

    Args:
        output_dir: Directory for benchmark results and reports
        verbose: Enable verbose logging

    Returns:
        Complete validation results
    """
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    logger.info("🚀 Starting complete performance validation suite...")
    logger.info(f"📁 Output directory: {output_dir}")

    # Create enhanced configuration for comprehensive testing
    config = BenchmarkConfig(
        # Increase test duration for more reliable results
        test_duration_seconds=600,  # 10 minutes per scenario
        benchmark_iterations=2000,
        concurrent_connections=20,
        # Larger dataset for realistic performance testing
        test_data_size=25000,
        # Enable all monitoring
        enable_detailed_metrics=True,
        enable_memory_profiling=True,
        # Test all optimization levels
        optimization_levels=[
            OptimizationLevel.NONE,
            OptimizationLevel.BASIC,
            OptimizationLevel.ADVANCED,
            OptimizationLevel.FULL,
        ],
        # Comprehensive workload coverage
        workload_types=[
            WorkloadType.READ_HEAVY,
            WorkloadType.VECTOR_SEARCH,
            WorkloadType.MIXED,
        ],
        # Enable geographic distribution testing
        simulate_geographic_distribution=True,
        # Enhanced reporting
        generate_html_report=True,
        generate_csv_export=True,
        include_visualizations=True,
        # Strict performance thresholds
        performance_thresholds=PerformanceThresholds(
            query_performance_improvement=3.0,  # Claimed 3x improvement
            vector_performance_improvement=30.0,  # Claimed 30x improvement
            memory_reduction_target=0.5,  # Claimed 50% reduction
            connection_pool_efficiency=0.85,
            cache_hit_ratio_target=0.80,
        ),
    )

    # Initialize benchmark runner
    runner = BenchmarkRunner(config, output_dir)

    try:
        # Phase 1: Complete comparison benchmarks
        logger.info("📊 Phase 1: Running complete comparison benchmarks...")
        comparison_results = await runner.run_comparison_benchmarks()

        logger.info("✅ Comparison benchmarks completed")
        logger.info(
            f"📈 Report generated: {comparison_results.get('report_path', 'N/A')}"
        )

        # Phase 2: High-concurrency testing
        logger.info("🔄 Phase 2: Running high-concurrency benchmarks...")
        concurrency_results = await runner.run_high_concurrency_benchmarks()

        logger.info("✅ High-concurrency benchmarks completed")
        logger.info(
            f"📈 Report generated: {concurrency_results.get('report_path', 'N/A')}"
        )

        # Phase 3: Optimization claims validation
        logger.info("🎯 Phase 3: Validating optimization claims...")
        validation_results = await runner.validate_optimization_claims()

        # Phase 4: Generate comprehensive summary
        logger.info("📋 Phase 4: Generating comprehensive summary...")
        summary = runner.get_benchmark_summary()

        # Compile final results
        final_results = {
            "validation_suite_version": "1.0.0",
            "execution_timestamp": time.time(),
            "configuration": config.model_dump(),
            "results": {
                "comparison": comparison_results,
                "high_concurrency": concurrency_results,
                "validation": validation_results,
                "summary": summary,
            },
            "success": validation_results.get("overall_success", False),
            "reports": {
                "comparison_report": comparison_results.get("report_path"),
                "concurrency_report": concurrency_results.get("report_path"),
                "validation_report": validation_results.get("validation_report_path"),
                "csv_export": comparison_results.get("csv_export_path"),
            },
        }

        # Save comprehensive results
        results_file = output_dir / "complete_validation_results.json"
        with open(results_file, "w") as f:
            json.dump(final_results, f, indent=2, default=str)

        # Print validation summary
        print_validation_summary(validation_results, summary)

        logger.info(
            f"🎉 Complete validation suite finished! Results saved to: {results_file}"
        )
        return final_results

    except Exception as e:
        logger.error(f"❌ Validation suite failed: {e}")
        raise


def print_validation_summary(
    validation_results: Dict[str, Any], summary: Dict[str, Any]
) -> None:
    """Print a formatted summary of validation results."""

    print("\n" + "=" * 80)
    print("🎯 PERFORMANCE OPTIMIZATION VALIDATION SUMMARY")
    print("=" * 80)

    # Overall status
    overall_success = validation_results.get("overall_success", False)
    status_emoji = "✅" if overall_success else "❌"
    print(
        f"\n{status_emoji} OVERALL VALIDATION: "
        f"{'PASSED' if overall_success else 'FAILED'}"
    )

    # Claims validation
    claims = validation_results.get("claims_validation", {})
    if claims:
        print("\n📊 OPTIMIZATION CLAIMS VALIDATION:")
        for _claim_name, claim_data in claims.items():
            target_met = claim_data.get("target_met", False)
            emoji = "✅" if target_met else "❌"
            claimed = claim_data.get("claimed_improvement", "Unknown")
            measured = claim_data.get("measured_improvement", 0)

            if isinstance(measured, (int, float)) and measured > 0:
                if "3x" in claimed or "30x" in claimed:
                    print(f"   {emoji} {claimed}: {measured:.1f}x improvement measured")
                elif "50%" in claimed:
                    print(f"   {emoji} {claimed}: {measured:.1%} reduction measured")
                else:
                    print(f"   {emoji} {claimed}: {measured:.1%} efficiency")
            else:
                print(f"   {emoji} {claimed}: Could not measure")

    # Performance improvements
    improvements = summary.get("performance_improvements", {})
    if improvements:
        print("\n📈 KEY PERFORMANCE METRICS:")

        # Query latency improvements
        if "query_latency" in improvements:
            latency = improvements["query_latency"]
            baseline_ms = latency.get("baseline_p95_ms", 0)
            optimized_ms = latency.get("optimized_p95_ms", 0)
            improvement_ratio = latency.get("improvement_ratio", 0)

            print(
                f"   🚀 Query Latency (P95): {baseline_ms:.1f}ms → "
                f"{optimized_ms:.1f}ms ({improvement_ratio:.1f}x faster)"
            )

        # Throughput improvements
        if "throughput" in improvements:
            throughput = improvements["throughput"]
            baseline_ops = throughput.get("baseline_ops_per_second", 0)
            optimized_ops = throughput.get("optimized_ops_per_second", 0)
            improvement_ratio = throughput.get("improvement_ratio", 0)

            print(
                f"   ⚡ Throughput: {baseline_ops:.0f} ops/sec → "
                f"{optimized_ops:.0f} ops/sec ({improvement_ratio:.1f}x faster)"
            )

    # Execution summary
    exec_summary = summary.get("execution_summary", {})
    if exec_summary:
        total_time = exec_summary.get("total_execution_time", 0)
        total_scenarios = exec_summary.get("total_scenarios", 0)
        successful_scenarios = exec_summary.get("successful_scenarios", 0)

        print("\n📋 EXECUTION SUMMARY:")
        print(f"   ⏱️  Total execution time: {total_time:.1f} seconds")
        print(f"   📊 Scenarios executed: {successful_scenarios}/{total_scenarios}")

    # Recommendations
    recommendations = validation_results.get("recommendations", [])
    if recommendations:
        print("\n💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"   • {rec}")

    print("\n" + "=" * 80)


@click.group()
def main():
    """TripSage Database Performance Benchmarking Suite."""
    pass


@main.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./benchmark_results",
    help="Output directory for results",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--timeout",
    "-t",
    type=int,
    default=3600,
    help="Total timeout in seconds (default: 1 hour)",
)
def full_validation(output_dir: str, verbose: bool, timeout: int):
    """
    Run the complete validation suite to verify all optimization claims.

    This command runs comprehensive benchmarks to validate:
    - 3x general query performance improvement
    - 30x pgvector performance improvement
    - 50% memory reduction
    - Connection pool efficiency improvements
    - Cache effectiveness improvements
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    async def run_with_timeout():
        try:
            results = await asyncio.wait_for(
                run_complete_validation_suite(output_path, verbose), timeout=timeout
            )
            return results
        except asyncio.TimeoutError:
            click.echo(f"❌ Validation suite timed out after {timeout} seconds")
            sys.exit(1)

    try:
        results = asyncio.run(run_with_timeout())

        if results["success"]:
            click.echo("🎉 All optimization claims validated successfully!")
            sys.exit(0)
        else:
            click.echo(
                "⚠️  Some optimization claims were not met. Check the reports for "
                "details."
            )
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Validation suite failed: {e}")
        sys.exit(1)


@main.command()
@click.option(
    "--scenario",
    type=click.Choice(["read_heavy", "vector_search", "mixed"]),
    required=True,
    help="Workload scenario to run",
)
@click.option(
    "--optimization",
    type=click.Choice(["none", "basic", "advanced", "full"]),
    default="full",
    help="Optimization level",
)
@click.option("--duration", type=int, default=300, help="Test duration in seconds")
@click.option("--users", type=int, default=10, help="Concurrent users")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./benchmark_results",
    help="Output directory",
)
def quick_test(
    scenario: str, optimization: str, duration: int, users: int, output_dir: str
):
    """
    Run a quick performance test for a specific scenario.

    Useful for rapid testing during development or CI/CD pipelines.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config = BenchmarkConfig(
        test_duration_seconds=duration,
        concurrent_connections=users,
        generate_html_report=True,
    )

    runner = BenchmarkRunner(config, output_path)

    async def run_test():
        try:
            results = await runner.run_custom_scenario(
                scenario_name=f"quick_test_{scenario}",
                workload_type=WorkloadType(scenario),
                optimization_level=OptimizationLevel(optimization),
                duration_seconds=duration,
                concurrent_users=users,
                operations_per_user=100,
            )

            click.echo("✅ Quick test completed!")
            click.echo(f"📈 Report: {results.get('report_path', 'N/A')}")

        except Exception as e:
            click.echo(f"❌ Quick test failed: {e}")
            sys.exit(1)

    asyncio.run(run_test())


@main.command()
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help="Custom configuration file",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./benchmark_results",
    help="Output directory",
)
def ci_validation(config_file: Optional[str], output_dir: str):
    """
    Run benchmarks suitable for CI/CD pipeline validation.

    This runs a streamlined version of the benchmarks optimized for CI environments:
    - Shorter test duration
    - Focused on critical performance metrics
    - Machine-readable output
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # CI-optimized configuration
    config = BenchmarkConfig(
        test_duration_seconds=120,  # 2 minutes per scenario
        benchmark_iterations=500,
        concurrent_connections=5,
        test_data_size=5000,
        # Focus on critical metrics
        workload_types=[WorkloadType.READ_HEAVY, WorkloadType.VECTOR_SEARCH],
        optimization_levels=[OptimizationLevel.NONE, OptimizationLevel.FULL],
        # Minimal reporting for CI
        generate_html_report=False,
        generate_csv_export=True,
        include_visualizations=False,
    )

    runner = BenchmarkRunner(config, output_path)

    async def run_ci_tests():
        try:
            # Run comparison benchmarks
            results = await runner.run_comparison_benchmarks()

            # Validate optimization claims
            validation = await runner.validate_optimization_claims()

            # Output CI-friendly results
            ci_results = {
                "success": validation.get("overall_success", False),
                "validation_passed": validation.get("overall_success", False),
                "high_confidence_claims_met": validation.get(
                    "high_confidence_claims_met", 0
                ),
                "total_high_confidence_claims": validation.get(
                    "total_high_confidence_claims", 0
                ),
                "reports": {
                    "csv": results.get("csv_export_path"),
                    "validation": validation.get("validation_report_path"),
                },
            }

            # Save CI results
            ci_results_file = output_path / "ci_results.json"
            with open(ci_results_file, "w") as f:
                json.dump(ci_results, f, indent=2)

            # Print CI summary
            success_rate = ci_results["high_confidence_claims_met"] / max(
                ci_results["total_high_confidence_claims"], 1
            )

            click.echo(f"CI_VALIDATION_SUCCESS={ci_results['success']}")
            click.echo(f"CI_CLAIMS_SUCCESS_RATE={success_rate:.2f}")
            click.echo(f"CI_RESULTS_FILE={ci_results_file}")

            if not ci_results["success"]:
                sys.exit(1)

        except Exception as e:
            click.echo(f"❌ CI validation failed: {e}")
            sys.exit(1)

    asyncio.run(run_ci_tests())


# Add the CLI commands from benchmark_runner
main.add_command(benchmark_cli)


if __name__ == "__main__":
    main()
