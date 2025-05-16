"""Comprehensive test suite for database migration verification."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from tripsage.models.db.trip import Trip, TripStatus
from tripsage.models.db.user import User

# Mock the settings before importing tools
with patch("tripsage.config.app_settings.settings"):
    from tripsage.mcp_abstraction.manager import MCPManager
    from tripsage.tools import memory_tools, supabase_tools


class TestDatabaseMigrationCompleteness:
    """Test to ensure all database operations are properly migrated to MCP-based approach."""

    @pytest.fixture
    def mock_mcp_manager(self):
        """Create a mock MCP manager for testing."""
        manager = Mock(spec=MCPManager)
        manager.invoke = AsyncMock()
        return manager

    @pytest.fixture
    def mock_supabase_response(self):
        """Create mock Supabase responses."""

        def _response(data=None, error=None):
            response = Mock()
            response.data = data
            response.error = error
            response.status_code = 200 if not error else 400
            return response

        return _response

    @pytest.fixture
    def mock_memory_response(self):
        """Create mock Memory MCP responses."""

        def _response(result=None, error=None):
            response = Mock()
            response.result = result
            response.error = error
            return response

        return _response


class TestUserOperations(TestDatabaseMigrationCompleteness):
    """Test user-related database operations."""

    async def test_find_user_by_email(self, mock_mcp_manager, mock_supabase_response):
        """Test finding user by email."""
        expected_user = {
            "id": 1,
            "email": "test@example.com",
            "username": "testuser",
            "created_at": datetime.now().isoformat(),
        }

        mock_response = MagicMock()
        mock_response.result = {"rows": [expected_user]}
        mock_response.error = None
        mock_mcp_manager.invoke.return_value = mock_response

        with patch("tripsage.tools.supabase_tools.mcp_manager", mock_mcp_manager):
            result = await supabase_tools.find_user_by_email(
                project_id="test", email="test@example.com"
            )

        assert result["users"][0]["email"] == expected_user["email"]
        mock_mcp_manager.invoke.assert_called_once()

    async def test_update_user_preferences(
        self, mock_mcp_manager, mock_supabase_response
    ):
        """Test updating user preferences."""
        updated_user = {"id": 1, "preferences": {"theme": "dark", "currency": "USD"}}

        mock_mcp_manager.invoke.return_value = mock_supabase_response([updated_user])

        with patch(
            "tripsage.tools.supabase_tools.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            result = await supabase_tools.update_user_preferences(
                project_id="test",
                user_id=1,
                preferences={"theme": "dark", "currency": "USD"},
            )

        assert result["preferences"]["theme"] == "dark"

    async def test_missing_user_operations(self):
        """Verify that missing user operations are documented."""
        # These operations are missing from the new implementation
        missing_ops = [
            "set_admin_status",
            "set_disabled_status",
            "update_password",
            "get_admins",
        ]

        # Check that these don't exist in supabase_tools
        for op in missing_ops:
            assert not hasattr(supabase_tools, op), f"{op} should not exist yet"


class TestTripOperations(TestDatabaseMigrationCompleteness):
    """Test trip-related database operations."""

    async def test_create_trip(self, mock_mcp_manager, mock_supabase_response):
        """Test creating a new trip."""
        new_trip = {
            "id": 1,
            "user_id": 1,
            "title": "Summer Vacation",
            "start_date": "2024-07-01",
            "end_date": "2024-07-15",
            "status": "planning",
        }

        mock_mcp_manager.invoke.return_value = mock_supabase_response([new_trip])

        with patch(
            "tripsage.tools.supabase_tools.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            result = await supabase_tools.create_trip(
                project_id="test",
                user_id=1,
                title="Summer Vacation",
                start_date="2024-07-01",
                end_date="2024-07-15",
            )

        assert result["title"] == "Summer Vacation"

    async def test_find_trips_by_user(self, mock_mcp_manager, mock_supabase_response):
        """Test finding trips by user ID."""
        trips = [
            {"id": 1, "user_id": 1, "title": "Trip 1"},
            {"id": 2, "user_id": 1, "title": "Trip 2"},
        ]

        mock_mcp_manager.invoke.return_value = mock_supabase_response(trips)

        with patch(
            "tripsage.tools.supabase_tools.get_mcp_manager",
            return_value=mock_mcp_manager,
        ):
            result = await supabase_tools.find_trips_by_user(
                project_id="test", user_id=1
            )

        assert len(result["trips"]) == 2

    async def test_missing_trip_operations(self):
        """Verify that missing trip operations are documented."""
        # This operation is missing from the new implementation
        assert not hasattr(supabase_tools, "get_upcoming_trips")


class TestFlightOperations(TestDatabaseMigrationCompleteness):
    """Test flight-related database operations."""

    async def test_missing_flight_operations(self):
        """Verify that all flight operations are missing and need implementation."""
        missing_ops = [
            "find_flights_by_trip_id",
            "find_flights_by_route",
            "find_flights_by_date_range",
            "update_flight_booking_status",
            "get_flight_statistics",
        ]

        # Check that these don't exist in supabase_tools
        for op in missing_ops:
            assert not hasattr(supabase_tools, op), f"{op} should not exist yet"


class TestNeo4jOperations(TestDatabaseMigrationCompleteness):
    """Test Neo4j memory operations."""

    async def test_find_destinations_by_country(
        self, mock_mcp_manager, mock_memory_response
    ):
        """Test finding destinations by country."""
        destinations = {
            "entities": [
                {
                    "name": "Paris",
                    "entityType": "Destination",
                    "observations": ["country:France"],
                },
                {
                    "name": "Lyon",
                    "entityType": "Destination",
                    "observations": ["country:France"],
                },
            ]
        }

        mock_mcp_manager.invoke.return_value = mock_memory_response(destinations)

        with patch(
            "tripsage.tools.memory_tools.get_mcp_manager", return_value=mock_mcp_manager
        ):
            result = await memory_tools.find_destinations_by_country("France")

        assert len(result["destinations"]) == 2
        assert result["destinations"][0]["name"] == "Paris"

    async def test_create_trip_entities(self, mock_mcp_manager, mock_memory_response):
        """Test creating trip entities in the knowledge graph."""
        mock_mcp_manager.invoke.return_value = mock_memory_response(
            {"status": "success"}
        )

        trip_data = {
            "id": 1,
            "user_id": 1,
            "destinations": ["Paris", "Rome"],
            "start_date": "2024-07-01",
            "end_date": "2024-07-15",
        }

        with patch(
            "tripsage.tools.memory_tools.get_mcp_manager", return_value=mock_mcp_manager
        ):
            result = await memory_tools.create_trip_entities(
                trip_id=1,
                user_id=1,
                destinations=["Paris", "Rome"],
                start_date="2024-07-01",
                end_date="2024-07-15",
            )

        assert result["status"] == "success"
        # Verify both entity and relation creation were called
        assert mock_mcp_manager.invoke.call_count >= 2


class TestModelMigration(TestDatabaseMigrationCompleteness):
    """Test that business models are properly migrated."""

    def test_user_model_validation(self):
        """Test User model validation and business logic."""
        user = User(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.preferences == {}

        # Test preference validation
        user.update_preferences({"theme": "dark", "currency": "USD"})
        assert user.preferences["theme"] == "dark"

        # Test admin validation
        user.role = "admin"
        assert user.is_admin

    def test_trip_model_validation(self):
        """Test Trip model validation and business logic."""
        trip = Trip(
            user_id=1,
            title="Summer Trip",
            start_date="2024-07-01",
            end_date="2024-07-15",
            status=TripStatus.PLANNING,
        )

        assert trip.duration_days == 14
        assert trip.status == TripStatus.PLANNING

        # Test budget calculations
        trip.budget = 1400
        assert trip.budget_per_day == 100

    def test_missing_flight_model(self):
        """Verify that Flight model is not in the database models."""
        import tripsage.models.db as db_models

        assert not hasattr(db_models, "Flight")


class TestMigrationRunnners(TestDatabaseMigrationCompleteness):
    """Test migration runner functionality."""

    async def test_sql_migration_runner(self, mock_mcp_manager, mock_supabase_response):
        """Test SQL migration runner uses MCP."""
        from tripsage.db.migrations.runner import apply_migration

        mock_mcp_manager.invoke.return_value = mock_supabase_response(
            {"status": "success"}
        )

        with patch(
            "tripsage.db.migrations.runner.MCPManager.get_instance",
            return_value=mock_mcp_manager,
        ):
            result = await apply_migration(
                mcp_manager=mock_mcp_manager,
                project_id="test",
                filename="test_migration.sql",
                content="CREATE TABLE test (id INT);",
            )

        assert result is True
        mock_mcp_manager.invoke.assert_called()

    async def test_neo4j_migration_runner(self, mock_mcp_manager, mock_memory_response):
        """Test Neo4j migration runner uses Memory MCP."""
        from tripsage.db.migrations.neo4j_runner import initialize_neo4j_schema

        mock_mcp_manager.invoke.return_value = mock_memory_response(
            {"status": "success"}
        )

        await initialize_neo4j_schema(mock_mcp_manager)

        # Should create entity types and relationships
        assert mock_mcp_manager.invoke.call_count >= 2


class TestInitialization(TestDatabaseMigrationCompleteness):
    """Test database initialization."""

    async def test_initialize_databases(self, mock_mcp_manager):
        """Test database initialization uses MCPs."""
        from tripsage.db.initialize import initialize_databases

        mock_mcp_manager.invoke.return_value = Mock(
            error=None, result={"version": "14.0"}
        )

        with patch(
            "tripsage.db.initialize.MCPManager.get_instance",
            return_value=mock_mcp_manager,
        ):
            result = await initialize_databases(
                verify_connections=True, project_id="test"
            )

        assert result is True
        # Should verify both SQL and Neo4j connections
        assert mock_mcp_manager.invoke.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
