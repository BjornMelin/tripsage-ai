"""Health check endpoints for the TripSage API.

This module provides endpoints for checking the health and status of the API
and its dependencies using modern dependency injection patterns.
"""

from fastapi import APIRouter

from tripsage.api.core.dependencies import MCPManagerDep, SettingsDep

router = APIRouter()


@router.get("/health")
async def health_check(settings: SettingsDep):
    """Basic health check endpoint.

    Returns:
        Dict with status and application information
    """
    return {
        "status": "healthy",
        "application": "TripSage API",
        "version": "1.0.0",
        "environment": settings.environment,
    }


@router.get("/health/mcp")
async def mcp_health_check(mcp_manager: MCPManagerDep):
    """Check the health of MCP services.

    Returns:
        Dict with MCP status information
    """
    try:
        available_mcps = mcp_manager.get_available_mcps()
        initialized_mcps = mcp_manager.get_initialized_mcps()

        return {
            "status": "healthy",
            "available_mcps": available_mcps,
            "enabled_mcps": initialized_mcps,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "available_mcps": [],
            "enabled_mcps": [],
        }
