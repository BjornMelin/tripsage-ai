"""Realtime dashboard response schemas (feature-first)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class RealtimeMetrics(BaseModel):
    """Real-time metrics data payload."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    requests_per_second: float
    errors_per_second: float
    success_rate: float
    avg_latency_ms: float
    active_connections: int
    cache_hit_rate: float
    memory_usage_percentage: float


class AlertNotification(BaseModel):
    """Notification emitted when an alert occurs/changes."""

    alert_id: str
    type: str
    severity: str
    message: str
    service: str | None = None
    key_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class SystemEvent(BaseModel):
    """System-level event for realtime stream."""

    event_id: str
    event_type: str
    message: str
    severity: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    affected_services: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class BroadcastResponse(BaseModel):
    """Outcome of a broadcast operation."""

    success: bool
    message: str
    alert_id: str | None = None


class ConnectionsStatusResponse(BaseModel):
    """Summary of active realtime connections."""

    total_connections: int
    connections: list[dict[str, Any]]
