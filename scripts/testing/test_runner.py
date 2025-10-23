#!/usr/bin/env python3
"""Minimal environment smoke test for TripSage.

Runs a few import and version checks without requiring pytest or external
services. Exits with code 0 on success, 1 on failure.
"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class CheckResult:
    """Represents the outcome of a single smoke check.

    Attributes:
        name: Short name for the check.
        success: Whether the check passed.
        detail: Optional additional information.
    """

    name: str
    success: bool
    detail: str = ""


def check_python_version() -> CheckResult:
    """Ensure Python version is 3.13 or newer."""
    required = (3, 13)
    version = sys.version_info[:3]
    ok = version >= required
    detail = (
        f"Detected {version[0]}.{version[1]}.{version[2]} (requires >= "
        f"{required[0]}.{required[1]})"
    )
    return CheckResult("python_version", ok, detail)


def check_settings_import() -> CheckResult:
    """Verify core settings can be imported and instantiated."""
    try:
        from tripsage_core.config import Settings, get_settings  # type: ignore

        s = Settings()
        s2 = get_settings()
        ok = isinstance(s, Settings) and isinstance(s2, Settings)
        return CheckResult("settings_import", ok, "tripsage_core.config available")
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return CheckResult("settings_import", False, f"Import failed: {exc}")


def check_benchmark_import() -> CheckResult:
    """Verify benchmark entry module imports without side effects."""
    try:
        __import__("scripts.benchmarks.benchmark")
        return CheckResult("benchmark_import", True, "benchmark module import ok")
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        return CheckResult("benchmark_import", False, f"Import failed: {exc}")


def main() -> int:
    """Run smoke checks and print a short summary."""
    checks: list[Callable[[], CheckResult]] = [
        check_python_version,
        check_settings_import,
        check_benchmark_import,
    ]

    results: list[CheckResult] = [fn() for fn in checks]

    passed = sum(1 for r in results if r.success)
    failed = len(results) - passed

    print("TripSage scripts/test_runner smoke checks")
    for r in results:
        status = "OK" if r.success else "FAIL"
        print(f"- {r.name}: {status} - {r.detail}")

    print(f"Summary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
