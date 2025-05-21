"""Health check endpoints for the TripSage API.

This module provides endpoints for checking the health and status of the API
and its dependencies.
"""

from fastapi import APIRouter

from tripsage.api.core.dependencies import get_settings_dependency
from tripsage.mcp_abstraction import mcp_manager

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint.

    Returns:
        Dict with status and application information
    """
    settings = get_settings_dependency()

    return {
        "status": "ok",
        "application": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }


@router.get("/health/mcp")
async def mcp_health_check():
    """Check the health of MCP services.

    Returns:
        Dict with MCP status information
    """
    available_mcps = mcp_manager.get_available_mcps()
    initialized_mcps = mcp_manager.get_initialized_mcps()

    return {
        "status": "ok",
        "available_mcps": available_mcps,
        "enabled_mcps": initialized_mcps,  # Use initialized MCPs instead of enabled
    }
