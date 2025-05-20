"""Health check endpoints for the TripSage API.

This module provides endpoints for checking the health and status of the API
and its dependencies.
"""

from fastapi import APIRouter, Depends

from tripsage.api.core.config import Settings, get_settings
from tripsage.mcp_abstraction import get_mcp_manager

router = APIRouter()


@router.get("/health")
async def health_check(settings: Settings = Depends(get_settings)):
    """Basic health check endpoint.
    
    Returns:
        Dict with status and application information
    """
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
    mcp_manager = get_mcp_manager()
    available_mcps = mcp_manager.get_available_mcps()
    enabled_mcps = mcp_manager.get_enabled_mcps()
    
    return {
        "status": "ok",
        "available_mcps": available_mcps,
        "enabled_mcps": enabled_mcps,
    }