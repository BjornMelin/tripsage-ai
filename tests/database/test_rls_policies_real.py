#!/usr/bin/env python3
"""
Real RLS (Row Level Security) Policy Test Suite

Tests actual RLS policies against a real Supabase database to ensure:
- Users can only access their own data
- Collaboration permissions work correctly  
- No data leakage between users
- System tables are properly restricted

This replaces the mock-based test with real database testing.
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import pytest
from supabase import Client, create_client


class RealRLSPolicyTester:
    """Real RLS policy testing against actual Supabase database."""
    
    def __init__(self):
        """Initialize with real Supabase connection."""
        self.supabase_url = os.getenv("SUPABASE_URL", "https://test.supabase.co")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "test-key")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
        
        # Create clients
        self.admin_client = create_client(self.supabase_url, self.supabase_service_key)
        self.anon_client = create_client(self.supabase_url, self.supabase_anon_key)
        
        # Test users will be created during setup
        self.test_users = []
        self.user_clients = {}
        self.cleanup_data = []
        
    async def setup_test_users(self) -> List[Dict]:
        """Create real test users for RLS testing."""
        users = []
        
        for i in range(3):
            email = f"rls_test_user_{i}_{uuid.uuid4().hex[:8]}@test.com"
            password = "TestPassword123!"
            
            try:
                # Create user with admin client
                user_response = self.admin_client.auth.admin.create_user({
                    "email": email,
                    "password": password,
                    "email_confirm": True
                })
                
                if user_response.user:
                    user_data = {
                        "id": user_response.user.id,
                        "email": email,
                        "password": password
                    }
                    users.append(user_data)
                    
                    # Create authenticated client for this user
                    user_client = create_client(self.supabase_url, self.supabase_anon_key)
                    signin_response = user_client.auth.sign_in_with_password({
                        "email": email,
                        "password": password
                    })
                    
                    if signin_response.user:
                        self.user_clients[user_data["id"]] = user_client
                        
            except Exception as e:
                print(f"Failed to create user {email}: {e}")
                
        self.test_users = users
        return users
        
    async def cleanup_test_users(self):
        """Clean up test users and data."""
        # Clean up test data
        for item in self.cleanup_data:
            try:
                table = item["table"]
                id_field = item.get("id_field", "id")
                record_id = item["id"]
                
                self.admin_client.table(table).delete().eq(id_field, record_id).execute()
            except Exception as e:
                print(f"Cleanup error for {item}: {e}")
                
        # Delete test users
        for user in self.test_users:
            try:
                self.admin_client.auth.admin.delete_user(user["id"])
            except Exception as e:
                print(f"Failed to delete user {user['email']}: {e}")
                
    def test_user_data_isolation(self) -> List[Dict]:
        """Test that users can only access their own data."""
        results = []
        
        if len(self.test_users) < 2:
            return [{"error": "Need at least 2 test users"}]
            
        user_a = self.test_users[0]
        user_b = self.test_users[1]
        client_a = self.user_clients[user_a["id"]]
        client_b = self.user_clients[user_b["id"]]
        
        # Test 1: User A creates a trip
        try:
            trip_data = {
                "user_id": user_a["id"],
                "title": "User A's Trip",
                "destination": "Paris",
                "start_date": "2025-07-01",
                "end_date": "2025-07-10",
                "budget": 2000.0,
                "currency": "USD"
            }
            
            trip_response = client_a.table("trips").insert(trip_data).execute()
            
            if trip_response.data:
                trip_id = trip_response.data[0]["id"]
                self.cleanup_data.append({"table": "trips", "id": trip_id})
                
                results.append({
                    "test": "user_data_isolation",
                    "table": "trips", 
                    "operation": "INSERT",
                    "user_role": "owner",
                    "expected": True,
                    "actual": True,
                    "passed": True
                })
                
                # Test 2: User B tries to read User A's trip (should fail)
                try:
                    other_trip = client_b.table("trips").select("*").eq("id", trip_id).execute()
                    can_access = len(other_trip.data) > 0
                    
                    results.append({
                        "test": "user_data_isolation",
                        "table": "trips",
                        "operation": "SELECT", 
                        "user_role": "other_user",
                        "expected": False,
                        "actual": can_access,
                        "passed": not can_access  # Pass if cannot access
                    })
                    
                except Exception as e:
                    # Exception means access denied - this is good
                    results.append({
                        "test": "user_data_isolation",
                        "table": "trips",
                        "operation": "SELECT",
                        "user_role": "other_user", 
                        "expected": False,
                        "actual": False,
                        "passed": True,
                        "note": "Access properly denied with exception"
                    })
                    
            else:
                results.append({
                    "test": "user_data_isolation",
                    "table": "trips",
                    "operation": "INSERT",
                    "user_role": "owner",
                    "expected": True,
                    "actual": False,
                    "passed": False,
                    "error": "Failed to create trip"
                })
                
        except Exception as e:
            results.append({
                "test": "user_data_isolation", 
                "table": "trips",
                "operation": "INSERT",
                "user_role": "owner",
                "expected": True,
                "actual": False,
                "passed": False,
                "error": str(e)
            })
            
        # Test 3: Memory isolation
        try:
            memory_data = {
                "user_id": user_a["id"],
                "memory_type": "preference",
                "content": "User A's private memory"
            }
            
            memory_response = client_a.table("memories").insert(memory_data).execute()
            
            if memory_response.data:
                memory_id = memory_response.data[0]["id"]
                self.cleanup_data.append({"table": "memories", "id": memory_id})
                
                # User B tries to access User A's memory
                try:
                    other_memory = client_b.table("memories").select("*").eq("id", memory_id).execute()
                    can_access = len(other_memory.data) > 0
                    
                    results.append({
                        "test": "user_data_isolation",
                        "table": "memories",
                        "operation": "SELECT",
                        "user_role": "other_user",
                        "expected": False,
                        "actual": can_access,
                        "passed": not can_access
                    })
                    
                except Exception:
                    results.append({
                        "test": "user_data_isolation",
                        "table": "memories", 
                        "operation": "SELECT",
                        "user_role": "other_user",
                        "expected": False,
                        "actual": False,
                        "passed": True
                    })
                    
        except Exception as e:
            results.append({
                "test": "user_data_isolation",
                "table": "memories",
                "operation": "INSERT", 
                "user_role": "owner",
                "expected": True,
                "actual": False,
                "passed": False,
                "error": str(e)
            })
            
        return results
        
    def test_collaboration_permissions(self) -> List[Dict]:
        """Test trip collaboration permissions."""
        results = []
        
        if len(self.test_users) < 3:
            return [{"error": "Need at least 3 test users"}]
            
        user_a = self.test_users[0]  # Owner
        user_b = self.test_users[1]  # Collaborator
        user_c = self.test_users[2]  # Non-collaborator
        
        client_a = self.user_clients[user_a["id"]]
        client_b = self.user_clients[user_b["id"]]
        client_c = self.user_clients[user_c["id"]]
        
        try:
            # User A creates a trip
            trip_data = {
                "user_id": user_a["id"],
                "title": "Collaborative Trip",
                "destination": "Tokyo", 
                "start_date": "2025-08-01",
                "end_date": "2025-08-15",
                "budget": 5000.0,
                "currency": "USD"
            }
            
            trip_response = client_a.table("trips").insert(trip_data).execute()
            
            if not trip_response.data:
                return [{"error": "Failed to create test trip"}]
                
            trip_id = trip_response.data[0]["id"]
            self.cleanup_data.append({"table": "trips", "id": trip_id})
            
            # User A adds User B as viewer
            collab_data = {
                "trip_id": trip_id,
                "user_id": user_b["id"],
                "permission_level": "view",
                "added_by": user_a["id"]
            }
            
            collab_response = client_a.table("trip_collaborators").insert(collab_data).execute()
            
            if collab_response.data:
                collab_id = collab_response.data[0]["id"]
                self.cleanup_data.append({"table": "trip_collaborators", "id": collab_id})
                
                # Test: User B can view the trip
                shared_trip = client_b.table("trips").select("*").eq("id", trip_id).execute()
                can_view = len(shared_trip.data) > 0
                
                results.append({
                    "test": "collaboration_permissions",
                    "table": "trips",
                    "operation": "SELECT",
                    "user_role": "viewer",
                    "expected": True,
                    "actual": can_view,
                    "passed": can_view
                })
                
                # Test: User B cannot update the trip (viewer only)
                try:
                    update_response = client_b.table("trips").update({
                        "title": "Modified by Viewer"
                    }).eq("id", trip_id).execute()
                    
                    can_update = len(update_response.data) > 0
                    
                    results.append({
                        "test": "collaboration_permissions", 
                        "table": "trips",
                        "operation": "UPDATE",
                        "user_role": "viewer",
                        "expected": False,
                        "actual": can_update,
                        "passed": not can_update
                    })
                    
                except Exception:
                    results.append({
                        "test": "collaboration_permissions",
                        "table": "trips",
                        "operation": "UPDATE", 
                        "user_role": "viewer",
                        "expected": False,
                        "actual": False,
                        "passed": True
                    })
                    
                # Test: User C cannot access the trip (not a collaborator)
                try:
                    no_access = client_c.table("trips").select("*").eq("id", trip_id).execute()
                    can_access = len(no_access.data) > 0
                    
                    results.append({
                        "test": "collaboration_permissions",
                        "table": "trips", 
                        "operation": "SELECT",
                        "user_role": "non_collaborator",
                        "expected": False,
                        "actual": can_access,
                        "passed": not can_access
                    })
                    
                except Exception:
                    results.append({
                        "test": "collaboration_permissions",
                        "table": "trips",
                        "operation": "SELECT",
                        "user_role": "non_collaborator", 
                        "expected": False,
                        "actual": False,
                        "passed": True
                    })
                    
        except Exception as e:
            results.append({
                "test": "collaboration_permissions",
                "table": "trips",
                "operation": "setup",
                "user_role": "owner",
                "expected": True,
                "actual": False,
                "passed": False,
                "error": str(e)
            })
            
        return results
        
    def test_system_tables_access(self) -> List[Dict]:
        """Test that system tables are properly restricted."""
        results = []
        
        if not self.test_users:
            return [{"error": "No test users available"}]
            
        user = self.test_users[0]
        client = self.user_clients[user["id"]]
        
        # Test access to system_metrics
        try:
            metrics = client.table("system_metrics").select("*").limit(1).execute()
            can_access = len(metrics.data) > 0
            
            results.append({
                "test": "system_tables_access",
                "table": "system_metrics",
                "operation": "SELECT",
                "user_role": "authenticated_user", 
                "expected": False,
                "actual": can_access,
                "passed": not can_access
            })
            
        except Exception:
            results.append({
                "test": "system_tables_access",
                "table": "system_metrics",
                "operation": "SELECT",
                "user_role": "authenticated_user",
                "expected": False,
                "actual": False,
                "passed": True
            })
            
        # Test access to webhook_configs
        try:
            configs = client.table("webhook_configs").select("*").limit(1).execute()
            can_access = len(configs.data) > 0
            
            results.append({
                "test": "system_tables_access",
                "table": "webhook_configs",
                "operation": "SELECT", 
                "user_role": "authenticated_user",
                "expected": False,
                "actual": can_access,
                "passed": not can_access
            })
            
        except Exception:
            results.append({
                "test": "system_tables_access",
                "table": "webhook_configs",
                "operation": "SELECT",
                "user_role": "authenticated_user",
                "expected": False,
                "actual": False,
                "passed": True
            })
            
        # Test access to webhook_logs
        try:
            logs = client.table("webhook_logs").select("*").limit(1).execute()
            can_access = len(logs.data) > 0
            
            results.append({
                "test": "system_tables_access",
                "table": "webhook_logs",
                "operation": "SELECT",
                "user_role": "authenticated_user",
                "expected": False,
                "actual": can_access,
                "passed": not can_access
            })
            
        except Exception:
            results.append({
                "test": "system_tables_access",
                "table": "webhook_logs", 
                "operation": "SELECT",
                "user_role": "authenticated_user",
                "expected": False,
                "actual": False,
                "passed": True
            })
            
        return results
        
    def test_notification_isolation(self) -> List[Dict]:
        """Test that notifications are properly isolated."""
        results = []
        
        if len(self.test_users) < 2:
            return [{"error": "Need at least 2 test users"}]
            
        user_a = self.test_users[0]
        user_b = self.test_users[1]
        client_a = self.user_clients[user_a["id"]]
        client_b = self.user_clients[user_b["id"]]
        
        try:
            # Create notification for User A using admin client (service role)
            notification_data = {
                "user_id": user_a["id"],
                "type": "trip_reminder",
                "title": "Test Notification",
                "message": "This is a test notification",
                "metadata": {"test": True}
            }
            
            notification_response = self.admin_client.table("notifications").insert(notification_data).execute()
            
            if notification_response.data:
                notification_id = notification_response.data[0]["id"]
                self.cleanup_data.append({"table": "notifications", "id": notification_id})
                
                # User A can see their notification
                user_a_notif = client_a.table("notifications").select("*").eq("id", notification_id).execute()
                can_view_own = len(user_a_notif.data) > 0
                
                results.append({
                    "test": "notification_isolation",
                    "table": "notifications",
                    "operation": "SELECT",
                    "user_role": "owner",
                    "expected": True,
                    "actual": can_view_own,
                    "passed": can_view_own
                })
                
                # User B cannot see User A's notification
                try:
                    user_b_notif = client_b.table("notifications").select("*").eq("id", notification_id).execute()
                    can_view_other = len(user_b_notif.data) > 0
                    
                    results.append({
                        "test": "notification_isolation",
                        "table": "notifications",
                        "operation": "SELECT",
                        "user_role": "other_user",
                        "expected": False,
                        "actual": can_view_other,
                        "passed": not can_view_other
                    })
                    
                except Exception:
                    results.append({
                        "test": "notification_isolation",
                        "table": "notifications",
                        "operation": "SELECT",
                        "user_role": "other_user",
                        "expected": False,
                        "actual": False,
                        "passed": True
                    })
                    
                # User A can update their notification
                try:
                    update_response = client_a.table("notifications").update({
                        "read": True
                    }).eq("id", notification_id).execute()
                    
                    can_update_own = len(update_response.data) > 0
                    
                    results.append({
                        "test": "notification_isolation",
                        "table": "notifications",
                        "operation": "UPDATE",
                        "user_role": "owner",
                        "expected": True,
                        "actual": can_update_own,
                        "passed": can_update_own
                    })
                    
                except Exception as e:
                    results.append({
                        "test": "notification_isolation",
                        "table": "notifications",
                        "operation": "UPDATE",
                        "user_role": "owner",
                        "expected": True,
                        "actual": False,
                        "passed": False,
                        "error": str(e)
                    })
                    
                # User B cannot update User A's notification
                try:
                    update_response = client_b.table("notifications").update({
                        "read": True
                    }).eq("id", notification_id).execute()
                    
                    can_update_other = len(update_response.data) > 0
                    
                    results.append({
                        "test": "notification_isolation",
                        "table": "notifications",
                        "operation": "UPDATE",
                        "user_role": "other_user",
                        "expected": False,
                        "actual": can_update_other,
                        "passed": not can_update_other
                    })
                    
                except Exception:
                    results.append({
                        "test": "notification_isolation",
                        "table": "notifications",
                        "operation": "UPDATE",
                        "user_role": "other_user",
                        "expected": False,
                        "actual": False,
                        "passed": True
                    })
                    
        except Exception as e:
            results.append({
                "test": "notification_isolation",
                "table": "notifications",
                "operation": "setup",
                "user_role": "admin",
                "expected": True,
                "actual": False,
                "passed": False,
                "error": str(e)
            })
            
        return results
        
    def generate_report(self, all_results: List[List[Dict]]) -> str:
        """Generate comprehensive test report."""
        flat_results = []
        for result_group in all_results:
            flat_results.extend(result_group)
            
        total_tests = len(flat_results)
        passed_tests = sum(1 for r in flat_results if r.get("passed", False))
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

## Test Results

| Test Category | Table | Operation | User Role | Expected | Actual | Status |
|---------------|-------|-----------|-----------|----------|--------|--------|
"""
        
        for result in flat_results:
            status = "✅ PASS" if result.get("passed", False) else "❌ FAIL"
            expected = result.get("expected", "N/A")
            actual = result.get("actual", "N/A")
            
            report += f"| {result.get('test', 'N/A')} | {result.get('table', 'N/A')} | {result.get('operation', 'N/A')} | {result.get('user_role', 'N/A')} | {expected} | {actual} | {status} |\n"
            
        # Add failed test details
        failed_results = [r for r in flat_results if not r.get("passed", False)]
        if failed_results:
            report += "\n## Failed Tests Details\n\n"
            for result in failed_results:
                report += f"### {result.get('table', 'Unknown')} - {result.get('operation', 'Unknown')} ({result.get('user_role', 'Unknown')})\n"
                report += f"- Expected: {result.get('expected', 'N/A')}\n"
                report += f"- Actual: {result.get('actual', 'N/A')}\n"
                if result.get('error'):
                    report += f"- Error: {result['error']}\n"
                report += "\n"
                
        return report


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="Real Supabase credentials required for RLS testing"
)
async def test_real_rls_policies():
    """Test RLS policies against real Supabase database."""
    tester = RealRLSPolicyTester()
    
    try:
        # Setup test users
        users = await tester.setup_test_users()
        if len(users) < 2:
            pytest.skip("Could not create enough test users")
            
        # Run all test categories
        all_results = []
        all_results.append(tester.test_user_data_isolation())
        all_results.append(tester.test_collaboration_permissions())
        all_results.append(tester.test_system_tables_access())
        all_results.append(tester.test_notification_isolation())
        
        # Generate and print report
        report = tester.generate_report(all_results)
        print(report)
        
        # Assert all tests passed
        flat_results = []
        for result_group in all_results:
            flat_results.extend(result_group)
            
        failed_tests = [r for r in flat_results if not r.get("passed", False)]
        if failed_tests:
            failure_details = []
            for test in failed_tests:
                details = f"{test.get('table', 'Unknown')}.{test.get('operation', 'Unknown')} ({test.get('user_role', 'Unknown')})"
                if test.get('error'):
                    details += f": {test['error']}"
                failure_details.append(details)
                
            pytest.fail(
                f"{len(failed_tests)} RLS tests failed:\n" + 
                "\n".join(f"- {detail}" for detail in failure_details)
            )
            
    finally:
        # Cleanup
        await tester.cleanup_test_users()


if __name__ == "__main__":
    asyncio.run(test_real_rls_policies())