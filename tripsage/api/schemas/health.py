"""Health API schemas.

Defines Pydantic models for health and readiness endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ComponentHealth(BaseModel):
    """Health status of a system component.

    Attributes:
        name: Component name.
        status: Health status string (healthy|degraded|unhealthy|unknown).
        latency_ms: Optional response latency in milliseconds.
        message: Optional status message.
        details: Additional details map.
    """

    name: str
    status: str
    latency_ms: float | None = None
    message: str | None = None
    details: dict[str, object] = Field(default_factory=dict)


class SystemHealth(BaseModel):
    """Overall system health status.

    Attributes:
        status: Overall health status string.
        timestamp: Current timestamp.
        version: API version string.
        environment: Deployment environment.
        components: List of component health statuses.
    """

    status: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0.0"
    environment: str
    components: list[ComponentHealth]


class ReadinessCheck(BaseModel):
    """Readiness check result.

    Attributes:
        ready: Whether the application is ready to serve traffic.
        timestamp: Current timestamp.
        checks: Map of dependency name to readiness boolean.
        details: Optional details per dependency.
    """

    ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checks: dict[str, bool]
    details: dict[str, str] = Field(default_factory=dict)
