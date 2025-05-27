"""Integration tests for the key monitoring system.

This module provides integration tests for the key monitoring system, testing
the interaction between key service, monitoring service, and API endpoints.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tripsage.api.services.key import KeyService
from tripsage.api.services.key_monitoring import (
    KeyMonitoringService,
    KeyOperation,
    check_key_expiration,
)


@pytest.fixture
def mock_redis_mcp():
    """Create a mock Redis MCP client."""
    redis_mcp = AsyncMock()
    redis_mcp.invoke_method = AsyncMock()
    return redis_mcp


@pytest.fixture
def mock_supabase_mcp():
    """Create a mock Supabase MCP client."""
    supabase_mcp = AsyncMock()
    supabase_mcp.invoke_method = AsyncMock()
    return supabase_mcp


@pytest.fixture
def setup_mocked_services(mock_redis_mcp, mock_supabase_mcp):
    """Setup mocked services for testing."""
    monitoring_service = KeyMonitoringService()
    monitoring_service.redis_mcp = mock_redis_mcp
    monitoring_service.initialized = True

    key_service = KeyService()
    key_service.supabase_mcp = mock_supabase_mcp
    key_service.monitoring_service = monitoring_service
    key_service.initialized = True

    # Patch the services to use our mocked instances
    with (
        patch(
            "tripsage.api.routers.keys.get_key_service",
            return_value=key_service,
        ),
        patch(
            "tripsage.api.services.key.mcp_manager.initialize_mcp",
            new_callable=AsyncMock,
            return_value=mock_supabase_mcp,
        ),
        patch(
            "tripsage.api.services.key_monitoring.mcp_manager.initialize_mcp",
            new_callable=AsyncMock,
            return_value=mock_redis_mcp,
        ),
        patch(
            "tripsage.api.services.key_monitoring.KeyMonitoringService",
            return_value=monitoring_service,
        ),
    ):
        yield key_service, monitoring_service


@pytest.mark.asyncio
async def test_create_key_with_monitoring(
    async_client: AsyncClient, auth_headers, setup_mocked_services
):
    """Test creating an API key with monitoring integration.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
        setup_mocked_services: Fixture that sets up mocked services
    """
    key_service, monitoring_service = setup_mocked_services
    redis_mcp = monitoring_service.redis_mcp
    supabase_mcp = key_service.supabase_mcp

    # Configure mocks
    # For key validation
    with patch(
        "tripsage.api.services.key._validate_openai_key", AsyncMock(return_value=True)
    ):
        # For pattern detection
        redis_mcp.invoke_method.return_value = {"data": []}

        # For key creation
        supabase_mcp.invoke_method.side_effect = [
            # First call: encrypt key
            {"data": "encrypted-key"},
            # Second call: insert key
            {
                "data": [
                    {
                        "id": "new-key",
                        "user_id": "test-user-id",
                        "name": "New OpenAI API Key",
                        "service": "openai",
                        "description": "New OpenAI API key",
                        "created_at": "2023-07-27T12:34:56.789Z",
                        "updated_at": "2023-07-27T12:34:56.789Z",
                        "expires_at": None,
                        "is_valid": True,
                        "last_used": None,
                    }
                ]
            },
        ]

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

        # Verify monitoring service was used
        assert redis_mcp.invoke_method.call_count >= 2
        # At least one call should be to check for suspicious patterns
        redis_mcp.invoke_method.assert_any_call(
            "list_get", params={"key": "key_ops:test-user-id:create"}
        )
        # At least one call should be to log the operation
        redis_mcp.invoke_method.assert_any_call(
            "list_push",
            params={
                "key": "key_logs:test-user-id",
                "value": {
                    "timestamp": pytest.approx(
                        datetime.now(datetime.UTC).isoformat(), abs=timedelta(seconds=5)
                    ),
                    "operation": KeyOperation.CREATE,
                    "user_id": "test-user-id",
                    "key_id": "new-key",
                    "service": "openai",
                    "success": True,
                    "metadata": {"execution_time": pytest.approx(0, abs=1000)},
                },
                "ttl": 2592000,
            },
        )


@pytest.mark.asyncio
async def test_suspicious_key_creation(
    async_client: AsyncClient, auth_headers, setup_mocked_services
):
    """Test handling suspicious key creation.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
        setup_mocked_services: Fixture that sets up mocked services
    """
    key_service, monitoring_service = setup_mocked_services
    redis_mcp = monitoring_service.redis_mcp
    supabase_mcp = key_service.supabase_mcp

    # Configure mocks
    # For key validation
    with patch(
        "tripsage.api.services.key._validate_openai_key", AsyncMock(return_value=True)
    ):
        # For pattern detection - return many operations to trigger suspicious pattern
        redis_mcp.invoke_method.side_effect = [
            # First call: check pattern
            {"data": ["2023-01-01T00:00:00Z"] * 10},
            # Second call: log pattern
            {"data": "OK"},
            # Third call: log alert
            {"data": "OK"},
            # Fourth call: log operation
            {"data": "OK"},
        ]

        # For key creation
        supabase_mcp.invoke_method.side_effect = [
            # First call: encrypt key
            {"data": "encrypted-key"},
            # Second call: insert key
            {
                "data": [
                    {
                        "id": "suspicious-key",
                        "user_id": "test-user-id",
                        "name": "Suspicious Key",
                        "service": "openai",
                        "description": "Suspicious key",
                        "created_at": "2023-07-27T12:34:56.789Z",
                        "updated_at": "2023-07-27T12:34:56.789Z",
                        "expires_at": None,
                        "is_valid": True,
                        "last_used": None,
                    }
                ]
            },
        ]

        # Send request
        response = await async_client.post(
            "/api/user/keys",
            headers=auth_headers,
            json={
                "name": "Suspicious Key",
                "service": "openai",
                "key": "sk-1234567890",
                "description": "Suspicious key",
            },
        )

        # Check response - should still succeed but log an alert
        assert response.status_code == 201
        data = response.json()

        assert data["id"] == "suspicious-key"
        assert data["name"] == "Suspicious Key"
        assert data["service"] == "openai"

        # Verify monitoring service was used
        assert redis_mcp.invoke_method.call_count >= 3
        # First call: check for suspicious patterns
        redis_mcp.invoke_method.assert_any_call(
            "list_get", params={"key": "key_ops:test-user-id:create"}
        )
        # Call to log an alert should be made
        redis_mcp.invoke_method.assert_any_call(
            "list_push",
            params={
                "key": "key_alerts",
                "value": {
                    "timestamp": pytest.approx(
                        datetime.now(datetime.UTC).isoformat(), abs=timedelta(seconds=5)
                    ),
                    "message": (
                        "ALERT: Suspicious API key create activity detected for user "
                        "test-user-id"
                    ),
                    "operation": KeyOperation.CREATE,
                    "user_id": "test-user-id",
                    "data": {"count": 10},
                },
                "ttl": 2592000,
            },
        )


@pytest.mark.asyncio
async def test_rate_limited_key_operation(
    async_client: AsyncClient, auth_headers, setup_mocked_services
):
    """Test handling rate limited key operations.

    Args:
        async_client: Async HTTP client
        auth_headers: Authentication headers
        setup_mocked_services: Fixture that sets up mocked services
    """
    key_service, monitoring_service = setup_mocked_services
    redis_mcp = monitoring_service.redis_mcp

    # Configure mocks - make rate limiting return True
    redis_mcp.invoke_method.return_value = {"limited": True}

    # Send request
    response = await async_client.post(
        "/api/user/keys",
        headers=auth_headers,
        json={
            "name": "Rate Limited Key",
            "service": "openai",
            "key": "sk-1234567890",
            "description": "Rate limited key",
        },
    )

    # Check response - should fail with 429 Too Many Requests
    assert response.status_code == 429
    data = response.json()

    assert "detail" in data
    assert "Rate limit exceeded" in data["detail"]

    # Verify rate limit check was called
    redis_mcp.invoke_method.assert_called_once_with(
        "rate_limit",
        params={
            "key": "rate_limit:key_ops:test-user-id:create",
            "limit": 10,
            "window": 60,
        },
    )


@pytest.mark.asyncio
async def test_expiring_keys_integration(setup_mocked_services):
    """Test integration between check_key_expiration and services.

    Args:
        setup_mocked_services: Fixture that sets up mocked services
    """
    key_service, monitoring_service = setup_mocked_services
    supabase_mcp = key_service.supabase_mcp

    # Configure mocks
    supabase_mcp.invoke_method.return_value = {
        "data": [
            {
                "id": "expiring-key-1",
                "user_id": "test-user-id",
                "name": "Expiring Key 1",
                "service": "openai",
                "expires_at": (
                    datetime.now(datetime.UTC) + timedelta(days=5)
                ).isoformat(),
            },
            {
                "id": "expiring-key-2",
                "user_id": "other-user",
                "name": "Expiring Key 2",
                "service": "googlemaps",
                "expires_at": (
                    datetime.now(datetime.UTC) + timedelta(days=3)
                ).isoformat(),
            },
        ]
    }

    # Call check_key_expiration
    results = await check_key_expiration(monitoring_service, 7)

    # Verify results
    assert len(results) == 2
    assert results[0]["id"] == "expiring-key-1"
    assert results[0]["user_id"] == "test-user-id"
    assert results[0]["name"] == "Expiring Key 1"
    assert results[1]["id"] == "expiring-key-2"

    # Verify Supabase call
    supabase_mcp.invoke_method.assert_called_once()
    # Verify the query includes expiration date criteria
    call_args = supabase_mcp.invoke_method.call_args[1]
    assert call_args["method"] == "from"
    assert call_args["params"]["table"] == "api_keys"
    assert "expires_at" in call_args["params"]["query"]
