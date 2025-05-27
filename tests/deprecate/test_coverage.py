"""
Test coverage utilities for the TripSage project.

This module provides utilities to measure and report test coverage
across the codebase to ensure we meet the 90%+ coverage requirement.
"""

import subprocess
import sys
from pathlib import Path


def run_coverage_report():
    """Run pytest with coverage and generate reports."""
    # Get project root
    project_root = Path(__file__).parent.parent

    # Coverage command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=tripsage",
        "--cov-report=html:htmlcov",
        "--cov-report=term-missing",
        "--cov-fail-under=90",
        str(project_root / "tests"),
    ]

    print("Running coverage report...")
    print(f"Command: {' '.join(cmd)}")

    try:
        # Run coverage
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Print output
        print("\n--- Coverage Report ---")
        print(result.stdout)

        if result.stderr:
            print("\n--- Errors ---")
            print(result.stderr)

        # Check if coverage met threshold
        if result.returncode == 0:
            print("\n✅ Coverage meets 90% threshold!")
        else:
            print("\n❌ Coverage below 90% threshold!")

        return result.returncode == 0

    except Exception as e:
        print(f"Error running coverage: {e}")
        return False


def find_uncovered_modules():
    """Find modules with low test coverage."""
    # Run coverage with json output
    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "json",
        "-o",
        "coverage.json",
    ]

    try:
        subprocess.run(cmd, check=True)

        # Read coverage data
        import json

        with open("coverage.json", "r") as f:
            coverage_data = json.load(f)

        # Find modules below threshold
        low_coverage = []
        for file, data in coverage_data["files"].items():
            if data["summary"]["percent_covered"] < 90:
                low_coverage.append(
                    {
                        "file": file,
                        "coverage": data["summary"]["percent_covered"],
                        "missing_lines": data["missing_lines"],
                    }
                )

        # Sort by coverage
        low_coverage.sort(key=lambda x: x["coverage"])

        # Report findings
        print("\n--- Modules Below 90% Coverage ---")
        for module in low_coverage:
            print(
                f"{module['file']}: {module['coverage']:.1f}% "
                f"(missing lines: {len(module['missing_lines'])})"
            )

        return low_coverage

    except Exception as e:
        print(f"Error analyzing coverage: {e}")
        return []


def generate_coverage_badge():
    """Generate a coverage badge for the README."""
    try:
        # Run coverage report
        subprocess.run(
            [sys.executable, "-m", "coverage", "report"],
            check=True,
            capture_output=True,
        )

        # Generate badge
        subprocess.run(
            [sys.executable, "-m", "coverage_badge", "-o", "coverage.svg"],
            check=True,
        )

        print("Coverage badge generated: coverage.svg")
        return True

    except Exception as e:
        print(f"Error generating badge: {e}")
        return False


if __name__ == "__main__":
    # Run coverage analysis
    print("TripSage Test Coverage Analysis")
    print("=" * 40)

    # Run coverage report
    coverage_met = run_coverage_report()

    # Find uncovered modules
    print("\n" + "=" * 40)
    uncovered = find_uncovered_modules()

    # Generate badge
    print("\n" + "=" * 40)
    generate_coverage_badge()

    # Exit with appropriate code
    sys.exit(0 if coverage_met else 1)
