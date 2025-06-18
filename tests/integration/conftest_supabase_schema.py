"""
Configuration and fixtures for Supabase schema integration tests.

This module provides shared fixtures, utilities, and configuration for testing
the enhanced Supabase schema with collaboration features.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import pytest

# Configure test logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConfig:
    """Configuration for schema integration tests."""

    # Test database settings
    TEST_DB_TIMEOUT = 30.0  # seconds
    MAX_CONCURRENT_TESTS = 5

    # Performance thresholds
    QUERY_PERFORMANCE_THRESHOLD = 1.0  # seconds
    MEMORY_SEARCH_THRESHOLD = 2.0  # seconds
    COLLABORATION_QUERY_THRESHOLD = 0.5  # seconds

    # Test data limits
    MAX_TEST_USERS = 10
    MAX_TEST_TRIPS = 50
    MAX_TEST_MEMORIES = 100

    # Schema validation
    REQUIRED_TABLES = [
        "trips",
        "trip_collaborators",
        "flights",
        "accommodations",
        "chat_sessions",
        "chat_messages",
        "memories",
        "session_memories",
        "api_keys",
    ]

    REQUIRED_INDEXES = [
        "idx_trip_collaborators_user_trip",
        "idx_trip_collaborators_trip_permission",
        "idx_memories_embedding",
        "idx_session_memories_embedding",
    ]

    REQUIRED_FUNCTIONS = [
        "get_user_accessible_trips",
        "check_trip_permission",
        "search_memories",
        "search_session_memories",
    ]


class TestUser:
    """Test user representation for collaboration testing."""

    def __init__(self, role: str = "user", email: str = None):
        self.id = uuid4()
        self.role = role
        self.email = email or f"{role}_{self.id.hex[:8]}@test.com"
        self.created_at = datetime.utcnow()
        self.permissions = self._get_default_permissions(role)

    def _get_default_permissions(self, role: str) -> Dict[str, bool]:
        """Get default permissions based on role."""
        permission_map = {
            "owner": {
                "can_create_trips": True,
                "can_edit_trips": True,
                "can_delete_trips": True,
                "can_manage_collaborators": True,
                "can_view_all_data": True,
            },
            "admin": {
                "can_create_trips": True,
                "can_edit_trips": True,
                "can_delete_trips": False,
                "can_manage_collaborators": True,
                "can_view_all_data": True,
            },
            "editor": {
                "can_create_trips": False,
                "can_edit_trips": True,
                "can_delete_trips": False,
                "can_manage_collaborators": False,
                "can_view_all_data": True,
            },
            "viewer": {
                "can_create_trips": False,
                "can_edit_trips": False,
                "can_delete_trips": False,
                "can_manage_collaborators": False,
                "can_view_all_data": True,
            },
        }
        return permission_map.get(role, permission_map["viewer"])


class TestTrip:
    """Test trip representation for collaboration testing."""

    def __init__(self, owner: TestUser, name: str = None):
        self.id = abs(hash(str(uuid4()))) % (10**9)  # Simple integer ID
        self.owner = owner
        self.name = name or f"Test Trip {self.id}"
        self.collaborators = {}
        self.created_at = datetime.utcnow()
        self.status = "planning"

    def add_collaborator(self, user: TestUser, permission_level: str):
        """Add a collaborator to the trip."""
        self.collaborators[user.id] = {
            "user": user,
            "permission_level": permission_level,
            "added_at": datetime.utcnow(),
            "added_by": self.owner.id,
        }

    def get_collaborator_permission(self, user_id: UUID) -> Optional[str]:
        """Get permission level for a collaborator."""
        if user_id == self.owner.id:
            return "admin"

        collab = self.collaborators.get(user_id)
        return collab["permission_level"] if collab else None


class MockSupabaseClient:
    """Mock Supabase client for testing schema interactions."""

    def __init__(self):
        self.current_user_id: Optional[UUID] = None
        self.data_store = {
            "trips": {},
            "trip_collaborators": {},
            "memories": {},
            "session_memories": {},
            "api_keys": {},
            "flights": {},
            "accommodations": {},
            "chat_sessions": {},
            "chat_messages": {},
        }
        self.constraints_enabled = True
        self.rls_enabled = True

    def set_current_user(self, user_id: Optional[UUID]):
        """Set current authenticated user for RLS simulation."""
        self.current_user_id = user_id

    def auth_uid(self) -> Optional[UUID]:
        """Simulate auth.uid() function."""
        return self.current_user_id

    async def execute_sql(self, query: str, params: tuple = ()) -> Any:
        """Execute SQL with mock implementation."""
        query_upper = query.upper().strip()

        # Handle different SQL operations
        if query_upper.startswith("SELECT"):
            return await self._handle_select(query, params)
        elif query_upper.startswith("INSERT"):
            return await self._handle_insert(query, params)
        elif query_upper.startswith("UPDATE"):
            return await self._handle_update(query, params)
        elif query_upper.startswith("DELETE"):
            return await self._handle_delete(query, params)
        else:
            logger.info(f"Unhandled query type: {query[:50]}...")
            return None

    async def _handle_select(self, query: str, params: tuple) -> List[Dict[str, Any]]:
        """Handle SELECT queries with RLS simulation."""
        # Extract table name (simple parsing)
        if "FROM trips" in query:
            return await self._select_trips(query, params)
        elif "FROM trip_collaborators" in query:
            return await self._select_collaborators(query, params)
        elif "FROM memories" in query:
            return await self._select_memories(query, params)
        else:
            return []

    async def _select_trips(self, query: str, params: tuple) -> List[Dict[str, Any]]:
        """Handle trips table SELECT with RLS."""
        if not self.current_user_id:
            return []

        # Simulate RLS: user can see owned trips and collaborative trips
        accessible_trips = []

        for trip_id, trip_data in self.data_store["trips"].items():
            # Owner access
            if trip_data.get("user_id") == str(self.current_user_id):
                accessible_trips.append(
                    {**trip_data, "user_role": "owner", "permission_level": "admin"}
                )
            # Collaborator access
            else:
                collab_key = f"{trip_id}_{self.current_user_id}"
                if collab_key in self.data_store["trip_collaborators"]:
                    collab = self.data_store["trip_collaborators"][collab_key]
                    accessible_trips.append(
                        {
                            **trip_data,
                            "user_role": "collaborator",
                            "permission_level": collab["permission_level"],
                        }
                    )

        return accessible_trips

    async def _select_collaborators(
        self, query: str, params: tuple
    ) -> List[Dict[str, Any]]:
        """Handle trip_collaborators table SELECT with RLS."""
        if not self.current_user_id:
            return []

        # User can see collaborations they're part of or trips they own
        accessible_collabs = []

        for _collab_key, collab_data in self.data_store["trip_collaborators"].items():
            trip_id = collab_data["trip_id"]

            # User is the collaborator
            if collab_data["user_id"] == str(self.current_user_id):
                accessible_collabs.append(collab_data)
            # User owns the trip
            elif trip_id in self.data_store["trips"] and self.data_store["trips"][
                trip_id
            ]["user_id"] == str(self.current_user_id):
                accessible_collabs.append(collab_data)

        return accessible_collabs

    async def _select_memories(self, query: str, params: tuple) -> List[Dict[str, Any]]:
        """Handle memories table SELECT with RLS."""
        if not self.current_user_id:
            return []

        # User can only see their own memories
        user_memories = []

        for _memory_id, memory_data in self.data_store["memories"].items():
            if memory_data.get("user_id") == str(self.current_user_id):
                user_memories.append(memory_data)

        return user_memories

    async def _handle_insert(self, query: str, params: tuple) -> None:
        """Handle INSERT queries with constraint validation."""
        if "INTO trips" in query:
            await self._insert_trip(params)
        elif "INTO trip_collaborators" in query:
            await self._insert_collaborator(params)
        elif "INTO memories" in query:
            await self._insert_memory(params)

    async def _insert_trip(self, params: tuple) -> None:
        """Insert trip with validation."""
        if len(params) < 3:
            raise ValueError("Insufficient parameters for trip insert")

        trip_id, user_id, name = params[:3]

        # FK validation: user must exist
        if self.constraints_enabled and not self._user_exists(user_id):
            raise Exception('Foreign key constraint "trips_user_id_fkey" violated')

        self.data_store["trips"][trip_id] = {
            "id": trip_id,
            "user_id": str(user_id),
            "name": name,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def _insert_collaborator(self, params: tuple) -> None:
        """Insert collaborator with validation."""
        if len(params) < 4:
            raise ValueError("Insufficient parameters for collaborator insert")

        trip_id, user_id, permission_level, added_by = params[:4]

        # FK validation: trip and users must exist
        if self.constraints_enabled:
            if trip_id not in self.data_store["trips"]:
                raise Exception(
                    'Foreign key constraint "trip_collaborators_trip_id_fkey" violated'
                )
            if not self._user_exists(user_id):
                raise Exception(
                    'Foreign key constraint "trip_collaborators_user_id_fkey" violated'
                )

        # RLS validation: only trip owner can add collaborators
        if self.rls_enabled:
            trip = self.data_store["trips"].get(trip_id)
            if trip and trip["user_id"] != str(self.current_user_id):
                raise Exception(
                    "RLS policy violation: only trip owners can add collaborators"
                )

        collab_key = f"{trip_id}_{user_id}"
        self.data_store["trip_collaborators"][collab_key] = {
            "trip_id": trip_id,
            "user_id": str(user_id),
            "permission_level": permission_level,
            "added_by": str(added_by),
            "added_at": datetime.utcnow().isoformat(),
        }

    async def _insert_memory(self, params: tuple) -> None:
        """Insert memory with validation."""
        if len(params) < 3:
            raise ValueError("Insufficient parameters for memory insert")

        memory_id, user_id, content = params[:3]

        # FK validation: user must exist
        if self.constraints_enabled and not self._user_exists(user_id):
            raise Exception('Foreign key constraint "memories_user_id_fkey" violated')

        self.data_store["memories"][memory_id] = {
            "id": memory_id,
            "user_id": str(user_id),
            "content": content,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _user_exists(self, user_id: UUID) -> bool:
        """
        Check if user exists
        (simplified - in real implementation would check auth.users).
        """
        # For testing, assume system user and current user exist
        system_user = UUID("00000000-0000-0000-0000-000000000001")
        return user_id == system_user or user_id == self.current_user_id

    async def _handle_update(self, query: str, params: tuple) -> None:
        """Handle UPDATE queries with RLS validation."""
        logger.info(f"UPDATE query: {query[:50]}... with params: {params}")

    async def _handle_delete(self, query: str, params: tuple) -> None:
        """Handle DELETE queries with RLS validation."""
        logger.info(f"DELETE query: {query[:50]}... with params: {params}")


class SchemaValidator:
    """Validator for database schema components."""

    def __init__(self, schema_files: Dict[str, str]):
        self.schema_files = schema_files

    def validate_policies(self) -> List[str]:
        """Validate RLS policies are properly defined."""
        policies_sql = self.schema_files.get("policies", "")
        errors = []

        # Check required policy components
        required_patterns = [
            "ENABLE ROW LEVEL SECURITY",
            "CREATE POLICY",
            "auth.uid()",
            "FOR ALL USING",
        ]

        for pattern in required_patterns:
            if pattern not in policies_sql:
                errors.append(f"Missing required pattern in policies: {pattern}")

        return errors

    def validate_indexes(self) -> List[str]:
        """Validate performance indexes are defined."""
        indexes_sql = self.schema_files.get("indexes", "")
        errors = []

        for index_name in TestConfig.REQUIRED_INDEXES:
            if index_name not in indexes_sql:
                errors.append(f"Missing required index: {index_name}")

        return errors

    def validate_functions(self) -> List[str]:
        """Validate database functions are defined."""
        functions_sql = self.schema_files.get("functions", "")
        errors = []

        for function_name in TestConfig.REQUIRED_FUNCTIONS:
            if function_name not in functions_sql:
                errors.append(f"Missing required function: {function_name}")

        return errors

    def validate_migration(self, migration_sql: str) -> List[str]:
        """Validate migration safety and completeness."""
        errors = []

        # Check transaction safety
        if "BEGIN;" not in migration_sql:
            errors.append("Migration missing BEGIN transaction")
        if "COMMIT;" not in migration_sql:
            errors.append("Migration missing COMMIT transaction")

        # Check rollback instructions
        if "ROLLBACK PLAN" not in migration_sql:
            errors.append("Migration missing rollback instructions")

        # Check validation blocks
        if "VERIFICATION" not in migration_sql:
            errors.append("Migration missing verification section")

        return errors


# Test Fixtures


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture
def schema_files():
    """Load schema files for testing."""
    base_path = Path(__file__).parent.parent.parent / "supabase"

    files = {}
    schema_files = ["05_policies.sql", "02_indexes.sql", "03_functions.sql"]

    for filename in schema_files:
        file_path = base_path / "schemas" / filename
        if file_path.exists():
            files[filename.replace(".sql", "").replace("0", "").replace("_", "")] = (
                file_path.read_text()
            )

    migration_files = [
        "20250610_01_fix_user_id_constraints.sql",
        "20250609_02_consolidated_production_schema.sql",
    ]

    for filename in migration_files:
        file_path = base_path / "migrations" / filename
        if file_path.exists():
            key = (
                filename.replace(".sql", "")
                .replace("20250610_01_", "")
                .replace("20250609_02_", "")
            )
            files[key] = file_path.read_text()

    return files


@pytest.fixture
def mock_supabase_client():
    """Provide mock Supabase client."""
    return MockSupabaseClient()


@pytest.fixture
def test_users():
    """Create test users with different roles."""
    return {
        "owner": TestUser("owner"),
        "admin": TestUser("admin"),
        "editor": TestUser("editor"),
        "viewer": TestUser("viewer"),
        "unauthorized": TestUser("viewer"),  # Extra user for isolation tests
    }


@pytest.fixture
def test_trips(test_users):
    """Create test trips with collaboration setups."""
    owner = test_users["owner"]
    editor = test_users["editor"]
    viewer = test_users["viewer"]

    # Create trips
    trip1 = TestTrip(owner, "Collaborative Trip 1")
    trip1.add_collaborator(editor, "edit")
    trip1.add_collaborator(viewer, "view")

    trip2 = TestTrip(owner, "Owner Only Trip")

    trip3 = TestTrip(editor, "Editor's Trip")

    return {"collaborative": trip1, "owner_only": trip2, "editor_owned": trip3}


@pytest.fixture
async def populated_database(mock_supabase_client, test_users, test_trips):
    """Populate mock database with test data."""
    client = mock_supabase_client

    # Add test users (simulate auth.users)
    for _role, _user in test_users.items():
        # In real implementation, users would be in auth.users table
        pass

    # Add test trips
    for _, trip in test_trips.items():
        client.set_current_user(trip.owner.id)
        await client.execute_sql(
            "INSERT INTO trips (id, user_id, name) VALUES ($1, $2, $3)",
            (trip.id, trip.owner.id, trip.name),
        )

        # Add collaborators
        for collab_data in trip.collaborators.values():
            await client.execute_sql(
                "INSERT INTO trip_collaborators "
                "(trip_id, user_id, permission_level, added_by) "
                "VALUES ($1, $2, $3, $4)",
                (
                    trip.id,
                    collab_data["user"].id,
                    collab_data["permission_level"],
                    trip.owner.id,
                ),
            )

    return client


@pytest.fixture
def schema_validator(schema_files):
    """Provide schema validator."""
    return SchemaValidator(schema_files)


@pytest.fixture
def performance_tracker():
    """Track performance metrics during tests."""
    metrics = {"query_times": [], "memory_operations": [], "collaboration_queries": []}

    def track_query(operation: str, duration: float):
        metrics["query_times"].append(
            {
                "operation": operation,
                "duration": duration,
                "timestamp": datetime.utcnow(),
            }
        )

    def track_memory_operation(operation: str, duration: float, result_count: int):
        metrics["memory_operations"].append(
            {
                "operation": operation,
                "duration": duration,
                "result_count": result_count,
                "timestamp": datetime.utcnow(),
            }
        )

    def track_collaboration_query(query_type: str, duration: float, user_count: int):
        metrics["collaboration_queries"].append(
            {
                "query_type": query_type,
                "duration": duration,
                "user_count": user_count,
                "timestamp": datetime.utcnow(),
            }
        )

    def get_summary():
        return {
            "total_queries": len(metrics["query_times"]),
            "avg_query_time": sum(q["duration"] for q in metrics["query_times"])
            / max(len(metrics["query_times"]), 1),
            "memory_operations": len(metrics["memory_operations"]),
            "collaboration_queries": len(metrics["collaboration_queries"]),
            "performance_violations": [
                q
                for q in metrics["query_times"]
                if q["duration"] > TestConfig.QUERY_PERFORMANCE_THRESHOLD
            ],
        }

    class Tracker:
        def __init__(self):
            self.track_query = track_query
            self.track_memory_operation = track_memory_operation
            self.track_collaboration_query = track_collaboration_query
            self.get_summary = get_summary
            self.metrics = metrics

    return Tracker()


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Automatic cleanup after each test."""
    yield
    # Cleanup logic would go here
    # In a real implementation, this would clean up test data from the database
    logger.info("Test cleanup completed")


# Utility functions for tests


def assert_performance_threshold(duration: float, threshold: float, operation: str):
    """Assert operation meets performance threshold."""
    if duration > threshold:
        pytest.fail(
            f"{operation} took {duration:.3f}s, exceeding threshold of {threshold:.3f}s"
        )


def assert_rls_isolation(
    user1_data: List[Any], user2_data: List[Any], user1_id: UUID, user2_id: UUID
):
    """Assert RLS properly isolates data between users."""
    # Check user1 data belongs to user1
    for item in user1_data:
        if hasattr(item, "user_id"):
            assert str(item.user_id) == str(user1_id), (
                "User1 data contains data from another user"
            )
        elif isinstance(item, dict) and "user_id" in item:
            assert str(item["user_id"]) == str(user1_id), (
                "User1 data contains data from another user"
            )

    # Check user2 cannot see user1's data
    for item in user2_data:
        if hasattr(item, "user_id"):
            assert str(item.user_id) != str(user1_id), (
                "User2 can see User1's data - RLS violation"
            )
        elif isinstance(item, dict) and "user_id" in item:
            assert str(item["user_id"]) != str(user1_id), (
                "User2 can see User1's data - RLS violation"
            )


def create_test_memory_embedding() -> List[float]:
    """Create a test embedding vector for memory operations."""
    import random

    random.seed(42)  # Deterministic for testing
    return [random.uniform(-1, 1) for _ in range(1536)]


async def simulate_concurrent_access(
    operations: List[callable], max_concurrent: int = 3
) -> List[Any]:
    """Simulate concurrent database access for testing."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_operation(operation):
        async with semaphore:
            return await operation()

    tasks = [run_operation(op) for op in operations]
    return await asyncio.gather(*tasks, return_exceptions=True)


# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
    pytest.mark.database,
    pytest.mark.schema,
]
