#!/usr/bin/env python3
"""
Script to fix all datetime.UTC references to use timezone.utc for Python 3.13 compatibility.
"""

import os
import re

files_to_fix = [
    "tests/e2e/test_chat_sessions.py",
    "tests/unit/models/test_price_history.py",
    "tests/unit/models/test_saved_option.py",
    "tests/unit/models/test_search_parameters.py",
    "tests/unit/models/test_trip_comparison.py",
    "tests/unit/models/test_trip_note.py",
    "tests/unit/tripsage_core/services/infrastructure/test_key_monitoring_service_enhanced.py",
    "tripsage/orchestration/handoff_coordinator.py",
    "tripsage/orchestration/memory_bridge.py",
    "tripsage/orchestration/nodes/accommodation_agent.py",
    "tripsage/orchestration/nodes/base.py",
    "tripsage/orchestration/nodes/budget_agent.py",
    "tripsage/orchestration/nodes/destination_research_agent.py",
    "tripsage/orchestration/nodes/error_recovery.py",
    "tripsage/orchestration/nodes/flight_agent.py",
    "tripsage/orchestration/routing.py",
    "tripsage/tools/planning_tools.py",
    "tripsage/tools/webcrawl/persistence.py",
    "tripsage/tools/webcrawl/result_normalizer.py",
    "tripsage_core/models/db/memory.py",
    "tripsage_core/services/external_apis/document_analyzer.py",
    "tripsage_core/services/infrastructure/key_monitoring_service.py",
]


def fix_datetime_utc_in_file(filepath):
    """Fix datetime.UTC references in a single file."""
    print(f"Processing {filepath}...")

    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # Check if file already imports timezone
    has_timezone_import = bool(re.search(r"from datetime import.*timezone", content))

    # Replace datetime.UTC with timezone.utc
    content = re.sub(r"datetime\.UTC", "timezone.utc", content)

    # Add timezone import if needed and file was modified
    if content != original_content and not has_timezone_import:
        # Find existing datetime imports
        import_match = re.search(r"from datetime import (.+)", content)
        if import_match:
            imports = import_match.group(1)
            # Add timezone to imports if not already there
            if "timezone" not in imports:
                new_imports = imports.rstrip() + ", timezone"
                content = content.replace(
                    f"from datetime import {imports}",
                    f"from datetime import {new_imports}",
                )
        else:
            # No existing datetime import, add one
            content = "from datetime import timezone\n" + content

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"  ✓ Fixed {filepath}")
    else:
        print(f"  - No changes needed in {filepath}")


def main():
    """Fix all files with datetime.UTC references."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    fixed_count = 0
    for relative_path in files_to_fix:
        filepath = os.path.join(base_dir, relative_path)
        if os.path.exists(filepath):
            fix_datetime_utc_in_file(filepath)
            fixed_count += 1
        else:
            print(f"  ! File not found: {filepath}")

    print(f"\nProcessed {fixed_count} files.")


if __name__ == "__main__":
    main()
