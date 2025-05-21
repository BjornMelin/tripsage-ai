"""Tests for API key monitoring endpoints.

This module provides tests for the API key monitoring endpoints in the TripSage API.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tripsage.api.services.key_monitoring import KeyOperation


@pytest.mark.asyncio
async def test_get_key_metrics(async_client: AsyncClient, auth_headers):
    """Test getting key health metrics.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key monitoring service
    with patch(
        "tripsage.api.services.key_monitoring.get_key_health_metrics", new_callable=AsyncMock
    ) as mock_metrics:
        # Configure mocks
        mock_metrics.return_value = {
            "total_count": 10,
            "service_count": [
                {"service": "openai", "count": 5},
                {"service": "googlemaps", "count": 3},
                {"service": "other", "count": 2},
            ],
            "expired_count": 2,
            "expiring_count": 3,
            "user_count": [
                {"user_id": "test-user-id", "count": 5},
                {"user_id": "other-user", "count": 5},
            ],
        }

        # Send request
        response = await async_client.get(
            "/api/admin/keys/metrics",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 10
        assert len(data["service_count"]) == 3
        assert data["service_count"][0]["service"] == "openai"
        assert data["service_count"][0]["count"] == 5
        assert data["expired_count"] == 2
        assert data["expiring_count"] == 3
        assert len(data["user_count"]) == 2

        # Verify mocks
        mock_metrics.assert_called_once()


@pytest.mark.asyncio
async def test_get_key_audit_logs(async_client: AsyncClient, auth_headers):
    """Test getting key audit logs.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key monitoring service
    with patch(
        "tripsage.api.services.key_monitoring.KeyMonitoringService.get_user_operations",
        new_callable=AsyncMock,
    ) as mock_audit:
        # Configure mocks
        mock_audit.return_value = [
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "operation": KeyOperation.CREATE,
                "user_id": "test-user-id",
                "key_id": "key-1",
                "service": "openai",
                "success": True,
                "metadata": {"execution_time": 123},
            },
            {
                "timestamp": "2023-01-02T00:00:00Z",
                "operation": KeyOperation.ROTATE,
                "user_id": "test-user-id",
                "key_id": "key-2",
                "service": "googlemaps",
                "success": True,
                "metadata": {"execution_time": 456},
            },
        ]

        # Send request
        response = await async_client.get(
            "/api/user/keys/audit",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["timestamp"] == "2023-01-01T00:00:00Z"
        assert data[0]["operation"] == KeyOperation.CREATE
        assert data[0]["user_id"] == "test-user-id"
        assert data[0]["key_id"] == "key-1"
        assert data[0]["service"] == "openai"
        assert data[0]["success"] is True
        assert data[1]["operation"] == KeyOperation.ROTATE

        # Verify mocks
        mock_audit.assert_called_once_with("test-user-id", 50)


@pytest.mark.asyncio
async def test_get_key_alerts(async_client: AsyncClient, auth_headers):
    """Test getting key security alerts.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key monitoring service
    with patch(
        "tripsage.api.services.key_monitoring.KeyMonitoringService.get_alerts",
        new_callable=AsyncMock,
    ) as mock_alerts:
        # Configure mocks
        mock_alerts.return_value = [
            {
                "timestamp": "2023-01-01T00:00:00Z",
                "message": "ALERT: Suspicious API key create activity detected for user test-user-id",
                "operation": KeyOperation.CREATE,
                "user_id": "test-user-id",
                "data": {"count": 10},
            },
            {
                "timestamp": "2023-01-02T00:00:00Z",
                "message": "ALERT: Suspicious API key rotate activity detected for user test-user-id",
                "operation": KeyOperation.ROTATE,
                "user_id": "test-user-id",
                "data": {"count": 5},
            },
        ]

        # Send request
        response = await async_client.get(
            "/api/admin/keys/alerts",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["timestamp"] == "2023-01-01T00:00:00Z"
        assert "Suspicious API key create activity" in data[0]["message"]
        assert data[0]["operation"] == KeyOperation.CREATE
        assert data[0]["user_id"] == "test-user-id"
        assert data[0]["data"]["count"] == 10
        assert data[1]["operation"] == KeyOperation.ROTATE

        # Verify mocks
        mock_alerts.assert_called_once_with(50)


@pytest.mark.asyncio
async def test_get_expiring_keys(async_client: AsyncClient, auth_headers):
    """Test getting expiring API keys.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key monitoring service
    with patch(
        "tripsage.api.services.key_monitoring.check_key_expiration",
        new_callable=AsyncMock,
    ) as mock_expiring:
        # Configure mocks
        mock_expiring.return_value = [
            {
                "id": "key-1",
                "user_id": "test-user-id",
                "name": "Expiring Key 1",
                "service": "openai",
                "expires_at": "2023-07-10T00:00:00Z",
            },
            {
                "id": "key-2",
                "user_id": "other-user",
                "name": "Expiring Key 2",
                "service": "googlemaps",
                "expires_at": "2023-07-15T00:00:00Z",
            },
        ]

        # Send request with 7 days parameter
        response = await async_client.get(
            "/api/admin/keys/expiring?days=7",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["id"] == "key-1"
        assert data[0]["user_id"] == "test-user-id"
        assert data[0]["name"] == "Expiring Key 1"
        assert data[0]["service"] == "openai"
        assert data[0]["expires_at"] == "2023-07-10T00:00:00Z"
        assert data[1]["id"] == "key-2"

        # Verify mocks
        mock_expiring.assert_called_once()
        # Verify days parameter was passed
        assert mock_expiring.call_args[0][1] == 7


@pytest.mark.asyncio
async def test_get_user_expiring_keys(async_client: AsyncClient, auth_headers):
    """Test getting expiring API keys for a specific user.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
    """
    # Mock the key monitoring service
    with patch(
        "tripsage.api.services.key_monitoring.check_key_expiration",
        new_callable=AsyncMock,
    ) as mock_expiring:
        # Configure mocks - full list of expiring keys
        mock_expiring.return_value = [
            {
                "id": "key-1",
                "user_id": "test-user-id",
                "name": "Expiring Key 1",
                "service": "openai",
                "expires_at": "2023-07-10T00:00:00Z",
            },
            {
                "id": "key-2",
                "user_id": "other-user",
                "name": "Expiring Key 2",
                "service": "googlemaps",
                "expires_at": "2023-07-15T00:00:00Z",
            },
        ]

        # Send request for user's expiring keys
        response = await async_client.get(
            "/api/user/keys/expiring",
            headers=auth_headers,
        )

        # Check response
        assert response.status_code == 200
        data = response.json()

        # Should only return the user's keys
        assert len(data) == 1
        assert data[0]["id"] == "key-1"
        assert data[0]["user_id"] == "test-user-id"
        assert data[0]["name"] == "Expiring Key 1"
        assert data[0]["service"] == "openai"
        assert data[0]["expires_at"] == "2023-07-10T00:00:00Z"

        # Verify mocks
        mock_expiring.assert_called_once()
        # Default value for days should be 30
        assert mock_expiring.call_args[0][1] == 30