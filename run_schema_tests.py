#!/usr/bin/env python3
"""
Quick script to run Supabase schema integration tests.

Usage examples:
    python run_schema_tests.py                    # Run quick validation tests
    python run_schema_tests.py --full             # Run full test suite
    python run_schema_tests.py --performance      # Run performance tests only
    python run_schema_tests.py --help             # Show help
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.integration.test_schema_runner import SchemaTestRunner


async def main():
    """Main entry point for schema tests."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Supabase schema integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_schema_tests.py                    # Quick validation tests
    python run_schema_tests.py --full             # Complete test suite
    python run_schema_tests.py --performance      # Performance tests only
    python run_schema_tests.py --security         # Security tests only
    python run_schema_tests.py --verbose          # Detailed output
        """,
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete test suite (default: quick tests only)",
    )

    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )

    parser.add_argument(
        "--security", action="store_true", help="Run security and RLS tests only"
    )

    parser.add_argument(
        "--migration", action="store_true", help="Run migration safety tests only"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output with detailed logging",
    )

    parser.add_argument(
        "--no-report", action="store_true", help="Skip generating test report"
    )

    args = parser.parse_args()

    # Configure test runner based on arguments
    config = {
        "verbose_output": args.verbose,
        "generate_report": not args.no_report,
        "cleanup_after_run": True,
    }

    # Determine which tests to run
    if args.performance:
        config["test_types"] = [
            "collaboration_performance",
            "index_performance",
            "performance_optimization",
        ]
        print("🚀 Running performance tests...")

    elif args.security:
        config["test_types"] = [
            "rls_policies",
            "security_isolation",
            "foreign_key_constraints",
        ]
        print("🔒 Running security tests...")

    elif args.migration:
        config["test_types"] = ["migration_compatibility", "schema_validation"]
        print("🔄 Running migration safety tests...")

    elif args.full:
        # Run all tests
        config["test_types"] = [
            "schema_validation",
            "rls_policies",
            "foreign_key_constraints",
            "index_performance",
            "database_functions",
            "collaboration_workflows",
            "multi_user_scenarios",
            "security_isolation",
            "migration_compatibility",
            "performance_optimization",
        ]
        print("🧪 Running complete test suite...")

    else:
        # Quick tests (default)
        config["test_types"] = [
            "schema_validation",
            "rls_policies",
            "foreign_key_constraints",
            "database_functions",
        ]
        print("⚡ Running quick validation tests...")

    # Initialize and run test runner
    runner = SchemaTestRunner(config)

    try:
        print("\n" + "=" * 60)
        print("SUPABASE SCHEMA INTEGRATION TESTS")
        print("=" * 60)

        result = await runner.run_all_tests()

        if result["success"]:
            print("\n✅ All tests completed successfully!")
            if result.get("analysis", {}).get("summary", {}).get("total_failed", 0) > 0:
                print(
                    f"⚠️  {result['analysis']['summary']['total_failed']} tests failed"
                )
                return 1
            return 0
        else:
            print(f"\n❌ Test execution failed: {result.get('error', 'Unknown error')}")
            return 1

    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1


def run_pytest_directly():
    """Alternative method using pytest directly."""
    import subprocess
    import sys

    # Parse command line for test type
    if len(sys.argv) > 1:
        test_type = sys.argv[1]

        if test_type == "--pytest-performance":
            cmd = [
                "python",
                "-m",
                "pytest",
                "tests/performance/test_collaboration_performance.py",
                "-v",
                "-m",
                "performance",
                "--durations=10",
            ]
        elif test_type == "--pytest-integration":
            cmd = [
                "python",
                "-m",
                "pytest",
                "tests/integration/test_supabase_collaboration_schema.py",
                "-v",
                "-m",
                "integration",
            ]
        elif test_type == "--pytest-all":
            cmd = [
                "python",
                "-m",
                "pytest",
                "tests/integration/test_supabase_collaboration_schema.py",
                "tests/performance/test_collaboration_performance.py",
                "-v",
            ]
        else:
            print(
                "Unknown pytest option. Use --pytest-performance, "
                "--pytest-integration, or --pytest-all"
            )
            return 1
    else:
        print("Direct pytest execution requires test type argument")
        return 1

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    # Check if user wants direct pytest execution
    if len(sys.argv) > 1 and sys.argv[1].startswith("--pytest"):
        exit_code = run_pytest_directly()
    else:
        exit_code = asyncio.run(main())

    sys.exit(exit_code)
