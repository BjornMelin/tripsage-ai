"""Final-only tests for KeyMonitoringService behavior with in-memory stubs.

Covers logging, alerting, rate limit checks, and DB-backed health metrics.
No external Redis or database connections are used.
"""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest

from tripsage_core.services.infrastructure.cache_service import CacheService
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.services.infrastructure.key_monitoring_service import (
    KeyMonitoringService,
    KeyOperation,
    check_key_expiration,
    get_key_health_metrics,
)


class _MemCache:
    """Simple in-memory cache stub matching the CacheService interface subset."""

    def __init__(self):
        self.kv: dict[str, Any] = {}

    async def get_json(self, key: str, default: Any | None = None) -> Any:
        """Get the JSON value from the cache."""
        return self.kv.get(key, default)

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set the JSON value in the cache."""
        self.kv[key] = value
        return True

    async def get(self, key: str) -> str | None:
        """Get the value from the cache."""
        val = self.kv.get(key)
        return str(val) if val is not None else None

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set the value in the cache."""
        self.kv[key] = value
        return True

    async def incr(self, key: str) -> int | None:
        """Increment the value in the cache."""
        val = int(self.kv.get(key, "0")) + 1
        self.kv[key] = str(val)
        return val


class _MemDB:
    """DatabaseService subset stub returning supplied data for select/count."""

    def __init__(
        self, rows: list[Any] | None = None, counts: dict[str, int] | None = None
    ):
        """Initialize the Memory Database."""
        self.rows = rows or []
        self.counts = counts or {"api_keys": 0}

    async def select(self, table: str, *args: Any, **kwargs: Any):
        """Select the rows from the table."""
        return self.rows

    async def count(self, table: str, *args: Any, **kwargs: Any) -> int:
        """Count the number of rows in the table."""
        return self.counts.get(table, 0)


@pytest.mark.asyncio
async def test_log_operation_and_alerting_path() -> None:
    """log_operation stores logs and triggers alert when threshold is met."""
    svc = KeyMonitoringService()
    svc.cache_service = cast(CacheService, _MemCache())
    svc.database_service = cast(DatabaseService, _MemDB())

    # Below threshold: no suspicious flag
    for _ in range(4):
        await svc.log_operation(KeyOperation.CREATE, user_id="u1")
    logs = await svc.get_user_operations("u1")
    assert len(logs) == 4
    alerts = await svc.get_alerts()
    assert alerts == []

    # Hit threshold (5 creates) → suspicious + alert stored
    await svc.log_operation(KeyOperation.CREATE, user_id="u1")
    alerts = await svc.get_alerts()
    assert len(alerts) == 1
    assert alerts[0]["operation"] == KeyOperation.CREATE.value


@pytest.mark.asyncio
async def test_rate_limit_checks_with_in_memory_cache() -> None:
    """is_rate_limited increments a counter and enforces a per-minute ceiling."""
    svc = KeyMonitoringService()
    svc.cache_service = cast(CacheService, _MemCache())
    svc.database_service = cast(DatabaseService, _MemDB())

    limited = await svc.is_rate_limited("u2", KeyOperation.ACCESS)
    assert limited is False
    # Simulate hits until limit is enforced on the next call
    for _ in range(10):
        limited = await svc.is_rate_limited("u2", KeyOperation.ACCESS)
    # Now counter is 11 (first set to 1, then incr 10x), check returns True
    limited = await svc.is_rate_limited("u2", KeyOperation.ACCESS)
    assert limited is True


@pytest.mark.asyncio
async def test_check_key_expiration_and_health_metrics() -> None:
    """check_key_expiration and get_key_health_metrics normalize DB rows."""
    svc = KeyMonitoringService()
    svc.cache_service = cast(CacheService, _MemCache())
    # Provide mixed row shapes: dicts and scalars
    rows = [{"service": "openai"}, "anthropic"]
    svc.database_service = cast(
        DatabaseService, _MemDB(rows=rows, counts={"api_keys": 2})
    )

    expiring = await check_key_expiration(svc, days_before=30)
    assert isinstance(expiring, list)

    with patch(
        "tripsage_core.services.infrastructure.key_monitoring_service.get_database_service",
        new=AsyncMock(
            return_value=cast(
                DatabaseService, _MemDB(rows=rows, counts={"api_keys": 2})
            )
        ),
    ):
        metrics = await get_key_health_metrics()
    assert metrics["total_count"] == 2
    # Services normalized and counted
    svc_counts = {d["service"]: d["count"] for d in metrics["service_count"]}
    assert svc_counts.get("openai", 0) >= 1 and svc_counts.get("anthropic", 0) >= 1
