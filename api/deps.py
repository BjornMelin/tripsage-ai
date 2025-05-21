"""
Dependency injection for TripSage API.

This module centralizes all FastAPI dependencies for the TripSage API.
"""

from typing import AsyncGenerator, Optional

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery, OAuth2PasswordBearer

from api.core.config import settings
from api.core.exceptions import AuthenticationError
from tripsage.mcp_abstraction import MCPManager, mcp_manager
from tripsage.storage.dual_storage import DualStorageService
from tripsage.utils.session_memory import SessionMemory

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


# Storage dependency
async def get_storage_service() -> AsyncGenerator[DualStorageService, None]:
    """Get the dual storage service as a dependency.

    Yields:
        DualStorageService instance
    """
    from tripsage.storage.dual_storage import get_dual_storage

    service = get_dual_storage()
    await service.initialize()
    try:
        yield service
    finally:
        await service.close()


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


async def get_current_user(
    user: Optional[dict] = Depends(get_current_user_optional),
):
    """Get the current authenticated user or raise an error.

    Args:
        user: User object from optional auth

    Returns:
        User object if authenticated

    Raises:
        AuthenticationError: If no user is authenticated
    """
    if user is None:
        raise AuthenticationError(message="Not authenticated")
    return user


# Weather MCP dependency
def get_weather_mcp_dep():
    """Get the weather MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_weather_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("weather")

    return _get_weather_mcp


# Flights MCP dependency
def get_flights_mcp_dep():
    """Get the flights MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_flights_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("flights")

    return _get_flights_mcp


# Accommodations MCP dependency
def get_accommodations_mcp_dep():
    """Get the accommodations MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_accommodations_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("accommodations")

    return _get_accommodations_mcp


# Google Maps MCP dependency
def get_googlemaps_mcp_dep():
    """Get the Google Maps MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_googlemaps_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("googlemaps")

    return _get_googlemaps_mcp


# Memory MCP dependency
def get_memory_mcp_dep():
    """Get the memory MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_memory_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("memory")

    return _get_memory_mcp


# WebCrawl MCP dependency
def get_webcrawl_mcp_dep():
    """Get the webcrawl MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_webcrawl_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("webcrawl")

    return _get_webcrawl_mcp


# Time MCP dependency
def get_time_mcp_dep():
    """Get the time MCP wrapper as a dependency."""
    mcp_manager_dependency = Depends(get_mcp_manager_dep)

    async def _get_time_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("time")

    return _get_time_mcp


# Define singleton dependencies
mcp_manager_dependency = Depends(get_mcp_manager_dep)
weather_mcp_dependency = Depends(get_weather_mcp_dep())
flights_mcp_dependency = Depends(get_flights_mcp_dep())
accommodations_mcp_dependency = Depends(get_accommodations_mcp_dep())
googlemaps_mcp_dependency = Depends(get_googlemaps_mcp_dep())
memory_mcp_dependency = Depends(get_memory_mcp_dep())
webcrawl_mcp_dependency = Depends(get_webcrawl_mcp_dep())
time_mcp_dependency = Depends(get_time_mcp_dep())
