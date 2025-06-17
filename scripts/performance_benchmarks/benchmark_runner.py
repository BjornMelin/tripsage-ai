"""
Main Benchmark Runner for Database Performance Validation.

This module provides the main entry point for executing comprehensive
database performance benchmarks to validate optimization improvements.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import click

from .config import BenchmarkConfig, OptimizationLevel, WorkloadType
from .metrics_collector import PerformanceMetricsCollector
from .report_generator import BenchmarkReportGenerator
from .scenario_manager import BenchmarkScenarioManager

logger = logging.getLogger(__name__)


class BenchmarkRunner:
    """
    Main benchmark runner for database performance validation.

    Orchestrates the execution of baseline and optimized benchmark scenarios,
    collects performance metrics, validates improvements, and generates
    comprehensive reports.
    """

    def __init__(
        self,
        config: Optional[BenchmarkConfig] = None,
        output_dir: Optional[Path] = None,
    ):
        """Initialize benchmark runner.

        Args:
            config: Benchmark configuration or None for defaults
            output_dir: Output directory for reports or None for default
        """
        self.config = config or BenchmarkConfig()
        self.output_dir = output_dir or Path("benchmark_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.scenario_manager = BenchmarkScenarioManager(self.config)
        self.report_generator = BenchmarkReportGenerator(self.output_dir)

        # Results storage
        self.results: Dict[str, Any] = {}
        self.start_time = time.time()

        logger.info(f"Benchmark runner initialized with output dir: {self.output_dir}")

    async def run_baseline_only(self) -> Dict[str, Any]:
        """Run only baseline benchmarks without optimizations.

        Returns:
            Baseline benchmark results
        """
        logger.info("Running baseline-only benchmarks...")

        try:
            # Execute baseline benchmarks
            (
                baseline_results,
                baseline_metrics,
            ) = await self.scenario_manager.execute_baseline_benchmarks()

            # Compile results
            results = {
                "execution_timestamp": self.start_time,
                "config": self.config.model_dump(),
                "baseline": {
                    "scenarios": baseline_results,
                    "metrics": baseline_metrics.get_comprehensive_metrics_summary(),
                },
                "execution_time": time.time() - self.start_time,
            }

            # Generate report
            report_path = await self.report_generator.generate_baseline_report(results)
            results["report_path"] = str(report_path)

            logger.info(f"Baseline benchmarks completed. Report: {report_path}")
            return results

        except Exception as e:
            logger.error(f"Baseline benchmark execution failed: {e}")
            raise

    async def run_optimized_only(self) -> Dict[str, Any]:
        """Run only optimized benchmarks.

        Returns:
            Optimized benchmark results
        """
        logger.info("Running optimized-only benchmarks...")

        try:
            # Execute optimized benchmarks
            (
                optimized_results,
                optimized_metrics,
            ) = await self.scenario_manager.execute_optimized_benchmarks()

            # Compile results
            results = {
                "execution_timestamp": self.start_time,
                "config": self.config.model_dump(),
                "optimized": {
                    "scenarios": optimized_results,
                    "metrics": optimized_metrics.get_comprehensive_metrics_summary(),
                },
                "execution_time": time.time() - self.start_time,
            }

            # Generate report
            report_path = await self.report_generator.generate_optimized_report(results)
            results["report_path"] = str(report_path)

            logger.info(f"Optimized benchmarks completed. Report: {report_path}")
            return results

        except Exception as e:
            logger.error(f"Optimized benchmark execution failed: {e}")
            raise

    async def run_comparison_benchmarks(self) -> Dict[str, Any]:
        """Run complete comparison benchmarks (baseline vs optimized).

        Returns:
            Complete benchmark comparison results
        """
        logger.info("Running complete comparison benchmarks...")

        try:
            # Execute complete benchmark suite
            results = await self.scenario_manager.execute_complete_benchmark_suite()
            results["execution_time"] = time.time() - self.start_time

            # Generate comprehensive report
            report_path = await self.report_generator.generate_comparison_report(
                results
            )
            results["report_path"] = str(report_path)

            # Generate CSV export if enabled
            if self.config.generate_csv_export:
                csv_path = await self.report_generator.export_to_csv(results)
                results["csv_export_path"] = str(csv_path)

            # Store results for later analysis
            self.results = results

            logger.info(f"Comparison benchmarks completed. Report: {report_path}")
            return results

        except Exception as e:
            logger.error(f"Comparison benchmark execution failed: {e}")
            raise

    async def run_high_concurrency_benchmarks(self) -> Dict[str, Any]:
        """Run high-concurrency benchmarks.

        Returns:
            High-concurrency benchmark results
        """
        logger.info("Running high-concurrency benchmarks...")

        try:
            # Execute high-concurrency benchmarks
            (
                concurrency_results,
                concurrency_metrics,
            ) = await self.scenario_manager.execute_high_concurrency_benchmarks()

            # Compile results
            results = {
                "execution_timestamp": self.start_time,
                "config": self.config.model_dump(),
                "high_concurrency": {
                    "scenarios": concurrency_results,
                    "metrics": concurrency_metrics.get_comprehensive_metrics_summary(),
                },
                "execution_time": time.time() - self.start_time,
            }

            # Generate report
            report_path = await self.report_generator.generate_concurrency_report(
                results
            )
            results["report_path"] = str(report_path)

            logger.info(f"High-concurrency benchmarks completed. Report: {report_path}")
            return results

        except Exception as e:
            logger.error(f"High-concurrency benchmark execution failed: {e}")
            raise

    async def run_custom_scenario(
        self,
        scenario_name: str,
        workload_type: WorkloadType,
        optimization_level: OptimizationLevel,
        duration_seconds: int = 300,
        concurrent_users: int = 10,
        operations_per_user: int = 100,
    ) -> Dict[str, Any]:
        """Run a custom benchmark scenario.

        Args:
            scenario_name: Name for the custom scenario
            workload_type: Type of workload to execute
            optimization_level: Level of optimizations to apply
            duration_seconds: Maximum test duration
            concurrent_users: Number of concurrent users to simulate
            operations_per_user: Operations per user

        Returns:
            Custom scenario results
        """
        logger.info(f"Running custom scenario: {scenario_name}")

        from .config import BenchmarkScenario

        # Create custom scenario
        scenario = BenchmarkScenario(
            name=scenario_name,
            description=(
                f"Custom {workload_type.value} workload with "
                f"{optimization_level.value} optimizations"
            ),
            workload_type=workload_type,
            optimization_level=optimization_level,
            duration_seconds=duration_seconds,
            concurrent_users=concurrent_users,
            operations_per_user=operations_per_user,
            data_size=self.config.test_data_size,
        )

        try:
            # Initialize services
            await self.scenario_manager.initialize_services()

            # Create metrics collector
            metrics_collector = PerformanceMetricsCollector(self.config)
            await metrics_collector.start_monitoring()

            # Execute scenario
            scenario_result = await self.scenario_manager.execute_scenario(
                scenario, metrics_collector
            )

            await metrics_collector.stop_monitoring()

            # Compile results
            results = {
                "execution_timestamp": self.start_time,
                "config": self.config.model_dump(),
                "custom_scenario": {
                    "scenario": scenario_result,
                    "metrics": metrics_collector.get_comprehensive_metrics_summary(),
                },
                "execution_time": time.time() - self.start_time,
            }

            # Generate report
            report_path = await self.report_generator.generate_custom_scenario_report(
                results, scenario_name
            )
            results["report_path"] = str(report_path)

            logger.info(f"Custom scenario completed. Report: {report_path}")
            return results

        except Exception as e:
            logger.error(f"Custom scenario execution failed: {e}")
            raise
        finally:
            await self.scenario_manager.cleanup_services()

    async def validate_optimization_claims(self) -> Dict[str, Any]:
        """Validate specific optimization claims against thresholds.

        Returns:
            Validation results for optimization claims
        """
        logger.info("Validating optimization claims...")

        if not self.results:
            # Run comparison benchmarks if not already done
            await self.run_comparison_benchmarks()

        validation_results = self.results.get("validation", {})

        # Enhanced validation logic
        claims_validation = {
            "query_performance_3x": {
                "claimed_improvement": "3x general query performance",
                "measured_improvement": validation_results.get("improvements", {})
                .get("query_performance", {})
                .get("improvement_ratio", 0),
                "target_met": False,
                "confidence": "high",
            },
            "vector_search_30x": {
                "claimed_improvement": "30x pgvector performance",
                "measured_improvement": validation_results.get("improvements", {})
                .get("vector_search", {})
                .get("improvement_ratio", 0),
                "target_met": False,
                "confidence": "high",
            },
            "memory_reduction_50pct": {
                "claimed_improvement": "50% memory reduction",
                "measured_improvement": 0,  # Would need memory comparison
                "target_met": False,
                "confidence": "medium",
            },
            "connection_pool_efficiency": {
                "claimed_improvement": "Improved connection efficiency",
                "measured_improvement": validation_results.get(
                    "threshold_compliance", {}
                )
                .get("connection_efficiency", {})
                .get("current", 0),
                "target_met": validation_results.get("threshold_compliance", {})
                .get("connection_efficiency", {})
                .get("meets_target", False),
                "confidence": "high",
            },
            "cache_effectiveness": {
                "claimed_improvement": "High cache hit ratios",
                "measured_improvement": validation_results.get(
                    "threshold_compliance", {}
                )
                .get("cache_hit_ratio", {})
                .get("current", 0),
                "target_met": validation_results.get("threshold_compliance", {})
                .get("cache_hit_ratio", {})
                .get("meets_target", False),
                "confidence": "high",
            },
        }

        # Check if targets are met
        for claim_key, claim_data in claims_validation.items():
            if "improvement_ratio" in validation_results.get("improvements", {}).get(
                claim_key.split("_")[0], {}
            ):
                improvement = validation_results["improvements"][
                    claim_key.split("_")[0]
                ]["improvement_ratio"]
                claim_data["measured_improvement"] = improvement

                if claim_key == "query_performance_3x":
                    claim_data["target_met"] = improvement >= 3.0
                elif claim_key == "vector_search_30x":
                    claim_data["target_met"] = improvement >= 30.0

        # Overall validation status
        overall_validation = {
            "timestamp": time.time(),
            "claims_validation": claims_validation,
            "overall_success": all(
                claim["target_met"] for claim in claims_validation.values()
            ),
            "high_confidence_claims_met": sum(
                1
                for claim in claims_validation.values()
                if claim["confidence"] == "high" and claim["target_met"]
            ),
            "total_high_confidence_claims": sum(
                1
                for claim in claims_validation.values()
                if claim["confidence"] == "high"
            ),
            "recommendations": validation_results.get("recommendations", []),
        }

        # Generate validation report
        report_path = await self.report_generator.generate_validation_report(
            overall_validation
        )
        overall_validation["validation_report_path"] = str(report_path)

        logger.info(f"Optimization claims validation completed. Report: {report_path}")
        return overall_validation

    def get_benchmark_summary(self) -> Dict[str, Any]:
        """Get a summary of all benchmark results.

        Returns:
            Comprehensive benchmark summary
        """
        if not self.results:
            return {"error": "No benchmark results available"}

        summary = {
            "execution_summary": {
                "start_time": self.start_time,
                "total_execution_time": self.results.get("execution_time", 0),
                "total_scenarios": self.results.get("summary", {}).get(
                    "total_scenarios", 0
                ),
                "successful_scenarios": self.results.get("summary", {}).get(
                    "successful_scenarios", 0
                ),
            },
            "performance_improvements": {},
            "validation_status": self.results.get("validation", {}).get(
                "validation_passed", False
            ),
            "key_metrics": {},
        }

        # Extract key metrics from baseline and optimized results
        if "baseline" in self.results and "optimized" in self.results:
            baseline_metrics = self.results["baseline"]["metrics"]
            optimized_metrics = self.results["optimized"]["metrics"]

            # Query performance comparison
            baseline_query = baseline_metrics.get("query_performance", {})
            optimized_query = optimized_metrics.get("query_performance", {})

            if (
                "duration_stats" in baseline_query
                and "duration_stats" in optimized_query
            ):
                baseline_p95 = baseline_query["duration_stats"]["p95"]
                optimized_p95 = optimized_query["duration_stats"]["p95"]

                summary["performance_improvements"]["query_latency"] = {
                    "baseline_p95_ms": baseline_p95 * 1000,
                    "optimized_p95_ms": optimized_p95 * 1000,
                    "improvement_ratio": baseline_p95 / optimized_p95
                    if optimized_p95 > 0
                    else float("inf"),
                    "improvement_percentage": (
                        (baseline_p95 - optimized_p95) / baseline_p95 * 100
                    )
                    if baseline_p95 > 0
                    else 0,
                }

            # Throughput comparison
            baseline_throughput = baseline_query.get("throughput", {}).get(
                "operations_per_second", 0
            )
            optimized_throughput = optimized_query.get("throughput", {}).get(
                "operations_per_second", 0
            )

            summary["performance_improvements"]["throughput"] = {
                "baseline_ops_per_second": baseline_throughput,
                "optimized_ops_per_second": optimized_throughput,
                "improvement_ratio": optimized_throughput / baseline_throughput
                if baseline_throughput > 0
                else float("inf"),
                "improvement_percentage": (
                    (optimized_throughput - baseline_throughput)
                    / baseline_throughput
                    * 100
                )
                if baseline_throughput > 0
                else 0,
            }

        return summary


# CLI Interface
@click.group()
@click.option(
    "--output-dir", "-o", type=click.Path(), help="Output directory for reports"
)
@click.option(
    "--config-file", "-c", type=click.Path(exists=True), help="Configuration file path"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, output_dir, config_file, verbose):
    """Database Performance Benchmarking Suite for TripSage."""
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Load configuration
    config = BenchmarkConfig()
    if config_file:
        # Would load from file if implemented
        pass

    # Setup context
    output_path = Path(output_dir) if output_dir else Path("benchmark_results")
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["output_dir"] = output_path
    ctx.obj["runner"] = BenchmarkRunner(config, output_path)


@cli.command()
@click.pass_context
def baseline(ctx):
    """Run baseline benchmarks only."""
    runner = ctx.obj["runner"]

    async def run():
        try:
            results = await runner.run_baseline_only()
            click.echo("✅ Baseline benchmarks completed!")
            click.echo(f"Report: {results.get('report_path', 'N/A')}")
            return 0
        except Exception as e:
            click.echo(f"❌ Baseline benchmarks failed: {e}")
            return 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


@cli.command()
@click.pass_context
def optimized(ctx):
    """Run optimized benchmarks only."""
    runner = ctx.obj["runner"]

    async def run():
        try:
            results = await runner.run_optimized_only()
            click.echo("✅ Optimized benchmarks completed!")
            click.echo(f"Report: {results.get('report_path', 'N/A')}")
            return 0
        except Exception as e:
            click.echo(f"❌ Optimized benchmarks failed: {e}")
            return 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


@cli.command()
@click.pass_context
def comparison(ctx):
    """Run complete comparison benchmarks (baseline vs optimized)."""
    runner = ctx.obj["runner"]

    async def run():
        try:
            results = await runner.run_comparison_benchmarks()
            click.echo("✅ Comparison benchmarks completed!")
            click.echo(f"Report: {results.get('report_path', 'N/A')}")

            # Show validation summary
            validation = results.get("validation", {})
            if validation.get("validation_passed"):
                click.echo("🎯 Performance validation: PASSED")
            else:
                click.echo("⚠️  Performance validation: FAILED")
                for rec in validation.get("recommendations", []):
                    click.echo(f"   - {rec}")

            return 0
        except Exception as e:
            click.echo(f"❌ Comparison benchmarks failed: {e}")
            return 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


@cli.command()
@click.pass_context
def concurrency(ctx):
    """Run high-concurrency benchmarks."""
    runner = ctx.obj["runner"]

    async def run():
        try:
            results = await runner.run_high_concurrency_benchmarks()
            click.echo("✅ High-concurrency benchmarks completed!")
            click.echo(f"Report: {results.get('report_path', 'N/A')}")
            return 0
        except Exception as e:
            click.echo(f"❌ High-concurrency benchmarks failed: {e}")
            return 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


@cli.command()
@click.option("--name", "-n", required=True, help="Scenario name")
@click.option(
    "--workload",
    "-w",
    type=click.Choice(["read_heavy", "vector_search", "mixed"]),
    default="mixed",
    help="Workload type",
)
@click.option(
    "--optimization",
    "-opt",
    type=click.Choice(["none", "basic", "advanced", "full"]),
    default="full",
    help="Optimization level",
)
@click.option(
    "--duration", "-d", type=int, default=300, help="Test duration in seconds"
)
@click.option("--users", "-u", type=int, default=10, help="Concurrent users")
@click.option("--operations", "-ops", type=int, default=100, help="Operations per user")
@click.pass_context
def custom(ctx, name, workload, optimization, duration, users, operations):
    """Run a custom benchmark scenario."""
    runner = ctx.obj["runner"]

    # Convert string enums
    workload_type = WorkloadType(workload)
    optimization_level = OptimizationLevel(optimization)

    async def run():
        try:
            results = await runner.run_custom_scenario(
                scenario_name=name,
                workload_type=workload_type,
                optimization_level=optimization_level,
                duration_seconds=duration,
                concurrent_users=users,
                operations_per_user=operations,
            )
            click.echo(f"✅ Custom scenario '{name}' completed!")
            click.echo(f"Report: {results.get('report_path', 'N/A')}")
            return 0
        except Exception as e:
            click.echo(f"❌ Custom scenario failed: {e}")
            return 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


@cli.command()
@click.pass_context
def validate(ctx):
    """Validate optimization claims against measured results."""
    runner = ctx.obj["runner"]

    async def run():
        try:
            validation = await runner.validate_optimization_claims()
            click.echo("✅ Optimization claims validation completed!")
            click.echo(f"Report: {validation.get('validation_report_path', 'N/A')}")

            # Show validation summary
            if validation.get("overall_success"):
                click.echo("🎯 All optimization claims validated successfully!")
            else:
                click.echo("⚠️  Some optimization claims not met:")
                for claim, data in validation.get("claims_validation", {}).items():
                    status = "✅" if data.get("target_met") else "❌"
                    click.echo(f"   {status} {data.get('claimed_improvement', claim)}")

            return 0
        except Exception as e:
            click.echo(f"❌ Validation failed: {e}")
            return 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


if __name__ == "__main__":
    cli()
