"""Dashboard model definitions used by DashboardService."""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


__all__ = [
    "AlertData",
    "AlertSeverity",
    "AlertType",
    "DashboardData",
    "RateLimitStatus",
    "RealTimeMetrics",
    "ServiceAnalytics",
    "UserActivityData",
]


def _empty_service_list() -> list[ServiceAnalytics]:
    """Return an empty list of service analytics."""
    return []


def _empty_user_list() -> list[UserActivityData]:
    """Return an empty list of user activity data."""
    return []


def _empty_alert_list() -> list[AlertData]:
    """Return an empty list of alert data."""
    return []


def _empty_trend_list() -> list[dict[str, Any]]:
    """Return an empty list of trend data."""
    return []


class AlertSeverity(str, enum.Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, enum.Enum):
    """Types of system alerts."""

    PERFORMANCE_DEGRADATION = "performance_degradation"
    HIGH_ERROR_RATE = "high_error_rate"
    SERVICE_UNHEALTHY = "service_unhealthy"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    API_KEY_EXPIRED = "api_key_expired"
    QUOTA_EXCEEDED = "quota_exceeded"
    SECURITY_ANOMALY = "security_anomaly"
    SYSTEM_OVERLOAD = "system_overload"


class RealTimeMetrics(BaseModel):
    """Real-time system metrics from live data sources."""

    total_requests: int = Field(description="Total requests in time period")
    total_errors: int = Field(description="Total errors in time period")
    success_rate: float = Field(description="Success rate percentage (0.0-1.0)")
    avg_latency_ms: float = Field(
        description="Average response latency in milliseconds"
    )
    p95_latency_ms: float = Field(description="95th percentile latency")
    p99_latency_ms: float = Field(description="99th percentile latency")
    active_keys_count: int = Field(description="Number of active API keys")
    unique_users_count: int = Field(description="Number of unique users")
    requests_per_minute: float = Field(description="Current requests per minute rate")
    period_start: datetime = Field(description="Start of metrics period")
    period_end: datetime = Field(description="End of metrics period")

    @computed_field
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        return 1.0 - self.success_rate if self.success_rate <= 1.0 else 0.0

    @computed_field
    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime based on success rate."""
        return min(100.0, self.success_rate * 100.0)


class ServiceAnalytics(BaseModel):
    """Analytics data for individual services."""

    service_name: str = Field(description="Service identifier")
    service_type: ServiceType = Field(description="Service type enum")
    total_requests: int = Field(description="Total requests to this service")
    total_errors: int = Field(description="Total errors from this service")
    success_rate: float = Field(description="Service success rate")
    avg_latency_ms: float = Field(description="Average latency for this service")
    active_keys: int = Field(description="Active keys for this service")
    last_health_check: datetime = Field(description="Last health check timestamp")
    health_status: ServiceHealthStatus = Field(description="Current health status")
    rate_limit_hits: int = Field(default=0, description="Rate limit violations")
    quota_usage_percent: float = Field(
        default=0.0, description="Quota usage percentage"
    )


class UserActivityData(BaseModel):
    """Real user activity analytics."""

    user_id: str = Field(description="User identifier")
    request_count: int = Field(description="Total requests by user")
    error_count: int = Field(description="Total errors by user")
    success_rate: float = Field(description="User's success rate")
    avg_latency_ms: float = Field(description="User's average latency")
    services_used: list[str] = Field(description="Services accessed by user")
    first_activity: datetime = Field(description="First recorded activity")
    last_activity: datetime = Field(description="Most recent activity")
    total_api_keys: int = Field(description="Number of API keys owned")

    @computed_field
    @property
    def activity_score(self) -> float:
        """Calculate user activity score (0-100)."""
        base_score = min(50.0, self.request_count / 10.0)
        success_bonus = self.success_rate * 30.0
        recency_days = (datetime.now(UTC) - self.last_activity).days
        recency_penalty = max(0.0, min(20.0, recency_days * 2.0))
        return max(0.0, base_score + success_bonus - recency_penalty)


class AlertData(BaseModel):
    """Real alert data with classification and context."""

    alert_id: str = Field(description="Unique alert identifier")
    alert_type: AlertType = Field(description="Type of alert")
    severity: AlertSeverity = Field(description="Alert severity level")
    title: str = Field(description="Alert title")
    message: str = Field(description="Detailed alert message")
    created_at: datetime = Field(description="Alert creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    service: str | None = Field(default=None, description="Related service")
    user_id: str | None = Field(default=None, description="Related user")
    api_key_id: str | None = Field(default=None, description="Related API key")

    acknowledged: bool = Field(
        default=False, description="Whether alert is acknowledged"
    )
    acknowledged_by: str | None = Field(
        default=None, description="User who acknowledged"
    )
    acknowledged_at: datetime | None = Field(
        default=None, description="Acknowledgment timestamp"
    )
    resolved: bool = Field(default=False, description="Whether alert is resolved")
    resolved_at: datetime | None = Field(
        default=None, description="Resolution timestamp"
    )

    threshold_value: float | None = Field(
        default=None, description="Threshold that triggered alert"
    )
    current_value: float | None = Field(
        default=None, description="Current metric value"
    )
    affected_resources: list[str] = Field(
        default_factory=list, description="Affected resources"
    )
    recommended_actions: list[str] = Field(
        default_factory=list, description="Suggested remediation"
    )

    tags: list[str] = Field(
        default_factory=list, description="Alert tags for filtering"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional context data"
    )

    @computed_field
    @property
    def age_minutes(self) -> int:
        """Calculate alert age in minutes."""
        return int((datetime.now(UTC) - self.created_at).total_seconds() / 60)

    @computed_field
    @property
    def priority_score(self) -> int:
        """Calculate priority score for sorting (higher = more urgent)."""
        severity_scores = {
            AlertSeverity.CRITICAL: 100,
            AlertSeverity.HIGH: 75,
            AlertSeverity.MEDIUM: 50,
            AlertSeverity.LOW: 25,
            AlertSeverity.INFO: 10,
        }
        base_score = severity_scores.get(self.severity, 0)
        if self.resolved:
            base_score = int(base_score * 0.1)
        elif self.acknowledged:
            base_score = int(base_score * 0.5)
        return base_score


class DashboardData(BaseModel):
    """Comprehensive dashboard data derived from real analytics."""

    metrics: RealTimeMetrics = Field(description="Aggregated real-time metrics")
    services: list[ServiceAnalytics] = Field(
        default_factory=_empty_service_list, description="Per-service analytics"
    )
    top_users: list[UserActivityData] = Field(
        default_factory=_empty_user_list, description="Top active users"
    )
    recent_alerts: list[AlertData] = Field(
        default_factory=_empty_alert_list, description="Recent system alerts"
    )
    usage_trend: list[dict[str, Any]] = Field(
        default_factory=_empty_trend_list, description="Historical trend data"
    )
    cache_stats: dict[str, Any] = Field(
        default_factory=dict, description="Cache performance statistics"
    )

    @computed_field
    @property
    def overall_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        if not self.services:
            return 0.0

        success_weight = 0.4
        latency_weight = 0.3
        service_health_weight = 0.3

        success_component = self.metrics.success_rate * (success_weight * 100.0)

        avg_latency = self.metrics.avg_latency_ms
        latency_component = max(
            0.0,
            (latency_weight * 100.0)
            - (avg_latency / 1000.0) * (latency_weight * 100.0),
        )

        healthy_services = sum(
            1
            for service in self.services
            if service.health_status == ServiceHealthStatus.HEALTHY
        )
        service_health_component = (healthy_services / len(self.services)) * (
            service_health_weight * 100.0
        )

        return success_component + latency_component + service_health_component


class RateLimitStatus(BaseModel):
    """Real-time rate limit status from cache."""

    key_id: str = Field(description="API key identifier")
    service: str = Field(description="Service name")
    current_usage: int = Field(description="Current usage count")
    limit: int = Field(description="Rate limit threshold")
    remaining: int = Field(description="Remaining quota")
    window_minutes: int = Field(description="Rate limit window in minutes")
    reset_at: datetime = Field(description="When the limit resets")
    percentage_used: float = Field(description="Percentage of limit used")
    is_throttled: bool = Field(default=False, description="Whether currently throttled")
    last_request: datetime | None = Field(
        default=None, description="Last request timestamp"
    )


class ServiceHealthStatus(str, enum.Enum):
    """Service health status indicator."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(str, enum.Enum):
    """Known third-party service identifiers."""

    GENERIC = "generic"
    OPENAI = "openai"
    WEATHER = "weather"
    GOOGLEMAPS = "googlemaps"
    EMAIL = "email"
