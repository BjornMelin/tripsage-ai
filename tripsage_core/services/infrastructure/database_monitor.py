"""Asynchronous database health monitoring.

This module provides a minimal, final-only monitor that periodically probes the
configured database service and records lightweight health telemetry. The
implementation focuses exclusively on health checks and metrics reporting; it
deliberately omits the security heuristics, recovery orchestration, and
callback shims that previously bloated the monitor surface.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol

from tripsage_core.config import Settings, get_settings
from tripsage_core.observability.otel import get_meter


logger = logging.getLogger(__name__)


DEFAULT_SERVICE_LABEL = "supabase"
MIN_HEALTH_INTERVAL_SECONDS = 0.1
DEFAULT_HISTORY_LIMIT = 32


class DatabaseServiceProtocol(Protocol):
    """Protocol describing the minimal database service API required."""

    @property
    def is_connected(self) -> bool:
        """Check if the database service is connected."""
        ...

    async def health_check(self) -> bool:
        """Perform a health probe and return True when the service is healthy."""
        ...


class HealthStatus(str, Enum):
    """Discrete health states emitted by the monitor."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class HealthSnapshot:
    """Immutable record of a single health probe.

    Attributes:
        status: Resulting health status.
        latency_s: Duration of the health probe in seconds.
        checked_at: Timestamp (UTC) when the probe completed.
        details: Optional structured metadata describing failure causes.
    """

    status: HealthStatus
    latency_s: float
    checked_at: datetime
    details: Mapping[str, Any] | None = None


class DatabaseConnectionMonitor:  # pylint: disable=too-many-instance-attributes
    """Periodically execute health checks for the configured database service."""

    def __init__(
        self,
        database_service: DatabaseServiceProtocol,
        *,
        settings: Settings | None = None,
        service_label: str = DEFAULT_SERVICE_LABEL,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> None:
        """Initialise the monitor with its dependencies.

        Args:
            database_service: Service that exposes an async ``health_check`` method.
            settings: TripSage settings used for interval configuration.
            service_label: Label recorded in metrics for this service.
            history_limit: Maximum number of recent snapshots retained in memory.
        """
        self._service = database_service
        self._settings = settings or get_settings()
        # Set up OTEL instruments (histogram and counter). Gauges are handled via
        # observable callbacks elsewhere when needed.
        meter = get_meter(__name__)
        self._m_hist = meter.create_histogram(
            "db.health_check.latency", unit="s", description="DB health probe latency"
        )
        self._m_count = meter.create_counter(
            "db.health_check.total", description="Total DB health probes"
        )
        self._service_label = service_label
        self._interval = max(
            self._settings.db_health_check_interval, MIN_HEALTH_INTERVAL_SECONDS
        )
        self._history: deque[HealthSnapshot] = deque(maxlen=max(1, history_limit))
        self._latest: HealthSnapshot | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._check_lock = asyncio.Lock()

    async def start_monitoring(self) -> None:
        """Start the asynchronous health monitoring loop."""
        if self._task and not self._task.done():
            logger.debug("Database monitoring already running")
            return

        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="database-monitor-loop")
        logger.info("Database monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop the monitoring loop and await task completion."""
        if not self._task:
            return

        self._stop_event.set()
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("Database monitoring stopped")

    async def check_now(self) -> HealthSnapshot:
        """Execute a health probe immediately and record the snapshot."""
        async with self._check_lock:
            snapshot = await self._execute_health_check()
            self._record_snapshot(snapshot)
            return snapshot

    def get_current_health(self) -> HealthSnapshot | None:
        """Return the most recent snapshot produced by the monitor."""
        return self._latest

    def get_health_history(self, limit: int | None = None) -> list[HealthSnapshot]:
        """Return the bounded history of health snapshots.

        Args:
            limit: Optional maximum number of entries to return from newest to oldest.

        Returns:
            A list of snapshots ordered from oldest to newest within the requested
            window.
        """
        if limit is None or limit >= len(self._history):
            return list(self._history)
        return list(self._history)[-limit:]

    def get_monitoring_status(self) -> dict[str, Any]:
        """Expose lightweight monitoring state for status endpoints."""
        snapshot = self._latest
        return {
            "monitoring_active": bool(self._task and not self._task.done()),
            "health_check_interval": self._interval,
            "last_health_check": None
            if snapshot is None
            else {
                "status": snapshot.status.value,
                "latency_s": snapshot.latency_s,
                "timestamp": snapshot.checked_at.isoformat(),
                "details": snapshot.details,
            },
            "health_history_count": len(self._history),
        }

    async def _run_loop(self) -> None:
        """Internal loop that executes health checks at the configured cadence."""
        try:
            while not self._stop_event.is_set():
                await self.check_now()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=self._interval
                    )
                except TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass

    async def _execute_health_check(self) -> HealthSnapshot:
        """Invoke the service health probe and translate it into a snapshot."""
        start_time = time.perf_counter()
        try:
            healthy = await self._service.health_check()
        except Exception as exc:
            latency = time.perf_counter() - start_time
            logger.exception("Database health check failed")
            return HealthSnapshot(
                status=HealthStatus.UNHEALTHY,
                latency_s=latency,
                checked_at=datetime.now(UTC),
                details={"error": str(exc)},
            )

        latency = time.perf_counter() - start_time
        is_connected = getattr(self._service, "is_connected", True)
        if healthy and is_connected:
            status = HealthStatus.HEALTHY
            details = None
        else:
            status = HealthStatus.UNHEALTHY
            details = {
                "reason": "service_reported_failure"
                if not healthy
                else "service_disconnected",
            }

        return HealthSnapshot(
            status=status,
            latency_s=latency,
            checked_at=datetime.now(UTC),
            details=details,
        )

    def _record_snapshot(self, snapshot: HealthSnapshot) -> None:
        """Persist the snapshot and update metrics."""
        self._latest = snapshot
        self._history.append(snapshot)
        try:
            attrs = {"service": self._service_label, "status": snapshot.status.value}
            self._m_hist.record(snapshot.latency_s, attrs)
            self._m_count.add(1, attrs)
        except Exception:  # noqa: BLE001 - metrics failures must not break loop
            # Never let metrics break monitoring loop
            logger.debug("OTEL metrics record failed", exc_info=True)
