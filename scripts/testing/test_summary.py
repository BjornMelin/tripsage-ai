#!/usr/bin/env python3
"""
Test summary script to show test progress.
"""

import os
import subprocess
import sys


def get_test_results(test_dir):
    """Run tests and get results."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["ENV"] = "test"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_dir,
        "--tb=no",
        "-q",
        "--no-header",
        "--no-summary",
    ]

    result = subprocess.run(cmd, env=env, capture_output=True, text=True)

    # Parse output
    passed = 0
    failed = 0
    errors = 0

    for line in result.stdout.split("\n"):
        if "passed" in line and "failed" in line:
            # Parse summary line
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    passed = int(parts[i - 1])
                elif part == "failed":
                    failed = int(parts[i - 1])
                elif part == "error" in line:
                    errors = int(parts[i - 1])
        elif " passed" in line and "failed" not in line:
            # Only passed tests
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    passed = int(parts[i - 1])

    total = passed + failed + errors
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "success_rate": (passed / total * 100) if total > 0 else 0,
    }


def main():
    """Run test summary."""
    print("Test Summary Report")
    print("=" * 60)

    test_dirs = [
        ("Unit Tests", "tests/unit/"),
        ("Orchestration Tests", "tests/unit/orchestration/"),
        ("Model Tests", "tests/unit/models/"),
        ("Service Tests", "tests/unit/tripsage_core/services/"),
        ("API Tests", "tests/unit/tripsage_api_routers/"),
    ]

    total_stats = {"total": 0, "passed": 0, "failed": 0, "errors": 0}

    for name, test_dir in test_dirs:
        if os.path.exists(test_dir):
            print(f"\n{name} ({test_dir}):")
            stats = get_test_results(test_dir)

            print(f"  Total:   {stats['total']:4d}")
            print(f"  Passed:  {stats['passed']:4d} ({stats['success_rate']:.1f}%)")
            print(f"  Failed:  {stats['failed']:4d}")
            print(f"  Errors:  {stats['errors']:4d}")

            # Update totals
            for key in ["total", "passed", "failed", "errors"]:
                total_stats[key] += stats[key]

    # Overall summary
    print("\n" + "=" * 60)
    print("Overall Summary:")
    print(f"  Total Tests:  {total_stats['total']:4d}")
    passed_pct = total_stats["passed"] / total_stats["total"] * 100
    print(f"  Passed:       {total_stats['passed']:4d} ({passed_pct:.1f}%)")
    print(f"  Failed:       {total_stats['failed']:4d}")
    print(f"  Errors:       {total_stats['errors']:4d}")
    success_rate = total_stats["passed"] / total_stats["total"] * 100
    print(f"  Success Rate: {success_rate:.1f}%")

    print("\n" + "=" * 60)
    print("Next Steps:")
    print("1. Fix remaining datetime.UTC issues in other test files")
    print("2. Update test mocking patterns for LangChain/OpenAI")
    print("3. Fix import errors and missing dependencies")
    print("4. Run 'ruff check . --fix && ruff format .' on all files")
    print("5. Achieve 90%+ test coverage")


if __name__ == "__main__":
    main()
