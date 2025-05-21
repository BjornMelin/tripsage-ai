"""Tests for authentication endpoints.

This module provides tests for the authentication endpoints in the TripSage API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt


@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient):
    """Test registering a new user.

    Args:
        async_client: Async HTTP client
    """
    # Mock the user service
    with (
        patch(
            "tripsage.api.services.user.UserService.get_user_by_email",
            new_callable=AsyncMock,
        ) as mock_get_user,
        patch(
            "tripsage.api.services.user.UserService.create_user", new_callable=AsyncMock
        ) as mock_create_user,
    ):
        # Configure mocks
        mock_get_user.return_value = None  # User doesn't exist
        mock_create_user.return_value = {
            "id": "test-user-id",
            "email": "new@example.com",
            "full_name": "New User",
            "created_at": "2023-07-27T12:34:56.789Z",
            "updated_at": "2023-07-27T12:34:56.789Z",
        }

        # Send request
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "new@example.com",
                "password": "password123",
                "full_name": "New User",
            },
        )

        # Check response
        assert response.status_code == 201
        data = response.json()

        assert data["id"] == "test-user-id"
        assert data["email"] == "new@example.com"
        assert data["full_name"] == "New User"
        assert "created_at" in data
        assert "updated_at" in data

        # Verify mocks
        mock_get_user.assert_called_once_with("new@example.com")
        mock_create_user.assert_called_once()


@pytest.mark.asyncio
async def test_register_existing_user(async_client: AsyncClient):
    """Test registering a user that already exists.

    Args:
        async_client: Async HTTP client
    """
    # Mock the user service
    with patch(
        "tripsage.api.services.user.UserService.get_user_by_email",
        new_callable=AsyncMock,
    ) as mock_get_user:
        # Configure mocks
        mock_get_user.return_value = {  # User already exists
            "id": "existing-user-id",
            "email": "existing@example.com",
            "full_name": "Existing User",
        }

        # Send request
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "existing@example.com",
                "password": "password123",
                "full_name": "Existing User",
            },
        )

        # Check response
        assert response.status_code == 400
        data = response.json()

        assert "detail" in data
        assert "Email already registered" in data["detail"]

        # Verify mocks
        mock_get_user.assert_called_once_with("existing@example.com")


@pytest.mark.asyncio
async def test_login(async_client: AsyncClient):
    """Test user login.

    Args:
        async_client: Async HTTP client
    """
    # Mock the auth service
    with patch(
        "tripsage.api.services.auth.AuthService.authenticate_user",
        new_callable=AsyncMock,
    ) as mock_auth:
        # Configure mocks
        mock_auth.return_value = {
            "id": "test-user-id",
            "email": "test@example.com",
            "full_name": "Test User",
        }

        # Send request (OAuth2 password flow)
        response = await async_client.post(
            "/api/auth/token",
            data={
                "username": "test@example.com",
                "password": "password123",
                "grant_type": "password",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data

        # Verify mocks
        mock_auth.assert_called_once_with("test@example.com", "password123")


@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient):
    """Test login with invalid credentials.

    Args:
        async_client: Async HTTP client
    """
    # Mock the auth service
    with patch(
        "tripsage.api.services.auth.AuthService.authenticate_user",
        new_callable=AsyncMock,
    ) as mock_auth:
        # Configure mocks
        mock_auth.return_value = None  # Authentication failed

        # Send request (OAuth2 password flow)
        response = await async_client.post(
            "/api/auth/token",
            data={
                "username": "wrong@example.com",
                "password": "wrong-password",
                "grant_type": "password",
            },
        )

        # Check response
        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "Invalid credentials" in data["detail"]

        # Verify mocks
        mock_auth.assert_called_once_with("wrong@example.com", "wrong-password")


@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient):
    """Test refreshing an access token.

    Args:
        async_client: Async HTTP client
    """
    # Mock the auth service
    with patch(
        "tripsage.api.services.auth.AuthService.validate_refresh_token",
        new_callable=AsyncMock,
    ) as mock_validate:
        # Configure mocks
        mock_validate.return_value = {
            "id": "test-user-id",
            "email": "test@example.com",
            "full_name": "Test User",
        }

        # Send request
        response = await async_client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": "valid-refresh-token",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data

        # Verify mocks
        mock_validate.assert_called_once_with("valid-refresh-token")


@pytest.mark.asyncio
async def test_refresh_token_invalid(async_client: AsyncClient):
    """Test refreshing a token with an invalid refresh token.

    Args:
        async_client: Async HTTP client
    """
    # Mock the auth service
    with patch(
        "tripsage.api.services.auth.AuthService.validate_refresh_token",
        new_callable=AsyncMock,
    ) as mock_validate:
        # Configure mocks
        mock_validate.return_value = None  # Invalid refresh token

        # Send request
        response = await async_client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": "invalid-refresh-token",
            },
        )

        # Check response
        assert response.status_code == 401
        data = response.json()

        assert "detail" in data
        assert "Invalid refresh token" in data["detail"]

        # Verify mocks
        mock_validate.assert_called_once_with("invalid-refresh-token")


@pytest.mark.asyncio
async def test_logout(async_client: AsyncClient, auth_headers):
    """Test user logout.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Send request with auth headers
    response = await async_client.post(
        "/api/auth/logout",
        headers=auth_headers,
    )

    # Check response
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Logged out successfully" in data["message"]


@pytest.mark.asyncio
async def test_logout_unauthorized(async_client: AsyncClient):
    """Test logout without authentication.

    Args:
        async_client: Async HTTP client
    """
    # Send request without auth headers
    response = await async_client.post("/api/auth/logout")

    # Check response
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Not authenticated" in data["detail"]


@pytest.mark.asyncio
async def test_get_user_info(async_client: AsyncClient, auth_headers, test_user):
    """Test getting authenticated user information.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
        test_user: Test user data
    """
    # Mock the user service
    with patch(
        "tripsage.api.services.user.UserService.get_user_by_id",
        new_callable=AsyncMock,
    ) as mock_get_user:
        # Configure mocks
        mock_get_user.return_value = {
            "id": test_user["id"],
            "email": test_user["email"],
            "full_name": test_user["full_name"],
            "created_at": "2023-07-27T12:34:56.789Z",
            "updated_at": "2023-07-27T12:34:56.789Z",
        }

        # Send request with auth headers
        response = await async_client.get(
            "/api/auth/me",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == test_user["id"]
        assert data["email"] == test_user["email"]
        assert data["full_name"] == test_user["full_name"]
        assert "created_at" in data
        assert "updated_at" in data

        # Verify mocks
        mock_get_user.assert_called_once_with(test_user["id"])


@pytest.mark.asyncio
async def test_get_user_info_unauthorized(async_client: AsyncClient):
    """Test getting user info without authentication.

    Args:
        async_client: Async HTTP client
    """
    # Send request without auth headers
    response = await async_client.get("/api/auth/me")

    # Check response
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Not authenticated" in data["detail"]


@pytest.mark.asyncio
async def test_get_user_preferences(async_client: AsyncClient, auth_headers, test_user):
    """Test getting user preferences.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
        test_user: Test user data
    """
    # Mock the user service
    with patch(
        "tripsage.api.services.user.UserService.get_user_preferences",
        new_callable=AsyncMock,
    ) as mock_get_prefs:
        # Configure mocks
        mock_get_prefs.return_value = {
            "theme": "light",
            "currency": "USD",
            "language": "en",
            "notifications_enabled": True,
            "travel_preferences": {
                "preferred_airlines": ["AAL", "UAL", "DAL"],
                "preferred_accommodations": ["hotel", "apartment"],
                "preferred_seat_type": "window",
            },
        }

        # Send request with auth headers
        response = await async_client.get(
            "/api/auth/preferences",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["theme"] == "light"
        assert data["currency"] == "USD"
        assert data["language"] == "en"
        assert data["notifications_enabled"] is True
        assert "travel_preferences" in data
        assert data["travel_preferences"]["preferred_seat_type"] == "window"

        # Verify mocks
        mock_get_prefs.assert_called_once_with(test_user["id"])


@pytest.mark.asyncio
async def test_update_user_preferences(
    async_client: AsyncClient, auth_headers, test_user
):
    """Test updating user preferences.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
        test_user: Test user data
    """
    # Mock the user service
    with patch(
        "tripsage.api.services.user.UserService.update_user_preferences",
        new_callable=AsyncMock,
    ) as mock_update_prefs:
        # Configure mocks
        updated_prefs = {
            "theme": "dark",
            "currency": "EUR",
            "language": "fr",
            "notifications_enabled": False,
            "travel_preferences": {
                "preferred_airlines": ["LHR", "KLM", "AFR"],
                "preferred_accommodations": ["boutique_hotel", "resort"],
                "preferred_seat_type": "aisle",
            },
        }
        mock_update_prefs.return_value = updated_prefs

        # Preferences to update
        prefs_to_update = {
            "theme": "dark",
            "currency": "EUR",
            "language": "fr",
            "notifications_enabled": False,
        }

        # Send request with auth headers
        response = await async_client.put(
            "/api/auth/preferences",
            headers=auth_headers,
            json=prefs_to_update,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["theme"] == "dark"
        assert data["currency"] == "EUR"
        assert data["language"] == "fr"
        assert data["notifications_enabled"] is False
        assert "travel_preferences" in data

        # Verify mocks
        mock_update_prefs.assert_called_once_with(test_user["id"], prefs_to_update)


@pytest.mark.asyncio
async def test_change_password(async_client: AsyncClient, auth_headers, test_user):
    """Test changing user password.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
        test_user: Test user data
    """
    # Mock the auth and user services
    with (
        patch(
            "tripsage.api.services.auth.AuthService.verify_password",
            new_callable=MagicMock,
        ) as mock_verify,
        patch(
            "tripsage.api.services.auth.AuthService.get_password_hash",
            new_callable=MagicMock,
        ) as mock_hash,
        patch(
            "tripsage.api.services.user.UserService.update_user_password",
            new_callable=AsyncMock,
        ) as mock_update_pwd,
    ):
        # Configure mocks
        mock_verify.return_value = True  # Current password is valid
        mock_hash.return_value = "new-hashed-password"
        mock_update_pwd.return_value = True

        # Send request with auth headers
        response = await async_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "current-password",
                "new_password": "new-password",
                "confirm_password": "new-password",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Password changed successfully" in data["message"]

        # Verify mocks
        mock_verify.assert_called_once()
        mock_hash.assert_called_once_with("new-password")
        mock_update_pwd.assert_called_once_with(test_user["id"], "new-hashed-password")


@pytest.mark.asyncio
async def test_change_password_mismatch(async_client: AsyncClient, auth_headers):
    """Test changing password with mismatched new passwords.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Send request with auth headers but mismatched new passwords
    response = await async_client.post(
        "/api/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "current-password",
            "new_password": "new-password",
            "confirm_password": "different-password",  # Mismatched
        },
    )

    # Check response
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "New passwords do not match" in data["detail"]


@pytest.mark.asyncio
async def test_change_password_invalid_current(async_client: AsyncClient, auth_headers):
    """Test changing password with invalid current password.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers with valid token
    """
    # Mock the auth service
    with patch(
        "tripsage.api.services.auth.AuthService.verify_password",
        new_callable=MagicMock,
    ) as mock_verify:
        # Configure mocks
        mock_verify.return_value = False  # Current password is invalid

        # Send request with auth headers
        response = await async_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "current_password": "wrong-current-password",
                "new_password": "new-password",
                "confirm_password": "new-password",
            },
        )

        # Check response
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid current password" in data["detail"]

        # Verify mocks
        mock_verify.assert_called_once()
