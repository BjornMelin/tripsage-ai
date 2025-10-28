"""Unit tests for keys router endpoints with DI overrides and stubs."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keys_metrics_admin(
    app: FastAPI,
    async_client_factory: Callable[[FastAPI], AsyncClient],
    monkeypatch: pytest.MonkeyPatch,
):
    """`GET /api/keys/metrics` returns aggregated payload for admins."""
    # Override admin principal dependency with an admin-capable principal
    from typing import ClassVar

    from tripsage.api.core import dependencies as dep

    class _Admin:
        """Admin principal stub."""

        id = "admin-user-1"
        type = "user"
        auth_method = "jwt"
        scopes: ClassVar[list[str]] = ["admin"]
        metadata: ClassVar[dict[str, list[str]]] = {"roles": ["admin"]}

    def _provide_admin() -> Any:
        """Provide admin principal for DI."""
        return _Admin()

    app.dependency_overrides[dep.require_admin_principal] = _provide_admin  # type: ignore[assignment]

    # Monkeypatch the metrics producer to return a minimal fake payload
    class _UserCount:
        """User count class."""

        def __init__(self, user_id: str, count: int) -> None:
            """Initialize user count."""
            self.user_id = user_id
            self.count = count

    class _Metrics:
        """Metrics class."""

        def __init__(self) -> None:
            """Initialize metrics."""
            self.error: str | None = None
            self.total_count = 2
            self.expired_count = 0
            self.expiring_count = 0
            self.service_count: list[Any] = []
            self.user_count = [_UserCount("u1", 1), _UserCount("u2", 1)]

        def model_dump(self, *args: object, **kwargs: object) -> dict[str, Any]:
            """Return serializable dict (excluding user_count by the router)."""
            return {
                "total_count": self.total_count,
                "expired_count": self.expired_count,
                "expiring_count": self.expiring_count,
                "service_count": self.service_count,
            }

    async def _fake_get_key_health_metrics():  # pragma: no cover - trivial
        """Return fake metrics."""
        return _Metrics()

    monkeypatch.setattr(
        "tripsage.api.routers.keys.get_key_health_metrics",
        _fake_get_key_health_metrics,
        raising=True,
    )

    client = async_client_factory(app)
    resp = await client.get("/api/keys/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 2
    assert data["user_distribution"]["total_keys"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_keys_audit_log_admin(
    app: FastAPI, async_client_factory: Callable[[FastAPI], AsyncClient]
):
    """`GET /api/keys/audit` returns sanitized audit log entries."""
    # Admin principal override
    from typing import ClassVar

    from tripsage.api.core import dependencies as dep
    from tripsage_core.services.infrastructure.key_monitoring_service import (
        KeyOperation,
    )

    class _Admin:
        """Admin class."""

        id = "admin-user-1"
        type = "user"
        auth_method = "jwt"
        scopes: ClassVar[list[str]] = ["admin"]
        metadata: ClassVar[dict[str, list[str]]] = {"roles": ["admin"]}

    def _provide_admin2() -> Any:
        """Provide admin principal for DI (audit)."""
        return _Admin()

    app.dependency_overrides[dep.require_admin_principal] = _provide_admin2  # type: ignore[assignment]

    # KeyMonitoringService stub
    class _Monitor:
        """Monitor class."""

        async def get_user_operations(self, user_id: str, limit: int):
            """Return minimal entries."""

            class Entry:
                """Entry class."""

                def __init__(self) -> None:
                    """Initialize entry."""
                    self.timestamp = datetime.now(UTC)
                    self.operation = KeyOperation.CREATE
                    self.user_id = user_id
                    self.key_id = "abcd1234efgh5678"
                    self.service = "openai"
                    self.success = True
                    self.metadata: dict[str, Any] = {}

            return [Entry()]

    def _provide_monitor() -> Any:
        """Provide key monitoring service stub."""
        return _Monitor()

    app.dependency_overrides[dep.get_key_monitoring_service] = _provide_monitor  # type: ignore[assignment]

    client = async_client_factory(app)
    resp = await client.get("/api/keys/audit")
    assert resp.status_code == 200
    rows: list[dict[str, Any]] = resp.json()
    assert isinstance(rows, list) and rows
    r0: dict[str, Any] = rows[0]
    assert r0["operation"] == "create"
    assert r0["service"] == "openai"
    # masked key id present
    assert "key_id" in r0
    assert r0["key_id"].startswith("abcd") and r0["key_id"].endswith("5678")
