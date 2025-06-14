#!/usr/bin/env python3
"""
Comprehensive RLS (Row Level Security) Policy Test Suite

Tests all RLS policies across the TripSage database to ensure:
- Users can only access their own data
- Collaboration permissions work correctly
- No data leakage between users
- Performance is within acceptable limits
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field
from supabase import create_client, Client


class RLSTestUser(BaseModel):
    """Test user model for RLS testing."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    password: str = "Test123!@#"
    client: Optional[Client] = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


class RLSTestResult(BaseModel):
    """Model for RLS test results."""

    test_name: str
    table_name: str
    operation: str
    user_role: str
    expected_access: bool
    actual_access: bool
    passed: bool
    error: Optional[str] = None
    performance_ms: Optional[float] = None


class RLSPolicyTester:
    """Comprehensive RLS policy testing framework."""

    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.admin_client = create_client(supabase_url, supabase_key)
        self.test_users: List[RLSTestUser] = []
        self.test_results: List[RLSTestResult] = []

    async def setup_test_users(self) -> List[RLSTestUser]:
        """Create test users for RLS testing."""
        users = [
            RLSTestUser(email="user_a@test.com"),
            RLSTestUser(email="user_b@test.com"),
            RLSTestUser(email="user_c@test.com"),
        ]

        for user in users:
            # Create user via auth
            auth_response = self.admin_client.auth.sign_up(
                {"email": user.email, "password": user.password}
            )
            user.id = auth_response.user.id
            user.client = create_client(self.supabase_url, self.supabase_key)
            await self._sign_in_user(user)

        self.test_users = users
        return users

    async def _sign_in_user(self, user: RLSTestUser) -> None:
        """Sign in a test user."""
        user.client.auth.sign_in_with_password(
            {"email": user.email, "password": user.password}
        )

    async def cleanup_test_users(self) -> None:
        """Clean up test users after testing."""
        for user in self.test_users:
            if user.client:
                user.client.auth.sign_out()
            # Admin delete user
            self.admin_client.auth.admin.delete_user(user.id)

    def record_result(
        self,
        test_name: str,
        table_name: str,
        operation: str,
        user_role: str,
        expected_access: bool,
        actual_access: bool,
        error: Optional[str] = None,
        performance_ms: Optional[float] = None,
    ) -> RLSTestResult:
        """Record a test result."""
        result = RLSTestResult(
            test_name=test_name,
            table_name=table_name,
            operation=operation,
            user_role=user_role,
            expected_access=expected_access,
            actual_access=actual_access,
            passed=expected_access == actual_access,
            error=error,
            performance_ms=performance_ms,
        )
        self.test_results.append(result)
        return result

    async def test_user_data_isolation(self) -> List[RLSTestResult]:
        """Test that users can only access their own data."""
        results = []

        # Test trips table
        user_a, user_b = self.test_users[0], self.test_users[1]

        # User A creates a trip
        start_time = time.time()
        trip_a = user_a.client.table("trips").insert(
            {
                "user_id": user_a.id,
                "name": "User A Trip",
                "start_date": "2025-07-01",
                "end_date": "2025-07-10",
                "destination": "Paris",
                "budget": 2000,
                "travelers": 2,
            }
        ).execute()
        perf_ms = (time.time() - start_time) * 1000

        results.append(
            self.record_result(
                "user_data_isolation",
                "trips",
                "INSERT",
                "owner",
                True,
                bool(trip_a.data),
                performance_ms=perf_ms,
            )
        )

        # User B tries to read User A's trip
        start_time = time.time()
        try:
            other_trips = (
                user_b.client.table("trips")
                .select("*")
                .eq("id", trip_a.data[0]["id"])
                .execute()
            )
            access_granted = len(other_trips.data) > 0
        except Exception as e:
            access_granted = False
            error = str(e)
        perf_ms = (time.time() - start_time) * 1000

        results.append(
            self.record_result(
                "user_data_isolation",
                "trips",
                "SELECT",
                "other_user",
                False,
                access_granted,
                error if not access_granted else None,
                performance_ms=perf_ms,
            )
        )

        # Test memories table
        memory_a = user_a.client.table("memories").insert(
            {
                "user_id": user_a.id,
                "memory_type": "user_preference",
                "content": "Prefers budget travel",
            }
        ).execute()

        try:
            other_memories = (
                user_b.client.table("memories")
                .select("*")
                .eq("id", memory_a.data[0]["id"])
                .execute()
            )
            access_granted = len(other_memories.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "user_data_isolation",
                "memories",
                "SELECT",
                "other_user",
                False,
                access_granted,
            )
        )

        return results

    async def test_collaboration_permissions(self) -> List[RLSTestResult]:
        """Test trip collaboration permissions."""
        results = []
        user_a, user_b, user_c = self.test_users

        # User A creates a trip
        trip = user_a.client.table("trips").insert(
            {
                "user_id": user_a.id,
                "name": "Collaborative Trip",
                "start_date": "2025-08-01",
                "end_date": "2025-08-15",
                "destination": "Tokyo",
                "budget": 5000,
                "travelers": 3,
            }
        ).execute()
        trip_id = trip.data[0]["id"]

        # User A adds User B as viewer
        collab_view = user_a.client.table("trip_collaborators").insert(
            {
                "trip_id": trip_id,
                "user_id": user_b.id,
                "permission_level": "view",
                "added_by": user_a.id,
            }
        ).execute()

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trip_collaborators",
                "INSERT",
                "trip_owner",
                True,
                bool(collab_view.data),
            )
        )

        # User B can view the trip
        shared_trip = (
            user_b.client.table("trips").select("*").eq("id", trip_id).execute()
        )
        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "SELECT",
                "viewer",
                True,
                len(shared_trip.data) > 0,
            )
        )

        # User B tries to update the trip (should fail)
        try:
            update_result = (
                user_b.client.table("trips")
                .update({"name": "Modified by User B"})
                .eq("id", trip_id)
                .execute()
            )
            update_allowed = len(update_result.data) > 0
        except Exception:
            update_allowed = False

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "UPDATE",
                "viewer",
                False,
                update_allowed,
            )
        )

        # User A upgrades User B to editor
        user_a.client.table("trip_collaborators").update(
            {"permission_level": "edit"}
        ).eq("trip_id", trip_id).eq("user_id", user_b.id).execute()

        # User B can now update the trip
        try:
            update_result = (
                user_b.client.table("trips")
                .update({"name": "Modified by Editor"})
                .eq("id", trip_id)
                .execute()
            )
            update_allowed = len(update_result.data) > 0
        except Exception:
            update_allowed = False

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "UPDATE",
                "editor",
                True,
                update_allowed,
            )
        )

        # User C cannot access the trip
        try:
            no_access = (
                user_c.client.table("trips").select("*").eq("id", trip_id).execute()
            )
            access_granted = len(no_access.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "SELECT",
                "non_collaborator",
                False,
                access_granted,
            )
        )

        return results

    async def test_cascade_permissions(self) -> List[RLSTestResult]:
        """Test that trip-related data inherits trip permissions."""
        results = []
        user_a, user_b = self.test_users[0], self.test_users[1]

        # User A creates a trip
        trip = user_a.client.table("trips").insert(
            {
                "user_id": user_a.id,
                "name": "Cascade Test Trip",
                "start_date": "2025-09-01",
                "end_date": "2025-09-07",
                "destination": "London",
                "budget": 3000,
                "travelers": 2,
            }
        ).execute()
        trip_id = trip.data[0]["id"]

        # User A adds flight to trip
        flight = user_a.client.table("flights").insert(
            {
                "trip_id": trip_id,
                "origin": "NYC",
                "destination": "LON",
                "departure_date": "2025-09-01",
                "price": 800,
            }
        ).execute()
        flight_id = flight.data[0]["id"]

        # User B cannot see the flight
        try:
            no_access = (
                user_b.client.table("flights")
                .select("*")
                .eq("id", flight_id)
                .execute()
            )
            access_granted = len(no_access.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "cascade_permissions",
                "flights",
                "SELECT",
                "non_collaborator",
                False,
                access_granted,
            )
        )

        # Add User B as collaborator
        user_a.client.table("trip_collaborators").insert(
            {
                "trip_id": trip_id,
                "user_id": user_b.id,
                "permission_level": "view",
                "added_by": user_a.id,
            }
        ).execute()

        # Now User B can see the flight
        shared_flight = (
            user_b.client.table("flights").select("*").eq("id", flight_id).execute()
        )

        results.append(
            self.record_result(
                "cascade_permissions",
                "flights",
                "SELECT",
                "viewer",
                True,
                len(shared_flight.data) > 0,
            )
        )

        # Test same pattern for accommodations
        accommodation = user_a.client.table("accommodations").insert(
            {
                "trip_id": trip_id,
                "name": "London Hotel",
                "check_in_date": "2025-09-01",
                "check_out_date": "2025-09-07",
                "price_per_night": 150,
                "total_price": 900,
            }
        ).execute()

        shared_accommodation = (
            user_b.client.table("accommodations")
            .select("*")
            .eq("id", accommodation.data[0]["id"])
            .execute()
        )

        results.append(
            self.record_result(
                "cascade_permissions",
                "accommodations",
                "SELECT",
                "viewer",
                True,
                len(shared_accommodation.data) > 0,
            )
        )

        return results

    async def test_anonymous_access(self) -> List[RLSTestResult]:
        """Test that anonymous users cannot access any data."""
        results = []

        # Create anonymous client
        anon_client = create_client(self.supabase_url, self.supabase_key)

        # Test various tables
        tables_to_test = [
            "trips",
            "flights",
            "accommodations",
            "memories",
            "api_keys",
            "chat_sessions",
            "notifications",
            "system_metrics",
            "webhook_configs",
            "webhook_logs",
        ]

        for table in tables_to_test:
            try:
                data = anon_client.table(table).select("*").limit(1).execute()
                access_granted = len(data.data) > 0
            except Exception:
                access_granted = False

            results.append(
                self.record_result(
                    "anonymous_access",
                    table,
                    "SELECT",
                    "anonymous",
                    False,
                    access_granted,
                )
            )

        return results

    async def test_search_cache_isolation(self) -> List[RLSTestResult]:
        """Test that search caches are user-specific."""
        results = []
        user_a, user_b = self.test_users[0], self.test_users[1]

        # User A creates a search cache entry
        search_cache = user_a.client.table("search_destinations").insert(
            {
                "user_id": user_a.id,
                "query": "Paris hotels",
                "query_hash": "abc123",
                "results": {"hotels": ["Hotel A", "Hotel B"]},
                "source": "cached",
                "expires_at": (datetime.now() + timedelta(days=1)).isoformat(),
            }
        ).execute()

        # User B cannot see User A's search cache
        try:
            other_cache = (
                user_b.client.table("search_destinations")
                .select("*")
                .eq("query_hash", "abc123")
                .execute()
            )
            access_granted = len(other_cache.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "search_cache_isolation",
                "search_destinations",
                "SELECT",
                "other_user",
                False,
                access_granted,
            )
        )

        return results

    async def test_notification_isolation(self) -> List[RLSTestResult]:
        """Test that users can only access their own notifications."""
        results = []
        user_a, user_b = self.test_users[0], self.test_users[1]

        # Create notification for User A (would be done by service role in production)
        # For testing, we'll use admin client to simulate service role
        notification = self.admin_client.table("notifications").insert(
            {
                "user_id": user_a.id,
                "type": "trip_reminder",
                "title": "Trip Tomorrow",
                "message": "Your trip to Paris starts tomorrow!",
                "metadata": {"trip_id": 123},
            }
        ).execute()

        if notification.data:
            notification_id = notification.data[0]["id"]

            # User A can see their notification
            user_a_notif = (
                user_a.client.table("notifications")
                .select("*")
                .eq("id", notification_id)
                .execute()
            )
            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "SELECT",
                    "owner",
                    True,
                    len(user_a_notif.data) > 0,
                )
            )

            # User B cannot see User A's notification
            try:
                user_b_notif = (
                    user_b.client.table("notifications")
                    .select("*")
                    .eq("id", notification_id)
                    .execute()
                )
                access_granted = len(user_b_notif.data) > 0
            except Exception:
                access_granted = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "SELECT",
                    "other_user",
                    False,
                    access_granted,
                )
            )

            # User A can mark their notification as read
            try:
                update_result = (
                    user_a.client.table("notifications")
                    .update({"read": True})
                    .eq("id", notification_id)
                    .execute()
                )
                update_allowed = len(update_result.data) > 0
            except Exception:
                update_allowed = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "UPDATE",
                    "owner",
                    True,
                    update_allowed,
                )
            )

            # User B cannot update User A's notification
            try:
                update_result = (
                    user_b.client.table("notifications")
                    .update({"read": True})
                    .eq("id", notification_id)
                    .execute()
                )
                update_allowed = len(update_result.data) > 0
            except Exception:
                update_allowed = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "UPDATE",
                    "other_user",
                    False,
                    update_allowed,
                )
            )

        return results

    async def test_system_tables_access(self) -> List[RLSTestResult]:
        """Test that system tables are properly restricted."""
        results = []
        user = self.test_users[0]

        # Test that users cannot access system_metrics directly
        try:
            metrics = user.client.table("system_metrics").select("*").execute()
            access_granted = len(metrics.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "system_tables_access",
                "system_metrics",
                "SELECT",
                "authenticated_user",
                False,
                access_granted,
            )
        )

        # Test that users cannot access webhook_configs
        try:
            configs = user.client.table("webhook_configs").select("*").execute()
            access_granted = len(configs.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "system_tables_access",
                "webhook_configs",
                "SELECT",
                "authenticated_user",
                False,
                access_granted,
            )
        )

        # Test that users cannot access webhook_logs
        try:
            logs = user.client.table("webhook_logs").select("*").execute()
            access_granted = len(logs.data) > 0
        except Exception:
            access_granted = False

        results.append(
            self.record_result(
                "system_tables_access",
                "webhook_logs",
                "SELECT",
                "authenticated_user",
                False,
                access_granted,
            )
        )

        return results

    async def test_performance_impact(self) -> Dict[str, float]:
        """Test RLS performance impact."""
        user = self.test_users[0]
        performance_results = {}

        # Create test data
        trip = user.client.table("trips").insert(
            {
                "user_id": user.id,
                "name": "Performance Test Trip",
                "start_date": "2025-10-01",
                "end_date": "2025-10-07",
                "destination": "Berlin",
                "budget": 2500,
                "travelers": 1,
            }
        ).execute()
        trip_id = trip.data[0]["id"]

        # Test SELECT performance
        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            user.client.table("trips").select("*").eq("id", trip_id).execute()
        select_avg_ms = ((time.time() - start_time) / iterations) * 1000
        performance_results["select_avg_ms"] = select_avg_ms

        # Test INSERT performance
        start_time = time.time()
        for i in range(10):
            user.client.table("flights").insert(
                {
                    "trip_id": trip_id,
                    "origin": "NYC",
                    "destination": f"DEST{i}",
                    "departure_date": "2025-10-01",
                    "price": 500 + i * 100,
                }
            ).execute()
        insert_avg_ms = ((time.time() - start_time) / 10) * 1000
        performance_results["insert_avg_ms"] = insert_avg_ms

        # Test JOIN performance (via RLS subqueries)
        start_time = time.time()
        for _ in range(20):
            user.client.table("flights").select("*, trips(*)").execute()
        join_avg_ms = ((time.time() - start_time) / 20) * 1000
        performance_results["join_avg_ms"] = join_avg_ms

        return performance_results

    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests

        report = f"""
# RLS Policy Test Report
Generated: {datetime.now().isoformat()}

## Summary
- Total Tests: {total_tests}
- Passed: {passed_tests}
- Failed: {failed_tests}
- Success Rate: {(passed_tests/total_tests*100):.1f}%

## Test Results by Category

### User Data Isolation
"""
        # Group results by test category
        categories = {}
        for result in self.test_results:
            if result.test_name not in categories:
                categories[result.test_name] = []
            categories[result.test_name].append(result)

        for category, results in categories.items():
            report += f"\n### {category.replace('_', ' ').title()}\n"
            report += "| Table | Operation | User Role | Expected | Actual | Status | Performance |\n"
            report += "|-------|-----------|-----------|----------|--------|--------|-------------|\n"

            for r in results:
                status = "✅ PASS" if r.passed else "❌ FAIL"
                perf = f"{r.performance_ms:.1f}ms" if r.performance_ms else "N/A"
                report += f"| {r.table_name} | {r.operation} | {r.user_role} | {r.expected_access} | {r.actual_access} | {status} | {perf} |\n"

                if not r.passed and r.error:
                    report += f"  - Error: {r.error}\n"

        # Add performance summary
        perf_results = [r for r in self.test_results if r.performance_ms]
        if perf_results:
            avg_perf = sum(r.performance_ms for r in perf_results) / len(perf_results)
            max_perf = max(r.performance_ms for r in perf_results)
            report += f"\n## Performance Summary\n"
            report += f"- Average Operation Time: {avg_perf:.2f}ms\n"
            report += f"- Max Operation Time: {max_perf:.2f}ms\n"
            report += f"- RLS Overhead: {'✅ Within limits' if max_perf < 10 else '⚠️ Exceeds 10ms target'}\n"

        # Add failed test details
        if failed_tests > 0:
            report += "\n## Failed Tests Details\n"
            for r in self.test_results:
                if not r.passed:
                    report += f"\n### {r.table_name} - {r.operation} ({r.user_role})\n"
                    report += f"- Expected: {r.expected_access}\n"
                    report += f"- Actual: {r.actual_access}\n"
                    if r.error:
                        report += f"- Error: {r.error}\n"

        return report


@pytest.mark.asyncio
async def test_rls_policies():
    """Main test function for RLS policies."""
    # Get Supabase credentials from environment
    import os

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        pytest.skip("Supabase credentials not configured")

    tester = RLSPolicyTester(supabase_url, supabase_key)

    try:
        # Setup test users
        await tester.setup_test_users()

        # Run all test categories
        await tester.test_user_data_isolation()
        await tester.test_collaboration_permissions()
        await tester.test_cascade_permissions()
        await tester.test_anonymous_access()
        await tester.test_search_cache_isolation()
        await tester.test_notification_isolation()
        await tester.test_system_tables_access()

        # Test performance
        perf_results = await tester.test_performance_impact()

        # Generate report
        report = tester.generate_report()
        print(report)

        # Write report to file
        with open("rls_test_report.md", "w") as f:
            f.write(report)

        # Assert all tests passed
        failed_tests = [r for r in tester.test_results if not r.passed]
        if failed_tests:
            pytest.fail(
                f"{len(failed_tests)} RLS tests failed. See report for details."
            )

        # Assert performance is within limits
        max_perf = max(perf_results.values())
        assert max_perf < 10, f"RLS performance exceeds 10ms limit: {max_perf:.2f}ms"

    finally:
        # Cleanup
        await tester.cleanup_test_users()


if __name__ == "__main__":
    asyncio.run(test_rls_policies())