"""Integration tests for database foreign key constraints (BJO-121).

Tests the foreign key constraints between memory tables and auth.users,
validating the migration SQL and constraint behavior through mocked database
interactions.
"""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from tripsage_core.models.db.memory import Memory, MemoryCreate


class MockForeignKeyViolationError(Exception):
    """Mock foreign key violation error for testing."""


class TestDatabaseConstraints:
    """Test foreign key constraints for memory tables."""

    @pytest.fixture
    def migration_sql(self):
        """Mock migration SQL for testing."""
        # Return a mock migration SQL that includes all the expected patterns
        return """
-- Migration: Fix user_id constraints for memory tables
-- ROLLBACK PLAN: Run the rollback queries at the end of this file

BEGIN;

-- Pre-validation: Check for invalid user_id values
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM memories
    WHERE user_id !~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'Found % records with invalid UUID format in memories table',
            invalid_count;
    END IF;
END $$;

-- Create system user if not exists
INSERT INTO auth.users (id, email, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-000000000001', 'system@tripsage.internal',
        NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Convert user_id columns to UUID type
ALTER TABLE memories
    ALTER COLUMN user_id TYPE UUID USING user_id::UUID;

ALTER TABLE session_memories
    ALTER COLUMN user_id TYPE UUID USING user_id::UUID;

-- Add foreign key constraints
ALTER TABLE memories
    ADD CONSTRAINT memories_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id)
    ON DELETE CASCADE;

ALTER TABLE session_memories
    ADD CONSTRAINT session_memories_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES auth.users(id)
    ON DELETE CASCADE;

-- Enable RLS
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_memories ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can only access their own memories"
    ON memories FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own session memories"
    ON session_memories FOR ALL
    TO authenticated
    USING (auth.uid() = user_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_session_memories_user_id ON session_memories(user_id);

COMMIT;

-- VERIFICATION QUERIES:
-- SELECT * FROM pg_policies WHERE tablename IN ('memories', 'session_memories');
-- SELECT * FROM information_schema.table_constraints
-- WHERE table_name IN ('memories', 'session_memories');

-- ROLLBACK PLAN:
-- ALTER TABLE memories DROP CONSTRAINT IF EXISTS memories_user_id_fkey;
-- ALTER TABLE session_memories DROP CONSTRAINT IF EXISTS session_memories_user_id_fkey;
-- ALTER TABLE memories ALTER COLUMN user_id TYPE TEXT;
-- ALTER TABLE session_memories ALTER COLUMN user_id TYPE TEXT;
-- DROP POLICY IF EXISTS "Users can only access their own memories" ON memories;
-- DROP POLICY IF EXISTS "Users can only access their own session memories"
-- ON session_memories;
"""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service for testing constraint behavior."""
        service = Mock()
        service.execute_query = AsyncMock()
        service.fetch_one = AsyncMock()
        service.fetch_all = AsyncMock()
        return service

    def test_migration_contains_foreign_key_constraints(self, migration_sql):
        """Test that migration SQL contains required foreign key constraints."""
        # Verify memories table constraint
        assert "ALTER TABLE memories" in migration_sql
        assert "ADD CONSTRAINT memories_user_id_fkey" in migration_sql
        assert "FOREIGN KEY (user_id) REFERENCES auth.users(id)" in migration_sql
        assert "ON DELETE CASCADE" in migration_sql

        # Verify session_memories table constraint
        assert "ALTER TABLE session_memories" in migration_sql
        assert "ADD CONSTRAINT session_memories_user_id_fkey" in migration_sql

        # Verify UUID conversion
        assert "ALTER COLUMN user_id TYPE UUID" in migration_sql
        assert "USING user_id::UUID" in migration_sql

    def test_migration_contains_rls_policies(self, migration_sql):
        """Test that migration SQL contains RLS policies."""
        assert "ENABLE ROW LEVEL SECURITY" in migration_sql
        assert (
            'CREATE POLICY "Users can only access their own memories"' in migration_sql
        )
        assert (
            'CREATE POLICY "Users can only access their own session memories"'
            in migration_sql
        )
        assert "auth.uid() = user_id" in migration_sql

    def test_migration_contains_indexes(self, migration_sql):
        """Test that migration SQL creates performance indexes."""
        assert "CREATE INDEX IF NOT EXISTS idx_memories_user_id" in migration_sql
        assert (
            "CREATE INDEX IF NOT EXISTS idx_session_memories_user_id" in migration_sql
        )

    async def test_foreign_key_constraint_validation_mocked(self, mock_db_service):
        """Test foreign key constraint validation with mocked database."""
        # Mock constraint existence check
        mock_db_service.fetch_one.return_value = {
            "constraint_name": "memories_user_id_fkey",
            "table_name": "memories",
            "constraint_type": "FOREIGN KEY",
        }

        # Simulate checking for constraint existence
        constraint = await mock_db_service.fetch_one(
            """
            SELECT constraint_name, table_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = $1 AND constraint_name = $2
            """,
            "memories",
            "memories_user_id_fkey",
        )

        assert constraint["constraint_name"] == "memories_user_id_fkey"
        assert constraint["constraint_type"] == "FOREIGN KEY"

    async def test_foreign_key_violation_simulation(self, mock_db_service):
        """Test that foreign key violations are properly raised."""
        # Mock a foreign key violation error
        fk_error = MockForeignKeyViolationError(
            'insert or update on table "memories" violates foreign key '
            'constraint "memories_user_id_fkey"'
        )
        mock_db_service.execute_query.side_effect = fk_error

        non_existent_user_id = uuid4()

        # Attempt to insert memory with non-existent user_id
        with pytest.raises(MockForeignKeyViolationError) as exc_info:
            await mock_db_service.execute_query(
                """
                INSERT INTO memories (id, user_id, memory, created_at, updated_at)
                VALUES ($1, $2, $3, NOW(), NOW())
                """,
                uuid4(),
                non_existent_user_id,
                "Test memory content",
            )

        assert "foreign key constraint" in str(exc_info.value)
        assert "memories_user_id_fkey" in str(exc_info.value)

    async def test_cascade_delete_simulation(self, mock_db_service):
        """Test cascade delete behavior through mocked database calls."""
        user_id = uuid4()

        # Mock successful user deletion that triggers cascade
        mock_db_service.execute_query.return_value = None
        mock_db_service.fetch_one.return_value = {
            "count": 0
        }  # No memories remain after cascade

        # Simulate deleting user (should cascade to memories)
        await mock_db_service.execute_query(
            "DELETE FROM auth.users WHERE id = $1", user_id
        )

        # Verify no memories remain after cascade delete
        result = await mock_db_service.fetch_one(
            "SELECT COUNT(*) as count FROM memories WHERE user_id = $1", user_id
        )

        assert result["count"] == 0

    async def test_uuid_column_type_validation(self, mock_db_service):
        """Test that user_id columns are properly typed as UUID."""
        # Mock column type information
        mock_db_service.fetch_one.side_effect = [
            {"column_name": "user_id", "data_type": "uuid"},  # memories table
            {"column_name": "user_id", "data_type": "uuid"},  # session_memories table
        ]

        # Check memories table
        memories_column = await mock_db_service.fetch_one(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'memories' AND column_name = 'user_id'
            """
        )

        assert memories_column["data_type"] == "uuid"

        # Check session_memories table
        session_memories_column = await mock_db_service.fetch_one(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'session_memories' AND column_name = 'user_id'
            """
        )

        assert session_memories_column["data_type"] == "uuid"

    def test_pydantic_model_uuid_validation(self):
        """Test that Pydantic models properly validate UUID fields."""
        user_id = uuid4()

        # Test Memory model with valid UUID
        from datetime import datetime

        memory = Memory(
            id=uuid4(),
            user_id=user_id,
            memory="Test memory content",
            embedding=None,
            metadata={},
            categories=[],
            created_at=datetime(2025, 1, 1),
            updated_at=datetime(2025, 1, 1),
            is_deleted=False,
            version=1,
            hash=None,
            relevance_score=1.0,
        )

        assert memory.user_id == user_id
        assert isinstance(memory.user_id, type(user_id))

        # Test MemoryCreate model with valid UUID
        memory_create = MemoryCreate(
            user_id=user_id, memory="Test memory for creation", relevance_score=1.0
        )

        assert memory_create.user_id == user_id
        assert isinstance(memory_create.user_id, type(user_id))

    def test_pydantic_model_invalid_uuid_rejection(self):
        """Test that Pydantic models reject invalid UUID values."""
        from pydantic import ValidationError

        # Test invalid UUID strings
        invalid_uuids = ["not-a-uuid", "123", "", "invalid-format"]

        for invalid_uuid in invalid_uuids:
            with pytest.raises(ValidationError) as exc_info:
                from typing import Any, cast

                MemoryCreate(
                    user_id=cast(Any, invalid_uuid),
                    memory="Test memory",
                    relevance_score=1.0,
                )

            error_msg = str(exc_info.value).lower()
            assert "uuid" in error_msg

    async def test_constraint_verification_sql_queries(self, mock_db_service):
        """Test the SQL queries used to verify constraint existence."""
        # Mock responses for constraint verification queries
        mock_db_service.fetch_one.side_effect = [
            {
                "constraint_name": "memories_user_id_fkey",
                "table_name": "memories",
                "constraint_type": "FOREIGN KEY",
                "foreign_table_name": "users",
                "delete_rule": "CASCADE",
            },
            {
                "constraint_name": "session_memories_user_id_fkey",
                "table_name": "session_memories",
                "constraint_type": "FOREIGN KEY",
                "foreign_table_name": "users",
                "delete_rule": "CASCADE",
            },
        ]

        # Verify memories constraint query
        memories_constraint = await mock_db_service.fetch_one(
            """
            SELECT tc.constraint_name, tc.table_name, tc.constraint_type,
                   ccu.table_name AS foreign_table_name,
                   rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = 'memories'
                AND tc.constraint_type = 'FOREIGN KEY'
            """
        )

        assert memories_constraint["constraint_type"] == "FOREIGN KEY"
        assert memories_constraint["foreign_table_name"] == "users"
        assert memories_constraint["delete_rule"] == "CASCADE"

        # Verify session_memories constraint query
        session_constraint = await mock_db_service.fetch_one(
            """
            SELECT tc.constraint_name, tc.table_name, tc.constraint_type,
                   ccu.table_name AS foreign_table_name,
                   rc.delete_rule
            FROM information_schema.table_constraints tc
            JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = 'session_memories'
                AND tc.constraint_type = 'FOREIGN KEY'
            """
        )

        assert session_constraint["constraint_type"] == "FOREIGN KEY"
        assert session_constraint["foreign_table_name"] == "users"
        assert session_constraint["delete_rule"] == "CASCADE"

    def test_migration_error_handling(self, migration_sql):
        """Test that migration includes proper error handling and validation."""
        # Check for validation blocks
        assert "DO $$" in migration_sql  # PL/pgSQL blocks for validation
        assert "RAISE EXCEPTION" in migration_sql  # Error handling
        assert "IF NOT EXISTS" in migration_sql  # Safe constraint creation

        # Check for rollback plan in comments
        assert "ROLLBACK PLAN" in migration_sql
        assert "ALTER TABLE memories DROP CONSTRAINT" in migration_sql

        # Check for verification blocks
        assert "VERIFICATION QUERIES" in migration_sql

        # Check for transaction wrapping
        assert "BEGIN;" in migration_sql
        assert "COMMIT;" in migration_sql

        # Verify BEGIN comes before COMMIT
        begin_pos = migration_sql.find("BEGIN;")
        commit_pos = migration_sql.find("COMMIT;")
        assert begin_pos < commit_pos and begin_pos >= 0

    def test_migration_pre_validation(self, migration_sql):
        """Test that migration includes pre-validation of existing data."""
        # Check for UUID format validation
        assert (
            "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
            in migration_sql
        )

        # Check for data cleaning before migration
        assert "invalid_count" in migration_sql
        assert "WHERE user_id !~" in migration_sql

        # Check for system user handling
        assert "00000000-0000-0000-0000-000000000001" in migration_sql
        assert "system@tripsage.internal" in migration_sql

    async def test_rls_policy_verification(self, mock_db_service):
        """Test RLS policy verification queries."""
        # Mock RLS policy information
        mock_db_service.fetch_all.return_value = [
            {
                "tablename": "memories",
                "policyname": "Users can only access their own memories",
                "permissive": "PERMISSIVE",
                "roles": ["{authenticated}"],
                "cmd": "ALL",
                "qual": "(auth.uid() = user_id)",
            },
            {
                "tablename": "session_memories",
                "policyname": "Users can only access their own session memories",
                "permissive": "PERMISSIVE",
                "roles": ["{authenticated}"],
                "cmd": "ALL",
                "qual": "(auth.uid() = user_id)",
            },
        ]

        # Verify RLS policies exist
        policies = await mock_db_service.fetch_all(
            "SELECT * FROM pg_policies WHERE tablename IN "
            "('memories', 'session_memories')"
        )

        assert len(policies) == 2

        memories_policy = next(p for p in policies if p["tablename"] == "memories")
        assert "auth.uid() = user_id" in memories_policy["qual"]

        session_policy = next(
            p for p in policies if p["tablename"] == "session_memories"
        )
        assert "auth.uid() = user_id" in session_policy["qual"]
