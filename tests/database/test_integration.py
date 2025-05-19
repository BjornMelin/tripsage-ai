"""Integration tests for database operations using real MCP connections."""

import os
from datetime import datetime

import pytest

from tripsage.config.mcp_settings import mcp_settings
from tripsage.db.initialize import initialize_databases, verify_database_schema
from tripsage.tools import memory_tools, supabase_tools

# Skip integration tests if not in CI or explicitly enabled
PYTEST_INTEGRATION = os.environ.get("PYTEST_INTEGRATION", "false").lower() == "true"


@pytest.mark.skipif(not PYTEST_INTEGRATION, reason="Integration tests disabled")
class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.fixture
    async def setup_test_db(self):
        """Set up test database environment."""
        # Initialize databases
        success = await initialize_databases(
            verify_connections=True, project_id=mcp_settings.SUPABASE_PROJECT_ID
        )
        assert success, "Failed to initialize databases"

        yield

        # Cleanup would go here

    async def test_full_user_lifecycle(self, setup_test_db):
        """Test complete user lifecycle: create, read, update."""
        project_id = mcp_settings.SUPABASE_PROJECT_ID

        # Create user
        test_email = f"test_{datetime.now().timestamp()}@example.com"
        user_data = {
            "email": test_email,
            "username": "testuser",
            "full_name": "Test User",
        }

        create_result = await supabase_tools.insert_data(
            project_id=project_id, table="users", data=user_data
        )
        assert create_result["id"] is not None
        user_id = create_result["id"]

        # Find user by email
        find_result = await supabase_tools.find_user_by_email(
            project_id=project_id, email=test_email
        )
        assert len(find_result["users"]) == 1
        assert find_result["users"][0]["email"] == test_email

        # Update preferences
        prefs = {"theme": "dark", "currency": "EUR"}
        update_result = await supabase_tools.update_user_preferences(
            project_id=project_id, user_id=user_id, preferences=prefs
        )
        assert update_result["preferences"]["theme"] == "dark"

        # Cleanup
        await supabase_tools.delete_data(
            project_id=project_id, table="users", conditions={"id": user_id}
        )

    async def test_trip_operations_with_neo4j(self, setup_test_db):
        """Test trip operations across both SQL and Neo4j."""
        project_id = mcp_settings.SUPABASE_PROJECT_ID

        # Create test user first
        user_data = {
            "email": f"triptest_{datetime.now().timestamp()}@example.com",
            "username": "tripuser",
        }
        user_result = await supabase_tools.insert_data(
            project_id=project_id, table="users", data=user_data
        )
        user_id = user_result["id"]

        # Create trip in SQL
        trip_data = {
            "user_id": user_id,
            "title": "European Adventure",
            "start_date": "2024-07-01",
            "end_date": "2024-07-15",
            "status": "planning",
            "budget": 3000.00,
            "currency": "EUR",
        }

        trip_result = await supabase_tools.create_trip(
            project_id=project_id, **trip_data
        )
        trip_id = trip_result["id"]

        # Create trip entities in Neo4j
        destinations = ["Paris", "Rome", "Barcelona"]
        neo4j_result = await memory_tools.create_trip_entities(
            trip_id=trip_id,
            user_id=user_id,
            destinations=destinations,
            start_date=trip_data["start_date"],
            end_date=trip_data["end_date"],
        )
        assert neo4j_result["status"] == "success"

        # Query destinations by country
        # We ignore the result since this is just testing connectivity
        await memory_tools.find_destinations_by_country("France")
        # Paris should be in the results (if it exists in the graph)

        # Find trips by destination
        # We ignore the result since this is just testing connectivity
        await supabase_tools.find_trips_by_destination(
            project_id=project_id, destination="Paris"
        )

        # Cleanup
        await supabase_tools.delete_data(
            project_id=project_id, table="trips", conditions={"id": trip_id}
        )
        await supabase_tools.delete_data(
            project_id=project_id, table="users", conditions={"id": user_id}
        )

    async def test_database_schema_verification(self, setup_test_db):
        """Test database schema verification."""
        schema_result = await verify_database_schema(
            project_id=mcp_settings.SUPABASE_PROJECT_ID
        )

        # Check SQL schema
        assert "sql" in schema_result
        assert "tables" in schema_result["sql"]
        expected_tables = ["users", "trips"]
        for table in expected_tables:
            assert table in schema_result["sql"]["tables"], (
                f"Missing expected table: {table}"
            )

        # Check Neo4j schema
        assert "neo4j" in schema_result
        assert schema_result["neo4j"]["initialized"] is True

    async def test_migration_system(self, setup_test_db):
        """Test that migration system works correctly."""
        from tripsage.db.migrations.runner import get_applied_migrations
        from tripsage.mcp_abstraction.manager import MCPManager

        project_id = mcp_settings.SUPABASE_PROJECT_ID
        mcp_manager = await MCPManager.get_instance(mcp_settings.dict())

        try:
            # Check applied migrations
            applied = await get_applied_migrations(mcp_manager, project_id)
            assert isinstance(applied, list)

            # The migrations table should exist
            tables_query = """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = 'migrations';
            """

            result = await mcp_manager.invoke(
                integration_name="supabase",
                tool_name="execute_sql",
                tool_args={"project_id": project_id, "sql": tables_query},
            )

            assert result.result["rows"][0]["tablename"] == "migrations"

        finally:
            await mcp_manager.cleanup()


if __name__ == "__main__":
    # Run integration tests if enabled
    if PYTEST_INTEGRATION:
        pytest.main([__file__, "-v", "-s"])
    else:
        print("Integration tests skipped. Set PYTEST_INTEGRATION=true to run.")
