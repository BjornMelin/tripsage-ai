#!/usr/bin/env python
"""
Final validation script for Phase 1 of TripSage Core migration.

Performs comprehensive assessment of:
1. Import path updates
2. File cleanup completion
3. Test coverage metrics
4. Model alignment checks
5. API functionality verification
"""

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_import_paths() -> Tuple[int, List[str]]:
    """Check for any remaining old import paths."""
    issues = []
    patterns = [
        (
            "tripsage.config.app_settings",
            "Should use tripsage_core.config.base_app_settings",
        ),
        ("api.core.exceptions", "Should use tripsage_core.exceptions.exceptions"),
        (
            "tripsage.api.core.exceptions",
            "Should use tripsage_core.exceptions.exceptions",
        ),
    ]

    total_files = 0
    for root, _, files in os.walk(project_root):
        # Skip irrelevant directories
        if any(
            skip in root
            for skip in [".venv", "node_modules", ".git", "__pycache__", "migrations"]
        ):
            continue

        for file in files:
            if file.endswith(".py"):
                total_files += 1
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r") as f:
                        content = f.read()

                    for old_import, suggestion in patterns:
                        if old_import in content and "validate_phase1" not in filepath:
                            issues.append(
                                f"{filepath}: Found '{old_import}' - {suggestion}"
                            )
                except Exception:
                    pass

    return total_files, issues


def check_deleted_files() -> List[str]:
    """Check if old exception files have been deleted."""
    files_should_not_exist = [
        "api/core/exceptions.py",
        "tripsage/api/core/exceptions.py",
    ]

    existing = []
    for file_path in files_should_not_exist:
        full_path = project_root / file_path
        if full_path.exists():
            existing.append(str(full_path))

    return existing


def run_test_coverage() -> Dict[str, float]:
    """Run pytest with coverage for tripsage_core."""
    coverage_data = {
        "overall": 0.0,
        "business_services": 0.0,
        "infrastructure_services": 0.0,
        "utilities": 0.0,
        "models": 0.0,
    }

    try:
        # Run pytest with coverage
        cmd = [
            "uv",
            "run",
            "pytest",
            "tests/unit/tripsage_core/",
            "--cov=tripsage_core",
            "--cov-report=term",
            "--no-header",
            "-q",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        output = result.stdout + result.stderr

        # Parse coverage output
        for line in output.split("\n"):
            if "TOTAL" in line and "%" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "%" in part:
                        coverage_data["overall"] = float(part.rstrip("%"))
                        break

            # Module-specific coverage
            if "services/business" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        coverage_data["business_services"] = float(part.rstrip("%"))
                        break

            if "services/infrastructure" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        coverage_data["infrastructure_services"] = float(
                            part.rstrip("%")
                        )
                        break

            if "tripsage_core/utils" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        coverage_data["utilities"] = float(part.rstrip("%"))
                        break

            if "tripsage_core/models" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        coverage_data["models"] = float(part.rstrip("%"))
                        break

        # Count test failures
        coverage_data["test_failures"] = output.count("FAILED")
        coverage_data["test_errors"] = output.count("ERROR")

    except Exception as e:
        print(f"Error running coverage: {e}")

    return coverage_data


def check_api_functionality() -> Dict[str, bool]:
    """Check if both APIs can start without errors."""
    results = {
        "frontend_api": False,
        "agent_api": False,
    }

    # Check imports for both APIs
    apis = [
        ("frontend_api", "api/main.py"),
        ("agent_api", "tripsage/api/main.py"),
    ]

    for api_name, api_path in apis:
        full_path = project_root / api_path
        if full_path.exists():
            try:
                # Try to parse the file to check for syntax errors
                with open(full_path, "r") as f:
                    ast.parse(f.read())

                # Check if main imports work
                cmd = [
                    "python",
                    "-c",
                    f"import sys; sys.path.insert(0, '{project_root}'); from {api_path.replace('/', '.').rstrip('.py')} import app",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    results[api_name] = True
                else:
                    print(f"{api_name} import error: {result.stderr}")

            except Exception as e:
                print(f"{api_name} error: {e}")

    return results


def calculate_phase1_score(
    import_issues: int,
    deleted_files: int,
    coverage: float,
    api_status: Dict[str, bool],
    test_failures: int,
) -> int:
    """Calculate overall Phase 1 completion score."""
    score = 100

    # Import issues (Critical - 30 points)
    if import_issues > 0:
        score -= min(30, import_issues * 2)

    # File cleanup (10 points)
    if deleted_files > 0:
        score -= deleted_files * 5

    # Test coverage (40 points)
    if coverage < 80:
        score -= int((80 - coverage) * 0.5)

    # API functionality (20 points)
    if not api_status["frontend_api"]:
        score -= 10
    if not api_status["agent_api"]:
        score -= 10

    # Test failures
    if test_failures > 0:
        score -= min(20, test_failures * 2)

    return max(0, score)


def main():
    """Run Phase 1 validation."""
    print("=" * 80)
    print("TRIPSAGE CORE MIGRATION - PHASE 1 FINAL VALIDATION REPORT")
    print("=" * 80)
    print()

    # 1. Check import paths
    print("1. IMPORT PATH VALIDATION")
    print("-" * 40)
    total_files, import_issues = check_import_paths()
    print(f"✓ Scanned {total_files} Python files")
    if import_issues:
        print(f"✗ Found {len(import_issues)} import issues:")
        for issue in import_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(import_issues) > 10:
            print(f"  ... and {len(import_issues) - 10} more")
    else:
        print("✓ All imports updated correctly!")
    print()

    # 2. Check file cleanup
    print("2. FILE CLEANUP VALIDATION")
    print("-" * 40)
    existing_files = check_deleted_files()
    if existing_files:
        print(f"✗ Found {len(existing_files)} files that should be deleted:")
        for file in existing_files:
            print(f"  - {file}")
    else:
        print("✓ All old files have been cleaned up!")
    print()

    # 3. Run test coverage
    print("3. TEST COVERAGE ANALYSIS")
    print("-" * 40)
    coverage = run_test_coverage()
    print(f"Overall Coverage: {coverage['overall']:.1f}%")
    print(f"Business Services: {coverage.get('business_services', 0):.1f}%")
    print(f"Infrastructure Services: {coverage.get('infrastructure_services', 0):.1f}%")
    print(f"Utilities: {coverage.get('utilities', 0):.1f}%")
    print(f"Models: {coverage.get('models', 0):.1f}%")

    if coverage["overall"] >= 80:
        print("✓ Coverage target met!")
    else:
        print(
            f"✗ Coverage below 80% target (need {80 - coverage['overall']:.1f}% more)"
        )

    if coverage.get("test_failures", 0) > 0:
        print(f"⚠️  {coverage['test_failures']} test failures detected")
    if coverage.get("test_errors", 0) > 0:
        print(f"⚠️  {coverage['test_errors']} test errors detected")
    print()

    # 4. Check API functionality
    print("4. API FUNCTIONALITY CHECK")
    print("-" * 40)
    api_status = check_api_functionality()
    for api, status in api_status.items():
        status_str = "✓ Working" if status else "✗ Import errors"
        print(f"{api}: {status_str}")
    print()

    # 5. Calculate final score
    print("5. PHASE 1 COMPLETION SCORE")
    print("-" * 40)
    score = calculate_phase1_score(
        len(import_issues),
        len(existing_files),
        coverage["overall"],
        api_status,
        coverage.get("test_failures", 0),
    )

    print(f"Final Score: {score}/100")

    # Status determination
    if score >= 80:
        status = "✓ PHASE 1 COMPLETE"
        emoji = "🎉"
    elif score >= 60:
        status = "⚠️  PHASE 1 NEARLY COMPLETE"
        emoji = "🔧"
    else:
        status = "✗ PHASE 1 INCOMPLETE"
        emoji = "❌"

    print(f"\n{emoji} {status}")

    # Recommendations
    if score < 100:
        print("\nRECOMMENDATIONS:")
        if import_issues:
            print("- Fix remaining import issues")
        if existing_files:
            print("- Delete old exception files")
        if coverage["overall"] < 80:
            print("- Increase test coverage to ≥80%")
        if not all(api_status.values()):
            print("- Fix API import errors")
        if coverage.get("test_failures", 0) > 0:
            print("- Fix failing tests")

    print("\n" + "=" * 80)

    return score >= 80


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
