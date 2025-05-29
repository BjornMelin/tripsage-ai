"""
Dependency injection for TripSage API.

This module centralizes all FastAPI dependencies for the TripSage API.
"""

from typing import Optional

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer

from api.core.config import settings
from api.core.exceptions import AuthenticationError
from tripsage.mcp_abstraction import MCPManager, mcp_manager
from tripsage.utils.session_memory import SessionMemory
from tripsage_core.services.infrastructure import get_cache_service

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", auto_error=False)

# API key authentication setup
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


# MCP Manager dependency
def get_mcp_manager_dep() -> MCPManager:
    """Get the MCP manager instance as a dependency.

    Returns:
        The singleton MCP manager instance
    """
    return mcp_manager


# Session memory dependency
async def get_session_memory(request: Request) -> SessionMemory:
    """Get the session memory for the current request.

    Args:
        request: The current FastAPI request

    Returns:
        SessionMemory instance for the current session
    """
    if not hasattr(request.state, "session_memory"):
        # Create or get a session memory instance for this request
        session_id = request.cookies.get("session_id", None)

        if not session_id:
            # Generate a new session ID if it doesn't exist
            from uuid import uuid4

            session_id = str(uuid4())

        # Initialize session memory
        request.state.session_memory = SessionMemory(session_id=session_id)

    return request.state.session_memory


# Authentication dependencies
async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key_header: Optional[str] = Security(api_key_header),
    api_key_query: Optional[str] = Security(api_key_query),
):
    """Get the current user if authenticated, otherwise return None.

    Args:
        token: OAuth2 token
        api_key_header: API key from header
        api_key_query: API key from query parameter

    Returns:
        User object if authenticated, None otherwise
    """
    # First check API key (from header or query)
    api_key = api_key_header or api_key_query

    if api_key:
        # Validate API key
        # This is a simplified implementation - in a real system,
        # you'd verify the key against a database
        if api_key.startswith("tripsage_"):
            # Get user info associated with this API key
            # This is just a placeholder - implement your actual logic
            return {
                "id": "api_user",
                "username": "api_user",
                "is_api": True,
                "api_key": api_key,
            }

    # If no API key, check OAuth2 token
    if token:
        try:
            # Validate JWT token and get user info
            # This is a simplified implementation
            # In a real system, you'd verify the JWT signature and extract claims
            import jwt

            payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])

            return {
                "id": payload["sub"],
                "username": payload["username"],
                "is_api": False,
            }
        except Exception:
            # Invalid token - return None for optional auth
            return None

    # No authentication provided
    return None


async def get_current_user():
    """Get the current authenticated user or raise an error.

    Returns:
        User object if authenticated

    Raises:
        AuthenticationError: If no user is authenticated
    """
    user = await get_current_user_optional()
    if user is None:
        raise AuthenticationError(message="Not authenticated")
    return user


# Module-level dependency singletons to avoid B008 linting errors
get_current_user_dep = Depends(get_current_user)


async def verify_api_key(
    current_user: dict = get_current_user_dep,
) -> bool:
    """Verify that the user has a valid API key for chat functionality.

    For now, this is a simplified check. In a full implementation,
    this would validate specific service keys (like OpenAI) from the database.

    Args:
        current_user: Current authenticated user

    Returns:
        True if user has valid API keys

    Raises:
        AuthenticationError: If no valid API key is found
    """
    # In a real implementation, you would:
    # 1. Query the database for the user's API keys
    # 2. Validate the keys against the respective services
    # 3. Return the validation status

    # For now, we'll assume authenticated users have valid keys
    # This will be enhanced when the full BYOK system is integrated
    return True


# Accommodations MCP dependency (only remaining MCP service)
def get_accommodations_mcp_dep():
    """Get the accommodations MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_accommodations_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("accommodations")

    return _get_accommodations_mcp


# Direct service dependencies (using comprehensive API implementations)
async def get_webcrawl_service():
    """Get the direct WebCrawl service."""
    from tripsage_core.services.external_apis.webcrawl_service import WebCrawlService

    return WebCrawlService()


async def get_memory_service():
    """Get the direct Memory service (Mem0)."""
    from tripsage.services.memory_service import TripSageMemoryService

    return TripSageMemoryService()


async def get_dragonfly_service():
    """Get the DragonflyDB cache service."""
    return await get_cache_service()


async def get_google_maps_service():
    """Get the direct Google Maps service."""
    from tripsage_core.services.external_apis.google_maps_service import (
        GoogleMapsService,
    )

    return GoogleMapsService()


async def get_playwright_service():
    """Get the direct Playwright service for complex web scraping."""
    from tripsage_core.services.external_apis.playwright_service import (
        PlaywrightService,
    )

    return PlaywrightService()


async def get_weather_service():
    """Get the comprehensive OpenWeatherMap API service."""
    from tripsage_core.services.external_apis.weather_service import (
        WeatherService as OpenWeatherMapService,
    )

    return OpenWeatherMapService()


async def get_calendar_service():
    """Get the comprehensive Google Calendar API service."""
    from tripsage_core.services.external_apis.calendar_service import (
        GoogleCalendarService,
    )

    service = GoogleCalendarService()
    await service.initialize()
    return service


async def get_flights_service():
    """Get the comprehensive Duffel Flights API service."""
    from tripsage_core.services.external_apis.duffel_http_client import (
        DuffelHTTPClient as DuffelFlightsService,
    )

    return DuffelFlightsService()


async def get_time_service():
    """Get the direct Time service using Python datetime."""
    from tripsage_core.services.external_apis.time_service import TimeService

    return TimeService()


# Define singleton dependencies
mcp_manager_dependency = Depends(get_mcp_manager_dep)
accommodations_mcp_dependency = Depends(get_accommodations_mcp_dep())

# Direct service dependencies
webcrawl_service_dependency = Depends(get_webcrawl_service)
memory_service_dependency = Depends(get_memory_service)
dragonfly_service_dependency = Depends(get_dragonfly_service)
google_maps_service_dependency = Depends(get_google_maps_service)
playwright_service_dependency = Depends(get_playwright_service)
weather_service_dependency = Depends(get_weather_service)
calendar_service_dependency = Depends(get_calendar_service)
flights_service_dependency = Depends(get_flights_service)
time_service_dependency = Depends(get_time_service)
