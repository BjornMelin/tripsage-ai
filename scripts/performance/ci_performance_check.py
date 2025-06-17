"""
CI/CD Performance Validation Script for TripSage PGVector Optimizations.

This script provides streamlined performance validation for continuous integration
pipelines. It runs abbreviated benchmarks and validates against performance targets
with clear exit codes for CI/CD systems.

Features:
- Fast CI-optimized benchmark execution
- Automatic baseline comparison
- Clear pass/fail exit codes
- Performance trend tracking
- Slack/Teams notifications (optional)
- Artifact generation for CI/CD dashboards
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import click
from pgvector_benchmark import BenchmarkConfig, PGVectorBenchmark
from regression_detector import (
    check_for_regressions,
    setup_baseline_from_benchmark_results,
)

logger = logging.getLogger(__name__)


class CIPerformanceValidator:
    """CI/CD optimized performance validator."""

    def __init__(
        self,
        baseline_dir: str = "./ci_baselines",
        output_dir: str = "./ci_performance_results",
        quick_mode: bool = True,
    ):
        """Initialize CI performance validator.

        Args:
            baseline_dir: Directory for baseline storage
            output_dir: Directory for CI artifacts
            quick_mode: Use abbreviated tests for faster CI execution
        """
        self.baseline_dir = Path(baseline_dir)
        self.output_dir = Path(output_dir)
        self.quick_mode = quick_mode

        # Create directories
        self.baseline_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Configure logging for CI
        self._setup_ci_logging()

    def _setup_ci_logging(self) -> None:
        """Configure logging optimized for CI environments."""
        log_file = self.output_dir / "ci_performance.log"

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        simple_formatter = logging.Formatter("%(levelname)s: %(message)s")

        # File handler for detailed logs
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(detailed_formatter)
        file_handler.setLevel(logging.DEBUG)

        # Console handler for CI output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(simple_formatter)
        console_handler.setLevel(logging.INFO)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def create_ci_config(self) -> BenchmarkConfig:
        """Create optimized configuration for CI execution."""
        config = BenchmarkConfig(output_directory=str(self.output_dir))

        if self.quick_mode:
            # Reduce test parameters for faster CI execution
            config.small_dataset_size = 100
            config.medium_dataset_size = 1000
            config.large_dataset_size = 2000  # Much smaller for CI
            config.benchmark_queries = 50
            config.warmup_queries = 10
            config.concurrent_connections = 5
            config.test_duration_seconds = 120  # 2 minutes max

            # Limit test variations for speed
            config.ef_search_values = [40, 100]  # Only test 2 values
            config.optimization_profiles = [
                config.optimization_profiles[1]
            ]  # Only balanced
            config.distance_functions = [config.distance_functions[0]]  # Only cosine

            # Disable detailed profiling for speed
            config.enable_memory_profiling = True
            config.metrics_collection_interval = 2.0  # Less frequent sampling

        return config

    async def run_ci_benchmark(self, git_commit: Optional[str] = None) -> Dict:
        """Run CI-optimized benchmark.

        Args:
            git_commit: Git commit hash for versioning

        Returns:
            Benchmark results dictionary
        """
        logger.info("Starting CI performance benchmark...")

        start_time = time.time()

        try:
            # Create CI configuration
            config = self.create_ci_config()

            # Run benchmark
            benchmark = PGVectorBenchmark(config)
            results = await benchmark.run_full_benchmark()

            # Save results with timestamp and commit info
            results_dict = self._serialize_results(results)
            results_dict["ci_metadata"] = {
                "git_commit": git_commit or "unknown",
                "ci_duration_seconds": time.time() - start_time,
                "quick_mode": self.quick_mode,
                "timestamp": time.time(),
            }

            # Save to file
            results_file = self.output_dir / "ci_benchmark_results.json"
            with open(results_file, "w") as f:
                json.dump(results_dict, f, indent=2, default=str)

            logger.info(
                f"CI benchmark completed in {time.time() - start_time:.1f} seconds"
            )
            return results_dict

        except Exception as e:
            logger.error(f"CI benchmark failed: {e}")
            raise

    def _serialize_results(self, results) -> Dict:
        """Convert benchmark results to JSON-serializable format."""

        def convert_to_dict(obj):
            if hasattr(obj, "__dict__"):
                return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [convert_to_dict(item) for item in obj]
            elif hasattr(obj, "isoformat"):  # datetime objects
                return obj.isoformat()
            else:
                return obj

        return convert_to_dict(results)

    def validate_performance(
        self,
        results_file: Optional[str] = None,
        update_baseline: bool = False,
        git_commit: Optional[str] = None,
    ) -> bool:
        """Validate performance against baselines and targets.

        Args:
            results_file: Path to results file (uses latest if None)
            update_baseline: Whether to update baseline with current results
            git_commit: Git commit for baseline versioning

        Returns:
            True if validation passes, False otherwise
        """
        if not results_file:
            results_file = self.output_dir / "ci_benchmark_results.json"

        if not Path(results_file).exists():
            logger.error(f"Results file not found: {results_file}")
            return False

        logger.info("Validating performance against baselines...")

        try:
            # Update baseline if requested (usually for main branch)
            if update_baseline:
                logger.info("Updating performance baseline...")
                setup_baseline_from_benchmark_results(
                    str(results_file),
                    str(self.baseline_dir),
                    git_commit or "ci_baseline",
                )

            # Check for regressions
            regression_report_file = self.output_dir / "regression_report.md"
            validation_passed = check_for_regressions(
                str(results_file), str(self.baseline_dir), str(regression_report_file)
            )

            # Generate CI summary
            self._generate_ci_summary(results_file, validation_passed)

            return validation_passed

        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            return False

    def _generate_ci_summary(self, results_file: str, validation_passed: bool) -> None:
        """Generate CI-friendly performance summary."""

        with open(results_file) as f:
            results = json.load(f)

        summary_file = self.output_dir / "ci_summary.md"

        summary = []
        summary.append("# CI Performance Validation Summary")
        summary.append("")

        # Overall status
        if validation_passed:
            summary.append("## ✅ PERFORMANCE VALIDATION PASSED")
        else:
            summary.append("## ❌ PERFORMANCE VALIDATION FAILED")
        summary.append("")

        # Key metrics
        if "optimized_query_metrics" in results:
            metrics = results["optimized_query_metrics"]
            if metrics:
                best_metric = min(metrics, key=lambda x: x["avg_latency_ms"])
                summary.append("### Key Performance Metrics")
                summary.append(
                    f"- **Best Query Latency:** {best_metric['avg_latency_ms']:.2f}ms"
                )
                summary.append(
                    f"- **Best Throughput:** {best_metric['queries_per_second']:.1f} QPS"
                )
                summary.append(f"- **Success Rate:** {best_metric['success_rate']:.1%}")
                summary.append("")

        # Performance improvements
        if "performance_improvements" in results:
            improvements = results["performance_improvements"]
            summary.append("### Performance Improvements")
            for metric, value in improvements.items():
                summary.append(
                    f"- **{metric.replace('_', ' ').title()}:** {value:.2f}x"
                )
            summary.append("")

        # CI metadata
        if "ci_metadata" in results:
            ci_meta = results["ci_metadata"]
            summary.append("### CI Information")
            summary.append(f"- **Git Commit:** {ci_meta.get('git_commit', 'unknown')}")
            summary.append(
                f"- **Test Duration:** {ci_meta.get('ci_duration_seconds', 0):.1f} seconds"
            )
            summary.append(f"- **Quick Mode:** {ci_meta.get('quick_mode', False)}")
            summary.append("")

        # Write summary
        with open(summary_file, "w") as f:
            f.write("\n".join(summary))

        # Also output to console for CI logs
        print("\n" + "\n".join(summary))

    def generate_ci_artifacts(self) -> None:
        """Generate artifacts for CI/CD dashboard integration."""

        artifacts_dir = self.output_dir / "artifacts"
        artifacts_dir.mkdir(exist_ok=True)

        # Copy key files to artifacts directory
        key_files = [
            "ci_benchmark_results.json",
            "ci_summary.md",
            "regression_report.md",
            "ci_performance.log",
        ]

        for filename in key_files:
            source = self.output_dir / filename
            if source.exists():
                import shutil

                shutil.copy2(source, artifacts_dir / filename)

        logger.info(f"CI artifacts generated in {artifacts_dir}")


# CLI interface using Click
@click.group()
def cli():
    """TripSage CI Performance Validation Tool."""
    pass


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    default="./ci_performance_results",
    help="Output directory for results",
)
@click.option(
    "--baseline-dir", "-b", default="./ci_baselines", help="Baseline directory"
)
@click.option("--git-commit", "-c", default=None, help="Git commit hash")
@click.option(
    "--quick/--full", default=True, help="Use quick mode for faster execution"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def benchmark(output_dir, baseline_dir, git_commit, quick, verbose):
    """Run CI performance benchmark."""

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def run():
        validator = CIPerformanceValidator(
            baseline_dir=baseline_dir, output_dir=output_dir, quick_mode=quick
        )

        try:
            await validator.run_ci_benchmark(git_commit)
            click.echo("✅ Benchmark completed successfully")
        except Exception as e:
            click.echo(f"❌ Benchmark failed: {e}")
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    default="./ci_performance_results",
    help="Output directory containing results",
)
@click.option(
    "--baseline-dir", "-b", default="./ci_baselines", help="Baseline directory"
)
@click.option(
    "--results-file", "-r", default=None, help="Specific results file to validate"
)
@click.option(
    "--update-baseline/--no-update-baseline",
    default=False,
    help="Update baseline with current results",
)
@click.option(
    "--git-commit", "-c", default=None, help="Git commit hash for baseline versioning"
)
@click.option(
    "--generate-artifacts/--no-artifacts", default=True, help="Generate CI artifacts"
)
def validate(
    output_dir,
    baseline_dir,
    results_file,
    update_baseline,
    git_commit,
    generate_artifacts,
):
    """Validate performance against baselines."""

    validator = CIPerformanceValidator(baseline_dir=baseline_dir, output_dir=output_dir)

    try:
        # Validate performance
        passed = validator.validate_performance(
            results_file=results_file,
            update_baseline=update_baseline,
            git_commit=git_commit,
        )

        # Generate artifacts for CI dashboard
        if generate_artifacts:
            validator.generate_ci_artifacts()

        if passed:
            click.echo("✅ Performance validation PASSED")
            sys.exit(0)
        else:
            click.echo("❌ Performance validation FAILED")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--output-dir",
    "-o",
    default="./ci_performance_results",
    help="Output directory for results",
)
@click.option(
    "--baseline-dir", "-b", default="./ci_baselines", help="Baseline directory"
)
@click.option("--git-commit", "-c", default=None, help="Git commit hash")
@click.option(
    "--update-baseline/--no-update-baseline",
    default=False,
    help="Update baseline with results (for main branch)",
)
@click.option(
    "--quick/--full", default=True, help="Use quick mode for faster execution"
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def full_pipeline(
    output_dir, baseline_dir, git_commit, update_baseline, quick, verbose
):
    """Run complete CI performance pipeline (benchmark + validate)."""

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    async def run():
        validator = CIPerformanceValidator(
            baseline_dir=baseline_dir, output_dir=output_dir, quick_mode=quick
        )

        try:
            # Run benchmark
            click.echo("🚀 Running performance benchmark...")
            await validator.run_ci_benchmark(git_commit)

            # Validate results
            click.echo("🔍 Validating performance...")
            passed = validator.validate_performance(
                update_baseline=update_baseline, git_commit=git_commit
            )

            # Generate artifacts
            click.echo("📋 Generating CI artifacts...")
            validator.generate_ci_artifacts()

            if passed:
                click.echo("✅ Complete CI performance pipeline PASSED")
                sys.exit(0)
            else:
                click.echo("❌ Complete CI performance pipeline FAILED")
                sys.exit(1)

        except Exception as e:
            click.echo(f"❌ CI pipeline failed: {e}")
            sys.exit(1)

    asyncio.run(run())


@cli.command()
@click.option(
    "--baseline-dir", "-b", default="./ci_baselines", help="Baseline directory"
)
@click.option(
    "--results-file", "-r", required=True, help="Results file to use as baseline"
)
@click.option(
    "--git-commit",
    "-c",
    default="manual_baseline",
    help="Version identifier for baseline",
)
def setup_baseline(baseline_dir, results_file, git_commit):
    """Setup performance baseline from results file."""

    try:
        setup_baseline_from_benchmark_results(results_file, baseline_dir, git_commit)
        click.echo(f"✅ Baseline setup completed for version: {git_commit}")
    except Exception as e:
        click.echo(f"❌ Baseline setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
