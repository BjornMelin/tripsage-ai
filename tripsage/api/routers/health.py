"""Health check endpoints for the TripSage API.

This module provides endpoints for checking the health and status of the API
and its dependencies.
"""

from fastapi import APIRouter

from tripsage_core.services.simple_mcp_service import mcp_manager

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint.

    Returns:
        Dict with status and application information
    """
    return {
        "status": "ok",
        "application": "TripSage API",
        "version": "1.0.0",
        "environment": "development",
    }


@router.get("/health/mcp")
async def mcp_health_check():
    """Check the health of MCP services.

    Returns:
        Dict with MCP status information
    """
    try:
        available_mcps = mcp_manager.get_available_mcps()
        initialized_mcps = mcp_manager.get_initialized_mcps()

        return {
            "status": "ok",
            "available_mcps": available_mcps,
            "enabled_mcps": initialized_mcps,  # Use initialized MCPs instead of enabled
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "available_mcps": [],
            "enabled_mcps": [],
        }
