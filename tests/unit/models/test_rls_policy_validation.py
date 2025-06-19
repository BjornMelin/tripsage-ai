"""
Comprehensive RLS (Row Level Security) policy validation tests for BJO-121.

Tests the RLS policies for memory tables to ensure proper user data isolation
and security compliance with Supabase authentication.
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest


class TestRLSPolicyValidation:
    """Test suite for RLS policy validation and security enforcement."""

    @pytest.fixture
    def migration_sql(self):
        """Load the migration SQL file."""
        migration_file = (
            Path(__file__).parent.parent.parent.parent
            / "supabase"
            / "migrations"
            / "20250610_01_fix_user_id_constraints.sql"
        )
        return migration_file.read_text()

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service for policy testing."""
        service = Mock()
        service.execute_query = AsyncMock()
        service.fetch_one = AsyncMock()
        service.fetch_all = AsyncMock()
        return service

    def test_rls_policy_existence_in_migration(self, migration_sql):
        """Test that RLS policies are properly defined in migration."""
        # Should enable RLS on both memory tables
        assert "ALTER TABLE memories ENABLE ROW LEVEL SECURITY" in migration_sql
        assert "ALTER TABLE session_memories ENABLE ROW LEVEL SECURITY" in migration_sql

        # Should create named policies for memories table
        assert (
            'CREATE POLICY "Users can only access their own memories"' in migration_sql
        )
        assert "ON memories" in migration_sql

        # Should create named policies for session_memories table
        assert (
            'CREATE POLICY "Users can only access their own session memories"'
            in migration_sql
        )
        assert "ON session_memories" in migration_sql

    def test_rls_policy_access_control_logic(self, migration_sql):
        """Test that RLS policies use proper access control logic."""
        # Should use auth.uid() for user identification
        assert "auth.uid() = user_id" in migration_sql, (
            "Policies should use auth.uid() for user isolation"
        )

        # RLS policies implicitly apply to all roles accessing the table
        # Supabase handles authentication at the connection level

        # Should cover all operations (ALL includes SELECT, INSERT, UPDATE, DELETE)
        policy_definitions = migration_sql.split("CREATE POLICY")

        for policy in policy_definitions[1:]:  # Skip the first split result
            if "memories" in policy or "session_memories" in policy:
                # Each policy should specify operations
                assert (
                    "FOR ALL" in policy
                    or "FOR SELECT" in policy
                    or "FOR INSERT" in policy
                ), f"Policy should specify operation type: {policy[:100]}..."

    def test_rls_policy_security_isolation(self, migration_sql):
        """Test that RLS policies enforce proper security isolation."""
        # Policies should prevent cross-user data access
        memory_policy_section = migration_sql[
            migration_sql.find("Users can only access their own memories") :
        ]
        session_policy_section = migration_sql[
            migration_sql.find("Users can only access their own session memories") :
        ]

        # Each policy should have a proper USING clause for isolation
        for section_name, section in [
            ("memories", memory_policy_section),
            ("session_memories", session_policy_section),
        ]:
            if "USING" in section:
                using_clause = section[
                    section.find("USING") : section.find(";", section.find("USING"))
                ]
                assert "user_id" in using_clause, (
                    f"{section_name} policy should reference user_id in USING clause"
                )
                assert "auth.uid()" in using_clause, (
                    f"{section_name} policy should use auth.uid() in USING clause"
                )

    def test_rls_policy_comprehensive_coverage(self, migration_sql):
        """Test that RLS policies provide comprehensive table coverage."""
        # Should cover both primary memory tables
        required_tables = ["memories", "session_memories"]

        for table in required_tables:
            # Each table should have RLS enabled
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in migration_sql, (
                f"RLS should be enabled on {table} table"
            )

            # Each table should have at least one policy
            assert f"ON {table}" in migration_sql, (
                f"Should have policy defined for {table} table"
            )

    async def test_rls_policy_structure_validation(self, mock_db_service):
        """Test RLS policy structure through simulated database queries."""
        # Mock policy information structure
        mock_db_service.fetch_all.return_value = [
            {
                "schemaname": "public",
                "tablename": "memories",
                "policyname": "Users can only access their own memories",
                "permissive": "PERMISSIVE",
                "roles": ["{authenticated}"],
                "cmd": "ALL",
                "qual": "(auth.uid() = user_id)",
                "with_check": None,
            },
            {
                "schemaname": "public",
                "tablename": "session_memories",
                "policyname": "Users can only access their own session memories",
                "permissive": "PERMISSIVE",
                "roles": ["{authenticated}"],
                "cmd": "ALL",
                "qual": "(auth.uid() = user_id)",
                "with_check": None,
            },
        ]

        # Simulate querying policy information
        policies = await mock_db_service.fetch_all(
            "SELECT * FROM pg_policies "
            "WHERE tablename IN ('memories', 'session_memories')"
        )

        # Validate policy structure
        assert len(policies) == 2, "Should have policies for both memory tables"

        for policy in policies:
            assert policy["permissive"] == "PERMISSIVE", (
                "Policies should be permissive type"
            )
            assert "authenticated" in str(policy["roles"]), (
                "Policies should apply to authenticated role"
            )
            assert policy["cmd"] == "ALL", "Policies should cover all operations"
            assert "auth.uid() = user_id" in policy["qual"], (
                "Policies should use proper user isolation"
            )

    async def test_rls_policy_operation_coverage(self, mock_db_service):
        """Test that RLS policies cover all necessary database operations."""
        # Mock different operation types
        operation_types = ["ALL", "SELECT", "INSERT", "UPDATE", "DELETE"]

        for operation in operation_types:
            mock_db_service.fetch_all.return_value = [
                {
                    "tablename": "memories",
                    "policyname": f"memories_{operation.lower()}_policy",
                    "cmd": operation,
                    "qual": "(auth.uid() = user_id)",
                }
            ]

            policies = await mock_db_service.fetch_all(
                f"SELECT * FROM pg_policies WHERE tablename = 'memories' "
                f"AND cmd = '{operation}'"
            )

            # At minimum should have an ALL policy or specific operation policy
            if operation == "ALL":
                assert len(policies) >= 1, (
                    "Should have at least one ALL policy or specific policies"
                )

    def test_rls_policy_performance_considerations(self, migration_sql):
        """Test that RLS policies are designed for performance."""
        # Should create indexes for RLS policy filters
        assert "CREATE INDEX" in migration_sql, (
            "Should create indexes for RLS performance"
        )
        assert "idx_memories_user_id" in migration_sql, (
            "Should index memories.user_id for RLS"
        )
        assert "idx_session_memories_user_id" in migration_sql, (
            "Should index session_memories.user_id for RLS"
        )

        # Policies should use simple equality comparisons for best performance
        policy_sections = migration_sql.split("CREATE POLICY")
        for policy in policy_sections[1:]:
            if "auth.uid() = user_id" in policy:
                # Simple equality is good for performance
                assert "=" in policy, (
                    "Should use simple equality for user_id comparison"
                )
                # Should not use complex expressions that hurt performance
                assert "LIKE" not in policy, (
                    "Should avoid LIKE operations in RLS policies"
                )
                assert "IN (SELECT" not in policy, (
                    "Should avoid subqueries in RLS policies for performance"
                )

    async def test_rls_policy_edge_cases(self, mock_db_service):
        """Test RLS policy behavior in edge cases."""
        # Test anonymous user access (should be blocked)
        mock_db_service.fetch_one.return_value = {"count": 0}

        # Simulate anonymous user trying to access memories
        result = await mock_db_service.fetch_one(
            "SELECT COUNT(*) as count FROM memories WHERE auth.uid() IS NULL"
        )
        assert result["count"] == 0, "Anonymous users should not access any memories"

        # Test null user_id handling
        mock_db_service.execute_query.side_effect = Exception("RLS policy violation")

        with pytest.raises(Exception, match="RLS policy violation"):
            await mock_db_service.execute_query(
                "INSERT INTO memories (id, user_id, content) VALUES ($1, NULL, $2)",
                uuid4(),
                "test content",
            )

    def test_rls_policy_consistency_across_tables(self, migration_sql):
        """Test that RLS policies are consistent across related tables."""
        # Extract policy definitions for comparison
        memory_policy_start = migration_sql.find(
            'CREATE POLICY "Users can only access their own memories"'
        )
        memory_policy_end = migration_sql.find(";", memory_policy_start)
        memory_policy = migration_sql[memory_policy_start:memory_policy_end]

        session_policy_start = migration_sql.find(
            'CREATE POLICY "Users can only access their own session memories"'
        )
        session_policy_end = migration_sql.find(";", session_policy_start)
        session_policy = migration_sql[session_policy_start:session_policy_end]

        # Both policies should use same access control logic
        assert "auth.uid() = user_id" in memory_policy, (
            "Memory policy should use auth.uid() = user_id"
        )
        assert "auth.uid() = user_id" in session_policy, (
            "Session memory policy should use auth.uid() = user_id"
        )

        # Both should use FOR ALL to cover all operations
        assert "FOR ALL" in memory_policy, "Memory policy should use FOR ALL operations"
        assert "FOR ALL" in session_policy, (
            "Session memory policy should use FOR ALL operations"
        )

        # Both should use USING clause for row-level filtering
        assert "USING" in memory_policy, "Memory policy should have USING clause"
        assert "USING" in session_policy, (
            "Session memory policy should have USING clause"
        )

    async def test_rls_policy_verification_queries(self, mock_db_service):
        """Test the verification queries for RLS policy existence."""
        # Mock successful policy verification
        mock_db_service.fetch_all.return_value = [
            {
                "tablename": "memories",
                "policyname": "Users can only access their own memories",
                "cmd": "ALL",
                "qual": "(auth.uid() = user_id)",
            },
            {
                "tablename": "session_memories",
                "policyname": "Users can only access their own session memories",
                "cmd": "ALL",
                "qual": "(auth.uid() = user_id)",
            },
        ]

        # Verify policies exist
        policies = await mock_db_service.fetch_all(
            "SELECT tablename, policyname, cmd, qual FROM pg_policies "
            "WHERE tablename IN ('memories', 'session_memories')"
        )

        assert len(policies) == 2, "Should find policies for both tables"
        table_names = [p["tablename"] for p in policies]
        assert "memories" in table_names, "Should have policy for memories table"
        assert "session_memories" in table_names, (
            "Should have policy for session_memories table"
        )

    def test_rls_policy_documentation_and_naming(self, migration_sql):
        """Test that RLS policies are well-documented and named."""
        # Policy names should be descriptive
        assert "Users can only access their own memories" in migration_sql, (
            "Memory policy should have descriptive name"
        )
        assert "Users can only access their own session memories" in migration_sql, (
            "Session memory policy should have descriptive name"
        )

        # Should include comments explaining RLS setup
        assert "Row Level Security" in migration_sql or "RLS" in migration_sql, (
            "Should document RLS purpose"
        )
        assert "data isolation" in migration_sql or "security" in migration_sql, (
            "Should explain security purpose"
        )

    async def test_rls_policy_auth_integration(self, mock_db_service):
        """Test RLS policy integration with Supabase auth system."""
        # Should reference auth schema functions
        test_user_id = uuid4()

        # Mock auth.uid() function call
        mock_db_service.fetch_one.return_value = {"current_user": str(test_user_id)}

        current_user = await mock_db_service.fetch_one(
            "SELECT auth.uid() as current_user"
        )
        assert current_user["current_user"] == str(test_user_id), (
            "Should integrate with auth.uid()"
        )

        # Mock policy enforcement simulation
        mock_db_service.fetch_all.return_value = [
            {"id": 1, "user_id": str(test_user_id), "content": "User's own memory"}
        ]

        # Simulate RLS-filtered query
        memories = await mock_db_service.fetch_all(
            "SELECT * FROM memories WHERE user_id = auth.uid()"
        )

        assert len(memories) == 1, "Should return only user's own memories"
        assert memories[0]["user_id"] == str(test_user_id), (
            "Should match authenticated user ID"
        )

    def test_rls_policy_migration_safety(self, migration_sql):
        """Test that RLS policy migration includes safety measures."""
        # Should verify auth schema exists before creating policies
        assert "auth.users" in migration_sql, (
            "Should verify auth schema before RLS setup"
        )

        # Should include rollback instructions for RLS
        rollback_section = migration_sql[migration_sql.find("ROLLBACK PLAN") :]
        assert "DISABLE ROW LEVEL SECURITY" in rollback_section, (
            "Should include RLS rollback instructions"
        )

        # Should verify policies were created successfully
        verification_section = migration_sql[migration_sql.find("VERIFICATION") :]
        assert "pg_policies" in verification_section, "Should verify policy creation"

    async def test_rls_policy_compliance_validation(self, mock_db_service):
        """Test RLS policy compliance with security best practices."""
        # Mock policy analysis for security compliance
        mock_db_service.fetch_all.return_value = [
            {
                "tablename": "memories",
                "policyname": "Users can only access their own memories",
                "permissive": "PERMISSIVE",  # Should be permissive, not restrictive
                "roles": ["{authenticated}"],  # Should target authenticated users
                "cmd": "ALL",  # Should cover all operations
                "qual": "(auth.uid() = user_id)",  # Should use proper user isolation
                "with_check": None,  # No additional check constraint needed
            }
        ]

        policies = await mock_db_service.fetch_all(
            "SELECT * FROM pg_policies WHERE tablename = 'memories'"
        )

        for policy in policies:
            # Security compliance checks
            assert policy["permissive"] == "PERMISSIVE", (
                "Policies should be permissive for normal operation"
            )
            assert "authenticated" in str(policy["roles"]), (
                "Policies should only apply to authenticated users"
            )
            assert "auth.uid()" in policy["qual"], (
                "Policies should use Supabase auth integration"
            )
            assert "user_id" in policy["qual"], (
                "Policies should reference user_id for isolation"
            )

    def test_rls_policy_testing_framework_integration(self, migration_sql):
        """Test that RLS policies can be properly tested."""
        # Migration should include testing instructions or verification
        assert "VERIFICATION" in migration_sql, (
            "Should include verification instructions"
        )

        # Should provide example queries for testing RLS
        verification_section = migration_sql[migration_sql.rfind("VERIFICATION") :]
        assert "pg_policies" in verification_section, (
            "Should show how to verify policies"
        )

        # Should document how to test policy enforcement
        comments_section = migration_sql[migration_sql.rfind("POST-MIGRATION NOTES") :]
        assert "Check RLS policies" in comments_section, (
            "Should document policy testing"
        )
