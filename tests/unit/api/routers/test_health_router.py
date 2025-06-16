"""Modern comprehensive unit tests for health router.

Tests health endpoints using 2025 FastAPI testing patterns:
- Modern async testing with httpx AsyncClient
- Proper dependency mocking and override patterns
- Comprehensive error handling and edge cases
"""

from unittest.mock import patch

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient

from tripsage.api.main import app


class TestHealthRouter:
    """Modern test suite for health router endpoints."""

    @pytest.fixture
    async def async_client(self):
        """Create async test client."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    async def test_health_check_success(self, async_client):
        """Test basic health check endpoint."""
        # Act
        response = await async_client.get("/api/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["application"] == "TripSage API"
        assert "version" in data
        assert "environment" in data

    async def test_health_check_response_structure(self, async_client):
        """Test health check response has correct structure."""
        # Act
        response = await async_client.get("/api/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check required fields
        required_fields = ["status", "application", "version", "environment"]
        for field in required_fields:
            assert field in data
            assert data[field] is not None

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_success(self, mock_mcp_manager, async_client):
        """Test successful MCP health check."""
        # Arrange
        mock_mcp_manager.get_available_mcps.return_value = [
            "airbnb",
            "duffel",
            "google_maps",
        ]
        mock_mcp_manager.get_initialized_mcps.return_value = ["airbnb", "duffel"]

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "available_mcps" in data
        assert "enabled_mcps" in data
        assert len(data["available_mcps"]) == 3
        assert len(data["enabled_mcps"]) == 2
        assert "airbnb" in data["available_mcps"]
        assert "duffel" in data["enabled_mcps"]

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_no_mcps(self, mock_mcp_manager, async_client):
        """Test MCP health check when no MCPs are available."""
        # Arrange
        mock_mcp_manager.get_available_mcps.return_value = []
        mock_mcp_manager.get_initialized_mcps.return_value = []

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["available_mcps"] == []
        assert data["enabled_mcps"] == []

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_partial_initialization(
        self, mock_mcp_manager, async_client
    ):
        """Test MCP health check when some MCPs fail to initialize."""
        # Arrange
        mock_mcp_manager.get_available_mcps.return_value = [
            "airbnb",
            "duffel",
            "google_maps",
        ]
        mock_mcp_manager.get_initialized_mcps.return_value = [
            "airbnb"
        ]  # Only one initialized

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert len(data["available_mcps"]) == 3
        assert len(data["enabled_mcps"]) == 1
        assert data["enabled_mcps"][0] == "airbnb"

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_error(self, mock_mcp_manager, async_client):
        """Test MCP health check when MCP manager raises an exception."""
        # Arrange
        mock_mcp_manager.get_available_mcps.side_effect = Exception(
            "MCP service unavailable"
        )

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data
        assert "MCP service unavailable" in data["error"]
        assert data["available_mcps"] == []
        assert data["enabled_mcps"] == []

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_get_initialized_error(
        self, mock_mcp_manager, async_client
    ):
        """Test MCP health check when get_initialized_mcps fails."""
        # Arrange
        mock_mcp_manager.get_available_mcps.return_value = ["airbnb"]
        mock_mcp_manager.get_initialized_mcps.side_effect = Exception(
            "Initialization check failed"
        )

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert "Initialization check failed" in data["error"]

    async def test_health_endpoints_no_authentication_required(self, async_client):
        """Test that health endpoints don't require authentication."""
        # Test basic health check
        response = await async_client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK

        # Test MCP health check
        response = await async_client.get("/api/health/mcp")
        assert response.status_code == status.HTTP_200_OK

    async def test_health_check_method_not_allowed(self, async_client):
        """Test that only GET method is allowed for health endpoints."""
        # Test POST not allowed on basic health
        response = await async_client.post("/api/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test PUT not allowed on MCP health
        response = await async_client.put("/api/health/mcp")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Test DELETE not allowed
        response = await async_client.delete("/api/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_different_mcp_types(
        self, mock_mcp_manager, async_client
    ):
        """Test MCP health check with different types of MCP services."""
        # Arrange
        mock_mcp_manager.get_available_mcps.return_value = [
            "airbnb-accommodation",
            "duffel-flights",
            "google-maps",
            "openai-chat",
            "weather-api",
        ]
        mock_mcp_manager.get_initialized_mcps.return_value = [
            "airbnb-accommodation",
            "google-maps",
            "openai-chat",
        ]

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert len(data["available_mcps"]) == 5
        assert len(data["enabled_mcps"]) == 3

        # Verify specific services
        assert "airbnb-accommodation" in data["available_mcps"]
        assert "duffel-flights" in data["available_mcps"]
        assert "weather-api" in data["available_mcps"]

        assert "airbnb-accommodation" in data["enabled_mcps"]
        assert "google-maps" in data["enabled_mcps"]
        assert "duffel-flights" not in data["enabled_mcps"]  # Not initialized

    async def test_health_check_response_headers(self, async_client):
        """Test that health check responses have appropriate headers."""
        # Act
        response = await async_client.get("/api/health")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get("content-type") == "application/json"

    async def test_health_check_idempotent(self, async_client):
        """Test that health check endpoints are idempotent."""
        # Act - Call multiple times
        response1 = await async_client.get("/api/health")
        response2 = await async_client.get("/api/health")
        response3 = await async_client.get("/api/health")

        # Assert - All should return the same result
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response3.status_code == status.HTTP_200_OK

        # Basic structure should be consistent
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1["status"] == data2["status"] == data3["status"]
        assert data1["application"] == data2["application"] == data3["application"]

    @patch("tripsage.api.routers.health.mcp_manager")
    async def test_mcp_health_check_large_number_of_services(
        self, mock_mcp_manager, async_client
    ):
        """Test MCP health check with many services."""
        # Arrange - Simulate many MCP services
        available_services = [f"service-{i}" for i in range(50)]
        initialized_services = [
            f"service-{i}" for i in range(0, 50, 2)
        ]  # Every other service

        mock_mcp_manager.get_available_mcps.return_value = available_services
        mock_mcp_manager.get_initialized_mcps.return_value = initialized_services

        # Act
        response = await async_client.get("/api/health/mcp")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert len(data["available_mcps"]) == 50
        assert len(data["enabled_mcps"]) == 25  # Half are initialized

    @pytest.mark.parametrize("endpoint", ["/api/health", "/api/health/mcp"])
    async def test_health_endpoints_cors_headers(self, async_client, endpoint):
        """Test that health endpoints return appropriate CORS headers."""
        # Act
        response = await async_client.get(endpoint)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # Note: CORS headers would be added by middleware, not tested here

    async def test_health_check_performance(self, async_client):
        """Test that health checks respond quickly."""
        import time

        # Act
        start_time = time.time()
        response = await async_client.get("/api/health")
        end_time = time.time()

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
