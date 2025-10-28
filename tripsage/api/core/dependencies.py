"""Modern dependency injection for TripSage API.

This module provides clean, modern dependency injection using Annotated types
for unified authentication across JWT (frontend) and API keys (agents).
"""

from collections.abc import Iterable as TypingIterable
from typing import Annotated, cast

from fastapi import Depends, Request

from tripsage.api.core.config import Settings, get_settings
from tripsage.api.core.protocols import ApiKeyServiceProto, ChatServiceProto
from tripsage.api.middlewares.authentication import Principal
from tripsage.app_state import AppServiceContainer
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreAuthorizationError,
)
from tripsage_core.services.airbnb_mcp import AirbnbMCP
from tripsage_core.services.business.accommodation_service import AccommodationService
from tripsage_core.services.business.activity_service import ActivityService
from tripsage_core.services.business.api_key_service import ApiKeyService
from tripsage_core.services.business.chat_service import ChatService
from tripsage_core.services.business.destination_service import DestinationService
from tripsage_core.services.business.file_processing_service import (
    FileProcessingService,
)
from tripsage_core.services.business.flight_service import FlightService
from tripsage_core.services.business.itinerary_service import ItineraryService
from tripsage_core.services.business.memory_service import MemoryService
from tripsage_core.services.business.trip_service import TripService
from tripsage_core.services.business.unified_search_service import UnifiedSearchService
from tripsage_core.services.business.user_service import UserService
from tripsage_core.services.external_apis.google_maps_service import GoogleMapsService
from tripsage_core.services.infrastructure import CacheService, KeyMonitoringService
from tripsage_core.services.infrastructure.database_service import DatabaseService
from tripsage_core.utils.session_utils import SessionMemory


def _get_services_container(request: Request) -> AppServiceContainer:
    """Return the lifespan-managed service container from app.state."""
    services = cast(
        AppServiceContainer | None,
        getattr(request.app.state, "services", None),
    )
    if services is None:
        raise RuntimeError(
            "Application services are not initialised; ensure initialise_app_state "
            "completes during startup."
        )
    return services


def _get_required_service[ServiceT](
    request: Request,
    attr: str,
    expected_type: type[ServiceT],
) -> ServiceT:
    """Fetch a required service from the container with type validation."""
    services = _get_services_container(request)
    return services.get_required_service(attr, expected_type=expected_type)


# Settings dependency
def get_settings_dependency() -> Settings:
    """Get settings instance as a dependency."""
    return get_settings()


# Database dependency
def get_db(request: Request) -> DatabaseService:
    """Get the lifespan-managed database service as a dependency."""
    return _get_required_service(
        request,
        "database_service",
        DatabaseService,
    )


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


async def require_admin_principal(request: Request) -> Principal:
    """Require a principal with admin privileges."""
    principal = await require_principal(request)

    if principal.type == "agent":
        raise CoreAuthorizationError(
            message="Admin privileges required",
            code="ADMIN_AUTH_REQUIRED",
            details={"additional_context": {"principal_type": principal.type}},
        )

    roles: set[str] = set()
    primary_role = principal.metadata.get("role")
    if isinstance(primary_role, str):
        roles.add(primary_role.lower())

    role_collection = principal.metadata.get("roles")
    if isinstance(role_collection, TypingIterable) and not isinstance(
        role_collection, (str, bytes)
    ):
        # Cast to an iterable of opaque objects to satisfy the type checker
        for role_item in cast(TypingIterable[object], role_collection):
            if isinstance(role_item, str):
                roles.add(role_item.lower())
            else:
                roles.add(str(role_item).lower())

    is_admin_flag = principal.metadata.get("is_admin")
    if isinstance(is_admin_flag, bool) and is_admin_flag:
        return principal

    allowed_roles = {"admin", "superadmin", "site_admin"}
    if roles.intersection(allowed_roles):
        return principal

    raise CoreAuthorizationError(
        message="Admin privileges required",
        code="ADMIN_AUTH_REQUIRED",
        details={"additional_context": {"roles": sorted(roles)}},
    )


# Principal utilities
def get_principal_id(principal: Principal) -> str:
    """Get the principal's ID as a string."""
    return principal.id


async def verify_service_access(
    principal: Principal,
    service: str = "openai",
    key_service: ApiKeyService | None = None,
) -> bool:
    """Verify that the principal has access to a specific service."""
    # Agents with API keys already have service access
    if principal.auth_method == "api_key":
        return True

    # For users, check they have the required service key
    if principal.type == "user":
        if key_service is None:
            # Without a DI-provided ApiKeyService, we cannot verify access.
            return False
        try:
            keys = await key_service.list_user_keys(principal.id)
            service_key = next((k for k in keys if k.service.value == service), None)
            return service_key is not None
        except (OSError, ValueError, TypeError):
            return False

    return False


# Cache service dependency
def get_cache_service_dep(request: Request) -> CacheService:
    """Get cache service (lifespan-managed singleton)."""
    return _get_required_service(request, "cache_service", CacheService)


# Google Maps service dependency (DI-managed in app lifespan)
def get_maps_service_dep(request: Request) -> GoogleMapsService:
    """Get DI-managed Google Maps service instance."""
    return _get_required_service(request, "google_maps_service", GoogleMapsService)


# Activity service dependency constructed from DI-managed services
def get_activity_service_dep(request: Request) -> ActivityService:
    """Return the ActivityService singleton."""
    return _get_required_service(request, "activity_service", ActivityService)


def get_file_processing_service(request: Request) -> FileProcessingService:
    """Return the FileProcessingService singleton."""
    return _get_required_service(
        request,
        "file_processing_service",
        FileProcessingService,
    )


def get_key_monitoring_service(request: Request) -> KeyMonitoringService:
    """Return the KeyMonitoringService singleton."""
    return _get_required_service(
        request,
        "key_monitoring_service",
        KeyMonitoringService,
    )


# Unified search service dependency
def get_unified_search_service_dep(request: Request) -> UnifiedSearchService:
    """Return the UnifiedSearchService singleton."""
    return _get_required_service(
        request,
        "unified_search_service",
        UnifiedSearchService,
    )


# MCP service dependency
def get_mcp_service(request: Request) -> AirbnbMCP:
    """Get DI-managed MCP service instance."""
    return _get_required_service(request, "mcp_service", AirbnbMCP)


# API Key service dependency
def get_api_key_service(request: Request) -> ApiKeyServiceProto:
    """Get the API key service singleton."""
    service: ApiKeyService = _get_required_service(
        request, "api_key_service", ApiKeyService
    )
    return cast(ApiKeyServiceProto, service)


# Business service dependencies (container-backed)
def get_accommodation_service(request: Request) -> AccommodationService:
    """Return AccommodationService from app.state container."""
    return _get_required_service(
        request,
        "accommodation_service",
        AccommodationService,
    )


def get_chat_service(request: Request) -> ChatServiceProto:
    """Return ChatService from the container."""
    service = _get_required_service(request, "chat_service", ChatService)
    return cast(ChatServiceProto, service)


def get_destination_service(request: Request) -> DestinationService:
    """Return DestinationService from the container."""
    return _get_required_service(
        request,
        "destination_service",
        DestinationService,
    )


def get_flight_service_dep(request: Request) -> FlightService:
    """Return FlightService from the container."""
    return _get_required_service(request, "flight_service", FlightService)


def get_itinerary_service(request: Request) -> ItineraryService:
    """Return ItineraryService from the container."""
    return _get_required_service(
        request,
        "itinerary_service",
        ItineraryService,
    )


def get_memory_service(request: Request) -> MemoryService:
    """Return MemoryService from the container."""
    return _get_required_service(request, "memory_service", MemoryService)


def get_trip_service(request: Request) -> TripService:
    """Return TripService from the container."""
    return _get_required_service(request, "trip_service", TripService)


def get_user_service(request: Request) -> UserService:
    """Return UserService from the container."""
    return _get_required_service(request, "user_service", UserService)


# Modern Annotated dependency types for 2025 best practices
SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DatabaseDep = Annotated[DatabaseService, Depends(get_db)]
CacheDep = Annotated[CacheService, Depends(get_cache_service_dep)]
SessionMemoryDep = Annotated[SessionMemory, Depends(get_session_memory)]
MCPServiceDep = Annotated[AirbnbMCP, Depends(get_mcp_service)]
MapsServiceDep = Annotated[GoogleMapsService, Depends(get_maps_service_dep)]
ActivityServiceDep = Annotated[ActivityService, Depends(get_activity_service_dep)]
UnifiedSearchServiceDep = Annotated[
    UnifiedSearchService, Depends(get_unified_search_service_dep)
]

# Principal-based authentication dependencies
CurrentPrincipalDep = Annotated[Principal | None, Depends(get_current_principal)]
RequiredPrincipalDep = Annotated[Principal, Depends(require_principal)]
UserPrincipalDep = Annotated[Principal, Depends(require_user_principal)]
AgentPrincipalDep = Annotated[Principal, Depends(require_agent_principal)]
AdminPrincipalDep = Annotated[Principal, Depends(require_admin_principal)]

# Business service dependencies (type aliases)
AccommodationServiceDep = Annotated[
    AccommodationService, Depends(get_accommodation_service)
]
ChatServiceDep = Annotated[ChatServiceProto, Depends(get_chat_service)]
DestinationServiceDep = Annotated[DestinationService, Depends(get_destination_service)]
FlightServiceDep = Annotated[FlightService, Depends(get_flight_service_dep)]
ItineraryServiceDep = Annotated[ItineraryService, Depends(get_itinerary_service)]
ApiKeyServiceDep = Annotated[ApiKeyServiceProto, Depends(get_api_key_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
TripServiceDep = Annotated[TripService, Depends(get_trip_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
FileProcessingServiceDep = Annotated[
    FileProcessingService, Depends(get_file_processing_service)
]
KeyMonitoringServiceDep = Annotated[
    KeyMonitoringService, Depends(get_key_monitoring_service)
]
