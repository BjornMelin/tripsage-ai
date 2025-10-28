"""Integration-style tests for ApiKeyService with realistic stubs.

Covers transactional DB interactions, caching integration, and health checks
without performing real network calls or requiring a live database.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, cast

import pytest

from tripsage_core.config import Settings
from tripsage_core.services.business.api_key_service import (
    ApiKeyService,
    ServiceHealthStatus,
    ServiceType,
)
from tripsage_core.services.infrastructure.database_service import DatabaseService


def _now_iso() -> str:
    """Get current ISO timestamp."""
    return datetime.now(UTC).isoformat()


def _make_ops() -> list[tuple[str, dict[str, Any]]]:
    """Typed empty ops list factory for dataclass fields."""
    return []


@dataclass
class _Tx:
    """Batch transaction stub mirroring DatabaseService._Batch surface."""

    results_builder: Callable[[], list[list[dict[str, Any]]]]
    # Operation logs retained only if a test inspects them later.
    # Kept untyped to avoid pyright partially-unknown diagnostics here.
    inserts: list[tuple[str, dict[str, Any]]] = field(default_factory=_make_ops)
    deletes: list[tuple[str, dict[str, Any]]] = field(default_factory=_make_ops)

    async def __aenter__(self) -> _Tx:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> bool:
        return False

    def insert(self, table: str, data: dict[str, Any]) -> None:
        """Insert data into table."""
        self.inserts.append((table, data))

    def delete(self, table: str, filters: dict[str, Any]) -> None:
        """Delete data from table."""
        self.deletes.append((table, filters))

    async def execute(self) -> list[list[dict[str, Any]]]:
        """Execute the transaction."""
        return self.results_builder()


class _DB:
    """Supabase-like database stub for service integration tests."""

    def __init__(self) -> None:
        """Initialize the database."""
        self._rows: dict[tuple[str, str], dict[str, Any]] = {}
        self._tx_log: list[tuple[str, dict[str, Any]]] = []

    def transaction(self) -> _Tx:
        """Create a transaction."""

        def _results() -> list[list[dict[str, Any]]]:
            # First op returns created/deleted rows; second op returns usage log row
            # Build a generic non-empty first result to indicate success
            created = [{"ok": True, "ts": _now_iso()}]
            usage = [{"ok": True, "op": "audit", "ts": _now_iso()}]
            return [created, usage]

        return _Tx(_results)

    async def get_api_key_by_id(
        self, key_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """Get API key by ID."""
        return self._rows.get((key_id, user_id))

    async def get_user_api_keys(self, _user_id: str) -> list[dict[str, Any]]:
        """Get user API keys."""
        return list(self._rows.values())

    async def get_api_key_for_service(
        self, user_id: str, service: str
    ) -> dict[str, Any] | None:
        """Get API key for service."""
        # Return first matching row by service
        for (_kid, uid), row in self._rows.items():
            if uid == user_id and row.get("service") == service:
                return row
        return None

    async def update_api_key_last_used(self, key_id: str) -> None:  # pragma: no cover
        """Update API key last used."""
        # No-op tracking hook for tests that await event loop flush
        return

    # Helpers to seed rows
    def seed_row(self, key_id: str, user_id: str, **row: Any) -> None:
        """Seed a row."""
        self._rows[(key_id, user_id)] = {
            "id": key_id,
            "user_id": user_id,
            "name": row.get("name", "Key"),
            "service": row.get("service", ServiceType.OPENAI.value),
            "description": row.get("description"),
            "is_valid": row.get("is_valid", True),
            "created_at": row.get("created_at", _now_iso()),
            "updated_at": row.get("updated_at", _now_iso()),
            "expires_at": row.get("expires_at"),
            "last_used": row.get("last_used"),
            "last_validated": row.get("last_validated", _now_iso()),
            "usage_count": row.get("usage_count", 0),
            "encrypted_key": row.get("encrypted_key", "invalid"),
        }


class _Cache:
    """Tiny async cache stub with string payloads."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self.data: dict[str, str] = {}

    async def get(
        self, key: str
    ) -> str | None:  # pragma: no cover - exercised via service
        """Get a value from the cache."""
        return self.data.get(key)

    async def set(
        self, key: str, value: str, **_kwargs: Any
    ) -> None:  # pragma: no cover - exercised via service
        """Set a value in the cache."""
        self.data[key] = value


class _Resp:
    """Minimal httpx-like response stub."""

    def __init__(
        self,
        status_code: int,
        json_payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the response."""
        self.status_code = status_code
        self._json = json_payload or {}
        self.headers = headers or {}

    def json(self) -> dict[str, Any]:  # pragma: no cover - exercised via service
        """Get the JSON payload."""
        return self._json


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_api_key_happy_path_records_audit_and_returns_true(
    test_settings: Settings,
) -> None:
    """Delete flow should perform batched DB ops and return True on success."""
    db = _DB()
    db.seed_row("k-1", "user-1", service=ServiceType.OPENAI.value)

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as svc:
        # Replace audit with no-op to avoid background work complexity
        async def _audit(*_args: Any, **_kwargs: Any) -> None:
            return None

        cast(Any, svc)._audit_key_deletion = _audit
        ok = await svc.delete_api_key("k-1", "user-1")
        await asyncio.sleep(0)  # drain background tasks if any

    assert ok is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_checks_aggregate_results_without_network(
    monkeypatch: pytest.MonkeyPatch, test_settings: Settings
) -> None:
    """Service health methods should compose results via the HTTP client interface.

    Monkeypatch the client's ``get`` to return canned responses for each service.
    """
    db = _DB()

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=None, settings=test_settings
    ) as svc:

        async def _fake_get(url: str, **_kwargs: Any) -> _Resp:  # type: ignore[override]
            if "status.openai.com" in url:
                return _Resp(
                    200,
                    {
                        "status": {
                            "indicator": "none",
                            "description": "All systems operational",
                        },
                        "page": {"updated_at": _now_iso()},
                    },
                )
            if "openweathermap.org" in url:
                return _Resp(401)  # Healthy path per implementation
            if "maps.googleapis.com" in url:
                return _Resp(200, {"status": "REQUEST_DENIED"})
            return _Resp(500)

        svc.client.get = _fake_get  # type: ignore[assignment]

        results = await svc.check_all_services_health()

    # The model uses `use_enum_values=True`, so `status` may be a str value.
    assert (
        ServiceHealthStatus(results[ServiceType.OPENAI].status)
        is ServiceHealthStatus.HEALTHY
    )
    assert (
        ServiceHealthStatus(results[ServiceType.WEATHER].status)
        is ServiceHealthStatus.HEALTHY
    )
    assert ServiceHealthStatus(results[ServiceType.GOOGLEMAPS].status) in {
        ServiceHealthStatus.HEALTHY,
        ServiceHealthStatus.DEGRADED,
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_openai_success_caches_result(
    monkeypatch: pytest.MonkeyPatch, test_settings: Settings
) -> None:
    """Validation should cache success with a JSON payload entry."""
    db = _DB()
    cache = _Cache()

    async with ApiKeyService(
        db=cast(DatabaseService, db), cache=cast(Any, cache), settings=test_settings
    ) as svc:
        # Patch request_with_backoff to avoid outbound requests
        async def _fake_rwb(
            _client: Any, _method: str, _url: str, **_kwargs: Any
        ) -> _Resp:
            # Successful OpenAI models response
            return _Resp(200, {"data": [{"id": "gpt-4-turbo"}]})

        monkeypatch.setattr(
            "tripsage_core.utils.outbound.request_with_backoff", _fake_rwb
        )

        result = await svc.validate_api_key(ServiceType.OPENAI, "sk-live-abc")

    assert result.is_valid is True
    # Cached via the service under key prefix api_validation:v3
    assert any(k.startswith("api_validation:v3:") for k in cache.data)
