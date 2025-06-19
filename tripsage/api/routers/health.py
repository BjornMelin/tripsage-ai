"""Enhanced health check endpoints with external service monitoring.

This module provides comprehensive health check endpoints including:
- Basic application health
- External service health checks (OpenAI, Weather, Google Maps)
- Database connectivity checks
- Cache (DragonflyDB) health
- Detailed readiness checks
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from tripsage.api.core.dependencies import (
    CacheDep,
    DatabaseDep,
    SettingsDep,
    get_all_dependency_health,
    reset_dependency_health,
)
from tripsage_core.services.business.api_key_validator import (
    ApiKeyValidator,
    ServiceHealthCheck,
    ServiceHealthStatus,
    ServiceType,
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
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    environment: str
    components: list[ComponentHealth]
    external_services: dict[str, ServiceHealthCheck] = Field(default_factory=dict)


class ReadinessCheck(BaseModel):
    """Readiness check result."""

    ready: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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

    # 4. External services health (concurrent checks)
    external_services = {}
    try:
        async with ApiKeyValidator() as validator:
            external_health = await validator.check_all_services_health()

            for service_type, health_check in external_health.items():
                external_services[service_type.value] = health_check

                # Add to components list
                component_status = "healthy"
                if health_check.status == ServiceHealthStatus.DEGRADED:
                    component_status = "degraded"
                    overall_status = (
                        "degraded" if overall_status == "healthy" else overall_status
                    )
                elif health_check.status == ServiceHealthStatus.UNHEALTHY:
                    component_status = "unhealthy"
                    overall_status = "unhealthy"

                components.append(
                    ComponentHealth(
                        name=f"external_{service_type.value}",
                        status=component_status,
                        latency_ms=health_check.latency_ms,
                        message=health_check.message,
                        details=health_check.details,
                    )
                )
    except Exception as e:
        logger.error(f"Failed to check external services: {e}")
        overall_status = "degraded"

    return SystemHealth(
        status=overall_status,
        environment=settings.environment,
        components=components,
        external_services=external_services,
    )


@router.get("/health/liveness")
async def liveness_check():
    """Basic liveness check for container orchestration.

    Returns 200 if the application is alive and can respond to requests.
    This endpoint should be lightweight and not check external dependencies.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    except asyncio.TimeoutError:
        checks["database"] = False
        details["database"] = "Database check timed out"
    except Exception as e:
        checks["database"] = False
        details["database"] = f"Database check failed: {str(e)}"

    # Check cache (with timeout)
    try:
        cache_health = await asyncio.wait_for(
            _check_cache_health(cache_service),
            timeout=3.0,
        )
        checks["cache"] = cache_health.status == "healthy"
        if cache_health.status != "healthy":
            details["cache"] = cache_health.message or "Cache not healthy"
    except asyncio.TimeoutError:
        checks["cache"] = False
        details["cache"] = "Cache check timed out"
    except Exception as e:
        checks["cache"] = False
        details["cache"] = f"Cache check failed: {str(e)}"

    # Determine overall readiness
    ready = all(checks.values())

    return ReadinessCheck(
        ready=ready,
        checks=checks,
        details=details,
    )


@router.get("/health/services/{service_type}")
async def check_specific_service_health(
    service_type: ServiceType,
    response: Response,
):
    """Check health of a specific external service.

    Args:
        service_type: The service to check (openai, weather, googlemaps)
        response: FastAPI response object for setting status codes

    Returns:
        Detailed health check result for the specified service
    """
    try:
        async with ApiKeyValidator() as validator:
            health_check = await validator.check_service_health(service_type)

            # Set appropriate HTTP status based on health
            if health_check.status == ServiceHealthStatus.UNHEALTHY:
                response.status_code = 503  # Service Unavailable
            elif health_check.status == ServiceHealthStatus.DEGRADED:
                response.status_code = 200  # OK but degraded

            return health_check

    except Exception as e:
        logger.error(f"Service health check failed: {e}")
        response.status_code = 500

        return ServiceHealthCheck(
            service=service_type,
            status=ServiceHealthStatus.UNKNOWN,
            latency_ms=0,
            message=f"Health check error: {str(e)}",
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
    start_time = datetime.now(timezone.utc)

    try:
        # Perform a simple query to check connectivity
        result = await db_service.execute_query("SELECT 1 as health_check")

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

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
        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return ComponentHealth(
            name="database",
            status="unhealthy",
            latency_ms=latency_ms,
            message=f"Database error: {str(e)}",
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

    start_time = datetime.now(timezone.utc)

    try:
        # Perform a simple ping
        result = await cache_service.ping()

        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

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
        latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        return ComponentHealth(
            name="cache",
            status="unhealthy",
            latency_ms=latency_ms,
            message=f"Cache error: {str(e)}",
            details={"error": str(e)},
        )


@router.get("/health/dependencies")
async def dependency_health_check():
    """Get health status of all dependency services.

    Returns comprehensive health information for all tracked dependencies
    including response times, error counts, and circuit breaker states.
    """
    dependency_health = get_all_dependency_health()

    overall_status = "healthy"
    for health in dependency_health.values():
        if not health.healthy:
            overall_status = "unhealthy"
            break
        elif health.response_time_ms > 1000:  # Slow response threshold
            overall_status = "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": dependency_health,
        "summary": {
            "total_dependencies": len(dependency_health),
            "healthy_dependencies": sum(
                1 for h in dependency_health.values() if h.healthy
            ),
            "unhealthy_dependencies": sum(
                1 for h in dependency_health.values() if not h.healthy
            ),
        },
    }


@router.post("/health/dependencies/reset")
async def reset_dependency_health_monitoring():
    """Reset dependency health monitoring (useful for tests and debugging).

    This endpoint clears all health tracking data and circuit breaker states.
    Use with caution in production environments.
    """
    reset_dependency_health()
    return {
        "message": "Dependency health monitoring reset successfully",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/dependencies/{dependency_name}")
async def get_specific_dependency_health(dependency_name: str):
    """Get health status for a specific dependency.

    Args:
        dependency_name: Name of the dependency to check

    Returns:
        Detailed health information for the specified dependency
    """
    from fastapi.responses import JSONResponse

    dependency_health = get_all_dependency_health()

    if dependency_name not in dependency_health:
        return JSONResponse(
            status_code=404,
            content={
                "error": True,
                "message": f"Dependency '{dependency_name}' not found",
                "available_dependencies": list(dependency_health.keys()),
            },
        )

    health = dependency_health[dependency_name]
    return {
        "dependency": dependency_name,
        "health": health,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
