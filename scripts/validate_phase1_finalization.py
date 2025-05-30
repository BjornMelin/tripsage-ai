#!/usr/bin/env python3
"""
Validation script for Phase 1 finalization of TripSage Core migration.

This script checks:
1. Import path consistency across the codebase
2. File cleanup completion
3. Test coverage for infrastructure services and utilities
4. Model alignment and application start capability
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Base directory
BASE_DIR = Path(__file__).parent.parent


def check_import_paths() -> Dict[str, List[str]]:
    """Check for old import paths that need updating."""
    issues = {
        "app_settings": [],
        "exceptions": [],
        "utilities": [],
    }

    # Patterns to check
    patterns = {
        "app_settings": [
            r"from\s+tripsage\.config\.app_settings\s+import",
            r"import\s+tripsage\.config\.app_settings",
        ],
        "exceptions": [
            r"from\s+api\.core\.exceptions\s+import",
            r"from\s+tripsage\.api\.core\.exceptions\s+import",
            r"import\s+api\.core\.exceptions",
            r"import\s+tripsage\.api\.core\.exceptions",
        ],
        "utilities": [
            r"from\s+tripsage\.utils\.(\w+)\s+import",
            r"import\s+tripsage\.utils\.(\w+)",
        ],
    }

    # Files to check
    py_files = list(BASE_DIR.rglob("*.py"))

    for py_file in py_files:
        # Skip migration scripts and test files for now
        if "migrations" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()

            for category, category_patterns in patterns.items():
                for pattern in category_patterns:
                    if re.search(pattern, content):
                        issues[category].append(str(py_file))
                        break
        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return issues


def check_file_cleanup() -> Dict[str, bool]:
    """Check if old files have been cleaned up."""
    old_files = [
        "api/core/exceptions.py",
        "tripsage/api/core/exceptions.py",
    ]

    cleanup_status = {}
    for file_path in old_files:
        full_path = BASE_DIR / file_path
        cleanup_status[file_path] = not full_path.exists()

    return cleanup_status


def check_test_coverage() -> Dict[str, float]:
    """Check test coverage for key modules."""
    coverage_data = {}

    # Run coverage for all tripsage_core tests
    try:
        cmd = [
            "uv",
            "run",
            "pytest",
            "tests/unit/tripsage_core/",
            "--cov=tripsage_core",
            "--cov-report=term",
            "-q",
        ]

        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)

        # Parse module-specific coverage from output
        modules_to_track = [
            "tripsage_core.services.infrastructure",
            "tripsage_core.utils",
            "tripsage_core.services.business",
            "tripsage_core.models",
        ]

        for module in modules_to_track:
            coverage_data[module] = 0.0

        if result.stdout:
            for line in result.stdout.split("\n"):
                for module in modules_to_track:
                    if line.startswith(module.replace(".", "/")):
                        parts = line.split()
                        if len(parts) >= 4:
                            try:
                                cov_str = parts[3].replace("%", "")
                                coverage_data[module] = float(cov_str)
                            except (ValueError, IndexError):
                                pass
                        break

        # If no specific coverage, check TOTAL
        if all(v == 0.0 for v in coverage_data.values()) and "TOTAL" in result.stdout:
            for line in result.stdout.split("\n"):
                if "TOTAL" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            coverage = float(parts[3].replace("%", ""))
                            # Assign same coverage to all modules as estimate
                            for module in modules_to_track:
                                coverage_data[module] = coverage
                        except ValueError:
                            pass
                    break

    except Exception as e:
        print(f"Error checking coverage: {e}")
        for module in [
            "tripsage_core.services.infrastructure",
            "tripsage_core.utils",
            "tripsage_core.services.business",
            "tripsage_core.models",
        ]:
            coverage_data[module] = 0.0

    return coverage_data


def check_application_start() -> Tuple[bool, str]:
    """Check if applications can start without errors."""
    apps = [
        "api/main.py",
        "tripsage/api/main.py",
    ]

    for app in apps:
        app_path = BASE_DIR / app
        if app_path.exists():
            try:
                # Try to import the module to check for import errors
                cmd = [
                    "uv",
                    "run",
                    "python",
                    "-c",
                    f"import sys; sys.path.insert(0, '{BASE_DIR}'); import {app.replace('/', '.').replace('.py', '')}",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode != 0:
                    return False, f"{app}: {result.stderr}"

            except Exception as e:
                return False, f"{app}: {str(e)}"

    return True, "All applications can be imported successfully"


def generate_report() -> str:
    """Generate a comprehensive validation report."""
    print("Running Phase 1 Finalization Validation...\n")

    # Check import paths
    print("1. Checking import paths...")
    import_issues = check_import_paths()

    # Check file cleanup
    print("2. Checking file cleanup...")
    cleanup_status = check_file_cleanup()

    # Check test coverage
    print("3. Checking test coverage...")
    coverage_data = check_test_coverage()

    # Check application start
    print("4. Checking application start capability...")
    app_start_ok, app_start_msg = check_application_start()

    # Generate report
    report = []
    report.append("=" * 80)
    report.append("PHASE 1 FINALIZATION VALIDATION REPORT")
    report.append("=" * 80)
    report.append("")

    # Import Path Status
    report.append("1. IMPORT PATH UPDATES:")
    report.append("-" * 40)

    total_import_issues = sum(len(issues) for issues in import_issues.values())
    if total_import_issues == 0:
        report.append("✅ All import paths have been updated correctly")
    else:
        report.append(f"❌ Found {total_import_issues} files with old import paths:")
        for category, files in import_issues.items():
            if files:
                report.append(f"   - {category}: {len(files)} files")
                for file in files[:5]:  # Show first 5
                    report.append(f"     • {file}")
                if len(files) > 5:
                    report.append(f"     ... and {len(files) - 5} more")

    report.append("")

    # File Cleanup Status
    report.append("2. FILE CLEANUP:")
    report.append("-" * 40)

    all_cleaned = all(cleanup_status.values())
    if all_cleaned:
        report.append("✅ All old files have been cleaned up")
    else:
        report.append("❌ Some files still need to be deleted:")
        for file, cleaned in cleanup_status.items():
            status = "✅ Deleted" if cleaned else "❌ Still exists"
            report.append(f"   - {file}: {status}")

    report.append("")

    # Test Coverage Status
    report.append("3. TEST COVERAGE:")
    report.append("-" * 40)

    for module, coverage in coverage_data.items():
        status = "✅" if coverage >= 80 else "❌"
        report.append(f"   {status} {module}: {coverage:.1f}%")

    avg_coverage = (
        sum(coverage_data.values()) / len(coverage_data) if coverage_data else 0
    )
    report.append(f"\n   Average Coverage: {avg_coverage:.1f}%")
    report.append("   Target: 80.0%")

    report.append("")

    # Application Start Status
    report.append("4. APPLICATION START:")
    report.append("-" * 40)

    if app_start_ok:
        report.append(f"✅ {app_start_msg}")
    else:
        report.append(f"❌ {app_start_msg}")

    report.append("")

    # Overall Score
    report.append("OVERALL PHASE 1 SCORE:")
    report.append("-" * 40)

    score = 0
    max_score = 100

    # Import paths (25 points)
    if total_import_issues == 0:
        score += 25

    # File cleanup (25 points)
    if all_cleaned:
        score += 25

    # Test coverage (40 points)
    coverage_score = min(40, int((avg_coverage / 80) * 40))
    score += coverage_score

    # Application start (10 points)
    if app_start_ok:
        score += 10

    report.append(f"   Score: {score}/{max_score}")

    if score >= 80:
        report.append("   Status: ✅ READY FOR PHASE 2")
    else:
        report.append("   Status: ❌ NEEDS MORE WORK")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


if __name__ == "__main__":
    report = generate_report()
    print("\n" + report)

    # Save report to file
    report_path = BASE_DIR / "PHASE1_VALIDATION_REPORT.md"
    report_path.write_text(report)
    print(f"\nReport saved to: {report_path}")
