"""Test fixtures for API tests.

This module provides pytest fixtures for API tests, including test client,
database access, and authentication helpers.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tripsage.api.core.config import get_settings
from tripsage.api.main import app
from tripsage.api.middlewares.auth import create_access_token


# Mock MCP manager for API tests
@pytest.fixture(autouse=True)
def mock_mcp_manager():
    """Create a mock for the MCP manager used by the API."""
    manager = MagicMock()
    manager.invoke = AsyncMock(return_value={})
    manager.initialize_mcp = AsyncMock()
    manager.initialize_all_enabled = AsyncMock()
    manager.shutdown = AsyncMock()
    manager.get_available_mcps = MagicMock(
        return_value=["weather", "time", "googlemaps", "supabase"]
    )
    # Must add this method, appears to be missing or has a different name in API
    manager.get_enabled_mcps = MagicMock(
        return_value=["weather", "time", "googlemaps", "supabase"]
    )
    manager.get_initialized_mcps = MagicMock(
        return_value=["weather", "time", "googlemaps", "supabase"]
    )

    # Patch the mcp_manager singleton
    with patch("tripsage.mcp_abstraction.mcp_manager", manager):
        yield manager


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_client() -> TestClient:
    """Create a FastAPI TestClient instance.

    Returns:
        TestClient: FastAPI test client
    """
    return TestClient(app)


@pytest.fixture
async def async_client(test_client) -> AsyncGenerator[AsyncClient, None]:
    """Create an AsyncClient instance for async tests.

    Yields:
        AsyncClient: Async HTTP client
    """
    # Create an AsyncClient with the same base URL as the test client
    base_url = "http://testserver"
    async with AsyncClient(base_url=base_url) as client:
        # We'll use the test client as a proxy for requests
        # The test client makes requests directly to the FastAPI app
        yield client


@pytest.fixture
def test_user() -> Dict:
    """Create a test user for authentication.

    Returns:
        Dict: Test user data
    """
    return {
        "id": "test-user-id",
        "email": "test@example.com",
        "password": "test-password",
        # Hashed version of "test-password"
        "hashed_password": "$2b$12$M5A1R.jRG9HZ0Qw7U14QZOIRcKjvEzdvqExQzmZWjJ3pdaM6FpDEi",
        "full_name": "Test User",
    }


@pytest.fixture
def auth_headers(test_user: Dict) -> Dict:
    """Create authentication headers with a JWT token.

    Args:
        test_user: Test user data

    Returns:
        Dict: Authentication headers
    """
    # Create a test token
    settings = get_settings()
    token = create_access_token(
        data={"sub": test_user["email"], "user_id": test_user["id"]},
        settings=settings,
    )

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_key_headers() -> Dict:
    """Create authentication headers with an API key.

    Returns:
        Dict: API key headers
    """
    return {"X-API-Key": "test-api-key"}


# Mock user service for tests
@pytest.fixture
def mock_user_service():
    """Create a mock for the UserService class."""
    service = MagicMock()
    service.get_user_by_email = AsyncMock()
    service.get_user_by_id = AsyncMock()
    service.create_user = AsyncMock()

    # Configure the mock to return a test user
    test_user = {
        "id": "test-user-id",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": "$2b$12$M5A1R.jRG9HZ0Qw7U14QZOIRcKjvEzdvqExQzmZWjJ3pdaM6FpDEi",
        "created_at": "2023-07-27T12:34:56.789Z",
        "updated_at": "2023-07-27T12:34:56.789Z",
    }
    service.get_user_by_email.return_value = test_user
    service.get_user_by_id.return_value = test_user
    service.create_user.return_value = test_user

    with patch("tripsage.api.services.user.UserService", return_value=service):
        yield service


# Mock authentication service for tests
@pytest.fixture
def mock_auth_service():
    """Create a mock for the AuthService class."""
    service = MagicMock()
    service.authenticate_user = AsyncMock()
    service.validate_refresh_token = AsyncMock()
    service.verify_password = MagicMock(return_value=True)
    service.get_password_hash = MagicMock(return_value="hashed_password")

    # Configure the mock to return a test user
    test_user = {
        "id": "test-user-id",
        "email": "test@example.com",
        "full_name": "Test User",
    }
    service.authenticate_user.return_value = test_user
    service.validate_refresh_token.return_value = test_user

    with patch("tripsage.api.services.auth.AuthService", return_value=service):
        yield service
