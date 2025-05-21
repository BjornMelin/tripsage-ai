"""Tests for authentication endpoints.

This module provides tests for the authentication endpoints in the TripSage API.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


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
