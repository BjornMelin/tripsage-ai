"""Simple test to document missing database operations without loading settings."""

import ast
import os


def check_function_exists(module_path: str, function_name: str) -> bool:
    """Check if a function exists in a Python module without importing it."""
    if not os.path.exists(module_path):
        return False

    with open(module_path, "r") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return True
    return False


def test_missing_operations():
    """Document missing database operations."""
    supabase_tools_path = (
        "/home/bjorn/repos/agents/openai/tripsage-ai/tripsage/tools/supabase_tools.py"
    )
    memory_tools_path = (
        "/home/bjorn/repos/agents/openai/tripsage-ai/tripsage/tools/memory_tools.py"
    )

    # Missing user operations
    missing_user_ops = [
        ("set_admin_status", "Set user admin status", "high"),
        ("set_disabled_status", "Enable/disable user account", "medium"),
        ("update_password", "Update user password hash", "high"),
        ("get_admins", "Get all admin users", "low"),
    ]

    # Missing trip operations
    missing_trip_ops = [
        ("get_upcoming_trips", "Get trips starting in the future", "medium"),
    ]

    # Missing flight operations
    missing_flight_ops = [
        ("find_flights_by_trip_id", "Find all flights for a trip", "high"),
        ("find_flights_by_route", "Find flights by origin and destination", "medium"),
        ("find_flights_by_date_range", "Find flights within date range", "medium"),
        ("update_flight_booking_status", "Update flight booking status", "high"),
        ("get_flight_statistics", "Get flight statistics for analytics", "low"),
    ]

    print("=== Missing Database Operations Report ===\n")

    # Check user operations
    print("Missing User Operations:")
    for op_name, desc, priority in missing_user_ops:
        exists = check_function_exists(supabase_tools_path, op_name)
        if not exists:
            print(f"  - {op_name}: {desc} (Priority: {priority})")

    # Check trip operations
    print("\nMissing Trip Operations:")
    for op_name, desc, priority in missing_trip_ops:
        exists = check_function_exists(supabase_tools_path, op_name)
        if not exists:
            print(f"  - {op_name}: {desc} (Priority: {priority})")

    # Check flight operations
    print("\nMissing Flight Operations:")
    for op_name, desc, priority in missing_flight_ops:
        exists = check_function_exists(supabase_tools_path, op_name)
        if not exists:
            print(f"  - {op_name}: {desc} (Priority: {priority})")

    # Check for missing Flight model
    db_models_path = "/home/bjorn/repos/agents/openai/tripsage-ai/tripsage/models/db"
    flight_model_exists = os.path.exists(os.path.join(db_models_path, "flight.py"))
    print("\nMissing Models:")
    if not flight_model_exists:
        print("  - Flight: Database model for flight bookings (Priority: medium)")

    # Summary
    print("\n=== Summary ===")
    print("Total missing operations: 10")
    print("  - User operations: 4")
    print("  - Trip operations: 1")
    print("  - Flight operations: 5")
    print("  - Missing models: 1")

    print("\nNote: These operations were present in the old src/db/ implementation")
    print("but have not been migrated to the new MCP-based approach.")


if __name__ == "__main__":
    test_missing_operations()
