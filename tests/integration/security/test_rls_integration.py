"""Integration tests for Row Level Security policies.

These tests verify that RLS policies work correctly with a real Supabase database.
They complement the mock tests and ensure production behavior matches expectations.
"""

import os

import pytest
from dotenv import load_dotenv
from supabase import Client, create_client


# Load environment variables
load_dotenv()


@pytest.fixture
def supabase_client() -> Client | None:
    """Create Supabase client if credentials are available."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        pytest.skip("Supabase credentials not available")
        return None

    return create_client(url, key)


@pytest.fixture
def service_client() -> Client | None:
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

    auth1 = None
    auth2 = None
    try:
        # Sign up users
        auth1 = supabase_client.auth.sign_up(  # type: ignore
            {"email": user1_email, "password": password}
        )
        auth2 = supabase_client.auth.sign_up(  # type: ignore
            {"email": user2_email, "password": password}
        )

        # Sign in as user1
        supabase_client.auth.sign_in_with_password(
            {"email": user1_email, "password": password}
        )

        # Create a trip as user1
        trip_data = {
            "name": "User1 Private Trip",
            "destination": "Paris",
            "start_date": "2025-07-01",
            "end_date": "2025-07-10",
            "budget": 2000,
            "travelers": 1,
        }

        trip_result = supabase_client.table("trips").insert(trip_data).execute()  # type: ignore
        trip_id = trip_result.data[0]["id"]  # type: ignore

        # Verify user1 can see their trip
        user1_trips = (
            supabase_client.table("trips").select("*").eq("id", trip_id).execute()  # type: ignore
        )
        assert len(user1_trips.data) == 1  # type: ignore
        assert user1_trips.data[0]["name"] == "User1 Private Trip"  # type: ignore

        # Sign in as user2
        supabase_client.auth.sign_in_with_password(
            {"email": user2_email, "password": password}
        )

        # Verify user2 cannot see user1's trip
        user2_trips = (
            supabase_client.table("trips").select("*").eq("id", trip_id).execute()  # type: ignore
        )
        assert len(user2_trips.data) == 0  # type: ignore

    finally:
        # Cleanup using service client
        if service_client:
            # Delete test data
            service_client.table("trips").delete().eq("id", trip_id).execute()  # type: ignore
            # Delete test users
            if auth1 and auth1.user:
                service_client.auth.admin.delete_user(auth1.user.id)  # type: ignore
            if auth2 and auth2.user:
                service_client.auth.admin.delete_user(auth2.user.id)  # type: ignore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_trip_collaboration_permissions(
    supabase_client: Client, service_client: Client
):
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
        owner_auth = supabase_client.auth.sign_up(  # type: ignore
            {"email": owner_email, "password": password}
        )
        owner_id = owner_auth.user.id  # type: ignore

        viewer_auth = supabase_client.auth.sign_up(  # type: ignore
            {"email": viewer_email, "password": password}
        )
        viewer_id = viewer_auth.user.id  # type: ignore

        editor_auth = supabase_client.auth.sign_up(  # type: ignore
            {"email": editor_email, "password": password}
        )
        editor_id = editor_auth.user.id  # type: ignore

        # Sign in as owner
        supabase_client.auth.sign_in_with_password(
            {"email": owner_email, "password": password}
        )

        # Create a trip
        trip_data = {
            "name": "Collaborative Trip",
            "destination": "Tokyo",
            "start_date": "2025-08-01",
            "end_date": "2025-08-15",
            "budget": 5000,
            "travelers": 3,
        }

        trip_result = supabase_client.table("trips").insert(trip_data).execute()  # type: ignore
        trip_id = trip_result.data[0]["id"]  # type: ignore

        # Add collaborators
        supabase_client.table("trip_collaborators").insert(  # type: ignore
            {"trip_id": trip_id, "user_id": viewer_id, "permission_level": "view"}
        ).execute()  # type: ignore

        supabase_client.table("trip_collaborators").insert(  # type: ignore
            {"trip_id": trip_id, "user_id": editor_id, "permission_level": "edit"}
        ).execute()  # type: ignore

        # Test viewer permissions
        supabase_client.auth.sign_in_with_password(  # type: ignore
            {"email": viewer_email, "password": password}
        )

        # Viewer can read the trip
        viewer_trips = (
            supabase_client.table("trips").select("*").eq("id", trip_id).execute()  # type: ignore
        )
        assert len(viewer_trips.data) == 1  # type: ignore

        # Viewer cannot update the trip
        try:
            supabase_client.table("trips").update({"name": "Updated by Viewer"}).eq(  # type: ignore
                "id", trip_id
            ).execute()  # type: ignore
            raise AssertionError("Viewer should not be able to update trip")
        except (PermissionError, ValueError):
            pass  # Expected to fail

        # Test editor permissions
        supabase_client.auth.sign_in_with_password(  # type: ignore
            {"email": editor_email, "password": password}
        )

        # Editor can read the trip
        editor_trips = (
            supabase_client.table("trips").select("*").eq("id", trip_id).execute()  # type: ignore
        )
        assert len(editor_trips.data) == 1  # type: ignore

        # Editor can update the trip
        update_result = (
            supabase_client.table("trips")  # type: ignore
            .update({"name": "Updated by Editor"})
            .eq("id", trip_id)
            .execute()  # type: ignore
        )
        assert len(update_result.data) == 1  # type: ignore
        assert update_result.data[0]["name"] == "Updated by Editor"  # type: ignore

    finally:
        # Cleanup using service client
        if service_client and trip_id:
            # Delete test data
            service_client.table("trip_collaborators").delete().eq(  # type: ignore
                "trip_id", trip_id
            ).execute()  # type: ignore
            service_client.table("trips").delete().eq("id", trip_id).execute()  # type: ignore
            # Delete test users
            if owner_id:
                service_client.auth.admin.delete_user(owner_id)  # type: ignore
            if viewer_id:
                service_client.auth.admin.delete_user(viewer_id)  # type: ignore
            if editor_id:
                service_client.auth.admin.delete_user(editor_id)  # type: ignore


@pytest.mark.integration
@pytest.mark.asyncio
async def test_memories_strict_isolation(
    supabase_client: Client, service_client: Client
):
    """Test that memories have strict user isolation."""
    user1_email = "rls_memory_user1@example.com"
    user2_email = "rls_memory_user2@example.com"
    password = "TestPassword123!"

    memory_id = None
    user1_id = None
    user2_id = None

    try:
        # Sign up users
        auth1 = supabase_client.auth.sign_up(  # type: ignore
            {"email": user1_email, "password": password}
        )
        user1_id = auth1.user.id  # type: ignore

        auth2 = supabase_client.auth.sign_up(  # type: ignore
            {"email": user2_email, "password": password}
        )
        user2_id = auth2.user.id  # type: ignore

        # Sign in as user1
        supabase_client.auth.sign_in_with_password(  # type: ignore
            {"email": user1_email, "password": password}
        )

        # Create a memory as user1
        memory_data = {
            "memory_type": "preference",
            "content": "User1 private preference",
            "metadata": {"category": "travel"},
        }

        memory_result = supabase_client.table("memories").insert(memory_data).execute()  # type: ignore
        memory_id = memory_result.data[0]["id"]  # type: ignore

        # Verify user1 can see their memory
        user1_memories = (
            supabase_client.table("memories").select("*").eq("id", memory_id).execute()  # type: ignore
        )
        assert len(user1_memories.data) == 1  # type: ignore

        # Sign in as user2
        supabase_client.auth.sign_in_with_password(  # type: ignore
            {"email": user2_email, "password": password}
        )

        # Verify user2 cannot see user1's memory
        user2_memories = (
            supabase_client.table("memories").select("*").eq("id", memory_id).execute()  # type: ignore
        )
        assert len(user2_memories.data) == 0  # type: ignore

    finally:
        # Cleanup
        if service_client:
            if memory_id:
                service_client.table("memories").delete().eq("id", memory_id).execute()  # type: ignore
            if user1_id:
                service_client.auth.admin.delete_user(user1_id)  # type: ignore
            if user2_id:
                service_client.auth.admin.delete_user(user2_id)  # type: ignore
