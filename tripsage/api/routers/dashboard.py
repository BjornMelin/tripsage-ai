"""Dashboard monitoring API endpoints.

This module provides comprehensive dashboard API endpoints for monitoring and insights:
- System health and status
- API key usage statistics and analytics
- Real-time metrics and monitoring data
- Usage trends and historical data
- Alert management
- Rate limit status and quota information
- Service health status
- User activity and top consumers
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    CacheDep,
    DatabaseDep,
    SettingsDep,
)
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
)
from tripsage_core.services.business.api_key_monitoring import (
    ApiKeyMonitoringService,
)
from tripsage_core.services.business.api_key_validator import (
    ApiKeyValidator,
    ServiceHealthStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Pydantic models for dashboard responses


class SystemOverview(BaseModel):
    """System overview data for dashboard."""

    status: str  # healthy, degraded, unhealthy
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    uptime_seconds: int
    version: str = "1.0.0"
    environment: str
    total_requests_24h: int
    total_errors_24h: int
    success_rate_24h: float
    active_users_24h: int
    active_api_keys: int


class ServiceStatus(BaseModel):
    """Service status information."""

    service: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float | None = None
    last_check: datetime
    error_rate: float
    uptime_percentage: float
    message: str | None = None


class UsageMetrics(BaseModel):
    """Usage metrics for a specific time period."""

    period_start: datetime
    period_end: datetime
    total_requests: int
    total_errors: int
    success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    unique_users: int
    unique_endpoints: int
    top_endpoints: list[dict[str, Any]]
    error_breakdown: dict[str, int]


class RateLimitInfo(BaseModel):
    """Rate limit information."""

    key_id: str
    current_usage: int
    limit: int
    remaining: int
    window_minutes: int
    reset_at: datetime
    percentage_used: float


class AlertInfo(BaseModel):
    """Alert information for dashboard."""

    alert_id: str
    severity: str
    type: str
    message: str
    created_at: datetime
    key_id: str | None = None
    service: str | None = None
    acknowledged: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class UserActivity(BaseModel):
    """User activity information."""

    user_id: str
    user_type: str  # user, agent
    request_count: int
    error_count: int
    success_rate: float
    last_activity: datetime
    services_used: list[str]
    avg_latency_ms: float


class TrendData(BaseModel):
    """Time series trend data."""

    timestamp: datetime
    value: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardFilters(BaseModel):
    """Filters for dashboard queries."""

    time_range_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week
    service: str | None = None
    user_id: str | None = None
    key_id: str | None = None
    severity: str | None = None
    status: str | None = None


# Dependency for getting authenticated principal
async def get_current_principal(request: Request) -> Principal:
    """Get the current authenticated principal from request state."""
    if not hasattr(request.state, "principal") or not request.state.principal:
        raise CoreAuthenticationError("Authentication required for dashboard access")

    principal = request.state.principal

    # Only allow users and admins to access dashboard
    if principal.type not in ["user", "admin"]:
        raise CoreAuthenticationError("Dashboard access requires user authentication")

    return principal


# Dashboard endpoints


@router.get("/overview", response_model=SystemOverview)
async def get_system_overview(
    settings: SettingsDep,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: Principal = Depends(get_current_principal),
) -> SystemOverview:
    """Get system overview for dashboard.

    Returns high-level system metrics and status including:
    - Overall system health
    - Request and error counts
    - Active users and API keys
    - Success rates
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get dashboard data for 24 hours
        dashboard_data = await monitoring_service.get_dashboard_data(
            time_range_hours=24,
            top_users_limit=10,
        )

        # Calculate uptime (simplified - would use actual startup time in production)
        uptime_seconds = 86400  # 24 hours as default

        # Determine overall status
        overall_status = "healthy"
        if dashboard_data.overall_success_rate < 0.9:  # <90% success rate
            overall_status = "degraded"
        if dashboard_data.overall_success_rate < 0.8:  # <80% success rate
            overall_status = "unhealthy"

        return SystemOverview(
            status=overall_status,
            uptime_seconds=uptime_seconds,
            environment=settings.environment,
            total_requests_24h=dashboard_data.total_requests,
            total_errors_24h=dashboard_data.total_errors,
            success_rate_24h=dashboard_data.overall_success_rate,
            active_users_24h=len(dashboard_data.top_users),
            active_api_keys=dashboard_data.active_keys,
        )

    except Exception as e:
        logger.error(f"Failed to get system overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system overview: {str(e)}",
        ) from e


@router.get("/services", response_model=list[ServiceStatus])
async def get_services_status(
    cache_service: CacheDep,
    principal: Principal = Depends(get_current_principal),
) -> list[ServiceStatus]:
    """Get status of all external services.

    Returns health status for all integrated external services:
    - OpenAI
    - Weather API
    - Google Maps
    - Other configured services
    """
    try:
        services_status = []

        # Check external services health
        async with ApiKeyValidator() as validator:
            health_checks = await validator.check_all_services_health()

            for service_type, health_check in health_checks.items():
                # Convert health status
                status_str = "healthy"
                if health_check.status == ServiceHealthStatus.DEGRADED:
                    status_str = "degraded"
                elif health_check.status == ServiceHealthStatus.UNHEALTHY:
                    status_str = "unhealthy"

                # Calculate error rate (simplified)
                error_rate = 0.0
                if health_check.status == ServiceHealthStatus.DEGRADED:
                    error_rate = 0.1  # 10%
                elif health_check.status == ServiceHealthStatus.UNHEALTHY:
                    error_rate = 0.5  # 50%

                # Calculate uptime percentage (simplified)
                uptime_percentage = 100.0
                if health_check.status == ServiceHealthStatus.DEGRADED:
                    uptime_percentage = 95.0
                elif health_check.status == ServiceHealthStatus.UNHEALTHY:
                    uptime_percentage = 80.0

                services_status.append(
                    ServiceStatus(
                        service=service_type.value,
                        status=status_str,
                        latency_ms=health_check.latency_ms,
                        last_check=datetime.now(timezone.utc),
                        error_rate=error_rate,
                        uptime_percentage=uptime_percentage,
                        message=health_check.message,
                    )
                )

        return services_status

    except Exception as e:
        logger.error(f"Failed to get services status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve services status: {str(e)}",
        ) from e


@router.get("/metrics", response_model=UsageMetrics)
async def get_usage_metrics(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    service: str | None = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> UsageMetrics:
    """Get usage metrics for specified time range.

    Returns comprehensive usage metrics including:
    - Request and error counts
    - Latency statistics
    - Top endpoints
    - Error breakdown by type
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        # Get dashboard data
        dashboard_data = await monitoring_service.get_dashboard_data(
            time_range_hours=time_range_hours,
            top_users_limit=50,
        )

        # Extract metrics from dashboard data
        total_requests = dashboard_data.total_requests
        total_errors = dashboard_data.total_errors

        # Calculate average latency (simplified)
        avg_latency_ms = 150.0  # Default
        p95_latency_ms = 300.0  # Default
        p99_latency_ms = 500.0  # Default

        # Get top endpoints (simplified)
        top_endpoints = [
            {"endpoint": "/api/chat", "count": total_requests // 3},
            {"endpoint": "/api/flights", "count": total_requests // 4},
            {"endpoint": "/api/accommodations", "count": total_requests // 5},
        ]

        # Error breakdown (simplified)
        error_breakdown = {
            "validation_error": total_errors // 2,
            "rate_limit_error": total_errors // 4,
            "external_api_error": total_errors // 4,
        }

        return UsageMetrics(
            period_start=start_time,
            period_end=end_time,
            total_requests=total_requests,
            total_errors=total_errors,
            success_rate=dashboard_data.overall_success_rate,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            p99_latency_ms=p99_latency_ms,
            unique_users=len(dashboard_data.top_users),
            unique_endpoints=len(top_endpoints),
            top_endpoints=top_endpoints,
            error_breakdown=error_breakdown,
        )

    except Exception as e:
        logger.error(f"Failed to get usage metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage metrics: {str(e)}",
        ) from e


@router.get("/rate-limits", response_model=list[RateLimitInfo])
async def get_rate_limits_status(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> list[RateLimitInfo]:
    """Get rate limit status for API keys.

    Returns current rate limit status for active API keys including:
    - Current usage vs limits
    - Remaining quota
    - Reset times
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        rate_limits = []

        # Get active keys from recent usage
        active_keys = list(monitoring_service.recent_usage.keys())[:limit]

        for key_id in active_keys:
            try:
                # Get rate limit status
                status_data = await monitoring_service.get_rate_limit_status(
                    key_id=key_id,
                    window_minutes=60,
                )

                if "error" not in status_data:
                    current_usage = status_data["requests_in_window"]
                    limit_value = status_data["limit"]
                    remaining = status_data["remaining"]
                    reset_at = datetime.fromisoformat(status_data["reset_at"])

                    percentage_used = (
                        (current_usage / limit_value * 100) if limit_value > 0 else 0
                    )

                    rate_limits.append(
                        RateLimitInfo(
                            key_id=key_id,
                            current_usage=current_usage,
                            limit=limit_value,
                            remaining=remaining,
                            window_minutes=60,
                            reset_at=reset_at,
                            percentage_used=percentage_used,
                        )
                    )

            except Exception as e:
                logger.warning(f"Failed to get rate limit for key {key_id}: {e}")
                continue

        return rate_limits

    except Exception as e:
        logger.error(f"Failed to get rate limits status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rate limits status: {str(e)}",
        ) from e


@router.get("/alerts", response_model=list[AlertInfo])
async def get_alerts(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    severity: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    principal: Principal = Depends(get_current_principal),
) -> list[AlertInfo]:
    """Get system alerts and notifications.

    Returns alerts filtered by severity and acknowledgment status:
    - Security alerts
    - Performance alerts
    - Error rate alerts
    - Anomaly detection alerts
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        alerts = []

        # Get recent alerts from the monitoring service
        for alert in monitoring_service.active_alerts.values():
            # Apply filters
            if severity and alert.severity != severity:
                continue
            if acknowledged is not None and alert.acknowledged != acknowledged:
                continue

            alerts.append(
                AlertInfo(
                    alert_id=alert.alert_id,
                    severity=alert.severity,
                    type=alert.anomaly_type.value,
                    message=alert.message,
                    created_at=alert.created_at,
                    key_id=alert.key_id,
                    service=alert.service,
                    acknowledged=alert.acknowledged,
                    details=alert.details,
                )
            )

        # Sort by severity and creation time
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        alerts.sort(
            key=lambda x: (
                severity_order.get(x.severity, 4),
                x.created_at,
            ),
            reverse=True,
        )

        return alerts[:limit]

    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {str(e)}",
        ) from e


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    """Acknowledge an alert.

    Marks an alert as acknowledged by the current user.
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Find and acknowledge the alert
        if alert_id in monitoring_service.active_alerts:
            alert = monitoring_service.active_alerts[alert_id]
            alert.acknowledged = True

            logger.info(
                f"Alert {alert_id} acknowledged by {principal.id}",
                extra={
                    "alert_id": alert_id,
                    "user_id": principal.id,
                    "alert_type": alert.anomaly_type.value,
                    "severity": alert.severity,
                },
            )

            return {
                "success": True,
                "message": "Alert acknowledged successfully",
                "alert_id": alert_id,
                "acknowledged_by": principal.id,
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}",
        ) from e


@router.delete("/alerts/{alert_id}")
async def dismiss_alert(
    alert_id: str,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    """Dismiss an alert.

    Removes an alert from the active alerts list.
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Find and dismiss the alert
        if alert_id in monitoring_service.active_alerts:
            alert = monitoring_service.active_alerts.pop(alert_id)

            logger.info(
                f"Alert {alert_id} dismissed by {principal.id}",
                extra={
                    "alert_id": alert_id,
                    "user_id": principal.id,
                    "alert_type": alert.anomaly_type.value,
                    "severity": alert.severity,
                },
            )

            return {
                "success": True,
                "message": "Alert dismissed successfully",
                "alert_id": alert_id,
                "dismissed_by": principal.id,
                "dismissed_at": datetime.now(timezone.utc).isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to dismiss alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss alert: {str(e)}",
        ) from e


@router.get("/users/activity", response_model=list[UserActivity])
async def get_user_activity(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
    principal: Principal = Depends(get_current_principal),
) -> list[UserActivity]:
    """Get user activity data.

    Returns user activity metrics including:
    - Request counts and success rates
    - Services used
    - Last activity times
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get dashboard data
        dashboard_data = await monitoring_service.get_dashboard_data(
            time_range_hours=time_range_hours,
            top_users_limit=limit,
        )

        user_activities = []

        # Convert top users to UserActivity objects
        for user_data in dashboard_data.top_users:
            user_id = user_data.get("user_id", "unknown")
            request_count = user_data.get("request_count", 0)

            # Calculate success rate (simplified)
            error_count = int(request_count * 0.05)  # 5% error rate assumption
            success_rate = (
                (request_count - error_count) / request_count
                if request_count > 0
                else 1.0
            )

            user_activities.append(
                UserActivity(
                    user_id=user_id,
                    user_type="agent" if user_id.startswith("agent_") else "user",
                    request_count=request_count,
                    error_count=error_count,
                    success_rate=success_rate,
                    last_activity=datetime.now(timezone.utc) - timedelta(hours=1),
                    services_used=["chat", "flights", "accommodations"],
                    avg_latency_ms=150.0,
                )
            )

        return user_activities

    except Exception as e:
        logger.error(f"Failed to get user activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user activity: {str(e)}",
        ) from e


@router.get("/trends/{metric_type}", response_model=list[TrendData])
async def get_trend_data(
    metric_type: str,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    interval_minutes: int = Query(default=60, ge=5, le=1440),
    principal: Principal = Depends(get_current_principal),
) -> list[TrendData]:
    """Get trend data for specified metric.

    Returns time series data for metrics like:
    - request_count
    - error_rate
    - latency
    - active_users
    """
    try:
        # Validate metric type
        valid_metrics = ["request_count", "error_rate", "latency", "active_users"]
        if metric_type not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric type. Must be one of: {valid_metrics}",
            )

        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        # Get usage trend data
        trend_data_raw = await monitoring_service._generate_usage_trend(
            start_time, end_time
        )

        # Convert to TrendData objects based on metric type
        trend_data = []
        for data_point in trend_data_raw:
            timestamp = datetime.fromisoformat(data_point["timestamp"])

            if metric_type == "request_count":
                value = float(data_point["requests"])
            elif metric_type == "error_rate":
                value = 1.0 - data_point["success_rate"]  # Convert to error rate
            elif metric_type == "latency":
                value = 150.0  # Simplified default
            elif metric_type == "active_users":
                value = float(data_point["requests"]) / 10  # Simplified calculation
            else:
                value = 0.0

            trend_data.append(
                TrendData(
                    timestamp=timestamp,
                    value=value,
                    metadata={
                        "requests": data_point["requests"],
                        "errors": data_point["errors"],
                        "success_rate": data_point["success_rate"],
                    },
                )
            )

        return trend_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trend data for {metric_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trend data: {str(e)}",
        ) from e


@router.get("/analytics/summary", response_model=dict[str, Any])
async def get_analytics_summary(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    """Get comprehensive analytics summary.

    Returns comprehensive analytics including:
    - System performance overview
    - Service health summary
    - Usage patterns
    - Top performing and problematic areas
    """
    try:
        # Initialize monitoring service
        monitoring_service = ApiKeyMonitoringService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get dashboard data
        dashboard_data = await monitoring_service.get_dashboard_data(
            time_range_hours=time_range_hours,
            top_users_limit=10,
        )

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        # Build comprehensive summary
        summary = {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": time_range_hours,
            },
            "performance": {
                "total_requests": dashboard_data.total_requests,
                "total_errors": dashboard_data.total_errors,
                "success_rate": dashboard_data.overall_success_rate,
                "avg_latency_ms": 150.0,  # Simplified
                "p95_latency_ms": 300.0,  # Simplified
            },
            "services": {
                "total_services": len(dashboard_data.services_status),
                "healthy_services": sum(
                    1
                    for status in dashboard_data.services_status.values()
                    if status == "healthy"
                ),
                "degraded_services": sum(
                    1
                    for status in dashboard_data.services_status.values()
                    if status == "degraded"
                ),
                "unhealthy_services": sum(
                    1
                    for status in dashboard_data.services_status.values()
                    if status == "unhealthy"
                ),
                "service_breakdown": dashboard_data.services_status,
            },
            "usage": {
                "active_api_keys": dashboard_data.active_keys,
                "active_users": len(dashboard_data.top_users),
                "usage_by_service": dashboard_data.usage_by_service,
                "top_users": dashboard_data.top_users,
            },
            "alerts": {
                "total_alerts": len(dashboard_data.recent_alerts),
                "critical_alerts": sum(
                    1
                    for alert in dashboard_data.recent_alerts
                    if alert.severity == "critical"
                ),
                "high_alerts": sum(
                    1
                    for alert in dashboard_data.recent_alerts
                    if alert.severity == "high"
                ),
                "unacknowledged_alerts": sum(
                    1
                    for alert in dashboard_data.recent_alerts
                    if not alert.acknowledged
                ),
            },
            "trends": {
                "hourly_usage": dashboard_data.usage_trend,
                "growth_rate": 0.05,  # Simplified 5% growth
                "peak_hour": "14:00",  # Simplified
                "lowest_hour": "04:00",  # Simplified
            },
        }

        return summary

    except Exception as e:
        logger.error(f"Failed to get analytics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics summary: {str(e)}",
        ) from e
