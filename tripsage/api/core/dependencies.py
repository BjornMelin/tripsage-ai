"""
Unified dependency injection for TripSage API.

This module provides clean, modern dependency injection using the Principal model
for unified authentication across JWT (frontend) and API keys (agents).
"""

from fastapi import Depends, Request

from tripsage.api.core.config import Settings, get_settings
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import CoreAuthenticationError
from tripsage_core.mcp_abstraction import MCPManager, mcp_manager
from tripsage_core.services.business.accommodation_service import (
    get_accommodation_service,
)
from tripsage_core.services.business.chat_service import get_chat_service
from tripsage_core.services.business.destination_service import get_destination_service
from tripsage_core.services.business.flight_service import get_flight_service
from tripsage_core.services.business.itinerary_service import get_itinerary_service
from tripsage_core.services.business.key_management_service import (
    get_key_management_service,
)
from tripsage_core.services.business.memory_service import get_memory_service
from tripsage_core.services.business.trip_service import get_trip_service
from tripsage_core.services.business.user_service import get_user_service
from tripsage_core.services.infrastructure import get_cache_service
from tripsage_core.services.infrastructure.database_service import get_database_service
from tripsage_core.utils.session_utils import SessionMemory


# Settings dependency
def get_settings_dependency() -> Settings:
    """Get settings instance as a dependency."""
    return get_settings()


# Database dependency
async def get_db():
    """Get database service as a dependency.
    
    Note: This returns DatabaseService, not AsyncSession.
    The name is kept for compatibility but the return type has changed.
    """
    return await get_database_service()


# Session memory dependency
async def get_session_memory(request: Request) -> SessionMemory:
    """Get session memory for the current request."""
    if not hasattr(request.state, "session_memory"):
        session_id = request.cookies.get("session_id", None)
        if not session_id:
            from uuid import uuid4

            session_id = str(uuid4())
        request.state.session_memory = SessionMemory(session_id=session_id)
    return request.state.session_memory


# Principal-based authentication
async def get_current_principal(request: Request) -> Principal | None:
    """Get the current authenticated principal from request state.

    This retrieves the Principal set by AuthenticationMiddleware.
    Returns None if no authentication is present.
    """
    return getattr(request.state, "principal", None)


async def require_principal(request: Request) -> Principal:
    """Require an authenticated principal or raise an error."""
    principal = await get_current_principal(request)
    if principal is None:
        raise CoreAuthenticationError(
            message="Authentication required",
            code="AUTH_REQUIRED",
            details={"additional_context": {"hint": "Provide JWT token or API key"}},
        )
    return principal


async def require_user_principal(request: Request) -> Principal:
    """Require a user principal (JWT-authenticated user)."""
    principal = await require_principal(request)
    if principal.type != "user":
        raise CoreAuthenticationError(
            message="User authentication required",
            code="USER_AUTH_REQUIRED",
            details={"additional_context": {"current_auth": principal.type}},
        )
    return principal


async def require_agent_principal(request: Request) -> Principal:
    """Require an agent principal (API key-authenticated agent)."""
    principal = await require_principal(request)
    if principal.type != "agent":
        raise CoreAuthenticationError(
            message="Agent authentication required",
            code="AGENT_AUTH_REQUIRED",
            details={"additional_context": {"current_auth": principal.type}},
        )
    return principal


# Principal utilities
def get_principal_id(principal: Principal) -> str:
    """Get the principal's ID as a string."""
    return principal.id


async def verify_service_access(
    principal: Principal,
    service: str = "openai",
    key_service=Depends(get_key_management_service),
) -> bool:
    """Verify that the principal has access to a specific service."""
    # Agents with API keys already have service access
    if principal.auth_method == "api_key":
        return True

    # For users, check they have the required service key
    if principal.type == "user":
        try:
            keys = await key_service.list_api_keys(principal.id)
            service_key = next((k for k in keys if k.service == service), None)
            return service_key is not None
        except Exception:
            return False

    return False


# Cache service dependency
async def get_cache_service_dep():
    """Get the cache service instance as a dependency."""
    return await get_cache_service()


# MCP Manager dependency
def get_mcp_manager() -> MCPManager:
    """Get the MCP Manager instance."""
    return mcp_manager


# Module-level dependency singletons
get_current_principal_dep = Depends(get_current_principal)
require_principal_dep = Depends(require_principal)
require_user_principal_dep = Depends(require_user_principal)
require_agent_principal_dep = Depends(require_agent_principal)
get_db_dep = Depends(get_db)
get_session_memory_dep = Depends(get_session_memory)
get_settings_dep = Depends(get_settings_dependency)
cache_service_dependency = Depends(get_cache_service_dep)
mcp_manager_dependency = Depends(get_mcp_manager)
verify_service_access_dep = Depends(verify_service_access)

# Unified API service dependencies
get_accommodation_service_dep = Depends(get_accommodation_service)
get_chat_service_dep = Depends(get_chat_service)
get_destination_service_dep = Depends(get_destination_service)
get_flight_service_dep = Depends(get_flight_service)
get_itinerary_service_dep = Depends(get_itinerary_service)
get_key_management_service_dep = Depends(get_key_management_service)
get_memory_service_dep = Depends(get_memory_service)
get_trip_service_dep = Depends(get_trip_service)
get_user_service_dep = Depends(get_user_service)
