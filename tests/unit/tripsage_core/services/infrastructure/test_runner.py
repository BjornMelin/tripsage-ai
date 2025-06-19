"""
Comprehensive test runner for DatabaseService test suite.

This module provides a centralized test runner that executes the complete
DatabaseService test suite with proper configuration, reporting, and
coverage analysis.

Features:
- Multi-layer test execution (unit, integration, performance, chaos)
- Coverage reporting with fail-under=90%
- Benchmark result collection and analysis
- Mutation testing integration
- Test categorization and filtering
- Parallel test execution
- Detailed reporting and metrics

Usage:
    python test_runner.py --all                    # Run all tests
    python test_runner.py --unit                   # Unit tests only
    python test_runner.py --integration            # Integration tests
    python test_runner.py --performance            # Performance benchmarks
    python test_runner.py --chaos                  # Chaos engineering tests
    python test_runner.py --coverage               # Generate coverage report
    python test_runner.py --mutation               # Run mutation testing
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pytest


class DatabaseServiceTestRunner:
    """Comprehensive test runner for DatabaseService tests."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_dir = project_root / "tests"
        self.infrastructure_tests = (
            self.test_dir / "unit" / "tripsage_core" / "services" / "infrastructure"
        )
        self.integration_tests = self.test_dir / "integration"
        self.coverage_dir = project_root / "coverage"
        self.reports_dir = project_root / "test_reports"

        # Ensure directories exist
        self.coverage_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

    def run_unit_tests(
        self, verbose: bool = True, coverage: bool = True
    ) -> Dict[str, Any]:
        """Run unit tests for DatabaseService."""
        print("🧪 Running DatabaseService unit tests...")

        test_files = [
            str(self.infrastructure_tests / "test_database_service_comprehensive.py"),
            str(self.infrastructure_tests / "test_database_service_stateful.py"),
        ]

        pytest_args = [
            "--verbose" if verbose else "--quiet",
            "--tb=short",
            "-ra",
            "--strict-markers",
            "--disable-warnings",
            "-m",
            "not slow and not integration and not chaos",
        ]

        if coverage:
            pytest_args.extend(
                [
                    f"--cov={self.project_root / 'tripsage_core' / 'services' / 'infrastructure'}",  # noqa: E501
                    "--cov-report=html:" + str(self.coverage_dir / "unit_html"),
                    "--cov-report=xml:" + str(self.coverage_dir / "unit_coverage.xml"),
                    "--cov-report=term-missing",
                    "--cov-fail-under=90",
                    "--cov-branch",
                ]
            )

        pytest_args.extend(test_files)

        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        result = {
            "test_type": "unit",
            "exit_code": exit_code,
            "duration": duration,
            "success": exit_code == 0,
            "test_files": test_files,
        }

        print(f"✅ Unit tests completed in {duration:.2f}s (exit code: {exit_code})")
        return result

    def run_performance_tests(
        self, benchmark_save: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run performance benchmark tests."""
        print("🚀 Running DatabaseService performance tests...")

        test_files = [
            str(self.infrastructure_tests / "test_database_service_performance.py"),
        ]

        pytest_args = [
            "--verbose",
            "--tb=short",
            "-ra",
            "--strict-markers",
            "--disable-warnings",
            "-m",
            "performance",
            "--benchmark-only",
            "--benchmark-warmup=on",
            "--benchmark-sort=mean",
            "--benchmark-columns=min,max,mean,stddev,median,iqr,outliers,ops,rounds",
        ]

        if benchmark_save:
            pytest_args.extend(
                [
                    f"--benchmark-save={benchmark_save}",
                    f"--benchmark-save-data={self.reports_dir / 'benchmark_data.json'}",
                ]
            )

        pytest_args.extend(test_files)

        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        result = {
            "test_type": "performance",
            "exit_code": exit_code,
            "duration": duration,
            "success": exit_code == 0,
            "test_files": test_files,
            "benchmark_save": benchmark_save,
        }

        print(
            f"⚡ Performance tests completed in {duration:.2f}s "
            f"(exit code: {exit_code})"
        )
        return result

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests with real database scenarios."""
        print("🔌 Running DatabaseService integration tests...")

        test_files = [
            str(self.integration_tests / "test_database_service_integration.py"),
        ]

        pytest_args = [
            "--verbose",
            "--tb=short",
            "-ra",
            "--strict-markers",
            "--disable-warnings",
            "-m",
            "integration",
            "--run-integration",  # Enable integration tests
        ]

        pytest_args.extend(test_files)

        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        result = {
            "test_type": "integration",
            "exit_code": exit_code,
            "duration": duration,
            "success": exit_code == 0,
            "test_files": test_files,
        }

        print(
            f"🔗 Integration tests completed in {duration:.2f}s "
            f"(exit code: {exit_code})"
        )
        return result

    def run_chaos_tests(self) -> Dict[str, Any]:
        """Run chaos engineering and load tests."""
        print("💥 Running DatabaseService chaos engineering tests...")

        test_files = [
            str(self.infrastructure_tests / "test_database_service_chaos.py"),
        ]

        pytest_args = [
            "--verbose",
            "--tb=short",
            "-ra",
            "--strict-markers",
            "--disable-warnings",
            "-m",
            "chaos",
            "--run-load-tests",  # Enable load tests
        ]

        pytest_args.extend(test_files)

        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        result = {
            "test_type": "chaos",
            "exit_code": exit_code,
            "duration": duration,
            "success": exit_code == 0,
            "test_files": test_files,
        }

        print(f"🌪️ Chaos tests completed in {duration:.2f}s (exit code: {exit_code})")
        return result

    def run_property_tests(self) -> Dict[str, Any]:
        """Run property-based tests with Hypothesis."""
        print("🎲 Running DatabaseService property-based tests...")

        test_files = [
            str(self.infrastructure_tests / "test_database_service_comprehensive.py"),
            str(self.infrastructure_tests / "test_database_service_stateful.py"),
        ]

        pytest_args = [
            "--verbose",
            "--tb=short",
            "-ra",
            "--strict-markers",
            "--disable-warnings",
            "-m",
            "property or stateful",
        ]

        pytest_args.extend(test_files)

        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        result = {
            "test_type": "property",
            "exit_code": exit_code,
            "duration": duration,
            "success": exit_code == 0,
            "test_files": test_files,
        }

        print(
            f"🎯 Property tests completed in {duration:.2f}s (exit code: {exit_code})"
        )
        return result

    def generate_coverage_report(self) -> Dict[str, Any]:
        """Generate comprehensive coverage report."""
        print("📊 Generating comprehensive coverage report...")

        # Run all tests with coverage
        test_patterns = [
            str(self.infrastructure_tests / "test_database_service_comprehensive.py"),
            str(self.infrastructure_tests / "test_database_service_performance.py"),
            str(self.infrastructure_tests / "test_database_service_stateful.py"),
            str(self.infrastructure_tests / "test_database_service_chaos.py"),
        ]

        pytest_args = [
            "--quiet",
            "--tb=no",
            "--disable-warnings",
            "-m",
            "not slow and not integration",  # Skip slow tests for coverage
            f"--cov={self.project_root / 'tripsage_core' / 'services' / 'infrastructure'}",  # noqa: E501
            "--cov-report=html:" + str(self.coverage_dir / "comprehensive_html"),
            "--cov-report=xml:" + str(self.coverage_dir / "comprehensive_coverage.xml"),
            "--cov-report=json:" + str(self.coverage_dir / "coverage.json"),
            "--cov-report=term-missing",
            "--cov-fail-under=90",
            "--cov-branch",
            "--cov-config=" + str(self.project_root / "pyproject.toml"),
        ]

        pytest_args.extend(test_patterns)

        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        duration = time.time() - start_time

        # Parse coverage results
        coverage_data = self._parse_coverage_json()

        result = {
            "test_type": "coverage",
            "exit_code": exit_code,
            "duration": duration,
            "success": exit_code == 0,
            "coverage_data": coverage_data,
            "reports": {
                "html": str(self.coverage_dir / "comprehensive_html" / "index.html"),
                "xml": str(self.coverage_dir / "comprehensive_coverage.xml"),
                "json": str(self.coverage_dir / "coverage.json"),
            },
        }

        print(f"📈 Coverage report generated in {duration:.2f}s")
        if coverage_data:
            print(
                f"📊 Coverage: "
                f"{coverage_data.get('totals', {}).get('percent_covered', 0):.1f}%"
            )

        return result

    def run_mutation_testing(self) -> Dict[str, Any]:
        """Run mutation testing to validate test quality."""
        print("🧬 Running mutation testing...")

        # Check if mutmut is available
        try:
            import mutmut  # noqa: F401
        except ImportError:
            print("⚠️ mutmut not installed. Install with: pip install mutmut")
            return {
                "test_type": "mutation",
                "exit_code": 1,
                "success": False,
                "error": "mutmut not installed",
            }

        # Run mutation testing on DatabaseService
        target_module = str(
            self.project_root
            / "tripsage_core"
            / "services"
            / "infrastructure"
            / "database_service.py"
        )

        # Configure mutation testing
        mutation_config = {
            "paths_to_mutate": [target_module],
            "tests_dir": str(self.infrastructure_tests),
            "runner": "python -m pytest",
        }

        start_time = time.time()

        try:
            # Run mutmut
            cmd = [
                "python",
                "-m",
                "mutmut",
                "run",
                "--paths-to-mutate",
                target_module,
                "--tests-dir",
                str(self.infrastructure_tests),
                "--runner",
                "python -m pytest",
            ]

            result_proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=1800,  # 30 minute timeout
            )

            duration = time.time() - start_time

            result = {
                "test_type": "mutation",
                "exit_code": result_proc.returncode,
                "duration": duration,
                "success": result_proc.returncode == 0,
                "stdout": result_proc.stdout,
                "stderr": result_proc.stderr,
                "config": mutation_config,
            }

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            result = {
                "test_type": "mutation",
                "exit_code": 124,  # Timeout exit code
                "duration": duration,
                "success": False,
                "error": "Mutation testing timed out after 30 minutes",
            }

        except Exception as e:
            duration = time.time() - start_time
            result = {
                "test_type": "mutation",
                "exit_code": 1,
                "duration": duration,
                "success": False,
                "error": str(e),
            }

        print(f"🔬 Mutation testing completed in {duration:.2f}s")
        return result

    def run_all_tests(self, skip_slow: bool = False) -> Dict[str, Any]:
        """Run the complete test suite."""
        print("🎯 Running complete DatabaseService test suite...")

        start_time = time.time()
        results = {}

        # Run tests in order of increasing complexity/time
        test_suites = [
            ("unit", self.run_unit_tests),
            ("property", self.run_property_tests),
            ("performance", lambda: self.run_performance_tests("comprehensive")),
        ]

        if not skip_slow:
            test_suites.extend(
                [
                    ("integration", self.run_integration_tests),
                    ("chaos", self.run_chaos_tests),
                ]
            )

        # Run each test suite
        for suite_name, suite_runner in test_suites:
            print(f"\n{'=' * 60}")
            print(f"Running {suite_name} tests...")
            print(f"{'=' * 60}")

            try:
                results[suite_name] = suite_runner()
            except Exception as e:
                results[suite_name] = {
                    "test_type": suite_name,
                    "exit_code": 1,
                    "success": False,
                    "error": str(e),
                }
                print(f"❌ {suite_name} tests failed with error: {e}")

        # Generate comprehensive coverage report
        print(f"\n{'=' * 60}")
        print("Generating coverage report...")
        print(f"{'=' * 60}")

        try:
            results["coverage"] = self.generate_coverage_report()
        except Exception as e:
            results["coverage"] = {
                "test_type": "coverage",
                "success": False,
                "error": str(e),
            }

        total_duration = time.time() - start_time

        # Summary
        successful_suites = sum(1 for r in results.values() if r.get("success", False))
        total_suites = len(results)

        summary = {
            "total_duration": total_duration,
            "successful_suites": successful_suites,
            "total_suites": total_suites,
            "success_rate": successful_suites / total_suites,
            "results": results,
        }

        print(f"\n{'=' * 60}")
        print("📋 TEST SUITE SUMMARY")
        print(f"{'=' * 60}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Successful suites: {successful_suites}/{total_suites}")
        print(f"Success rate: {summary['success_rate']:.1%}")
        print(f"{'=' * 60}")

        for suite_name, result in results.items():
            status = "✅" if result.get("success", False) else "❌"
            duration = result.get("duration", 0)
            print(f"{status} {suite_name}: {duration:.2f}s")

        return summary

    def _parse_coverage_json(self) -> Optional[Dict[str, Any]]:
        """Parse coverage JSON report."""
        coverage_json_path = self.coverage_dir / "coverage.json"

        if not coverage_json_path.exists():
            return None

        try:
            with open(coverage_json_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not parse coverage JSON: {e}")
            return None

    def save_test_report(self, results: Dict[str, Any]) -> Path:
        """Save comprehensive test report."""
        report_path = self.reports_dir / f"test_report_{int(time.time())}.json"

        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"📄 Test report saved to: {report_path}")
        return report_path


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for DatabaseService"
    )

    # Test type selection
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests"
    )
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests"
    )
    parser.add_argument(
        "--chaos", action="store_true", help="Run chaos engineering tests"
    )
    parser.add_argument(
        "--property", action="store_true", help="Run property-based tests"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument("--mutation", action="store_true", help="Run mutation testing")

    # Options
    parser.add_argument("--skip-slow", action="store_true", help="Skip slow tests")
    parser.add_argument("--benchmark-save", help="Save benchmark results")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--save-report", action="store_true", help="Save test report")

    args = parser.parse_args()

    # Find project root
    current_dir = Path(__file__).parent
    project_root = current_dir
    while project_root.parent != project_root:
        if (project_root / "pyproject.toml").exists():
            break
        project_root = project_root.parent
    else:
        print("❌ Could not find project root (pyproject.toml)")
        sys.exit(1)

    # Initialize test runner
    runner = DatabaseServiceTestRunner(project_root)

    # Determine what tests to run
    if args.all:
        results = runner.run_all_tests(skip_slow=args.skip_slow)
    elif args.unit:
        results = {"unit": runner.run_unit_tests(verbose=not args.quiet)}
    elif args.integration:
        results = {"integration": runner.run_integration_tests()}
    elif args.performance:
        results = {"performance": runner.run_performance_tests(args.benchmark_save)}
    elif args.chaos:
        results = {"chaos": runner.run_chaos_tests()}
    elif args.property:
        results = {"property": runner.run_property_tests()}
    elif args.coverage:
        results = {"coverage": runner.generate_coverage_report()}
    elif args.mutation:
        results = {"mutation": runner.run_mutation_testing()}
    else:
        # Default to unit tests
        print("No test type specified, running unit tests...")
        results = {"unit": runner.run_unit_tests(verbose=not args.quiet)}

    # Save report if requested
    if args.save_report:
        runner.save_test_report(results)

    # Exit with appropriate code
    if isinstance(results, dict) and "success_rate" in results:
        # Multiple test suites
        exit_code = 0 if results["success_rate"] == 1.0 else 1
    else:
        # Single test suite
        exit_code = 0 if all(r.get("success", False) for r in results.values()) else 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
