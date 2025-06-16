#!/usr/bin/env python3
"""
Real RLS (Row Level Security) Policy Tests

Tests RLS policies against actual Supabase database to ensure:
- Users can only access their own data
- Collaboration permissions work correctly
- No data leakage between users
- Policies perform well under load

This test suite connects to a real Supabase instance and creates/destroys
test data to verify RLS policies are working correctly.
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest

from supabase import create_client
from tripsage_core.models.base_core_model import TripSageModel


class RLSTestResult(TripSageModel):
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


class RealRLSPolicyTester:
    """Real RLS policy testing against actual Supabase database."""

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not self.supabase_url or not self.supabase_anon_key:
            pytest.skip("Supabase credentials not available for RLS testing")

        self.admin_client = create_client(self.supabase_url, self.supabase_anon_key)
        self.test_users: List[Dict] = []
        self.test_results: List[RLSTestResult] = []
        self.cleanup_data: List[Dict] = []

    async def setup_test_users(self) -> List[Dict]:
        """Create real test users for RLS testing."""
        test_users = []

        for i in range(3):
            email = f"rls_test_user_{i}_{int(time.time())}@tripsage.test"
            password = "TestPassword123!"

            try:
                # Create user
                response = self.admin_client.auth.sign_up(
                    {"email": email, "password": password}
                )

                if response.user:
                    user_data = {
                        "id": response.user.id,
                        "email": email,
                        "password": password,
                        "client": create_client(
                            self.supabase_url, self.supabase_anon_key
                        ),
                    }

                    # Sign in the user's client
                    await self._sign_in_user(user_data)
                    test_users.append(user_data)

            except Exception as e:
                print(f"Failed to create test user {email}: {e}")
                continue

        if len(test_users) < 2:
            pytest.skip("Failed to create sufficient test users for RLS testing")

        self.test_users = test_users
        return test_users

    async def _sign_in_user(self, user_data: Dict) -> None:
        """Sign in a test user."""
        try:
            response = user_data["client"].auth.sign_in_with_password(
                {"email": user_data["email"], "password": user_data["password"]}
            )
            if response.user:
                print(f"Successfully signed in user: {user_data['email']}")
        except Exception as e:
            print(f"Failed to sign in user {user_data['email']}: {e}")
            raise

    async def cleanup_test_data(self) -> None:
        """Clean up all test data and users."""
        # Clean up test data
        for cleanup_item in self.cleanup_data:
            try:
                table = cleanup_item["table"]
                record_id = cleanup_item["id"]
                self.admin_client.table(table).delete().eq("id", record_id).execute()
            except Exception as e:
                print(f"Failed to cleanup {cleanup_item}: {e}")

        # Clean up test users
        for user in self.test_users:
            try:
                user["client"].auth.sign_out()
                # Note: In production, you'd use admin client to delete users
                # self.admin_client.auth.admin.delete_user(user["id"])
            except Exception as e:
                print(f"Failed to cleanup user {user['email']}: {e}")

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

        if len(self.test_users) < 2:
            return results

        user_a, user_b = self.test_users[0], self.test_users[1]

        # Test 1: User A creates a trip
        start_time = time.time()
        try:
            trip_response = (
                user_a["client"]
                .table("trips")
                .insert(
                    {
                        "name": "User A Private Trip",
                        "start_date": "2025-07-01",
                        "end_date": "2025-07-10",
                        "destination": "Paris",
                        "budget": 2000,
                        "travelers": 2,
                    }
                )
                .execute()
            )

            trip_created = bool(trip_response.data)
            trip_id = trip_response.data[0]["id"] if trip_response.data else None

            if trip_id:
                self.cleanup_data.append({"table": "trips", "id": trip_id})

        except Exception:
            trip_created = False
            trip_id = None

        perf_ms = (time.time() - start_time) * 1000

        results.append(
            self.record_result(
                "user_data_isolation",
                "trips",
                "INSERT",
                "owner",
                True,
                trip_created,
                performance_ms=perf_ms,
            )
        )

        # Test 2: User B tries to read User A's trip (should fail)
        if trip_id:
            start_time = time.time()
            try:
                other_trip_response = (
                    user_b["client"]
                    .table("trips")
                    .select("*")
                    .eq("id", trip_id)
                    .execute()
                )
                access_granted = len(other_trip_response.data) > 0
                error = None
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
                    error=error,
                    performance_ms=perf_ms,
                )
            )

        # Test 3: User A creates a memory
        try:
            memory_response = (
                user_a["client"]
                .table("memories")
                .insert(
                    {
                        "memory_type": "user_preference",
                        "content": "Prefers budget travel",
                    }
                )
                .execute()
            )

            memory_id = memory_response.data[0]["id"] if memory_response.data else None
            if memory_id:
                self.cleanup_data.append({"table": "memories", "id": memory_id})
        except Exception:
            memory_id = None

        # Test 4: User B tries to read User A's memory (should fail)
        if memory_id:
            try:
                other_memory_response = (
                    user_b["client"]
                    .table("memories")
                    .select("*")
                    .eq("id", memory_id)
                    .execute()
                )
                access_granted = len(other_memory_response.data) > 0
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
        """Test trip collaboration permissions work correctly."""
        results = []

        if len(self.test_users) < 3:
            return results

        user_a, user_b, user_c = (
            self.test_users[0],
            self.test_users[1],
            self.test_users[2],
        )

        # User A creates a trip
        try:
            trip_response = (
                user_a["client"]
                .table("trips")
                .insert(
                    {
                        "name": "Collaborative Trip",
                        "start_date": "2025-08-01",
                        "end_date": "2025-08-15",
                        "destination": "Tokyo",
                        "budget": 5000,
                        "travelers": 3,
                    }
                )
                .execute()
            )

            trip_id = trip_response.data[0]["id"] if trip_response.data else None
            if trip_id:
                self.cleanup_data.append({"table": "trips", "id": trip_id})
        except Exception as e:
            trip_id = None
            print(f"Failed to create collaborative trip: {e}")

        if not trip_id:
            return results

        # User A adds User B as viewer
        try:
            collab_response = (
                user_a["client"]
                .table("trip_collaborators")
                .insert(
                    {
                        "trip_id": trip_id,
                        "user_id": user_b["id"],
                        "permission_level": "view",
                    }
                )
                .execute()
            )

            collab_id = collab_response.data[0]["id"] if collab_response.data else None
            if collab_id:
                self.cleanup_data.append(
                    {"table": "trip_collaborators", "id": collab_id}
                )

            collaboration_created = bool(collab_response.data)
        except Exception as e:
            collaboration_created = False
            print(f"Failed to create collaboration: {e}")

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trip_collaborators",
                "INSERT",
                "trip_owner",
                True,
                collaboration_created,
            )
        )

        # User B can view the shared trip
        try:
            shared_trip_response = (
                user_b["client"].table("trips").select("*").eq("id", trip_id).execute()
            )
            can_view = len(shared_trip_response.data) > 0
        except Exception:
            can_view = False

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "SELECT",
                "viewer",
                True,
                can_view,
            )
        )

        # User B tries to update the trip (should fail - viewers can't edit)
        try:
            update_response = (
                user_b["client"]
                .table("trips")
                .update({"name": "Modified by Viewer"})
                .eq("id", trip_id)
                .execute()
            )

            can_update = len(update_response.data) > 0
        except Exception:
            can_update = False

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "UPDATE",
                "viewer",
                False,
                can_update,
            )
        )

        # User C (non-collaborator) cannot access the trip
        try:
            no_access_response = (
                user_c["client"].table("trips").select("*").eq("id", trip_id).execute()
            )
            unauthorized_access = len(no_access_response.data) > 0
        except Exception:
            unauthorized_access = False

        results.append(
            self.record_result(
                "collaboration_permissions",
                "trips",
                "SELECT",
                "non_collaborator",
                False,
                unauthorized_access,
            )
        )

        return results

    async def test_cascade_permissions(self) -> List[RLSTestResult]:
        """Test that trip-related data inherits trip permissions."""
        results = []

        if len(self.test_users) < 2:
            return results

        user_a, user_b = self.test_users[0], self.test_users[1]

        # User A creates a trip
        try:
            trip_response = (
                user_a["client"]
                .table("trips")
                .insert(
                    {
                        "name": "Cascade Test Trip",
                        "start_date": "2025-09-01",
                        "end_date": "2025-09-07",
                        "destination": "London",
                        "budget": 3000,
                        "travelers": 2,
                    }
                )
                .execute()
            )

            trip_id = trip_response.data[0]["id"] if trip_response.data else None
            if trip_id:
                self.cleanup_data.append({"table": "trips", "id": trip_id})
        except Exception:
            trip_id = None

        if not trip_id:
            return results

        # User A adds flight to trip
        try:
            flight_response = (
                user_a["client"]
                .table("flights")
                .insert(
                    {
                        "trip_id": trip_id,
                        "origin": "NYC",
                        "destination": "LON",
                        "departure_date": "2025-09-01",
                        "price": 800,
                    }
                )
                .execute()
            )

            flight_id = flight_response.data[0]["id"] if flight_response.data else None
            if flight_id:
                self.cleanup_data.append({"table": "flights", "id": flight_id})
        except Exception:
            flight_id = None

        if flight_id:
            # User B cannot see the flight (not a collaborator)
            try:
                no_access_response = (
                    user_b["client"]
                    .table("flights")
                    .select("*")
                    .eq("id", flight_id)
                    .execute()
                )
                unauthorized_access = len(no_access_response.data) > 0
            except Exception:
                unauthorized_access = False

            results.append(
                self.record_result(
                    "cascade_permissions",
                    "flights",
                    "SELECT",
                    "non_collaborator",
                    False,
                    unauthorized_access,
                )
            )

        return results

    async def test_search_cache_isolation(self) -> List[RLSTestResult]:
        """Test that search caches are user-specific."""
        results = []

        if len(self.test_users) < 2:
            return results

        user_a, user_b = self.test_users[0], self.test_users[1]

        # User A creates a search cache entry
        try:
            search_response = (
                user_a["client"]
                .table("search_destinations")
                .insert(
                    {
                        "query": "Paris hotels test",
                        "query_hash": f"test_hash_{int(time.time())}",
                        "results": {"hotels": ["Test Hotel A", "Test Hotel B"]},
                        "source": "cached",
                        "expires_at": (datetime.now() + timedelta(days=1)).isoformat(),
                    }
                )
                .execute()
            )

            search_id = search_response.data[0]["id"] if search_response.data else None
            if search_id:
                self.cleanup_data.append(
                    {"table": "search_destinations", "id": search_id}
                )
                query_hash = search_response.data[0]["query_hash"]
        except Exception as e:
            search_id = None
            query_hash = None
            print(f"Failed to create search cache: {e}")

        if search_id and query_hash:
            # User B cannot see User A's search cache
            try:
                other_cache_response = (
                    user_b["client"]
                    .table("search_destinations")
                    .select("*")
                    .eq("query_hash", query_hash)
                    .execute()
                )
                unauthorized_access = len(other_cache_response.data) > 0
            except Exception:
                unauthorized_access = False

            results.append(
                self.record_result(
                    "search_cache_isolation",
                    "search_destinations",
                    "SELECT",
                    "other_user",
                    False,
                    unauthorized_access,
                )
            )

        return results

    async def test_notification_isolation(self) -> List[RLSTestResult]:
        """Test that users can only access their own notifications."""
        results = []

        if len(self.test_users) < 2:
            return results

        user_a, user_b = self.test_users[0], self.test_users[1]

        # Create notification for User A
        try:
            notification_response = (
                user_a["client"]
                .table("notifications")
                .insert(
                    {
                        "type": "trip_reminder",
                        "title": "Test Notification",
                        "message": "This is a test notification",
                        "metadata": {"test": True},
                    }
                )
                .execute()
            )

            notification_id = (
                notification_response.data[0]["id"]
                if notification_response.data
                else None
            )
            if notification_id:
                self.cleanup_data.append(
                    {"table": "notifications", "id": notification_id}
                )
        except Exception as e:
            notification_id = None
            print(f"Failed to create notification: {e}")

        if notification_id:
            # User A can see their notification
            try:
                own_notif_response = (
                    user_a["client"]
                    .table("notifications")
                    .select("*")
                    .eq("id", notification_id)
                    .execute()
                )
                can_view_own = len(own_notif_response.data) > 0
            except Exception:
                can_view_own = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "SELECT",
                    "owner",
                    True,
                    can_view_own,
                )
            )

            # User B cannot see User A's notification
            try:
                other_notif_response = (
                    user_b["client"]
                    .table("notifications")
                    .select("*")
                    .eq("id", notification_id)
                    .execute()
                )
                unauthorized_access = len(other_notif_response.data) > 0
            except Exception:
                unauthorized_access = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "SELECT",
                    "other_user",
                    False,
                    unauthorized_access,
                )
            )

            # User A can update their notification
            try:
                update_response = (
                    user_a["client"]
                    .table("notifications")
                    .update({"read": True})
                    .eq("id", notification_id)
                    .execute()
                )

                can_update_own = len(update_response.data) > 0
            except Exception:
                can_update_own = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "UPDATE",
                    "owner",
                    True,
                    can_update_own,
                )
            )

            # User B cannot update User A's notification
            try:
                unauthorized_update_response = (
                    user_b["client"]
                    .table("notifications")
                    .update({"read": True})
                    .eq("id", notification_id)
                    .execute()
                )

                unauthorized_update = len(unauthorized_update_response.data) > 0
            except Exception:
                unauthorized_update = False

            results.append(
                self.record_result(
                    "notification_isolation",
                    "notifications",
                    "UPDATE",
                    "other_user",
                    False,
                    unauthorized_update,
                )
            )

        return results

    def generate_report(self) -> str:
        """Generate a comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.passed)
        failed_tests = total_tests - passed_tests

        report = f"""
# Real RLS Policy Test Report
Generated: {datetime.now().isoformat()}
Database: {self.supabase_url}

## Summary
- Total Tests: {total_tests}
- Passed: {passed_tests}
- Failed: {failed_tests}
- Success Rate: {(passed_tests / total_tests * 100):.1f}%

## Test Results by Category
"""

        # Group results by test category
        categories = {}
        for result in self.test_results:
            if result.test_name not in categories:
                categories[result.test_name] = []
            categories[result.test_name].append(result)

        for category, results in categories.items():
            report += f"\n### {category.replace('_', ' ').title()}\n"
            report += (
                "| Table | Operation | User Role | Expected | Actual | Status | "
                "Performance |\n"
            )
            report += (
                "|-------|-----------|-----------|----------|--------|--------|"
                "-------------|\n"
            )

            for r in results:
                status = "✅ PASS" if r.passed else "❌ FAIL"
                perf = f"{r.performance_ms:.1f}ms" if r.performance_ms else "N/A"
                report += (
                    f"| {r.table_name} | {r.operation} | {r.user_role} | "
                    f"{r.expected_access} | {r.actual_access} | {status} | {perf} |\n"
                )

                if not r.passed and r.error:
                    report += f"  - Error: {r.error}\n"

        # Add failed test details
        if failed_tests > 0:
            report += "\n## ❌ Failed Tests - Action Required\n"
            for r in self.test_results:
                if not r.passed:
                    report += f"\n### {r.table_name} - {r.operation} ({r.user_role})\n"
                    report += f"- **Expected**: {r.expected_access}\n"
                    report += f"- **Actual**: {r.actual_access}\n"
                    if r.error:
                        report += f"- **Error**: {r.error}\n"

                    # Add recommendations
                    if r.table_name == "trips" and r.user_role == "other_user":
                        report += (
                            "- **Fix**: Review trips SELECT policy for user isolation\n"
                        )
                    elif (
                        r.table_name == "trips"
                        and r.user_role == "viewer"
                        and r.operation == "UPDATE"
                    ):
                        report += (
                            "- **Fix**: Review trips UPDATE policy to restrict "
                            "viewer permissions\n"
                        )
                    elif "other_user" in r.user_role:
                        report += (
                            f"- **Fix**: Review {r.table_name} policies for user "
                            f"isolation\n"
                        )

        return report


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"),
    reason="Supabase credentials not available",
)
async def test_real_rls_policies():
    """Main test function for real RLS policies."""
    tester = RealRLSPolicyTester()

    try:
        # Setup test users
        await tester.setup_test_users()

        # Run all test categories
        await tester.test_user_data_isolation()
        await tester.test_collaboration_permissions()
        await tester.test_cascade_permissions()
        await tester.test_search_cache_isolation()
        await tester.test_notification_isolation()

        # Generate report
        report = tester.generate_report()
        print(report)

        # Assert all tests passed
        failed_tests = [r for r in tester.test_results if not r.passed]
        if failed_tests:
            pytest.fail(
                f"{len(failed_tests)} real RLS tests failed. Database has "
                f"security vulnerabilities!"
            )

    finally:
        # Cleanup
        await tester.cleanup_test_data()


if __name__ == "__main__":
    asyncio.run(test_real_rls_policies())
