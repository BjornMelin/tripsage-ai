"""Tests for health check endpoints.

This module provides tests for the health check endpoints in the TripSage API.
"""

from fastapi.testclient import TestClient

# Import the mock_mcp_manager fixture from conftest.py


def test_health_check(test_client: TestClient):
    """Test the basic health check endpoint.

    Args:
        test_client: FastAPI test client
    """
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "application" in data
    assert "version" in data
    assert "environment" in data


def test_health_check_async(test_client: TestClient):
    """Test the basic health check endpoint with a different name.

    Args:
        test_client: FastAPI test client
    """
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "application" in data
    assert "version" in data
    assert "environment" in data


def test_mcp_health_check(test_client: TestClient):
    """Test the MCP health check endpoint.

    Args:
        test_client: FastAPI test client
    """
    response = test_client.get("/api/health/mcp")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "available_mcps" in data
    assert "enabled_mcps" in data
    assert isinstance(data["available_mcps"], list)
    assert isinstance(data["enabled_mcps"], list)
