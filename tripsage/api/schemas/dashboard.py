"""Dashboard API schemas.

This module defines Pydantic models for dashboard API requests and responses,
including validation schemas for monitoring and analytics endpoints.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, validator


class TimeRange(str, Enum):
    """Predefined time ranges for dashboard queries."""

    LAST_HOUR = "1h"
    LAST_6_HOURS = "6h"
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"


class MetricType(str, Enum):
    """Types of metrics available for trending."""

    REQUEST_COUNT = "request_count"
    ERROR_RATE = "error_rate"
    SUCCESS_RATE = "success_rate"
    LATENCY = "latency"
    ACTIVE_USERS = "active_users"
    ACTIVE_KEYS = "active_keys"
    THROUGHPUT = "throughput"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of alerts."""

    SPIKE = "spike"
    DROP = "drop"
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    PATTERN = "pattern"
    SECURITY = "security"
    RATE_LIMIT = "rate_limit"


class ServiceHealthStatus(str, Enum):
    """Service health status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SystemStatus(str, Enum):
    """Overall system status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"


# Request schemas


class DashboardQueryParams(BaseModel):
    """Base query parameters for dashboard endpoints."""

    time_range: TimeRange | None = Field(default=TimeRange.LAST_24_HOURS)
    time_range_hours: int | None = Field(default=None, ge=1, le=168)
    service: str | None = Field(default=None, max_length=50)

    @validator("time_range_hours")
    def validate_time_range_hours(cls, v, values):
        """Validate time_range_hours based on time_range."""
        if v is not None:
            return v

        time_range = values.get("time_range", TimeRange.LAST_24_HOURS)
        time_range_mapping = {
            TimeRange.LAST_HOUR: 1,
            TimeRange.LAST_6_HOURS: 6,
            TimeRange.LAST_24_HOURS: 24,
            TimeRange.LAST_7_DAYS: 168,
            TimeRange.LAST_30_DAYS: 720,
        }
        return time_range_mapping.get(time_range, 24)


class MetricsQueryParams(DashboardQueryParams):
    """Query parameters for metrics endpoints."""

    metric_type: MetricType | None = Field(default=None)
    interval_minutes: int | None = Field(default=60, ge=5, le=1440)
    aggregation: str | None = Field(default="avg", regex="^(avg|sum|min|max|count)$")


class AlertsQueryParams(BaseModel):
    """Query parameters for alerts endpoints."""

    severity: AlertSeverity | None = Field(default=None)
    alert_type: AlertType | None = Field(default=None)
    acknowledged: bool | None = Field(default=None)
    service: str | None = Field(default=None, max_length=50)
    limit: int | None = Field(default=50, ge=1, le=200)
    offset: int | None = Field(default=0, ge=0)


class UserActivityQueryParams(DashboardQueryParams):
    """Query parameters for user activity endpoints."""

    user_type: str | None = Field(default=None, regex="^(user|agent|admin)$")
    limit: int | None = Field(default=20, ge=1, le=100)
    sort_by: str | None = Field(
        default="request_count", regex="^(request_count|error_count|last_activity)$"
    )
    sort_order: str | None = Field(default="desc", regex="^(asc|desc)$")


class RateLimitQueryParams(BaseModel):
    """Query parameters for rate limit endpoints."""

    key_id: str | None = Field(default=None)
    service: str | None = Field(default=None, max_length=50)
    threshold_percentage: float | None = Field(default=80.0, ge=0.0, le=100.0)
    limit: int | None = Field(default=20, ge=1, le=100)


# Response schemas


class ComponentHealth(BaseModel):
    """Health status of a system component."""

    name: str = Field(..., description="Component name")
    status: ServiceHealthStatus = Field(..., description="Component health status")
    latency_ms: float | None = Field(
        default=None, description="Response latency in milliseconds"
    )
    message: str | None = Field(default=None, description="Status message")
    last_check: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional details"
    )


class SystemOverviewResponse(BaseModel):
    """System overview dashboard response."""

    status: SystemStatus = Field(..., description="Overall system status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    uptime_seconds: int = Field(..., description="System uptime in seconds")
    version: str = Field(default="1.0.0", description="API version")
    environment: str = Field(..., description="Deployment environment")

    # Performance metrics
    total_requests_24h: int = Field(..., description="Total requests in last 24 hours")
    total_errors_24h: int = Field(..., description="Total errors in last 24 hours")
    success_rate_24h: float = Field(
        ..., ge=0.0, le=1.0, description="Success rate in last 24 hours"
    )
    avg_latency_ms: float = Field(default=0.0, description="Average response latency")

    # Activity metrics
    active_users_24h: int = Field(..., description="Active users in last 24 hours")
    active_api_keys: int = Field(..., description="Active API keys")

    # Component health
    components: list[ComponentHealth] = Field(
        default_factory=list, description="Component health status"
    )


class ServiceStatusResponse(BaseModel):
    """Service status response."""

    service: str = Field(..., description="Service name")
    status: ServiceHealthStatus = Field(..., description="Service health status")
    latency_ms: float | None = Field(
        default=None, description="Response latency in milliseconds"
    )
    last_check: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Error rate")
    uptime_percentage: float = Field(
        default=100.0, ge=0.0, le=100.0, description="Uptime percentage"
    )
    message: str | None = Field(default=None, description="Status message")
    endpoint_health: dict[str, ServiceHealthStatus] = Field(default_factory=dict)


class UsageMetricsResponse(BaseModel):
    """Usage metrics response."""

    period_start: datetime = Field(..., description="Metrics period start time")
    period_end: datetime = Field(..., description="Metrics period end time")

    # Request metrics
    total_requests: int = Field(..., description="Total number of requests")
    total_errors: int = Field(..., description="Total number of errors")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate")

    # Latency metrics
    avg_latency_ms: float = Field(..., description="Average response latency")
    p50_latency_ms: float = Field(default=0.0, description="50th percentile latency")
    p95_latency_ms: float = Field(default=0.0, description="95th percentile latency")
    p99_latency_ms: float = Field(default=0.0, description="99th percentile latency")

    # Usage breakdown
    unique_users: int = Field(..., description="Number of unique users")
    unique_endpoints: int = Field(
        ..., description="Number of unique endpoints accessed"
    )
    top_endpoints: list[dict[str, Any]] = Field(
        default_factory=list, description="Top accessed endpoints"
    )
    error_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Error count by type"
    )

    # Service usage
    usage_by_service: dict[str, int] = Field(
        default_factory=dict, description="Request count by service"
    )


class RateLimitInfoResponse(BaseModel):
    """Rate limit information response."""

    key_id: str = Field(..., description="API key ID")
    service: str | None = Field(default=None, description="Service name")
    current_usage: int = Field(..., description="Current usage count")
    limit: int = Field(..., description="Rate limit threshold")
    remaining: int = Field(..., description="Remaining quota")
    window_minutes: int = Field(..., description="Rate limit window in minutes")
    reset_at: datetime = Field(..., description="Rate limit reset time")
    percentage_used: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage of quota used"
    )
    is_approaching_limit: bool = Field(..., description="Whether approaching the limit")

    @validator("is_approaching_limit", always=True)
    def calculate_approaching_limit(cls, v, values):
        """Calculate if approaching limit based on percentage used."""
        percentage = values.get("percentage_used", 0.0)
        return percentage >= 80.0


class AlertInfoResponse(BaseModel):
    """Alert information response."""

    alert_id: str = Field(..., description="Unique alert ID")
    severity: AlertSeverity = Field(..., description="Alert severity")
    alert_type: AlertType = Field(..., description="Type of alert")
    message: str = Field(..., description="Alert message")
    created_at: datetime = Field(..., description="Alert creation time")
    updated_at: datetime | None = Field(
        default=None, description="Alert last update time"
    )

    # Context information
    key_id: str | None = Field(default=None, description="Related API key ID")
    service: str | None = Field(default=None, description="Related service")
    user_id: str | None = Field(default=None, description="Related user ID")
    endpoint: str | None = Field(default=None, description="Related endpoint")

    # Status
    acknowledged: bool = Field(
        default=False, description="Whether alert is acknowledged"
    )
    acknowledged_by: str | None = Field(
        default=None, description="User who acknowledged"
    )
    acknowledged_at: datetime | None = Field(
        default=None, description="Acknowledgment time"
    )

    # Additional data
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional alert details"
    )
    resolution_steps: list[str] = Field(
        default_factory=list, description="Suggested resolution steps"
    )


class UserActivityResponse(BaseModel):
    """User activity response."""

    user_id: str = Field(..., description="User ID")
    user_type: str = Field(..., description="User type (user, agent, admin)")

    # Activity metrics
    request_count: int = Field(..., description="Total request count")
    error_count: int = Field(..., description="Total error count")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate")
    last_activity: datetime = Field(..., description="Last activity timestamp")

    # Usage patterns
    services_used: list[str] = Field(
        default_factory=list, description="Services accessed"
    )
    top_endpoints: list[dict[str, Any]] = Field(
        default_factory=list, description="Most used endpoints"
    )
    avg_latency_ms: float = Field(default=0.0, description="Average response latency")

    # Time-based analysis
    activity_hours: dict[str, int] = Field(
        default_factory=dict, description="Activity by hour"
    )
    peak_activity_hour: str | None = Field(
        default=None, description="Hour with most activity"
    )


class TrendDataPoint(BaseModel):
    """Single data point in a trend series."""

    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Metric value")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )


class TrendDataResponse(BaseModel):
    """Trend data response."""

    metric_type: MetricType = Field(..., description="Type of metric")
    period_start: datetime = Field(..., description="Trend period start")
    period_end: datetime = Field(..., description="Trend period end")
    interval_minutes: int = Field(..., description="Data point interval in minutes")
    data_points: list[TrendDataPoint] = Field(..., description="Trend data points")

    # Summary statistics
    min_value: float = Field(..., description="Minimum value in period")
    max_value: float = Field(..., description="Maximum value in period")
    avg_value: float = Field(..., description="Average value in period")
    trend_direction: str = Field(
        ..., description="Overall trend direction (up, down, stable)"
    )

    @validator("trend_direction", always=True)
    def calculate_trend_direction(cls, v, values):
        """Calculate trend direction from data points."""
        data_points = values.get("data_points", [])
        if len(data_points) < 2:
            return "stable"

        first_half = data_points[: len(data_points) // 2]
        second_half = data_points[len(data_points) // 2 :]

        if not first_half or not second_half:
            return "stable"

        first_avg = sum(p.value for p in first_half) / len(first_half)
        second_avg = sum(p.value for p in second_half) / len(second_half)

        difference_threshold = 0.05  # 5% change
        if second_avg > first_avg * (1 + difference_threshold):
            return "up"
        elif second_avg < first_avg * (1 - difference_threshold):
            return "down"
        else:
            return "stable"


class AnalyticsSummaryResponse(BaseModel):
    """Analytics summary response."""

    period: dict[str, Any] = Field(..., description="Analysis period information")

    # Performance summary
    performance: dict[str, Any] = Field(..., description="Performance metrics summary")

    # Service health summary
    services: dict[str, Any] = Field(..., description="Service health summary")

    # Usage summary
    usage: dict[str, Any] = Field(..., description="Usage metrics summary")

    # Alert summary
    alerts: dict[str, Any] = Field(..., description="Alert summary")

    # Trend summary
    trends: dict[str, Any] = Field(..., description="Trend analysis summary")

    # Insights and recommendations
    insights: list[str] = Field(default_factory=list, description="Key insights")
    recommendations: list[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )


# Action request schemas


class AcknowledgeAlertRequest(BaseModel):
    """Request to acknowledge an alert."""

    note: str | None = Field(
        default=None, max_length=500, description="Acknowledgment note"
    )


class DismissAlertRequest(BaseModel):
    """Request to dismiss an alert."""

    reason: str = Field(..., max_length=200, description="Dismissal reason")
    note: str | None = Field(
        default=None, max_length=500, description="Additional notes"
    )


class ConfigureAlertRequest(BaseModel):
    """Request to configure alert thresholds."""

    alert_type: AlertType = Field(..., description="Type of alert to configure")
    threshold: float = Field(..., description="Alert threshold value")
    enabled: bool = Field(default=True, description="Whether alert is enabled")
    notification_channels: list[str] = Field(
        default_factory=list, description="Notification channels"
    )


# Bulk operation schemas


class BulkAlertActionRequest(BaseModel):
    """Request for bulk alert actions."""

    alert_ids: list[str] = Field(
        ..., min_items=1, max_items=100, description="Alert IDs to process"
    )
    action: str = Field(
        ..., regex="^(acknowledge|dismiss)$", description="Action to perform"
    )
    note: str | None = Field(default=None, max_length=500, description="Action note")


class BulkAlertActionResponse(BaseModel):
    """Response for bulk alert actions."""

    processed: int = Field(..., description="Number of alerts processed")
    successful: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    errors: list[dict[str, str]] = Field(
        default_factory=list, description="Error details"
    )


# Export monitoring data schemas


class ExportRequest(BaseModel):
    """Request to export monitoring data."""

    data_type: str = Field(
        ...,
        regex="^(metrics|alerts|usage|trends)$",
        description="Type of data to export",
    )
    format: str = Field(
        default="json", regex="^(json|csv|excel)$", description="Export format"
    )
    time_range_hours: int = Field(
        default=24, ge=1, le=8760, description="Time range in hours"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Additional filters"
    )


class ExportResponse(BaseModel):
    """Response for data export request."""

    export_id: str = Field(..., description="Unique export ID")
    status: str = Field(..., description="Export status")
    download_url: str | None = Field(
        default=None, description="Download URL when ready"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime = Field(..., description="Export expiration time")
    file_size_bytes: int | None = Field(default=None, description="File size in bytes")
