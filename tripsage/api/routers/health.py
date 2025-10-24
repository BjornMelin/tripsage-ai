"""Health check endpoints for TripSage API.

This module provides health check endpoints including:
- Basic application health
- Database connectivity checks
- Cache (DragonflyDB) health
- Detailed readiness checks
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, Request, Response

from tripsage.api.core.dependencies import CacheDep, DatabaseDep, SettingsDep
from tripsage.api.limiting import limiter
from tripsage.api.schemas.health import (
    ComponentHealth,
    ReadinessCheck,
    SystemHealth,
)
from tripsage_core.observability.otel import (
    http_route_attr_fn,
    record_histogram,
    trace_span,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=SystemHealth)
@limiter.exempt
@trace_span(name="api.health")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def comprehensive_health_check(
    request: Request,
    response: Response,
    settings: SettingsDep,
    db_service: DatabaseDep,
    cache_service: CacheDep,
):
    """Comprehensive health check endpoint with all components.

    Returns detailed health status of the application and all its dependencies.
    """
    components = []
    overall_status = "healthy"

    # 1. Application health
    components.append(
        ComponentHealth(
            name="application",
            status="healthy",
            message="TripSage API is running",
        )
    )

    # 2. Database health via central monitor if available
    monitor = getattr(request.app.state, "database_monitor", None)  # type: ignore[attr-defined]
    if monitor is not None:
        snapshot = monitor.get_current_health()
        if snapshot is None:
            await monitor.check_now()
            snapshot = monitor.get_current_health()
        latency_ms = (snapshot.latency_s * 1000) if snapshot else None
        db_status = snapshot.status.value if snapshot else "unhealthy"
        db_health = ComponentHealth(
            name="database",
            status=db_status,
            latency_ms=latency_ms,
            message=(
                "Database is responsive"
                if db_status == "healthy"
                else "Database not healthy"
            ),
            details=(snapshot.details if snapshot else {}),
        )
    else:
        # Fallback to direct service probe
        ok = await db_service.health_check()
        db_health = ComponentHealth(
            name="database",
            status="healthy" if ok else "unhealthy",
            latency_ms=None,
            message=("Database is responsive" if ok else "Database not healthy"),
            details={},
        )
    components.append(db_health)
    if db_health.status != "healthy":
        overall_status = "degraded" if overall_status == "healthy" else overall_status

    # 3. Cache health
    ok_cache = True
    try:
        ok_cache = await cache_service.health_check() if cache_service else True
    except Exception as e:  # noqa: BLE001
        ok_cache = False
        logger.warning("Cache health check failed: %s", e)
    cache_health = ComponentHealth(
        name="cache",
        status="healthy" if ok_cache else "unhealthy",
        latency_ms=None,
        message=("Cache is responsive" if ok_cache else "Cache not healthy"),
        details={},
    )
    components.append(cache_health)
    if cache_health.status != "healthy" and overall_status == "healthy":
        overall_status = "degraded"

    return SystemHealth(
        status=overall_status,
        environment=settings.environment,
        components=components,
    )


@router.get("/health/liveness")
@limiter.exempt
@trace_span(name="api.health.liveness")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def liveness_check(request: Request, response: Response):
    """Basic liveness check for container orchestration.

    Returns 200 if the application is alive and can respond to requests.
    This endpoint should be lightweight and not check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/readiness", response_model=ReadinessCheck)
@limiter.exempt
@trace_span(name="api.health.readiness")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def readiness_check(
    request: Request,
    response: Response,
    db_service: DatabaseDep,
    cache_service: CacheDep,
):
    """Readiness check for container orchestration.

    Returns whether the application is ready to serve traffic.
    Checks critical dependencies but with shorter timeouts.
    """
    checks = {}
    details = {}

    # Check database (with timeout) via monitor or direct probe
    try:

        async def _db_probe() -> ComponentHealth:
            mon = getattr(request.app.state, "database_monitor", None)  # type: ignore[attr-defined]
            if mon is not None:
                snap = mon.get_current_health() or await mon.check_now()
                st = snap.status.value if snap else "unhealthy"
                return ComponentHealth(
                    name="database",
                    status=st,
                    latency_ms=(snap.latency_s * 1000) if snap else None,
                    message=(
                        "Database is responsive"
                        if st == "healthy"
                        else "Database not healthy"
                    ),
                )
            ok = await db_service.health_check()
            return ComponentHealth(
                name="database",
                status="healthy" if ok else "unhealthy",
                message=("Database is responsive" if ok else "Database not healthy"),
            )

        db_health = await asyncio.wait_for(_db_probe(), timeout=5.0)
        checks["database"] = db_health.status == "healthy"
        if db_health.status != "healthy":
            details["database"] = db_health.message or "Database not healthy"
    except TimeoutError:
        checks["database"] = False
        details["database"] = "Database check timed out"
    except Exception as e:  # noqa: BLE001
        checks["database"] = False
        details["database"] = f"Database check failed: {e!s}"

    # Check cache (with timeout)
    try:

        async def _cache_probe() -> ComponentHealth:
            ok = await cache_service.health_check() if cache_service else True
            return ComponentHealth(
                name="cache",
                status="healthy" if ok else "unhealthy",
                message=("Cache is responsive" if ok else "Cache not healthy"),
            )

        cache_health = await asyncio.wait_for(_cache_probe(), timeout=3.0)
        checks["cache"] = cache_health.status == "healthy"
        if cache_health.status != "healthy":
            details["cache"] = cache_health.message or "Cache not healthy"
    except TimeoutError:
        checks["cache"] = False
        details["cache"] = "Cache check timed out"
    except Exception as e:  # noqa: BLE001
        checks["cache"] = False
        details["cache"] = f"Cache check failed: {e!s}"

    # Determine overall readiness
    ready = all(checks.values())
    return ReadinessCheck(
        ready=ready,
        checks=checks,
        details=details,
    )


@router.get("/health/database")
@trace_span(name="api.health.database")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def database_health_check(request: Request, db_service: DatabaseDep):
    """Detailed database health check.

    Returns database health information including:
    - Connection status
    - Query performance
    - Connection pool stats
    """
    ok = await db_service.health_check()
    health = ComponentHealth(
        name="database",
        status="healthy" if ok else "unhealthy",
        message=("Database is responsive" if ok else "Database not healthy"),
    )

    # Add more detailed database metrics if available
    try:
        get_stats = getattr(db_service, "get_pool_stats", None)
        if callable(get_stats):
            _maybe = get_stats()  # type: ignore[no-any-return]
            if asyncio.iscoroutine(_maybe):
                pool_stats = await _maybe
            else:
                pool_stats = _maybe
            if isinstance(pool_stats, dict):
                # Assign to avoid pylint misdetection of Pydantic FieldInfo
                current = dict(health.details or {})
                current.update(pool_stats)
                health.details = current
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to get pool stats: %s", e)

    return health


@router.get("/health/cache")
@trace_span(name="api.health.cache")
@record_histogram("api.op.duration", unit="s", attr_fn=http_route_attr_fn)
async def cache_health_check(request: Request, cache_service: CacheDep):
    """Detailed cache (DragonflyDB) health check.

    Returns cache health information including:
    - Connection status
    - Memory usage
    - Key statistics
    """
    ok = await cache_service.health_check() if cache_service else True
    health = ComponentHealth(
        name="cache",
        status="healthy" if ok else "unhealthy",
        message=("Cache is responsive" if ok else "Cache not healthy"),
    )

    # Add more detailed cache metrics if available
    if hasattr(cache_service, "info"):
        try:
            info = await cast(Any, cache_service).info()
            current = dict(health.details or {})
            current.update(
                {
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                }
            )
            health.details = current
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to get cache info: %s", e)

    return health


# Internal helper functions removed; database health sourced from monitor,
# cache health via service.health_check().


@router.get("/health/ratelimit", response_model=dict)
@limiter.exempt
async def ratelimit_status(request: Request, response: Response):
    """Show current rate-limiting backend information (operators)."""
    lim = getattr(request.app.state, "limiter", None)
    if lim is None:
        return {"enabled": False}
    return {
        "enabled": True,
        "storage_uri": getattr(lim, "storage_uri", "unknown"),
        "storage_options": getattr(lim, "storage_options", {}),
        "headers_enabled": getattr(lim, "headers_enabled", False),
        "default_limits": getattr(lim, "default_limits", []),
    }
