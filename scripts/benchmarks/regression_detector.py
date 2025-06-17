"""
Performance Regression Detection System for TripSage PGVector Optimizations.

This module provides automated regression detection by comparing current benchmark
results against historical baselines. It's designed for CI/CD integration to catch
performance degradations early.

Features:
- Historical performance tracking
- Statistical significance testing
- Performance threshold validation
- Automated alerting for regressions
- CI/CD exit code integration
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class RegressionThresholds:
    """Thresholds for regression detection."""

    # Performance degradation thresholds (relative to baseline)
    max_latency_degradation_pct: float = 20.0  # 20% increase in latency is regression
    min_throughput_degradation_pct: float = (
        15.0  # 15% decrease in throughput is regression
    )
    max_memory_increase_pct: float = 25.0  # 25% increase in memory is regression

    # Absolute thresholds
    max_acceptable_latency_ms: float = 15.0  # Never exceed 15ms average latency
    min_acceptable_qps: float = 50.0  # Never drop below 50 QPS

    # Statistical significance
    confidence_level: float = 0.95  # 95% confidence for statistical tests
    min_samples_for_stats: int = 5  # Minimum samples for statistical analysis


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison."""

    timestamp: datetime
    test_version: str
    avg_latency_ms: float
    p95_latency_ms: float
    queries_per_second: float
    memory_usage_mb: float
    index_creation_time_s: float
    success_rate: float

    # Statistical data
    latency_samples: List[float]
    throughput_samples: List[float]
    memory_samples: List[float]


@dataclass
class RegressionAnalysisResult:
    """Result of regression analysis."""

    test_name: str
    current_performance: PerformanceBaseline
    baseline_performance: PerformanceBaseline

    # Regression flags
    latency_regression: bool
    throughput_regression: bool
    memory_regression: bool
    overall_regression: bool

    # Performance changes
    latency_change_pct: float
    throughput_change_pct: float
    memory_change_pct: float

    # Statistical significance
    latency_significant: bool
    throughput_significant: bool
    statistical_confidence: float

    # Recommendations
    recommendations: List[str]
    severity: str  # "low", "medium", "high", "critical"


class BaselineManager:
    """Manages performance baselines and historical data."""

    def __init__(self, baseline_dir: str = "./baselines"):
        """Initialize baseline manager.

        Args:
            baseline_dir: Directory to store baseline data
        """
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(exist_ok=True)

    def save_baseline(
        self, test_name: str, performance_data: Dict[str, Any], version: str = "unknown"
    ) -> None:
        """Save performance baseline.

        Args:
            test_name: Name of the test
            performance_data: Performance metrics
            version: Version/commit identifier
        """
        baseline_file = self.baseline_dir / f"{test_name}_baseline.json"

        # Load existing baselines
        baselines = []
        if baseline_file.exists():
            with open(baseline_file) as f:
                baselines = json.load(f)

        # Add new baseline
        baseline_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": version,
            "performance": performance_data,
        }

        baselines.append(baseline_entry)

        # Keep only last 50 baselines to avoid file bloat
        baselines = baselines[-50:]

        # Save updated baselines
        with open(baseline_file, "w") as f:
            json.dump(baselines, f, indent=2)

        logger.info(f"Saved baseline for {test_name} (version: {version})")

    def get_latest_baseline(self, test_name: str) -> Optional[PerformanceBaseline]:
        """Get the latest baseline for a test.

        Args:
            test_name: Name of the test

        Returns:
            Latest performance baseline or None if not found
        """
        baseline_file = self.baseline_dir / f"{test_name}_baseline.json"

        if not baseline_file.exists():
            return None

        with open(baseline_file) as f:
            baselines = json.load(f)

        if not baselines:
            return None

        latest = baselines[-1]
        perf = latest["performance"]

        return PerformanceBaseline(
            timestamp=datetime.fromisoformat(latest["timestamp"]),
            test_version=latest["version"],
            avg_latency_ms=perf.get("avg_latency_ms", 0),
            p95_latency_ms=perf.get("p95_latency_ms", 0),
            queries_per_second=perf.get("queries_per_second", 0),
            memory_usage_mb=perf.get("memory_usage_mb", 0),
            index_creation_time_s=perf.get("index_creation_time_s", 0),
            success_rate=perf.get("success_rate", 1.0),
            latency_samples=perf.get("latency_samples", []),
            throughput_samples=perf.get("throughput_samples", []),
            memory_samples=perf.get("memory_samples", []),
        )

    def get_historical_baselines(
        self, test_name: str, days_back: int = 30
    ) -> List[PerformanceBaseline]:
        """Get historical baselines for trend analysis.

        Args:
            test_name: Name of the test
            days_back: Number of days to look back

        Returns:
            List of historical baselines
        """
        baseline_file = self.baseline_dir / f"{test_name}_baseline.json"

        if not baseline_file.exists():
            return []

        with open(baseline_file) as f:
            baselines = json.load(f)

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        historical = []

        for baseline in baselines:
            timestamp = datetime.fromisoformat(baseline["timestamp"])
            if timestamp >= cutoff_date:
                perf = baseline["performance"]
                historical.append(
                    PerformanceBaseline(
                        timestamp=timestamp,
                        test_version=baseline["version"],
                        avg_latency_ms=perf.get("avg_latency_ms", 0),
                        p95_latency_ms=perf.get("p95_latency_ms", 0),
                        queries_per_second=perf.get("queries_per_second", 0),
                        memory_usage_mb=perf.get("memory_usage_mb", 0),
                        index_creation_time_s=perf.get("index_creation_time_s", 0),
                        success_rate=perf.get("success_rate", 1.0),
                        latency_samples=perf.get("latency_samples", []),
                        throughput_samples=perf.get("throughput_samples", []),
                        memory_samples=perf.get("memory_samples", []),
                    )
                )

        return historical


class RegressionDetector:
    """Detects performance regressions by comparing against baselines."""

    def __init__(
        self,
        baseline_manager: BaselineManager,
        thresholds: Optional[RegressionThresholds] = None,
    ):
        """Initialize regression detector.

        Args:
            baseline_manager: Manager for baseline data
            thresholds: Regression detection thresholds
        """
        self.baseline_manager = baseline_manager
        self.thresholds = thresholds or RegressionThresholds()

    def analyze_performance(
        self, test_name: str, current_results: Dict[str, Any]
    ) -> RegressionAnalysisResult:
        """Analyze current performance against baseline.

        Args:
            test_name: Name of the test
            current_results: Current performance results

        Returns:
            Regression analysis result
        """
        # Get baseline for comparison
        baseline = self.baseline_manager.get_latest_baseline(test_name)

        if not baseline:
            logger.warning(f"No baseline found for {test_name}")
            return self._create_no_baseline_result(test_name, current_results)

        # Create current performance baseline
        current = self._extract_performance_baseline(current_results)

        # Perform regression analysis
        return self._perform_regression_analysis(test_name, current, baseline)

    def _extract_performance_baseline(
        self, results: Dict[str, Any]
    ) -> PerformanceBaseline:
        """Extract performance baseline from results."""
        return PerformanceBaseline(
            timestamp=datetime.now(timezone.utc),
            test_version="current",
            avg_latency_ms=results.get("avg_latency_ms", 0),
            p95_latency_ms=results.get("p95_latency_ms", 0),
            queries_per_second=results.get("queries_per_second", 0),
            memory_usage_mb=results.get("memory_usage_mb", 0),
            index_creation_time_s=results.get("index_creation_time_s", 0),
            success_rate=results.get("success_rate", 1.0),
            latency_samples=results.get("latency_samples", []),
            throughput_samples=results.get("throughput_samples", []),
            memory_samples=results.get("memory_samples", []),
        )

    def _perform_regression_analysis(
        self,
        test_name: str,
        current: PerformanceBaseline,
        baseline: PerformanceBaseline,
    ) -> RegressionAnalysisResult:
        """Perform detailed regression analysis."""

        # Calculate percentage changes
        latency_change_pct = self._calculate_percentage_change(
            baseline.avg_latency_ms, current.avg_latency_ms
        )
        throughput_change_pct = self._calculate_percentage_change(
            baseline.queries_per_second, current.queries_per_second
        )
        memory_change_pct = self._calculate_percentage_change(
            baseline.memory_usage_mb, current.memory_usage_mb
        )

        # Check for regressions
        latency_regression = (
            latency_change_pct > self.thresholds.max_latency_degradation_pct
            or current.avg_latency_ms > self.thresholds.max_acceptable_latency_ms
        )

        throughput_regression = (
            -throughput_change_pct > self.thresholds.min_throughput_degradation_pct
            or current.queries_per_second < self.thresholds.min_acceptable_qps
        )

        memory_regression = memory_change_pct > self.thresholds.max_memory_increase_pct

        overall_regression = (
            latency_regression or throughput_regression or memory_regression
        )

        # Statistical significance testing
        latency_significant, throughput_significant, confidence = (
            self._test_statistical_significance(current, baseline)
        )

        # Generate recommendations and determine severity
        recommendations = self._generate_recommendations(
            current,
            baseline,
            latency_regression,
            throughput_regression,
            memory_regression,
        )

        severity = self._determine_severity(
            latency_regression,
            throughput_regression,
            memory_regression,
            latency_change_pct,
            throughput_change_pct,
            memory_change_pct,
        )

        return RegressionAnalysisResult(
            test_name=test_name,
            current_performance=current,
            baseline_performance=baseline,
            latency_regression=latency_regression,
            throughput_regression=throughput_regression,
            memory_regression=memory_regression,
            overall_regression=overall_regression,
            latency_change_pct=latency_change_pct,
            throughput_change_pct=throughput_change_pct,
            memory_change_pct=memory_change_pct,
            latency_significant=latency_significant,
            throughput_significant=throughput_significant,
            statistical_confidence=confidence,
            recommendations=recommendations,
            severity=severity,
        )

    def _calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change from old to new value."""
        if old_value == 0:
            return 0 if new_value == 0 else float("inf")
        return ((new_value - old_value) / old_value) * 100

    def _test_statistical_significance(
        self, current: PerformanceBaseline, baseline: PerformanceBaseline
    ) -> Tuple[bool, bool, float]:
        """Test statistical significance of performance changes."""

        latency_significant = False
        throughput_significant = False
        confidence = 0.0

        try:
            # Test latency significance
            if (
                len(current.latency_samples) >= self.thresholds.min_samples_for_stats
                and len(baseline.latency_samples)
                >= self.thresholds.min_samples_for_stats
            ):
                t_stat, p_value = stats.ttest_ind(
                    current.latency_samples, baseline.latency_samples
                )
                latency_significant = p_value < (1 - self.thresholds.confidence_level)
                confidence = max(confidence, 1 - p_value)

            # Test throughput significance
            if (
                len(current.throughput_samples) >= self.thresholds.min_samples_for_stats
                and len(baseline.throughput_samples)
                >= self.thresholds.min_samples_for_stats
            ):
                t_stat, p_value = stats.ttest_ind(
                    current.throughput_samples, baseline.throughput_samples
                )
                throughput_significant = p_value < (
                    1 - self.thresholds.confidence_level
                )
                confidence = max(confidence, 1 - p_value)

        except Exception as e:
            logger.warning(f"Statistical significance testing failed: {e}")

        return latency_significant, throughput_significant, confidence

    def _generate_recommendations(
        self,
        current: PerformanceBaseline,
        baseline: PerformanceBaseline,
        latency_regression: bool,
        throughput_regression: bool,
        memory_regression: bool,
    ) -> List[str]:
        """Generate recommendations based on regression analysis."""

        recommendations = []

        if latency_regression:
            if current.avg_latency_ms > baseline.avg_latency_ms * 1.5:
                recommendations.append(
                    "CRITICAL: Query latency has increased significantly. "
                    "Check for missing indexes or ef_search parameter tuning."
                )
            else:
                recommendations.append(
                    "Query latency has degraded. Consider adjusting ef_search "
                    "or reviewing recent database changes."
                )

        if throughput_regression:
            if current.queries_per_second < baseline.queries_per_second * 0.7:
                recommendations.append(
                    "CRITICAL: Query throughput has dropped significantly. "
                    "Check connection pool configuration and database health."
                )
            else:
                recommendations.append(
                    "Query throughput has declined. Review connection pool "
                    "settings and concurrent query patterns."
                )

        if memory_regression:
            recommendations.append(
                "Memory usage has increased beyond acceptable limits. "
                "Check for memory leaks or inefficient query patterns."
            )

        # Performance optimization recommendations
        if current.avg_latency_ms > 5.0:
            recommendations.append(
                "Consider optimizing HNSW parameters (ef_search) for better latency."
            )

        if current.queries_per_second < 100:
            recommendations.append(
                "Low throughput detected. Consider connection pool optimization "
                "or read replica usage."
            )

        return recommendations

    def _determine_severity(
        self,
        latency_regression: bool,
        throughput_regression: bool,
        memory_regression: bool,
        latency_change_pct: float,
        throughput_change_pct: float,
        memory_change_pct: float,
    ) -> str:
        """Determine severity level of performance regression."""

        # Critical conditions
        if (
            latency_change_pct > 100  # 2x latency increase
            or -throughput_change_pct > 50  # 50% throughput decrease
            or memory_change_pct > 100
        ):  # 2x memory increase
            return "critical"

        # High severity conditions
        if (
            latency_change_pct > 50  # 50% latency increase
            or -throughput_change_pct > 30  # 30% throughput decrease
            or memory_change_pct > 50
        ):  # 50% memory increase
            return "high"

        # Medium severity
        if latency_regression or throughput_regression or memory_regression:
            return "medium"

        # Low severity (minor degradations)
        if (
            latency_change_pct > 10
            or -throughput_change_pct > 10
            or memory_change_pct > 10
        ):
            return "low"

        return "none"

    def _create_no_baseline_result(
        self, test_name: str, current_results: Dict[str, Any]
    ) -> RegressionAnalysisResult:
        """Create result when no baseline is available."""

        current = self._extract_performance_baseline(current_results)

        return RegressionAnalysisResult(
            test_name=test_name,
            current_performance=current,
            baseline_performance=current,  # Use current as baseline
            latency_regression=False,
            throughput_regression=False,
            memory_regression=False,
            overall_regression=False,
            latency_change_pct=0,
            throughput_change_pct=0,
            memory_change_pct=0,
            latency_significant=False,
            throughput_significant=False,
            statistical_confidence=0,
            recommendations=[
                "No baseline available. This result will be used as the new baseline."
            ],
            severity="none",
        )


class PerformanceReporter:
    """Generates performance regression reports."""

    @staticmethod
    def generate_regression_report(
        results: List[RegressionAnalysisResult], output_file: Optional[str] = None
    ) -> str:
        """Generate a comprehensive regression report.

        Args:
            results: List of regression analysis results
            output_file: Optional file to write report to

        Returns:
            Report content as markdown string
        """
        report = []

        # Header
        report.append("# Performance Regression Analysis Report")
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        report.append(f"**Generated:** {timestamp}")
        report.append("")

        # Executive Summary
        regressions = [r for r in results if r.overall_regression]
        critical_issues = [r for r in results if r.severity == "critical"]
        high_issues = [r for r in results if r.severity == "high"]

        report.append("## Executive Summary")
        report.append("")

        if not regressions:
            report.append("✅ **No Performance Regressions Detected**")
        else:
            report.append(f"❌ **{len(regressions)} Performance Regressions Detected**")

            if critical_issues:
                critical_count = len(critical_issues)
                report.append(
                    f"🚨 **{critical_count} Critical Issues "
                    f"Requiring Immediate Attention**"
                )
            if high_issues:
                report.append(f"⚠️ **{len(high_issues)} High Severity Issues**")

        report.append("")

        # Individual Test Results
        report.append("## Test Results")
        report.append("")

        for result in results:
            report.append(f"### {result.test_name}")
            report.append("")

            # Status indicator
            if result.overall_regression:
                status_emoji = "❌" if result.severity in ["critical", "high"] else "⚠️"
                severity = result.severity.upper()
                report.append(
                    f"{status_emoji} **Status:** Regression Detected ({severity})"
                )
            else:
                report.append("✅ **Status:** Performance Acceptable")

            report.append("")

            # Performance Changes
            report.append("**Performance Changes:**")
            report.append(
                f"- Latency: {result.latency_change_pct:+.1f}% "
                f"({result.baseline_performance.avg_latency_ms:.2f}ms → "
                f"{result.current_performance.avg_latency_ms:.2f}ms)"
            )
            report.append(
                f"- Throughput: {result.throughput_change_pct:+.1f}% "
                f"({result.baseline_performance.queries_per_second:.1f} → "
                f"{result.current_performance.queries_per_second:.1f} QPS)"
            )
            report.append(
                f"- Memory: {result.memory_change_pct:+.1f}% "
                f"({result.baseline_performance.memory_usage_mb:.1f} → "
                f"{result.current_performance.memory_usage_mb:.1f} MB)"
            )
            report.append("")

            # Recommendations
            if result.recommendations:
                report.append("**Recommendations:**")
                for rec in result.recommendations:
                    report.append(f"- {rec}")
                report.append("")

        # Summary Table
        report.append("## Summary Table")
        report.append("")
        report.append(
            "| Test | Status | Latency Change | Throughput Change | "
            "Memory Change | Severity |"
        )
        report.append(
            "|------|--------|----------------|-------------------|---------------|----------|"
        )

        for result in results:
            status = "PASS" if not result.overall_regression else "FAIL"
            report.append(
                f"| {result.test_name} | {status} | "
                f"{result.latency_change_pct:+.1f}% | "
                f"{result.throughput_change_pct:+.1f}% | "
                f"{result.memory_change_pct:+.1f}% | "
                f"{result.severity.upper()} |"
            )

        report.append("")

        report_content = "\n".join(report)

        # Write to file if specified
        if output_file:
            with open(output_file, "w") as f:
                f.write(report_content)
            logger.info(f"Regression report written to {output_file}")

        return report_content


# CLI utility functions
def setup_baseline_from_benchmark_results(
    benchmark_results_file: str,
    baseline_dir: str = "./baselines",
    version: str = "unknown",
) -> None:
    """Set up baselines from benchmark results file.

    Args:
        benchmark_results_file: Path to benchmark results JSON file
        baseline_dir: Directory to store baselines
        version: Version identifier for the baseline
    """
    with open(benchmark_results_file) as f:
        results = json.load(f)

    manager = BaselineManager(baseline_dir)

    # Extract and save baselines for different test types
    if "optimized_query_metrics" in results:
        for metric in results["optimized_query_metrics"]:
            test_name = metric["test_name"]
            performance_data = {
                "avg_latency_ms": metric["avg_latency_ms"],
                "p95_latency_ms": metric["p95_latency_ms"],
                "queries_per_second": metric["queries_per_second"],
                "memory_usage_mb": metric["memory_usage_mb"],
                "success_rate": metric["success_rate"],
            }
            manager.save_baseline(test_name, performance_data, version)

    logger.info(f"Baselines saved from {benchmark_results_file}")


def check_for_regressions(
    benchmark_results_file: str,
    baseline_dir: str = "./baselines",
    output_file: Optional[str] = None,
) -> bool:
    """Check for performance regressions and generate report.

    Args:
        benchmark_results_file: Path to current benchmark results
        baseline_dir: Directory containing baselines
        output_file: Optional file to write regression report

    Returns:
        True if no regressions detected, False otherwise (for CI/CD exit code)
    """
    with open(benchmark_results_file) as f:
        results = json.load(f)

    manager = BaselineManager(baseline_dir)
    detector = RegressionDetector(manager)

    analysis_results = []

    # Analyze optimized query metrics
    if "optimized_query_metrics" in results:
        for metric in results["optimized_query_metrics"]:
            test_name = metric["test_name"]
            analysis = detector.analyze_performance(test_name, metric)
            analysis_results.append(analysis)

    # Generate report
    if output_file:
        PerformanceReporter.generate_regression_report(analysis_results, output_file)
    else:
        report = PerformanceReporter.generate_regression_report(analysis_results)
        print(report)

    # Return status for CI/CD
    regressions_detected = any(r.overall_regression for r in analysis_results)
    critical_issues = any(r.severity == "critical" for r in analysis_results)

    if critical_issues:
        logger.error("Critical performance regressions detected!")
        return False
    elif regressions_detected:
        logger.warning("Performance regressions detected")
        return False
    else:
        logger.info("No performance regressions detected")
        return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python regression_detector.py <command> [args...]")
        print("Commands:")
        print("  setup-baseline <results_file> [baseline_dir] [version]")
        print("  check-regression <results_file> [baseline_dir] [output_file]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "setup-baseline":
        results_file = sys.argv[2]
        baseline_dir = sys.argv[3] if len(sys.argv) > 3 else "./baselines"
        version = sys.argv[4] if len(sys.argv) > 4 else "unknown"
        setup_baseline_from_benchmark_results(results_file, baseline_dir, version)

    elif command == "check-regression":
        results_file = sys.argv[2]
        baseline_dir = sys.argv[3] if len(sys.argv) > 3 else "./baselines"
        output_file = sys.argv[4] if len(sys.argv) > 4 else None

        success = check_for_regressions(results_file, baseline_dir, output_file)
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
