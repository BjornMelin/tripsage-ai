#!/usr/bin/env python3
"""
TripSage Application Health Check

This script performs a systematic health check of the TripSage application
to identify import errors, circular dependencies, and startup issues.
"""

import sys
import traceback
from pathlib import Path

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def test_import(module_name: str, description: str) -> bool:
    """Test importing a module and report the result."""
    try:
        print(f"Testing {description}...")
        __import__(module_name)
        print(f"✅ {description} imported successfully")
        return True
    except Exception as e:
        print(f"❌ {description} import failed: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def main():
    """Run health checks."""
    print("🔍 TripSage Application Health Check")
    print("=" * 50)

    all_passed = True

    # Test core modules first
    checks = [
        ("tripsage_core.config.base_app_settings", "TripSage Core Settings"),
        ("tripsage_core", "TripSage Core Module"),
        ("tripsage.mcp_abstraction", "MCP Abstraction Layer"),
        ("tripsage.api.core.config", "TripSage API Config"),
        ("api.core.config", "API Core Config"),
    ]

    for module_name, description in checks:
        success = test_import(module_name, description)
        all_passed = all_passed and success
        print()

    # Test main applications
    main_checks = [
        ("tripsage.api.main", "TripSage API Main (tripsage/api/main.py)"),
        ("api.main", "API Main (api/main.py)"),
    ]

    print("\n📱 Testing Main Applications")
    print("-" * 30)

    for module_name, description in main_checks:
        success = test_import(module_name, description)
        all_passed = all_passed and success
        print()

    # Summary
    print("\n📊 Health Check Summary")
    print("=" * 30)
    if all_passed:
        print("✅ All health checks passed!")
        return 0
    else:
        print("❌ Some health checks failed. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
