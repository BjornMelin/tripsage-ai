"""Integration tests for API key administration endpoints."""

from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient

from tripsage.api.core.dependencies import require_admin_principal
from tripsage.api.middlewares.authentication import Principal


def _admin_principal() -> Principal:
    """Return an admin principal."""
    return Principal(
        id="admin-001",
        type="user",
        email="admin@example.com",
        service=None,
        auth_method="jwt",
        scopes=["admin"],
        metadata={"role": "admin", "roles": ["admin"]},
    )


@pytest.mark.asyncio
async def test_metrics_requires_admin(async_client: AsyncClient, app: FastAPI) -> None:
    """Non-admin callers should receive 403 responses for key metrics."""

    async def _deny_access() -> Principal:
        """Deny access."""
        raise HTTPException(status_code=403, detail="Admin privileges required")

    app.dependency_overrides[require_admin_principal] = _deny_access
    try:
        response = await async_client.get("/api/keys/metrics")
    finally:
        app.dependency_overrides.pop(require_admin_principal, None)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_metrics_sanitizes_user_counts(
    async_client: AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User identifiers should be aggregated and not leaked in metrics payloads."""
    admin = _admin_principal()

    async def _grant_access() -> Principal:
        """Grant access."""
        return admin

    async def _mock_metrics() -> dict[str, Any]:
        """Mock metrics."""
        return {
            "total_count": 4,
            "service_count": [{"service": "openai", "count": 3}],
            "expired_count": 1,
            "expiring_count": 1,
            "user_count": [
                {"user_id": "user-a", "count": 2},
                {"user_id": "user-b", "count": 2},
            ],
        }

    monkeypatch.setattr(
        "tripsage.api.routers.keys.get_key_health_metrics", _mock_metrics, raising=True
    )

    app.dependency_overrides[require_admin_principal] = _grant_access
    try:
        response = await async_client.get("/api/keys/metrics")
    finally:
        app.dependency_overrides.pop(require_admin_principal, None)

    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert "user_count" not in payload
    assert payload["user_distribution"] == {
        "unique_users": 2,
        "total_keys": 4,
        "avg_keys_per_user": 2.0,
    }


@pytest.mark.asyncio
async def test_audit_log_masks_key_ids(
    async_client: AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Audit log responses should mask sensitive key identifiers."""
    admin = _admin_principal()

    async def _grant_access() -> Principal:
        """Grant access."""
        return admin

    async def _mock_operations(
        self: Any, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Mock user operations."""
        return [
            {
                "timestamp": "2025-10-28T12:00:00Z",
                "operation": "create",
                "user_id": user_id,
                "key_id": "key-1234567890",
                "service": "openai",
                "success": True,
                "metadata": {"execution_time": 0.2},
            }
        ]

    monkeypatch.setattr(
        "tripsage_core.services.infrastructure.key_monitoring_service.KeyMonitoringService.get_user_operations",
        _mock_operations,
        raising=True,
    )

    app.dependency_overrides[require_admin_principal] = _grant_access
    try:
        response = await async_client.get("/api/keys/audit")
    finally:
        app.dependency_overrides.pop(require_admin_principal, None)

    assert response.status_code == 200
    payload = cast(list[dict[str, Any]], response.json())
    assert payload
    record = payload[0]
    assert record["key_id"].startswith("key-")
    assert record["key_id"].endswith("7890")
    assert "***" in record["key_id"]


@pytest.mark.asyncio
async def test_audit_log_handles_empty_response(
    async_client: AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty audit responses should be returned verbatim."""
    admin = _admin_principal()

    async def _grant_access() -> Principal:
        """Grant access."""
        return admin

    async def _mock_operations(
        self: Any, user_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Mock user operations."""
        return []

    monkeypatch.setattr(
        "tripsage_core.services.infrastructure.key_monitoring_service.KeyMonitoringService.get_user_operations",
        _mock_operations,
        raising=True,
    )

    app.dependency_overrides[require_admin_principal] = _grant_access
    try:
        response = await async_client.get("/api/keys/audit")
    finally:
        app.dependency_overrides.pop(require_admin_principal, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload == []


@pytest.mark.asyncio
async def test_metrics_handles_unexpected_user_count_shape(
    async_client: AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Metrics endpoint should tolerate malformed user_count payloads."""
    admin = _admin_principal()

    async def _grant_access() -> Principal:
        """Grant access."""
        return admin

    async def _mock_metrics() -> dict[str, Any]:
        """Mock metrics."""
        return {
            "total_count": 2,
            "user_count": "unexpected",
        }

    monkeypatch.setattr(
        "tripsage.api.routers.keys.get_key_health_metrics", _mock_metrics, raising=True
    )

    app.dependency_overrides[require_admin_principal] = _grant_access
    try:
        response = await async_client.get("/api/keys/metrics")
    finally:
        app.dependency_overrides.pop(require_admin_principal, None)

    assert response.status_code == 200
    payload: dict[str, Any] = response.json()
    assert payload["user_distribution"] == {
        "unique_users": 0,
        "total_keys": 0,
        "avg_keys_per_user": 0.0,
    }
