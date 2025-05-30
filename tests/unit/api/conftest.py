"""
Pytest configuration for API unit tests.

This module provides fixtures for testing FastAPI endpoints.
"""

from datetime import datetime

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.fixture
def mock_app():
    """Create a simple FastAPI app for testing."""
    app = FastAPI()

    @app.get("/api/health")
    def health_check():
        return {
            "status": "ok",
            "application": "TripSage API",
            "version": "1.0.0",
            "environment": "test",
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/api/health/async")
    async def health_check_async():
        return {
            "status": "ok",
            "application": "TripSage API",
            "version": "1.0.0",
            "environment": "test",
            "async": True,
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/api/health/mcp")
    def mcp_health_check():
        return {
            "status": "ok",
            "mcp_status": "connected",
            "available_mcps": ["weather", "flights", "memory"],
            "enabled_mcps": ["weather", "flights"],
            "timestamp": datetime.now().isoformat(),
        }

    return app


@pytest.fixture
def test_client(mock_app):
    """Create a test client for synchronous API testing."""
    with TestClient(mock_app) as client:
        yield client


@pytest.fixture
async def async_client(mock_app):
    """Create an async client for asynchronous API testing."""
    # Use transport parameter for newer httpx versions
    transport = httpx.ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_token():
    """Generate a mock JWT token for testing."""
    return "mock-jwt-token-12345"


@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers with Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def test_user():
    """Test user data."""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "created_at": datetime.now().isoformat(),
        "is_active": True,
    }


@pytest.fixture
def sample_trip_request():
    """Sample trip creation request data."""
    return {
        "title": "Paris Vacation",
        "destination": "Paris, France",
        "start_date": "2024-06-01",
        "end_date": "2024-06-07",
        "travelers": 2,
        "budget": 2500.00,
        "preferences": {"accommodation_type": "hotel", "travel_style": "leisure"},
    }


@pytest.fixture
def sample_api_key_request():
    """Sample API key creation request data."""
    return {
        "service": "openai",
        "api_key": "sk-test-api-key-12345",
        "description": "Test API key for development",
    }


def assert_success_response(response, expected_status=200):
    """Helper to assert successful API responses."""
    assert response.status_code == expected_status
    assert response.headers["content-type"] == "application/json"


def assert_error_response(response, expected_status=400):
    """Helper to assert error API responses."""
    assert response.status_code == expected_status
    data = response.json()
    assert "error" in data or "detail" in data


def assert_auth_required(response):
    """Helper to assert authentication is required."""
    assert response.status_code == 401
    data = response.json()
    assert (
        "unauthorized" in data.get("detail", "").lower()
        or "authentication" in data.get("detail", "").lower()
    )
