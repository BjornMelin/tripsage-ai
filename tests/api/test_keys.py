"""Tests for API key management endpoints.

This module provides tests for the API key management endpoints in the TripSage API.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_keys(async_client: AsyncClient, auth_headers):
    """Test listing API keys.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key service
    with patch(
        "tripsage.api.services.key.KeyService.list_keys", new_callable=AsyncMock
    ) as mock_list:
        # Configure mocks
        mock_list.return_value = [
            {
                "id": "key-1",
                "name": "OpenAI API Key",
                "service": "openai",
                "description": "OpenAI API key for GPT-4",
                "created_at": "2023-07-27T12:34:56.789Z",
                "updated_at": "2023-07-27T12:34:56.789Z",
                "expires_at": "2024-07-27T12:34:56.789Z",
                "is_valid": True,
                "last_used": "2023-07-27T12:34:56.789Z",
            },
            {
                "id": "key-2",
                "name": "Google Maps API Key",
                "service": "googlemaps",
                "description": "Google Maps API key",
                "created_at": "2023-07-27T12:34:56.789Z",
                "updated_at": "2023-07-27T12:34:56.789Z",
                "expires_at": None,
                "is_valid": True,
                "last_used": None,
            },
        ]

        # Send request
        response = await async_client.get(
            "/api/user/keys",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["id"] == "key-1"
        assert data[0]["name"] == "OpenAI API Key"
        assert data[0]["service"] == "openai"
        assert data[1]["id"] == "key-2"
        assert data[1]["name"] == "Google Maps API Key"
        assert data[1]["service"] == "googlemaps"

        # Verify mocks
        mock_list.assert_called_once_with("test-user-id")


@pytest.mark.asyncio
async def test_create_key(async_client: AsyncClient, auth_headers):
    """Test creating an API key.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key service
    with (
        patch(
            "tripsage.api.services.key.KeyService.validate_key", new_callable=AsyncMock
        ) as mock_validate,
        patch(
            "tripsage.api.services.key.KeyService.create_key", new_callable=AsyncMock
        ) as mock_create,
    ):
        # Configure mocks
        mock_validate.return_value = {
            "is_valid": True,
            "service": "openai",
            "message": "API key is valid",
        }

        mock_create.return_value = {
            "id": "new-key",
            "name": "New OpenAI API Key",
            "service": "openai",
            "description": "New OpenAI API key",
            "created_at": "2023-07-27T12:34:56.789Z",
            "updated_at": "2023-07-27T12:34:56.789Z",
            "expires_at": None,
            "is_valid": True,
            "last_used": None,
        }

        # Send request
        response = await async_client.post(
            "/api/user/keys",
            headers=auth_headers,
            json={
                "name": "New OpenAI API Key",
                "service": "openai",
                "key": "sk-1234567890",
                "description": "New OpenAI API key",
            },
        )

        # Check response
        assert response.status_code == 201
        data = response.json()

        assert data["id"] == "new-key"
        assert data["name"] == "New OpenAI API Key"
        assert data["service"] == "openai"
        assert data["description"] == "New OpenAI API key"

        # Verify mocks
        mock_validate.assert_called_once_with("sk-1234567890", "openai")
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_create_key_invalid(async_client: AsyncClient, auth_headers):
    """Test creating an API key with an invalid key.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key service
    with patch(
        "tripsage.api.services.key.KeyService.validate_key", new_callable=AsyncMock
    ) as mock_validate:
        # Configure mocks
        mock_validate.return_value = {
            "is_valid": False,
            "service": "openai",
            "message": "Invalid API key",
        }

        # Send request
        response = await async_client.post(
            "/api/user/keys",
            headers=auth_headers,
            json={
                "name": "Invalid OpenAI API Key",
                "service": "openai",
                "key": "invalid-key",
                "description": "Invalid OpenAI API key",
            },
        )

        # Check response
        assert response.status_code == 400
        data = response.json()

        assert "detail" in data
        assert "Invalid API key" in data["detail"]

        # Verify mocks
        mock_validate.assert_called_once_with("invalid-key", "openai")


@pytest.mark.asyncio
async def test_delete_key(async_client: AsyncClient, auth_headers):
    """Test deleting an API key.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key service
    with (
        patch(
            "tripsage.api.services.key.KeyService.get_key", new_callable=AsyncMock
        ) as mock_get,
        patch(
            "tripsage.api.services.key.KeyService.delete_key", new_callable=AsyncMock
        ) as mock_delete,
    ):
        # Configure mocks
        mock_get.return_value = {
            "id": "key-to-delete",
            "user_id": "test-user-id",
            "name": "Key to Delete",
            "service": "openai",
        }

        mock_delete.return_value = True

        # Send request
        response = await async_client.delete(
            "/api/user/keys/key-to-delete",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 204

        # Verify mocks
        mock_get.assert_called_once_with("key-to-delete")
        mock_delete.assert_called_once_with("key-to-delete")


@pytest.mark.asyncio
async def test_delete_key_not_found(async_client: AsyncClient, auth_headers):
    """Test deleting a non-existent API key.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key service
    with patch(
        "tripsage.api.services.key.KeyService.get_key", new_callable=AsyncMock
    ) as mock_get:
        # Configure mocks
        mock_get.return_value = None  # Key not found

        # Send request
        response = await async_client.delete(
            "/api/user/keys/nonexistent-key",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 404
        data = response.json()

        assert "detail" in data
        assert "API key not found" in data["detail"]

        # Verify mocks
        mock_get.assert_called_once_with("nonexistent-key")


@pytest.mark.asyncio
async def test_validate_key(async_client: AsyncClient):
    """Test validating an API key.

    Args:
        async_client: Async HTTP client
    """
    # Mock the key service
    with patch(
        "tripsage.api.services.key.KeyService.validate_key", new_callable=AsyncMock
    ) as mock_validate:
        # Configure mocks
        mock_validate.return_value = {
            "is_valid": True,
            "service": "openai",
            "message": "API key is valid",
        }

        # Send request
        response = await async_client.post(
            "/api/user/keys/validate",
            json={
                "key": "sk-1234567890",
                "service": "openai",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["is_valid"] is True
        assert data["service"] == "openai"
        assert data["message"] == "API key is valid"

        # Verify mocks
        mock_validate.assert_called_once_with("sk-1234567890", "openai")


@pytest.mark.asyncio
async def test_rotate_key(async_client: AsyncClient, auth_headers):
    """Test rotating an API key.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key service
    with (
        patch(
            "tripsage.api.services.key.KeyService.get_key", new_callable=AsyncMock
        ) as mock_get,
        patch(
            "tripsage.api.services.key.KeyService.validate_key", new_callable=AsyncMock
        ) as mock_validate,
        patch(
            "tripsage.api.services.key.KeyService.rotate_key", new_callable=AsyncMock
        ) as mock_rotate,
    ):
        # Configure mocks
        mock_get.return_value = {
            "id": "key-to-rotate",
            "user_id": "test-user-id",
            "name": "Key to Rotate",
            "service": "openai",
        }

        mock_validate.return_value = {
            "is_valid": True,
            "service": "openai",
            "message": "API key is valid",
        }

        mock_rotate.return_value = {
            "id": "key-to-rotate",
            "name": "Key to Rotate",
            "service": "openai",
            "description": "Rotated OpenAI API key",
            "created_at": "2023-07-27T12:34:56.789Z",
            "updated_at": "2023-07-28T12:34:56.789Z",
            "expires_at": None,
            "is_valid": True,
            "last_used": None,
        }

        # Send request
        response = await async_client.post(
            "/api/user/keys/key-to-rotate/rotate",
            headers=auth_headers,
            json={
                "new_key": "sk-new-key-12345",
            },
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "key-to-rotate"
        assert data["name"] == "Key to Rotate"
        assert data["service"] == "openai"

        # Verify mocks
        mock_get.assert_called_once_with("key-to-rotate")
        mock_validate.assert_called_once_with("sk-new-key-12345", "openai")
        mock_rotate.assert_called_once_with("key-to-rotate", "sk-new-key-12345")
