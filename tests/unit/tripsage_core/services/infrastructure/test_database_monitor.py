"""Unit tests for the final database connection monitor."""

from __future__ import annotations

import asyncio
from datetime import UTC

import pytest

from tripsage_core.config import Settings
from tripsage_core.monitoring.database_metrics import (
    DatabaseMetrics,
    reset_database_metrics,
)
from tripsage_core.services.infrastructure.database_monitor import (
    DatabaseConnectionMonitor,
    HealthSnapshot,
    HealthStatus,
)


class _FakeDatabaseService:
    """Minimal async service used for exercising the monitor."""

    def __init__(
        self, *, healthy: bool = True, raises: Exception | None = None
    ) -> None:
        """Initialize the fake database service."""
        self._connected = True
        self._healthy = healthy
        self._raises = raises
        self.call_count = 0

    @property
    def is_connected(self) -> bool:
        """Check if the fake database service is connected."""
        return self._connected

    async def health_check(self) -> bool:
        """Perform a health check."""
        self.call_count += 1
        if self._raises is not None:
            raise self._raises
        return self._healthy


@pytest.fixture(autouse=True)
def reset_metrics() -> None:
    """Ensure global metrics state is reset between tests."""
    reset_database_metrics()


@pytest.fixture()
def fast_settings() -> Settings:
    """Provide settings with a fast health-interval for deterministic tests."""
    return Settings(db_health_check_interval=0.05)


@pytest.mark.asyncio
async def test_check_now_records_success_snapshot(fast_settings: Settings) -> None:
    """A successful probe yields a healthy snapshot and updates metrics."""
    service = _FakeDatabaseService(healthy=True)
    metrics = DatabaseMetrics()
    monitor = DatabaseConnectionMonitor(
        service,
        settings=fast_settings,
        metrics=metrics,
        history_limit=4,
    )

    snapshot = await monitor.check_now()

    assert snapshot.status is HealthStatus.HEALTHY
    assert snapshot.latency_s >= 0
    assert snapshot.checked_at.tzinfo is UTC
    assert monitor.get_current_health() == snapshot

    summary = metrics.get_metrics_summary()
    assert any(value == 1.0 for value in summary["health_status"].values())


@pytest.mark.asyncio
async def test_check_now_translates_exceptions_to_unhealthy(
    fast_settings: Settings,
) -> None:
    """Exceptions raised by the service are captured as unhealthy snapshots."""
    service = _FakeDatabaseService(raises=RuntimeError("boom"))
    monitor = DatabaseConnectionMonitor(
        service, settings=fast_settings, metrics=DatabaseMetrics()
    )

    snapshot = await monitor.check_now()

    assert snapshot.status is HealthStatus.UNHEALTHY
    assert snapshot.details == {"error": "boom"}


@pytest.mark.asyncio
async def test_start_and_stop_execute_periodic_checks(fast_settings: Settings) -> None:
    """Starting the monitor triggers repeated probes until stop is requested."""
    service = _FakeDatabaseService(healthy=True)
    monitor = DatabaseConnectionMonitor(
        service, settings=fast_settings, metrics=DatabaseMetrics()
    )

    await monitor.start_monitoring()
    await asyncio.sleep(0.18)
    await monitor.stop_monitoring()

    assert service.call_count >= 2
    assert isinstance(monitor.get_current_health(), HealthSnapshot)


@pytest.mark.asyncio
async def test_history_limit_is_respected(fast_settings: Settings) -> None:
    """Health history retains only the configured number of snapshots."""
    service = _FakeDatabaseService(healthy=True)
    monitor = DatabaseConnectionMonitor(
        service,
        settings=fast_settings,
        metrics=DatabaseMetrics(),
        history_limit=2,
    )

    await monitor.check_now()
    await monitor.check_now()
    await monitor.check_now()

    history = monitor.get_health_history()
    assert len(history) == 2
    assert history[0].checked_at <= history[1].checked_at
