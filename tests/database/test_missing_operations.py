"""Test suite to identify and document missing database operations."""

from tripsage.tools import supabase_tools


class TestMissingDatabaseOperations:
    """Document and test for missing database operations from the migration."""

    def test_document_missing_user_operations(self):
        """Document missing user repository operations."""
        missing_operations = [
            {
                "operation": "set_admin_status",
                "description": "Set user admin status",
                "old_location": "src/db/repositories/user.py",
                "parameters": ["user_id", "is_admin"],
                "priority": "medium",
            },
            {
                "operation": "set_disabled_status",
                "description": "Enable/disable user account",
                "old_location": "src/db/repositories/user.py",
                "parameters": ["user_id", "is_disabled"],
                "priority": "medium",
            },
            {
                "operation": "update_password",
                "description": "Update user password hash",
                "old_location": "src/db/repositories/user.py",
                "parameters": ["user_id", "password_hash"],
                "priority": "high",
            },
            {
                "operation": "get_admins",
                "description": "Get all admin users",
                "old_location": "src/db/repositories/user.py",
                "parameters": [],
                "priority": "low",
            },
        ]

        # Verify these operations don't exist
        for op in missing_operations:
            assert not hasattr(supabase_tools, op["operation"]), (
                f"{op['operation']} unexpectedly exists in supabase_tools"
            )

        return missing_operations

    def test_document_missing_trip_operations(self):
        """Document missing trip repository operations."""
        missing_operations = [
            {
                "operation": "get_upcoming_trips",
                "description": "Get trips starting in the future",
                "old_location": "src/db/repositories/trip.py",
                "parameters": ["user_id", "days_ahead"],
                "priority": "medium",
            }
        ]

        # Verify these operations don't exist
        for op in missing_operations:
            assert not hasattr(supabase_tools, op["operation"]), (
                f"{op['operation']} unexpectedly exists in supabase_tools"
            )

        return missing_operations

    def test_document_missing_flight_operations(self):
        """Document missing flight repository operations."""
        missing_operations = [
            {
                "operation": "find_flights_by_trip_id",
                "description": "Find all flights for a trip",
                "old_location": "src/db/repositories/flight.py",
                "parameters": ["trip_id"],
                "priority": "high",
            },
            {
                "operation": "find_flights_by_route",
                "description": "Find flights by origin and destination",
                "old_location": "src/db/repositories/flight.py",
                "parameters": ["origin", "destination"],
                "priority": "medium",
            },
            {
                "operation": "find_flights_by_date_range",
                "description": "Find flights within date range",
                "old_location": "src/db/repositories/flight.py",
                "parameters": ["start_date", "end_date"],
                "priority": "medium",
            },
            {
                "operation": "update_flight_booking_status",
                "description": "Update flight booking status",
                "old_location": "src/db/repositories/flight.py",
                "parameters": ["flight_id", "booking_status"],
                "priority": "high",
            },
            {
                "operation": "get_flight_statistics",
                "description": "Get flight statistics for analytics",
                "old_location": "src/db/repositories/flight.py",
                "parameters": ["user_id"],
                "priority": "low",
            },
        ]

        # Verify these operations don't exist
        for op in missing_operations:
            assert not hasattr(supabase_tools, op["operation"]), (
                f"{op['operation']} unexpectedly exists in supabase_tools"
            )

        return missing_operations

    def test_generate_missing_operations_report(self):
        """Generate a comprehensive report of all missing operations."""
        report = {
            "user_operations": self.test_document_missing_user_operations(),
            "trip_operations": self.test_document_missing_trip_operations(),
            "flight_operations": self.test_document_missing_flight_operations(),
        }

        # Count total missing operations
        total_missing = sum(len(ops) for ops in report.values())

        # Group by priority
        priority_groups = {"high": [], "medium": [], "low": []}
        for category, operations in report.items():
            for op in operations:
                priority_groups[op["priority"]].append({"category": category, **op})

        print("\n=== Missing Database Operations Report ===")
        print(f"Total missing operations: {total_missing}")
        print(f"High priority: {len(priority_groups['high'])}")
        print(f"Medium priority: {len(priority_groups['medium'])}")
        print(f"Low priority: {len(priority_groups['low'])}")

        print("\n=== High Priority Operations ===")
        for op in priority_groups["high"]:
            print(f"- {op['operation']} ({op['category']}): {op['description']}")

        return report


class TestMissingModelOperations:
    """Document missing model operations."""

    def test_missing_flight_model(self):
        """Document that Flight model is missing from database models."""
        try:
            import importlib.util

            spec = importlib.util.find_spec("tripsage.models.db.flight")
            if spec is not None:
                raise AssertionError("Flight model unexpectedly exists")
        except ImportError:
            # This is expected
            pass

        missing_model = {
            "model": "Flight",
            "old_location": "src/db/models/flight.py",
            "description": "Database model for flight bookings",
            "fields": [
                "id",
                "trip_id",
                "user_id",
                "flight_number",
                "origin",
                "destination",
                "departure_time",
                "arrival_time",
                "airline",
                "booking_status",
                "price",
                "currency",
                "created_at",
                "updated_at",
            ],
            "priority": "high" if self._check_flight_persistence_needed() else "low",
        }

        return missing_model

    def _check_flight_persistence_needed(self) -> bool:
        """Check if flight persistence is needed based on current architecture."""
        # Check if any tools expect to persist flight data
        flight_tools_exist = hasattr(supabase_tools, "create_flight_booking")
        return flight_tools_exist


if __name__ == "__main__":
    # Run the tests and generate report
    missing_ops_test = TestMissingDatabaseOperations()
    missing_ops_test.test_generate_missing_operations_report()

    missing_models_test = TestMissingModelOperations()
    flight_model = missing_models_test.test_missing_flight_model()
    print("\n=== Missing Models ===")
    print(
        f"- {flight_model['model']}: {flight_model['description']} "
        f"(Priority: {flight_model['priority']})"
    )
