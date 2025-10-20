"""Performance tests for collaboration features in the Supabase schema.

This module tests query performance, indexing efficiency, and scalability
of collaboration-related database operations.
"""

import statistics
import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tests.integration.conftest_supabase_schema import (
    MockSupabaseClient,
    TestConfig,
    TestTrip,
    TestUser,
    assert_performance_threshold,
    create_test_memory_embedding,
    simulate_concurrent_access,
)


class CollaborationPerformanceTestSuite:
    """Performance test suite for collaboration features."""

    @pytest.fixture
    def large_dataset(self):
        """Create a large dataset for performance testing."""
        # Create many users
        users = [TestUser(f"user_{i}") for i in range(50)]

        # Create many trips with varying collaboration patterns
        trips = []
        for i in range(100):
            owner = users[i % len(users)]
            trip = TestTrip(owner, f"Performance Test Trip {i}")

            # Add random collaborators
            import random

            random.seed(i)  # Deterministic for testing

            num_collaborators = random.randint(1, 10)
            for _ in range(num_collaborators):
                collaborator = random.choice(users)
                if collaborator.id != owner.id:
                    permission = random.choice(["view", "edit", "admin"])
                    trip.add_collaborator(collaborator, permission)

            trips.append(trip)

        return {"users": users, "trips": trips}

    async def test_collaboration_query_performance_at_scale(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test collaboration query performance with large datasets."""
        client = mock_supabase_client
        users = large_dataset["users"]
        trips = large_dataset["trips"]

        # Populate database
        for trip in trips:
            client.set_current_user(trip.owner.id)
            await client.execute_sql(
                "INSERT INTO trips (id, user_id, name) VALUES ($1, $2, $3)",
                (trip.id, trip.owner.id, trip.name),
            )

            for collab_data in trip.collaborators.values():
                await client.execute_sql(
                    "INSERT INTO trip_collaborators (trip_id, user_id, permission_level, added_by) VALUES ($1, $2, $3, $4)",  # noqa: E501
                    (
                        trip.id,
                        collab_data["user"].id,
                        collab_data["permission_level"],
                        trip.owner.id,
                    ),
                )

        # Test collaborative trip access performance
        test_user = users[0]
        client.set_current_user(test_user.id)

        start_time = time.time()

        # Simulate complex collaboration query
        _accessible_trips = await client.execute_sql(
            """
            SELECT t.id, t.name, t.user_id,
                   CASE WHEN t.user_id = $1 THEN 'owner' ELSE 'collaborator' END as user_role,
                   COALESCE(tc.permission_level, 'admin') as permission_level
            FROM trips t
            LEFT JOIN trip_collaborators tc ON t.id = tc.trip_id AND tc.user_id = $1
            WHERE t.user_id = $1 OR tc.user_id = $1
            ORDER BY t.created_at DESC
            LIMIT 50
            """,  # noqa: E501
            (test_user.id,),
        )

        duration = time.time() - start_time
        performance_tracker.track_collaboration_query(
            "accessible_trips", duration, len(users)
        )

        # Performance assertion
        assert_performance_threshold(
            duration,
            TestConfig.COLLABORATION_QUERY_THRESHOLD,
            "Collaborative trips query",
        )

    async def test_permission_check_performance(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test performance of permission checking operations."""
        client = mock_supabase_client
        users = large_dataset["users"]
        trips = large_dataset["trips"]

        # Populate database
        await self._populate_database(client, trips)

        # Test permission checks for multiple users and trips
        permission_checks = []

        for i in range(100):  # 100 permission checks
            user = users[i % len(users)]
            trip = trips[i % len(trips)]

            start_time = time.time()

            # Simulate permission check query
            _permission = await self._check_permission(client, user.id, trip.id, "edit")

            duration = time.time() - start_time
            permission_checks.append(duration)

            performance_tracker.track_query("permission_check", duration)

        # Analyze performance statistics
        avg_duration = statistics.mean(permission_checks)
        max_duration = max(permission_checks)
        p95_duration = statistics.quantiles(permission_checks, n=20)[
            18
        ]  # 95th percentile

        # Performance assertions
        assert avg_duration < 0.1, (
            f"Average permission check too slow: {avg_duration:.3f}s"
        )
        assert max_duration < 0.5, f"Max permission check too slow: {max_duration:.3f}s"
        assert p95_duration < 0.2, f"95th percentile too slow: {p95_duration:.3f}s"

    async def test_memory_search_performance_with_collaboration(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test memory search performance in collaborative contexts."""
        client = mock_supabase_client
        users = large_dataset["users"]

        # Create many memories for users
        memories_per_user = 20
        for user in users[:10]:  # Test with 10 users
            client.set_current_user(user.id)

            for i in range(memories_per_user):
                await client.execute_sql(
                    "INSERT INTO memories (id, user_id, content, embedding) "
                    "VALUES ($1, $2, $3, $4)",
                    (
                        uuid4(),
                        user.id,
                        f"Memory content {i} for user {user.id}",
                        create_test_memory_embedding(),
                    ),
                )

        # Test vector search performance
        test_user = users[0]
        client.set_current_user(test_user.id)

        start_time = time.time()

        # Simulate memory search with vector similarity
        memories = await client.execute_sql(
            """
            SELECT m.id, m.content, m.user_id,
                   1 - (m.embedding <=> $1) as similarity
            FROM memories m
            WHERE m.user_id = $2
            AND (1 - (m.embedding <=> $1)) >= $3
            ORDER BY m.embedding <=> $1
            LIMIT $4
            """,
            (
                create_test_memory_embedding(),  # query_embedding
                test_user.id,  # user_id for RLS
                0.3,  # similarity_threshold
                10,  # limit
            ),
        )

        duration = time.time() - start_time
        performance_tracker.track_memory_operation(
            "vector_search", duration, len(memories or [])
        )

        # Performance assertion for memory search
        assert_performance_threshold(
            duration,
            TestConfig.MEMORY_SEARCH_THRESHOLD,
            "Memory vector search with RLS",
        )

    async def test_concurrent_collaboration_access(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test performance under concurrent collaboration access."""
        client = mock_supabase_client
        users = large_dataset["users"]
        trips = large_dataset["trips"]

        await self._populate_database(client, trips)

        # Create concurrent operations
        async def user_access_operation(user: TestUser):
            """Simulate a user accessing their collaborative trips."""
            client.set_current_user(user.id)

            start_time = time.time()

            # Access user's trips
            user_trips = await client.execute_sql(
                """
                SELECT t.*, tc.permission_level
                FROM trips t
                LEFT JOIN trip_collaborators tc ON t.id = tc.trip_id AND tc.user_id = $1
                WHERE t.user_id = $1 OR tc.user_id = $1
                """,
                (user.id,),
            )

            duration = time.time() - start_time
            return {
                "user": user.id,
                "trips": len(user_trips or []),
                "duration": duration,
            }

        # Run concurrent operations
        operations = [user_access_operation(user) for user in users[:20]]

        start_time = time.time()
        results = await simulate_concurrent_access(operations, max_concurrent=10)
        total_duration = time.time() - start_time

        # Analyze concurrent performance
        successful_results = [r for r in results if not isinstance(r, Exception)]
        durations = [r["duration"] for r in successful_results]

        avg_duration = statistics.mean(durations) if durations else 0
        _max_duration = max(durations) if durations else 0

        performance_tracker.track_collaboration_query(
            "concurrent_access", total_duration, len(users)
        )

        # Performance assertions
        assert len(successful_results) == len(operations), (
            "Some concurrent operations failed"
        )
        assert avg_duration < 1.0, (
            f"Average concurrent operation too slow: {avg_duration:.3f}s"
        )
        assert total_duration < 10.0, (
            f"Total concurrent test too slow: {total_duration:.3f}s"
        )

    async def test_bulk_permission_update_performance(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test performance of bulk permission updates."""
        client = mock_supabase_client
        _users = large_dataset["users"]
        trips = large_dataset["trips"]

        await self._populate_database(client, trips)

        # Test bulk permission updates
        test_trip = trips[0]
        client.set_current_user(test_trip.owner.id)

        start_time = time.time()

        # Simulate bulk permission update
        permission_updates = [
            {"user_id": str(collab_data["user"].id), "permission_level": "view"}
            for collab_data in list(test_trip.collaborators.values())[:10]
        ]

        # Mock bulk update function call
        await client.execute_sql(
            "SELECT bulk_update_collaborator_permissions($1, $2, $3)",
            (test_trip.id, test_trip.owner.id, permission_updates),
        )

        duration = time.time() - start_time
        performance_tracker.track_query("bulk_permission_update", duration)

        # Performance assertion
        assert_performance_threshold(
            duration,
            2.0,  # 2 second threshold for bulk operations
            "Bulk permission update",
        )

    async def test_index_efficiency_analysis(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test that indexes are effectively used for collaboration queries."""
        client = mock_supabase_client
        users = large_dataset["users"]
        trips = large_dataset["trips"]

        await self._populate_database(client, trips)

        # Test queries that should use specific indexes
        index_tests = [
            {
                "name": "trip_collaborators_user_trip_index",
                "query": """
                    SELECT tc.* FROM trip_collaborators tc
                    WHERE tc.user_id = $1 AND tc.trip_id = $2
                """,
                "params": (users[0].id, trips[0].id),
                "expected_duration": 0.1,
            },
            {
                "name": "trip_collaborators_permission_index",
                "query": """
                    SELECT tc.* FROM trip_collaborators tc
                    WHERE tc.trip_id = $1 AND tc.permission_level = $2
                """,
                "params": (trips[0].id, "edit"),
                "expected_duration": 0.1,
            },
            {
                "name": "memories_user_id_index",
                "query": """
                    SELECT m.* FROM memories m
                    WHERE m.user_id = $1
                    ORDER BY m.created_at DESC
                    LIMIT 10
                """,
                "params": (users[0].id,),
                "expected_duration": 0.2,
            },
        ]

        for test in index_tests:
            start_time = time.time()

            await client.execute_sql(test["query"], test["params"])

            duration = time.time() - start_time
            performance_tracker.track_query(f"index_test_{test['name']}", duration)

            # Assert index efficiency
            assert_performance_threshold(
                duration, test["expected_duration"], f"Index test: {test['name']}"
            )

    async def test_collaboration_statistics_performance(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test performance of collaboration statistics queries."""
        client = mock_supabase_client
        trips = large_dataset["trips"]

        await self._populate_database(client, trips)

        start_time = time.time()

        # Simulate collaboration statistics function
        _stats = await client.execute_sql(
            "SELECT * FROM get_collaboration_statistics()"
        )

        duration = time.time() - start_time
        performance_tracker.track_query("collaboration_statistics", duration)

        # Performance assertion for statistics query
        assert_performance_threshold(duration, 1.0, "Collaboration statistics query")

    async def test_memory_cleanup_performance(
        self, mock_supabase_client, large_dataset, performance_tracker
    ):
        """Test performance of memory cleanup operations."""
        client = mock_supabase_client
        users = large_dataset["users"]

        # Create old memories for cleanup testing
        old_date = datetime.utcnow() - timedelta(days=400)

        for user in users[:5]:
            client.set_current_user(user.id)

            for i in range(50):  # 50 old memories per user
                await client.execute_sql(
                    "INSERT INTO memories (id, user_id, content, created_at) VALUES ($1, $2, $3, $4)",  # noqa: E501
                    (uuid4(), user.id, f"Old memory {i}", old_date),
                )

        start_time = time.time()

        # Simulate cleanup function
        _deleted_count = await client.execute_sql(
            "SELECT cleanup_old_memories($1, $2)",
            (365, 100),  # days_old, max_memories_per_user
        )

        duration = time.time() - start_time
        performance_tracker.track_query("memory_cleanup", duration)

        # Performance assertion for cleanup
        assert_performance_threshold(
            duration,
            5.0,  # 5 second threshold for cleanup operations
            "Memory cleanup operation",
        )

    # Helper methods

    async def _populate_database(
        self, client: MockSupabaseClient, trips: list[TestTrip]
    ):
        """Helper to populate database with trip data."""
        for trip in trips:
            client.set_current_user(trip.owner.id)

            await client.execute_sql(
                "INSERT INTO trips (id, user_id, name) VALUES ($1, $2, $3)",
                (trip.id, trip.owner.id, trip.name),
            )

            for collab_data in trip.collaborators.values():
                await client.execute_sql(
                    "INSERT INTO trip_collaborators (trip_id, user_id, permission_level, added_by) VALUES ($1, $2, $3, $4)",  # noqa: E501
                    (
                        trip.id,
                        collab_data["user"].id,
                        collab_data["permission_level"],
                        trip.owner.id,
                    ),
                )

    async def _check_permission(
        self, client: MockSupabaseClient, user_id, trip_id, required_permission
    ):
        """Helper to check user permission for a trip."""
        return await client.execute_sql(
            "SELECT check_trip_permission($1, $2, $3) as has_permission",
            (user_id, trip_id, required_permission),
        )


class PerformanceRegressionTests:
    """Tests to detect performance regressions."""

    def test_query_complexity_analysis(self, schema_files):
        """Analyze query complexity in schema files."""
        policies_sql = schema_files.get("policies", "")

        # Count subqueries in RLS policies (indicator of complexity)
        subquery_count = policies_sql.count("SELECT") - policies_sql.count("CREATE")

        # Performance concern if too many subqueries
        assert subquery_count < 50, (
            f"Too many subqueries in RLS policies: {subquery_count}"
        )

        # Check for performance anti-patterns
        performance_warnings = []

        if "NOT IN (SELECT" in policies_sql:
            performance_warnings.append(
                "NOT IN subqueries can be slow - consider EXISTS"
            )

        if policies_sql.count("UNION") > 10:
            performance_warnings.append("Many UNION operations may impact performance")

        # Log warnings but don't fail (these are optimizations)
        if performance_warnings:
            import logging

            logger = logging.getLogger(__name__)
            for warning in performance_warnings:
                logger.warning("Performance consideration: %s", warning)

    def test_index_coverage_analysis(self, schema_files):
        """Analyze index coverage for performance-critical queries."""
        indexes_sql = schema_files.get("indexes", "")
        policies_sql = schema_files.get("policies", "")

        # Extract columns used in WHERE clauses of policies
        import re

        # Find patterns like "WHERE column_name = "
        where_patterns = re.findall(r"WHERE\s+(\w+\.\w+|\w+)\s*[=<>]", policies_sql)
        join_patterns = re.findall(
            r"JOIN\s+\w+\s+\w+\s+ON\s+(\w+\.\w+|\w+)\s*=", policies_sql
        )

        critical_columns = set(where_patterns + join_patterns)

        # Check if critical columns have indexes
        missing_indexes = []
        for column in critical_columns:
            if column not in indexes_sql and not any(
                col in column for col in ["auth.uid()", "id"]
            ):
                missing_indexes.append(column)

        # This is informational - indexes might exist with different names
        if missing_indexes:
            import logging

            logger = logging.getLogger(__name__)
            logger.info("Columns that might benefit from indexing: %s", missing_indexes)

    async def test_performance_baseline_establishment(self, performance_tracker):
        """Establish performance baselines for regression testing."""
        # This test establishes baseline performance metrics
        # In a real implementation, these would be stored and compared over time

        summary = performance_tracker.get_summary()

        baselines = {
            "max_query_time": 2.0,
            "max_memory_search_time": 3.0,
            "max_collaboration_query_time": 1.0,
            "acceptable_failure_rate": 0.01,  # 1%
        }

        # Check against baselines
        violations = summary.get("performance_violations", [])
        failure_rate = len(violations) / max(summary.get("total_queries", 1), 1)

        assert failure_rate <= baselines["acceptable_failure_rate"], (
            f"Performance failure rate {failure_rate:.2%} exceeds baseline "
            f"{baselines['acceptable_failure_rate']:.2%}"
        )

        # Log performance summary for monitoring
        import logging

        logger = logging.getLogger(__name__)
        logger.info("Performance summary: %s", summary)


# Test configuration
pytestmark = [
    pytest.mark.performance,
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.slow,  # Mark as slow tests that may be skipped in quick test runs
]


# Performance test runner helper
if __name__ == "__main__":
    # Run performance tests with specific configuration
    pytest.main(
        [
            __file__,
            "-v",
            "--tb=short",
            "-m",
            "performance",
            "--durations=10",  # Show 10 slowest tests
        ]
    )
