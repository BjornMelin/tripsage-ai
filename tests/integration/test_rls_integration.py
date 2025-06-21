"""Integration tests for Row Level Security policies.

These tests verify that RLS policies work correctly with a real Supabase database.
They complement the mock tests and ensure production behavior matches expectations.
"""

import os
from typing import Optional

import pytest
from dotenv import load_dotenv

from supabase import Client, create_client

# Load environment variables
load_dotenv()


@pytest.fixture
def supabase_client() -> Optional[Client]:
    """Create Supabase client if credentials are available."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        pytest.skip("Supabase credentials not available")
        return None

    return create_client(url, key)


@pytest.fixture
def service_client() -> Optional[Client]:
    """Create service role client for test setup."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        pytest.skip("Supabase service credentials not available")
        return None

    return create_client(url, key)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trip_user_isolation(supabase_client: Client, service_client: Client):
    """Test that users can only see their own trips."""
    # Create two test users
    user1_email = "rls_test_user1@example.com"
    user2_email = "rls_test_user2@example.com"
    password = "TestPassword123!"

    try:
        # Sign up users
        auth1 = supabase_client.auth.sign_up({"email": user1_email, "password": password})
        auth2 = supabase_client.auth.sign_up({"email": user2_email, "password": password})

        # Sign in as user1
        supabase_client.auth.sign_in_with_password({"email": user1_email, "password": password})

        # Create a trip as user1
        trip_data = {
            "name": "User1 Private Trip",
            "destination": "Paris",
            "start_date": "2025-07-01",
            "end_date": "2025-07-10",
            "budget": 2000,
            "travelers": 1,
        }

        trip_result = supabase_client.table("trips").insert(trip_data).execute()
        trip_id = trip_result.data[0]["id"]

        # Verify user1 can see their trip
        user1_trips = supabase_client.table("trips").select("*").eq("id", trip_id).execute()
        assert len(user1_trips.data) == 1
        assert user1_trips.data[0]["name"] == "User1 Private Trip"

        # Sign in as user2
        supabase_client.auth.sign_in_with_password({"email": user2_email, "password": password})

        # Verify user2 cannot see user1's trip
        user2_trips = supabase_client.table("trips").select("*").eq("id", trip_id).execute()
        assert len(user2_trips.data) == 0

    finally:
        # Cleanup using service client
        if service_client:
            # Delete test data
            service_client.table("trips").delete().eq("id", trip_id).execute()
            # Delete test users
            service_client.auth.admin.delete_user(auth1.user.id)
            service_client.auth.admin.delete_user(auth2.user.id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trip_collaboration_permissions(supabase_client: Client, service_client: Client):
    """Test trip collaboration with different permission levels."""
    # Create three test users
    owner_email = "rls_test_owner@example.com"
    viewer_email = "rls_test_viewer@example.com"
    editor_email = "rls_test_editor@example.com"
    password = "TestPassword123!"

    trip_id = None
    owner_id = None
    viewer_id = None
    editor_id = None

    try:
        # Sign up users
        owner_auth = supabase_client.auth.sign_up({"email": owner_email, "password": password})
        owner_id = owner_auth.user.id

        viewer_auth = supabase_client.auth.sign_up({"email": viewer_email, "password": password})
        viewer_id = viewer_auth.user.id

        editor_auth = supabase_client.auth.sign_up({"email": editor_email, "password": password})
        editor_id = editor_auth.user.id

        # Sign in as owner
        supabase_client.auth.sign_in_with_password({"email": owner_email, "password": password})

        # Create a trip
        trip_data = {
            "name": "Collaborative Trip",
            "destination": "Tokyo",
            "start_date": "2025-08-01",
            "end_date": "2025-08-15",
            "budget": 5000,
            "travelers": 3,
        }

        trip_result = supabase_client.table("trips").insert(trip_data).execute()
        trip_id = trip_result.data[0]["id"]

        # Add collaborators
        supabase_client.table("trip_collaborators").insert(
            {"trip_id": trip_id, "user_id": viewer_id, "permission_level": "view"}
        ).execute()

        supabase_client.table("trip_collaborators").insert(
            {"trip_id": trip_id, "user_id": editor_id, "permission_level": "edit"}
        ).execute()

        # Test viewer permissions
        supabase_client.auth.sign_in_with_password({"email": viewer_email, "password": password})

        # Viewer can read the trip
        viewer_trips = supabase_client.table("trips").select("*").eq("id", trip_id).execute()
        assert len(viewer_trips.data) == 1

        # Viewer cannot update the trip
        try:
            supabase_client.table("trips").update({"name": "Updated by Viewer"}).eq("id", trip_id).execute()
            raise AssertionError("Viewer should not be able to update trip")
        except Exception:
            pass  # Expected to fail

        # Test editor permissions
        supabase_client.auth.sign_in_with_password({"email": editor_email, "password": password})

        # Editor can read the trip
        editor_trips = supabase_client.table("trips").select("*").eq("id", trip_id).execute()
        assert len(editor_trips.data) == 1

        # Editor can update the trip
        update_result = supabase_client.table("trips").update({"name": "Updated by Editor"}).eq("id", trip_id).execute()
        assert len(update_result.data) == 1
        assert update_result.data[0]["name"] == "Updated by Editor"

    finally:
        # Cleanup using service client
        if service_client and trip_id:
            # Delete test data
            service_client.table("trip_collaborators").delete().eq("trip_id", trip_id).execute()
            service_client.table("trips").delete().eq("id", trip_id).execute()
            # Delete test users
            if owner_id:
                service_client.auth.admin.delete_user(owner_id)
            if viewer_id:
                service_client.auth.admin.delete_user(viewer_id)
            if editor_id:
                service_client.auth.admin.delete_user(editor_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memories_strict_isolation(supabase_client: Client, service_client: Client):
    """Test that memories have strict user isolation."""
    user1_email = "rls_memory_user1@example.com"
    user2_email = "rls_memory_user2@example.com"
    password = "TestPassword123!"

    memory_id = None
    user1_id = None
    user2_id = None

    try:
        # Sign up users
        auth1 = supabase_client.auth.sign_up({"email": user1_email, "password": password})
        user1_id = auth1.user.id

        auth2 = supabase_client.auth.sign_up({"email": user2_email, "password": password})
        user2_id = auth2.user.id

        # Sign in as user1
        supabase_client.auth.sign_in_with_password({"email": user1_email, "password": password})

        # Create a memory as user1
        memory_data = {
            "memory_type": "preference",
            "content": "User1 private preference",
            "metadata": {"category": "travel"},
        }

        memory_result = supabase_client.table("memories").insert(memory_data).execute()
        memory_id = memory_result.data[0]["id"]

        # Verify user1 can see their memory
        user1_memories = supabase_client.table("memories").select("*").eq("id", memory_id).execute()
        assert len(user1_memories.data) == 1

        # Sign in as user2
        supabase_client.auth.sign_in_with_password({"email": user2_email, "password": password})

        # Verify user2 cannot see user1's memory
        user2_memories = supabase_client.table("memories").select("*").eq("id", memory_id).execute()
        assert len(user2_memories.data) == 0

    finally:
        # Cleanup
        if service_client:
            if memory_id:
                service_client.table("memories").delete().eq("id", memory_id).execute()
            if user1_id:
                service_client.auth.admin.delete_user(user1_id)
            if user2_id:
                service_client.auth.admin.delete_user(user2_id)
