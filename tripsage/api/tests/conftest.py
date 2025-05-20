"""Test fixtures for API tests.

This module provides pytest fixtures for API tests, including test client,
database access, and authentication helpers.
"""

import asyncio
from typing import AsyncGenerator, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from tripsage.api.core.config import get_settings
from tripsage.api.main import app
from tripsage.api.middlewares.auth import create_access_token


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
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an AsyncClient instance for async tests.

    Yields:
        AsyncClient: Async HTTP client
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
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
