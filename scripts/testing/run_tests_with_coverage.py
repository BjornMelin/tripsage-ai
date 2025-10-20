#!/usr/bin/env python3
"""Run tests with coverage report and detailed failure information."""

import os
import subprocess
import sys


def run_tests():
    """Run tests and display results."""
    print("Running tests with coverage...")
    print("=" * 80)

    # Set environment variables for testing
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    env["ENV"] = "test"

    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=tripsage",
        "--cov-report=term-missing",
        "--tb=short",
        "-v",
        "--no-header",
        "tests/unit/",
        "--maxfail=10",  # Stop after 10 failures to see patterns
    ]

    result = subprocess.run(cmd, env=env, capture_output=False)

    print("\n" + "=" * 80)
    print("Test run completed.")

    # Run a quick summary
    summary_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--tb=no",
        "-q",
        "tests/unit/",
        "--co",  # Just collect tests
    ]

    summary_result = subprocess.run(
        summary_cmd, env=env, capture_output=True, text=True
    )

    if summary_result.returncode == 0:
        lines = summary_result.stdout.strip().split("\n")
        test_count = len([line for line in lines if "test_" in line])
        print(f"\nTotal tests collected: {test_count}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
