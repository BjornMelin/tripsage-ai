"""test runner for Supabase schema integration tests.

This module provides a test runner that orchestrates all schema-related tests
with proper setup, teardown, and reporting.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class SchemaTestError(Exception):
    """Base exception for schema test runner errors."""


class SchemaValidationError(SchemaTestError):
    """Raised when schema validation fails."""


class TestExecutionError(SchemaTestError):
    """Raised when test execution fails."""


class ConfigurationError(SchemaTestError):
    """Raised when test configuration is invalid."""


class TestEnvironmentError(SchemaTestError):
    """Raised when test environment is not properly set up."""


class SchemaTestRunner:
    """Orchestrates schema integration tests with setup and reporting."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize runner with optional configuration overrides."""
        self.config = config or self._default_config()
        self._validate_config()
        self.test_results = {}
        self.start_time = None
        self.end_time = None

    def _validate_config(self):
        """Validate test configuration."""
        required_keys = ["test_types", "performance_thresholds", "test_data_size"]
        for key in required_keys:
            if key not in self.config:
                raise ConfigurationError(f"Missing required configuration key: {key}")

        if not isinstance(self.config["test_types"], list):
            raise ConfigurationError("test_types must be a list")

        if not self.config["test_types"]:
            raise ConfigurationError("test_types cannot be empty")

        # Validate performance thresholds
        thresholds = self.config.get("performance_thresholds", {})
        if not isinstance(thresholds, dict):
            raise ConfigurationError("performance_thresholds must be a dictionary")

        required_thresholds = [
            "query_timeout",
            "memory_search_timeout",
            "collaboration_query_timeout",
        ]
        for threshold in required_thresholds:
            if threshold not in thresholds:
                raise ConfigurationError(f"Missing performance threshold: {threshold}")
            if not isinstance(thresholds[threshold], (int, float)):
                raise ConfigurationError(
                    f"Performance threshold {threshold} must be numeric"
                )

    def _default_config(self) -> dict[str, Any]:
        """Get default test configuration."""
        return {
            "test_types": [
                "schema_validation",
                "rls_policies",
                "foreign_key_constraints",
                "index_performance",
                "database_functions",
                "collaboration_workflows",
                "multi_user_scenarios",
                "security_isolation",
                "migration_safety",
                "performance_benchmarks",
            ],
            "performance_thresholds": {
                "query_timeout": 30.0,
                "memory_search_timeout": 5.0,
                "collaboration_query_timeout": 2.0,
            },
            "test_data_size": {
                "users": 50,
                "trips": 100,
                "memories_per_user": 20,
                "collaborators_per_trip": 5,
            },
            "parallel_execution": True,
            "max_workers": 4,
            "verbose_output": True,
            "generate_report": True,
            "cleanup_after_run": True,
        }

    async def run_all_tests(self) -> dict[str, Any]:
        """Run all schema integration tests."""
        self.start_time = datetime.utcnow()

        try:
            # Pre-test validation
            await self._pre_test_validation()

            # Run test suites
            results = await self._execute_test_suites()

            # Post-test analysis
            analysis = await self._post_test_analysis(results)

            # Generate reports
            if self.config["generate_report"]:
                await self._generate_test_report(results, analysis)

            return self._create_success_result(results, analysis)

        except (TestExecutionError, TestEnvironmentError, ConfigurationError) as e:
            return self._create_error_result(e)
        except Exception as e:  # noqa: BLE001
            return self._create_error_result(e, "UnexpectedError")

        finally:
            self.end_time = datetime.utcnow()
            if self.config["cleanup_after_run"]:
                await self._cleanup()

    def _create_success_result(
        self, results: dict[str, Any], analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a success result dictionary."""
        return {
            "success": True,
            "results": results,
            "analysis": analysis,
            "duration": self._get_duration(),
        }

    def _create_error_result(
        self, error: Exception, error_type: str | None = None
    ) -> dict[str, Any]:
        """Create an error result dictionary."""
        return {
            "success": False,
            "error": str(error),
            "error_type": error_type or type(error).__name__,
            "duration": self._get_duration(),
        }

    def _get_duration(self) -> float:
        """Get the test execution duration."""
        return (
            (datetime.utcnow() - self.start_time).total_seconds()
            if self.start_time
            else 0.0
        )

    async def _pre_test_validation(self):
        """Validate test environment before running tests."""
        # Validate required files exist
        self._validate_required_files(
            Path(__file__).parent.parent.parent / "supabase" / "schemas",
            [
                "01_tables.sql",
                "02_indexes.sql",
                "03_functions.sql",
                "05_policies.sql",
            ],
        )

        self._validate_required_files(
            Path(__file__).parent.parent.parent / "supabase" / "migrations",
            [
                "20250609_02_consolidated_production_schema.sql",
                "20250610_01_fix_user_id_constraints.sql",
            ],
        )

    def _validate_required_files(self, directory: Path, filenames: list[str]):
        """Validate that all required files exist in the given directory."""
        for filename in filenames:
            if not (directory / filename).exists():
                raise TestEnvironmentError(f"Required file not found: {filename}")

    async def _execute_test_suites(self) -> dict[str, Any]:
        """Execute all test suites."""
        results = {}

        for suite in self._get_test_suites():
            if suite["name"] in self.config["test_types"]:
                suite_result = await self._run_test_suite(suite)
                results[suite["name"]] = suite_result

        return results

    def _get_test_suites(self) -> list[dict[str, str]]:
        """Get the list of available test suites."""
        base_module = "test_supabase_collaboration_schema"
        perf_module = "test_collaboration_performance"

        return [
            self._create_test_suite(
                "schema_validation",
                f"{base_module}::TestRLSPolicyValidation",
                "RLS policy validation tests",
            ),
            self._create_test_suite(
                "foreign_key_constraints",
                f"{base_module}::TestForeignKeyConstraints",
                "Foreign key constraint tests",
            ),
            self._create_test_suite(
                "index_performance",
                f"{base_module}::TestIndexPerformance",
                "Database index performance tests",
            ),
            self._create_test_suite(
                "database_functions",
                f"{base_module}::TestDatabaseFunctions",
                "Database function correctness tests",
            ),
            self._create_test_suite(
                "collaboration_workflows",
                f"{base_module}::TestCollaborationWorkflows",
                "End-to-end collaboration workflow tests",
            ),
            self._create_test_suite(
                "multi_user_scenarios",
                f"{base_module}::TestMultiUserScenarios",
                "Complex multi-user scenario tests",
            ),
            self._create_test_suite(
                "security_isolation",
                f"{base_module}::TestSecurityIsolation",
                "Security isolation and boundary tests",
            ),
            self._create_test_suite(
                "performance_optimization",
                f"{base_module}::TestPerformanceOptimization",
                "Performance optimization tests",
            ),
            self._create_test_suite(
                "migration_compatibility",
                f"{base_module}::TestMigrationCompatibility",
                "Migration safety and compatibility tests",
            ),
            self._create_test_suite(
                "collaboration_performance",
                f"{perf_module}::CollaborationPerformanceTestSuite",
                "Collaboration feature performance tests",
            ),
        ]

    def _create_test_suite(
        self, name: str, module: str, description: str
    ) -> dict[str, str]:
        """Create a test suite configuration dictionary."""
        return {"name": name, "module": module, "description": description}

    async def _run_test_suite(self, suite: dict[str, str]) -> dict[str, Any]:
        """Run a single test suite."""
        start_time = time.time()

        try:
            # Mock pytest execution (in real implementation, would use pytest.main())
            await asyncio.sleep(0.1)  # Simulate test execution time

            # Simulate test results - in real implementation, would parse
            # actual test output
            test_count = 10  # Mock test count
            passed = test_count - 1  # Mock one failure for demonstration
            failed = 1

            duration = time.time() - start_time

            if failed > 0:
                raise TestExecutionError(
                    f"Test suite '{suite['name']}' failed: {failed}/{test_count} "
                    "tests failed"
                )

            return self._create_test_result(
                suite, True, test_count, passed, failed, duration
            )

        except TestExecutionError as e:
            return self._create_test_result(
                suite,
                False,
                error=str(e),
                error_type="TestExecutionError",
                duration=time.time() - start_time,
            )
        except Exception as e:  # noqa: BLE001
            return self._create_test_result(
                suite,
                False,
                error=str(e),
                error_type="UnexpectedError",
                duration=time.time() - start_time,
            )

    def _create_test_result(
        self,
        suite: dict[str, str],
        success: bool,
        total_tests: int = 0,
        passed: int = 0,
        failed: int = 0,
        duration: float = 0.0,
        error: str | None = None,
        error_type: str | None = None,
    ) -> dict[str, Any]:
        """Create a test result dictionary."""
        result = {
            "success": success,
            "duration": duration,
            "details": {
                "module": suite["module"],
                "description": suite["description"],
            },
        }

        if success:
            result.update(
                {
                    "total_tests": total_tests,
                    "passed": passed,
                    "failed": failed,
                }
            )
        else:
            result.update(
                {
                    "error": error,
                    "error_type": error_type,
                }
            )

        return result

    async def _post_test_analysis(self, results: dict[str, Any]) -> dict[str, Any]:
        """Analyze test results and generate insights."""
        total_tests = sum(r.get("total_tests", 0) for r in results.values())
        total_passed = sum(r.get("passed", 0) for r in results.values())
        total_failed = sum(r.get("failed", 0) for r in results.values())
        total_duration = sum(r.get("duration", 0) for r in results.values())

        success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0

        # Identify performance issues
        slow_tests = []
        for suite_name, result in results.items():
            if result.get("duration", 0) > 5.0:  # Tests taking longer than 5 seconds
                slow_tests.append({"suite": suite_name, "duration": result["duration"]})

        # Identify failed test patterns
        failed_suites = [
            {"suite": name, "error": result.get("error")}
            for name, result in results.items()
            if not result.get("success", True)
        ]

        return {
            "summary": {
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "success_rate": success_rate,
                "total_duration": total_duration,
            },
            "performance": {
                "slow_tests": slow_tests,
                "average_test_duration": total_duration / len(results)
                if results
                else 0,
            },
            "failures": {
                "failed_suites": failed_suites,
                "failure_rate": (len(failed_suites) / len(results)) * 100
                if results
                else 0,
            },
            "recommendations": self._generate_recommendations(
                results, slow_tests, failed_suites
            ),
        }

    def _generate_recommendations(
        self,
        results: dict[str, Any],
        slow_tests: list[dict[str, Any]],
        failed_suites: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Performance recommendations
        if slow_tests:
            recommendations.append(
                f"Consider optimizing {len(slow_tests)} slow test suites for "
                "better CI/CD performance"
            )

        # Failure recommendations
        if failed_suites:
            recommendations.append(
                f"Address {len(failed_suites)} failing test suites before "
                "production deployment"
            )

        # Schema-specific recommendations
        schema_tests = ["schema_validation", "rls_policies", "foreign_key_constraints"]
        schema_failures = [
            suite
            for suite in failed_suites
            if any(schema_test in suite["suite"] for schema_test in schema_tests)
        ]

        if schema_failures:
            recommendations.append(
                "Critical schema validation failures detected - "
                "review database migration safety"
            )

        # Performance test recommendations
        perf_tests = [
            "index_performance",
            "collaboration_performance",
            "performance_optimization",
        ]
        perf_issues = [
            test
            for test in slow_tests
            if any(perf_test in test["suite"] for perf_test in perf_tests)
        ]

        if perf_issues:
            recommendations.append(
                "Performance tests indicate potential scalability issues - "
                "review indexing strategy"
            )

        # Security recommendations
        security_tests = ["security_isolation", "rls_policies"]
        security_failures = [
            suite
            for suite in failed_suites
            if any(sec_test in suite["suite"] for sec_test in security_tests)
        ]

        if security_failures:
            recommendations.append(
                "Security test failures detected - review RLS policies and "
                "data isolation"
            )

        if not recommendations:
            recommendations.append(
                "All tests passing - schema is ready for production deployment"
            )

        return recommendations

    async def _generate_test_report(
        self, results: dict[str, Any], analysis: dict[str, Any]
    ):
        """Generate test report."""
        report = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "duration": (
                    (self.end_time - self.start_time).total_seconds()
                    if self.end_time is not None and self.start_time is not None
                    else None
                ),
                "config": self.config,
            },
            "results": results,
            "analysis": analysis,
            "environment": {
                "python_version": sys.version,
                "test_runner_version": "1.0.0",
            },
        }

        # Save report to file
        report_path = Path(__file__).parent.parent.parent / "test_reports"
        report_path.mkdir(exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_file = report_path / f"schema_integration_test_report_{timestamp}.json"

        with report_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        # Generate human-readable summary
        self._print_test_summary(analysis)

    def _print_test_summary(self, analysis: dict[str, Any]):
        """Print human-readable test summary."""
        summary = analysis["summary"]

        print("\n" + "=" * 80)
        print("SUPABASE SCHEMA INTEGRATION TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['total_passed']}")
        print(f"Failed: {summary['total_failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print()

        if analysis["failures"]["failed_suites"]:
            print("FAILED TEST SUITES:")
            for failure in analysis["failures"]["failed_suites"]:
                print(
                    f"  ❌ {failure['suite']}: {failure.get('error', 'Unknown error')}"
                )
            print()

        if analysis["performance"]["slow_tests"]:
            print("SLOW TEST SUITES:")
            for slow_test in analysis["performance"]["slow_tests"]:
                print(f"  ⚠️  {slow_test['suite']}: {slow_test['duration']:.2f}s")
            print()

        print("RECOMMENDATIONS:")
        for recommendation in analysis["recommendations"]:
            print(f"  💡 {recommendation}")

        print("=" * 80)

    async def _cleanup(self):
        """Cleanup test resources."""
        # Cleanup logic would go here
        # In a real implementation, this would clean up test databases, files, etc.


# CLI interface for running tests
async def main():
    """Main entry point for test runner."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Supabase schema integration tests"
    )
    parser.add_argument("--config", help="Path to test configuration file")
    parser.add_argument("--test-types", nargs="+", help="Specific test types to run")
    parser.add_argument(
        "--performance-only", action="store_true", help="Run only performance tests"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Run quick test suite only"
    )

    args = parser.parse_args()
    config = load_config(args)

    # Run tests
    try:
        runner = SchemaTestRunner(config)
        result = await runner.run_all_tests()
        sys.exit(0 if result["success"] else 1)
    except (ConfigurationError, TestEnvironmentError):
        print("Configuration or environment error", file=sys.stderr)
        sys.exit(1)
    except Exception:  # noqa: BLE001
        print("Unexpected error", file=sys.stderr)
        sys.exit(1)


def load_config(args) -> dict[str, Any]:
    """Load and configure test settings from CLI arguments."""
    config = {}
    if args.config:
        config_path = Path(args.config)
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

    # Override config with CLI arguments
    if args.test_types:
        config["test_types"] = args.test_types
    elif args.performance_only:
        config["test_types"] = ["collaboration_performance", "performance_optimization"]
    elif args.quick:
        config["test_types"] = [
            "schema_validation",
            "rls_policies",
            "foreign_key_constraints",
        ]

    return config


__all__ = [
    "ConfigurationError",
    "SchemaTestError",
    "SchemaTestRunner",
    "SchemaValidationError",
    "TestEnvironmentError",
    "TestExecutionError",
    "load_config",
    "main",
]


if __name__ == "__main__":
    asyncio.run(main())
