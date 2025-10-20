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

from fastapi import APIRouter
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    CacheDep,
    DatabaseDep,
    SettingsDep,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class ComponentHealth(BaseModel):
    """Health status of a system component."""

    name: str
    status: str  # healthy, degraded, unhealthy
    latency_ms: float | None = None
    message: str | None = None
    details: dict = Field(default_factory=dict)


class SystemHealth(BaseModel):
    """Overall system health status."""

    status: str  # healthy, degraded, unhealthy
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0.0"
    environment: str
    components: list[ComponentHealth]


class ReadinessCheck(BaseModel):
    """Readiness check result."""

    ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    checks: dict[str, bool]
    details: dict[str, str] = Field(default_factory=dict)


@router.get("/health", response_model=SystemHealth)
async def comprehensive_health_check(
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

    # 2. Database health
    db_health = await _check_database_health(db_service)
    components.append(db_health)
    if db_health.status != "healthy":
        overall_status = "degraded" if overall_status == "healthy" else overall_status

    # 3. Cache health
    cache_health = await _check_cache_health(cache_service)
    components.append(cache_health)
    if cache_health.status != "healthy":
        overall_status = "degraded" if overall_status == "healthy" else overall_status

    return SystemHealth(
        status=overall_status,
        environment=settings.environment,
        components=components,
    )


@router.get("/health/liveness")
async def liveness_check():
    """Basic liveness check for container orchestration.

    Returns 200 if the application is alive and can respond to requests.
    This endpoint should be lightweight and not check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/readiness", response_model=ReadinessCheck)
async def readiness_check(
    db_service: DatabaseDep,
    cache_service: CacheDep,
):
    """Readiness check for container orchestration.

    Returns whether the application is ready to serve traffic.
    Checks critical dependencies but with shorter timeouts.
    """
    checks = {}
    details = {}

    # Check database (with timeout)
    try:
        db_health = await asyncio.wait_for(
            _check_database_health(db_service),
            timeout=5.0,
        )
        checks["database"] = db_health.status == "healthy"
        if db_health.status != "healthy":
            details["database"] = db_health.message or "Database not healthy"
    except TimeoutError:
        checks["database"] = False
        details["database"] = "Database check timed out"
    except Exception as e:
        checks["database"] = False
        details["database"] = f"Database check failed: {e!s}"

    # Check cache (with timeout)
    try:
        cache_health = await asyncio.wait_for(
            _check_cache_health(cache_service),
            timeout=3.0,
        )
        checks["cache"] = cache_health.status == "healthy"
        if cache_health.status != "healthy":
            details["cache"] = cache_health.message or "Cache not healthy"
    except TimeoutError:
        checks["cache"] = False
        details["cache"] = "Cache check timed out"
    except Exception as e:
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
async def database_health_check(db_service: DatabaseDep):
    """Detailed database health check.

    Returns comprehensive database health information including:
    - Connection status
    - Query performance
    - Connection pool stats
    """
    health = await _check_database_health(db_service)

    # Add more detailed database metrics if available
    if hasattr(db_service, "get_pool_stats"):
        try:
            pool_stats = await db_service.get_pool_stats()
            health.details.update(pool_stats)
        except Exception as e:
            logger.warning(f"Failed to get pool stats: {e}")

    return health


@router.get("/health/cache")
async def cache_health_check(cache_service: CacheDep):
    """Detailed cache (DragonflyDB) health check.

    Returns comprehensive cache health information including:
    - Connection status
    - Memory usage
    - Key statistics
    """
    health = await _check_cache_health(cache_service)

    # Add more detailed cache metrics if available
    if hasattr(cache_service, "info"):
        try:
            info = await cache_service.info()
            health.details.update(
                {
                    "used_memory": info.get("used_memory_human"),
                    "connected_clients": info.get("connected_clients"),
                    "total_commands_processed": info.get("total_commands_processed"),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to get cache info: {e}")

    return health


async def _check_database_health(db_service) -> ComponentHealth:
    """Check database health and connectivity."""
    start_time = datetime.now(UTC)

    try:
        # Perform a simple query to check connectivity
        result = await db_service.execute_query("SELECT 1 as health_check")

        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        if result:
            return ComponentHealth(
                name="database",
                status="healthy",
                latency_ms=latency_ms,
                message="Database is responsive",
                details={"query_result": result},
            )
        else:
            return ComponentHealth(
                name="database",
                status="unhealthy",
                latency_ms=latency_ms,
                message="Database query returned no results",
            )

    except Exception as e:
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return ComponentHealth(
            name="database",
            status="unhealthy",
            latency_ms=latency_ms,
            message=f"Database error: {e!s}",
            details={"error": str(e)},
        )


async def _check_cache_health(cache_service) -> ComponentHealth:
    """Check cache (DragonflyDB) health and connectivity."""
    if not cache_service:
        return ComponentHealth(
            name="cache",
            status="healthy",
            message="Cache not configured (optional component)",
        )

    start_time = datetime.now(UTC)

    try:
        # Perform a simple ping
        result = await cache_service.ping()

        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        if result:
            return ComponentHealth(
                name="cache",
                status="healthy",
                latency_ms=latency_ms,
                message="Cache is responsive",
            )
        else:
            return ComponentHealth(
                name="cache",
                status="unhealthy",
                latency_ms=latency_ms,
                message="Cache ping failed",
            )

    except Exception as e:
        latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

        return ComponentHealth(
            name="cache",
            status="unhealthy",
            latency_ms=latency_ms,
            message=f"Cache error: {e!s}",
            details={"error": str(e)},
        )
