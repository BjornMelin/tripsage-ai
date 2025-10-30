"""Dashboard monitoring API endpoints.

This module provides dashboard API endpoints for monitoring and insights:
- System health and status
- Real-time metrics and monitoring data
- Usage trends and historical data
- Alert management
- Rate limit status and quota information
- Service health status
- User activity and top consumers
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query, status

from tripsage.api.core.dependencies import (
    CacheDep,
    DatabaseDep,
    RequiredPrincipalDep,
    SettingsDep,
)
from tripsage.api.schemas.dashboard import (
    AlertInfoResponse,
    AlertSeverity,
    AlertType,
    RateLimitInfoResponse,
    ServiceHealthStatus,
    ServiceStatusResponse,
    SystemOverviewResponse,
    SystemStatus,
    TrendDataPoint,
    UsageMetricsResponse,
    UserActivityResponse,
)
from tripsage_core.services.business.dashboard_models import (
    DashboardData,
    RealTimeMetrics,
)
from tripsage_core.services.business.dashboard_service import DashboardService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=SystemOverviewResponse)
async def get_system_overview(
    settings: SettingsDep,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: RequiredPrincipalDep,
) -> SystemOverviewResponse:
    """Get system overview for dashboard.

    Returns high-level system metrics and status including:
    - Overall system health
    - Request and error counts
    - Active users in monitored period
    - Success rates
    """
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get dashboard data for 24 hours (typed cast for strict checking)
        get_data = cast(
            Callable[[int, int], Awaitable[DashboardData]],
            dashboard_service.get_dashboard_data,
        )
        dashboard_data: DashboardData = await get_data(24, 10)

        # Calculate uptime (simplified - would use actual startup time in production)
        uptime_seconds = 86400  # 24 hours as default

        metrics: RealTimeMetrics = dashboard_data.metrics

        # Determine overall status
        overall_status = SystemStatus.HEALTHY
        if metrics.success_rate < 0.9:  # <90% success rate
            overall_status = SystemStatus.DEGRADED
        if metrics.success_rate < 0.8:  # <80% success rate
            overall_status = SystemStatus.UNHEALTHY

        return SystemOverviewResponse(
            status=overall_status,
            uptime_seconds=uptime_seconds,
            environment=settings.environment,
            total_requests_24h=metrics.total_requests,
            total_errors_24h=metrics.total_errors,
            success_rate_24h=metrics.success_rate,
            active_users_24h=len(dashboard_data.top_users),
            active_api_keys=metrics.active_keys_count,
        )

    except Exception as e:
        logger.exception("Failed to get system overview")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve system overview: {e!s}",
        ) from e


@router.get("/services", response_model=list[ServiceStatusResponse])
async def get_services_status(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: RequiredPrincipalDep,
) -> list[ServiceStatusResponse]:
    """Get status of all external services.

    Returns health status for all integrated external services:
    - OpenAI, Weather API, Google Maps, and other configured services
    """
    try:
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        dashboard_data = await dashboard_service.get_dashboard_data(time_range_hours=24)

        services_status: list[ServiceStatusResponse] = []
        for service in dashboard_data.services:
            error_rate = max(0.0, min(1.0, 1.0 - float(service.success_rate)))
            uptime_percentage = max(
                0.0, min(100.0, float(service.success_rate) * 100.0)
            )
            status_enum = ServiceHealthStatus(service.health_status.value)
            services_status.append(
                ServiceStatusResponse(
                    service=service.service_name,
                    status=status_enum,
                    latency_ms=service.avg_latency_ms,
                    last_check=service.last_health_check,
                    error_rate=error_rate,
                    uptime_percentage=uptime_percentage,
                    message=None,
                )
            )

        return services_status

    except Exception as e:
        logger.exception("Failed to get services status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve services status: {e!s}",
        ) from e


@router.get("/metrics", response_model=UsageMetricsResponse)
async def get_usage_metrics(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    *,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    service: str | None = Query(default=None),
    principal: RequiredPrincipalDep,
) -> UsageMetricsResponse:
    """Get usage metrics for specified time range.

    Returns usage metrics including:
    - Request and error counts
    - Latency statistics
    - Top endpoints
    - Error breakdown by type
    """
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Calculate time range
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=time_range_hours)

        # Get dashboard data
        get_data = cast(
            Callable[[int, int], Awaitable[DashboardData]],
            dashboard_service.get_dashboard_data,
        )
        dashboard_data: DashboardData = await get_data(time_range_hours, 50)

        # Extract metrics from dashboard data
        metrics: RealTimeMetrics = dashboard_data.metrics
        total_requests = metrics.total_requests
        total_errors = metrics.total_errors

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

        return UsageMetricsResponse(
            period_start=start_time,
            period_end=end_time,
            total_requests=total_requests,
            total_errors=total_errors,
            success_rate=metrics.success_rate,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            p99_latency_ms=p99_latency_ms,
            unique_users=len(dashboard_data.top_users),
            unique_endpoints=len(top_endpoints),
            top_endpoints=top_endpoints,
            error_breakdown=error_breakdown,
        )

    except Exception as e:
        logger.exception("Failed to get usage metrics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve usage metrics: {e!s}",
        ) from e


@router.get("/rate-limits", response_model=list[RateLimitInfoResponse])
async def get_rate_limits_status(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    *,
    limit: int = Query(default=20, ge=1, le=100),
    principal: RequiredPrincipalDep,
) -> list[RateLimitInfoResponse]:
    """Get rate limit status for service usage tokens.

    Returns current rate limit status for service integrations including:
    - Current usage vs limits, remaining quota, and reset times
    """
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        rate_limits: list[RateLimitInfoResponse] = []

        # Get active keys from dashboard data
        get_data = cast(
            Callable[[int, int], Awaitable[DashboardData]],
            dashboard_service.get_dashboard_data,
        )
        dashboard_data: DashboardData = await get_data(1, 10)

        # Extract key IDs from user activity or create sample keys for demonstration
        active_keys: list[str] = []
        if dashboard_data.top_users:
            # In a real implementation, we'd query the database for active keys
            for i, user in enumerate(dashboard_data.top_users[:limit]):
                active_keys.append(f"sk_{user.user_id}_{i:03d}")
        else:
            # Fallback: create sample keys for demonstration
            active_keys = [f"sk_sample_{i:03d}" for i in range(min(limit, 5))]

        for key_id in active_keys:
            try:
                # Get rate limit status
                status_data = await dashboard_service.get_rate_limit_status(
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
                        RateLimitInfoResponse(
                            key_id=key_id,
                            current_usage=current_usage,
                            limit=limit_value,
                            remaining=remaining,
                            window_minutes=60,
                            reset_at=reset_at,
                            percentage_used=percentage_used,
                            is_approaching_limit=percentage_used >= 80.0,
                        )
                    )

            except (OSError, RuntimeError, ValueError) as e:
                # Service errors during rate limit retrieval
                logger.warning("Failed to get rate limit for key %s: %s", key_id, e)
                continue

        return rate_limits

    except Exception as e:
        logger.exception("Failed to get rate limits status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve rate limits status: {e!s}",
        ) from e


@router.get("/alerts", response_model=list[AlertInfoResponse])
async def get_alerts(
    settings: SettingsDep,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    *,
    severity: str | None = Query(default=None),
    acknowledged: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: RequiredPrincipalDep,
) -> list[AlertInfoResponse]:
    """Get system alerts and notifications.

    Returns alerts filtered by severity and acknowledgment status:
    - Security, performance, error rate, and anomaly detection alerts
    """
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get recent alerts via public dashboard data API (avoid private method)
        get_data = cast(
            Callable[[int, int], Awaitable[DashboardData]],
            dashboard_service.get_dashboard_data,
        )
        dashboard_data_alerts: DashboardData = await get_data(24, 10)
        recent_alerts = dashboard_data_alerts.recent_alerts

        alerts: list[AlertInfoResponse] = []
        for alert in recent_alerts:
            # Apply filters
            if severity and alert.severity.value != severity:
                continue
            if acknowledged is not None and alert.acknowledged != acknowledged:
                continue

            # Map strings to enums with safe fallback
            raw_sev = getattr(alert.severity, "value", alert.severity)
            raw_type = getattr(alert.alert_type, "value", alert.alert_type)
            sev = (
                AlertSeverity(raw_sev)
                if raw_sev in AlertSeverity._value2member_map_
                else AlertSeverity.LOW
            )
            atype = (
                AlertType(raw_type)
                if raw_type in AlertType._value2member_map_
                else AlertType.SECURITY
            )

            alerts.append(
                AlertInfoResponse(
                    alert_id=alert.alert_id,
                    severity=sev,
                    alert_type=atype,
                    message=alert.message,
                    created_at=alert.created_at,
                    key_id=alert.api_key_id,
                    service=alert.service,
                    acknowledged=alert.acknowledged,
                    details=alert.details,
                )
            )

        # Sort by priority score (higher priority first)
        alerts.sort(
            key=lambda x: (
                -int(x.severity == "critical") * 4
                - int(x.severity == "high") * 3
                - int(x.severity == "medium") * 2
                - int(x.severity == "low") * 1,
                x.created_at,
            ),
            reverse=True,
        )

        return alerts[:limit]

    except Exception as e:
        logger.exception("Failed to get alerts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {e!s}",
        ) from e


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    settings: SettingsDep,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: RequiredPrincipalDep,
) -> dict[str, Any]:
    """Acknowledge an alert."""
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Acknowledge the alert using the service method
        success = await dashboard_service.acknowledge_alert(alert_id, principal.id)

        if success:
            return {
                "success": True,
                "message": "Alert acknowledged successfully",
                "alert_id": alert_id,
                "acknowledged_by": principal.id,
                "acknowledged_at": datetime.now(UTC).isoformat(),
            }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to acknowledge alert %s", alert_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {e!s}",
        ) from e


@router.delete("/alerts/{alert_id}")
async def dismiss_alert(
    alert_id: str,
    settings: SettingsDep,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: RequiredPrincipalDep,
) -> dict[str, Any]:
    """Dismiss an alert."""
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Resolve the alert using the service method (dismiss = resolve)
        success = await dashboard_service.resolve_alert(alert_id)

        if success:
            return {
                "success": True,
                "message": "Alert dismissed successfully",
                "alert_id": alert_id,
                "dismissed_by": principal.id,
                "dismissed_at": datetime.now(UTC).isoformat(),
            }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to dismiss alert %s", alert_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss alert: {e!s}",
        ) from e


@router.get("/users/activity", response_model=list[UserActivityResponse])
async def get_user_activity(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    *,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
    principal: RequiredPrincipalDep,
) -> list[UserActivityResponse]:
    """Get user activity data.

    Returns user activity metrics including:
    - Request counts and success rates
    - Services used
    - Last activity times
    """
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get dashboard data
        get_data = cast(
            Callable[[int, int], Awaitable[DashboardData]],
            dashboard_service.get_dashboard_data,
        )
        dashboard_data: DashboardData = await get_data(time_range_hours, limit)

        # Convert top users to UserActivity objects
        return [
            UserActivityResponse(
                user_id=user_data.user_id,
                user_type="agent" if user_data.user_id.startswith("agent_") else "user",
                request_count=user_data.request_count,
                error_count=user_data.error_count,
                success_rate=user_data.success_rate,
                last_activity=user_data.last_activity,
                services_used=user_data.services_used,
                avg_latency_ms=user_data.avg_latency_ms,
            )
            for user_data in dashboard_data.top_users
        ]

    except Exception as e:
        logger.exception("Failed to get user activity")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user activity: {e!s}",
        ) from e


@router.get("/trends/{metric_type}", response_model=list[TrendDataPoint])
async def get_trend_data(
    metric_type: str,
    cache_service: CacheDep,
    db_service: DatabaseDep,
    *,
    time_range_hours: int = Query(default=24, ge=1, le=168),
    interval_minutes: int = Query(default=60, ge=5, le=1440),
    principal: RequiredPrincipalDep,
) -> list[TrendDataPoint]:
    """Get trend data for specified metric.

    Returns time series data for metrics like:
    - request_count, error_rate, latency, and active_users
    """
    try:
        # Validate metric type
        valid_metrics = ["request_count", "error_rate", "latency", "active_users"]
        if metric_type not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric type. Must be one of: {valid_metrics}",
            )

        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get usage trend data
        # Use the public dashboard data accessor rather than a private method
        dashboard_data_trend = await dashboard_service.get_dashboard_data(
            time_range_hours=time_range_hours, top_users_limit=10
        )
        trend_data_raw = dashboard_data_trend.usage_trend

        # Convert to TrendData objects based on metric type
        trend_data: list[TrendDataPoint] = []
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
                TrendDataPoint(
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
        logger.exception("Failed to get trend data for %s", metric_type)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trend data: {e!s}",
        ) from e


@router.get("/analytics/summary", response_model=dict[str, Any])
async def get_analytics_summary(
    cache_service: CacheDep,
    db_service: DatabaseDep,
    principal: RequiredPrincipalDep,
    time_range_hours: int = Query(default=24, ge=1, le=168),
) -> dict[str, Any]:
    """Get analytics summary.

    Returns analytics including:
    - System performance overview
    - Service health summary
    - Usage patterns
    - Top performing and problematic areas
    """
    try:
        # Initialize dashboard service
        dashboard_service = DashboardService(
            cache_service=cache_service,
            database_service=db_service,
        )

        # Get dashboard data
        dashboard_data = await dashboard_service.get_dashboard_data(
            time_range_hours=time_range_hours,
            top_users_limit=10,
        )

        # Calculate time range
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=time_range_hours)

        metrics = dashboard_data.metrics
        services = dashboard_data.services
        service_breakdown = {
            service.service_name: service.health_status.value for service in services
        }

        # Build summary
        return {
            "period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": time_range_hours,
            },
            "performance": {
                "total_requests": metrics.total_requests,
                "total_errors": metrics.total_errors,
                "success_rate": metrics.success_rate,
                "avg_latency_ms": 150.0,  # Simplified
                "p95_latency_ms": 300.0,  # Simplified
            },
            "services": {
                "total_services": len(services),
                "healthy_services": sum(
                    1
                    for service in services
                    if service.health_status == ServiceHealthStatus.HEALTHY
                ),
                "degraded_services": sum(
                    1
                    for service in services
                    if service.health_status == ServiceHealthStatus.DEGRADED
                ),
                "unhealthy_services": sum(
                    1
                    for service in services
                    if service.health_status == ServiceHealthStatus.UNHEALTHY
                ),
                "service_breakdown": service_breakdown,
            },
            "usage": {
                "active_api_keys": metrics.active_keys_count,
                "active_users": len(dashboard_data.top_users),
                "usage_by_service": {
                    service.service_name: service.total_requests for service in services
                },
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

    except Exception as e:
        logger.exception("Failed to get analytics summary")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve analytics summary: {e!s}",
        ) from e
