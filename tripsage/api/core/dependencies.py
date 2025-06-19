"""
Modern dependency injection for TripSage API.

This module provides clean, modern dependency injection using Annotated types
for unified authentication across JWT (frontend) and API keys (agents).

Features:
- Request-scoped dependencies with proper lifecycle management
- Async context managers for database sessions
- Dependency health monitoring and circuit breaker patterns
- Testing utilities for dependency overrides
- Performance optimizations with intelligent caching
"""

import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Annotated
from weakref import WeakKeyDictionary

from fastapi import Depends, Request
from pydantic import BaseModel

from tripsage.api.core.config import Settings, get_settings
from tripsage.api.middlewares.authentication import Principal
from tripsage_core.exceptions.exceptions import (
    CoreAuthenticationError,
    CoreServiceError,
)
from tripsage_core.services.business.accommodation_service import (
    AccommodationService,
    get_accommodation_service,
)
from tripsage_core.services.business.api_key_service import (
    ApiKeyService,
    get_api_key_service,
)
from tripsage_core.services.business.chat_service import ChatService, get_chat_service
from tripsage_core.services.business.destination_service import (
    DestinationService,
    get_destination_service,
)
from tripsage_core.services.business.flight_service import (
    FlightService,
    get_flight_service,
)
from tripsage_core.services.business.itinerary_service import (
    ItineraryService,
    get_itinerary_service,
)
from tripsage_core.services.business.memory_service_async import (
    AsyncMemoryService as MemoryService,
)
from tripsage_core.services.business.memory_service_async import (
    get_async_memory_service as get_memory_service,
)
from tripsage_core.services.business.trip_service import TripService, get_trip_service
from tripsage_core.services.business.user_service import UserService, get_user_service
from tripsage_core.services.infrastructure import (
    CacheService,
    DatabaseService,
    get_cache_service,
    get_database_service,
)
from tripsage_core.services.mcp_service import SimpleMCPService as MCPManager
from tripsage_core.services.mcp_service import mcp_manager
from tripsage_core.utils.session_utils import SessionMemory

logger = logging.getLogger(__name__)

# === Dependency Health Monitoring ===


class DependencyHealth(BaseModel):
    """Health status of a dependency."""

    name: str
    healthy: bool
    response_time_ms: float
    error_count: int = 0
    last_error: str | None = None
    last_check: float = 0.0


class CircuitBreaker:
    """Simple circuit breaker for dependency health."""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN

    def record_success(self):
        """Record a successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Global dependency health tracking
_dependency_health: dict[str, DependencyHealth] = {}
_circuit_breakers: dict[str, CircuitBreaker] = {}
_request_scoped_cache: WeakKeyDictionary = WeakKeyDictionary()


def get_dependency_health(name: str) -> DependencyHealth:
    """Get health status for a dependency."""
    return _dependency_health.get(
        name, DependencyHealth(name=name, healthy=True, response_time_ms=0.0)
    )


def record_dependency_call(
    name: str, duration_ms: float, success: bool, error: str | None = None
):
    """Record a dependency call for health monitoring."""
    if name not in _dependency_health:
        _dependency_health[name] = DependencyHealth(
            name=name, healthy=True, response_time_ms=0.0
        )

    health = _dependency_health[name]
    health.response_time_ms = duration_ms
    health.last_check = time.time()

    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker()

    circuit_breaker = _circuit_breakers[name]

    if success:
        circuit_breaker.record_success()
        health.healthy = True
    else:
        circuit_breaker.record_failure()
        health.error_count += 1
        health.last_error = error
        health.healthy = circuit_breaker.state != "OPEN"


@asynccontextmanager
async def monitored_dependency(name: str):
    """Context manager for monitoring dependency calls."""
    if name in _circuit_breakers and not _circuit_breakers[name].can_execute():
        raise CoreServiceError(
            message=f"Circuit breaker open for {name}",
            code=f"{name.upper()}_CIRCUIT_OPEN",
        )

    start_time = time.time()
    try:
        yield
        duration_ms = (time.time() - start_time) * 1000
        record_dependency_call(name, duration_ms, True)
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        record_dependency_call(name, duration_ms, False, str(e))
        raise


# === Request-Scoped Dependency Management ===


class RequestScope:
    """Manages request-scoped dependencies with proper cleanup."""

    def __init__(self, request: Request):
        self.request = request
        self._services: dict[str, any] = {}
        self._cleanup_tasks: list = []

    async def get_or_create(self, key: str, factory):
        """Get or create a request-scoped service."""
        if key not in self._services:
            self._services[key] = await factory()
        return self._services[key]

    def add_cleanup_task(self, coro):
        """Add a cleanup task to be executed on request completion."""
        self._cleanup_tasks.append(coro)

    async def cleanup(self):
        """Clean up all request-scoped resources."""
        for task in reversed(self._cleanup_tasks):
            try:
                await task
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


def get_request_scope(request: Request) -> RequestScope:
    """Get the request scope for dependency management."""
    if not hasattr(request.state, "dependency_scope"):
        request.state.dependency_scope = RequestScope(request)
    return request.state.dependency_scope


# === Enhanced Database Dependencies ===


async def get_db_with_monitoring():
    """Get database service with health monitoring and circuit breaker."""
    async with monitored_dependency("database"):
        return await get_database_service()


async def get_db_session(request: Request) -> AsyncGenerator[DatabaseService, None]:
    """Get a request-scoped database session with proper cleanup."""
    scope = get_request_scope(request)

    async def create_session():
        async with monitored_dependency("database_session"):
            db = await get_database_service()
            # Add any session-specific setup here
            return db

    db = await scope.get_or_create("database_session", create_session)

    # Add cleanup if needed
    async def cleanup():
        # Perform any session cleanup here
        pass

    scope.add_cleanup_task(cleanup())
    yield db


# === Enhanced Cache Dependencies ===


async def get_cache_with_monitoring():
    """Get cache service with health monitoring and circuit breaker."""
    async with monitored_dependency("cache"):
        return await get_cache_service()


# Settings dependency
def get_settings_dependency() -> Settings:
    """Get settings instance as a dependency."""
    return get_settings()


# Database dependency
async def get_db():
    """Get database service as a dependency.

    Note: This returns the consolidated DatabaseService with LIFO pooling,
    monitoring, and security features.
    """
    return await get_db_with_monitoring()


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
    key_service=Depends(get_api_key_service),
) -> bool:
    """Verify that the principal has access to a specific service."""
    # Agents with API keys already have service access
    if principal.auth_method == "api_key":
        return True

    # For users, check they have the required service key
    if principal.type == "user":
        try:
            keys = await key_service.get_user_api_keys(principal.id)
            service_key = next((k for k in keys if k.service.value == service), None)
            return service_key is not None
        except Exception:
            return False

    return False


# Cache service dependency
async def get_cache_service_dep():
    """Get the cache service instance as a dependency."""
    return await get_cache_with_monitoring()


# MCP Manager dependency
def get_mcp_manager() -> MCPManager:
    """Get the MCP Manager instance."""
    return mcp_manager


# API Key service dependency
async def get_api_key_service() -> ApiKeyService:
    """Get the API key service instance as a dependency."""
    async with monitored_dependency("api_key_service"):
        db = await get_database_service()
        cache = await get_cache_service()
        settings = get_settings()
        return ApiKeyService(db=db, cache=cache, settings=settings)


# === Enhanced Business Service Dependencies ===


async def get_accommodation_service_monitored() -> AccommodationService:
    """Get accommodation service with monitoring."""
    async with monitored_dependency("accommodation_service"):
        return await get_accommodation_service()


async def get_chat_service_monitored() -> ChatService:
    """Get chat service with monitoring."""
    async with monitored_dependency("chat_service"):
        return await get_chat_service()


async def get_destination_service_monitored() -> DestinationService:
    """Get destination service with monitoring."""
    async with monitored_dependency("destination_service"):
        return await get_destination_service()


async def get_flight_service_monitored() -> FlightService:
    """Get flight service with monitoring."""
    async with monitored_dependency("flight_service"):
        return await get_flight_service()


async def get_itinerary_service_monitored() -> ItineraryService:
    """Get itinerary service with monitoring."""
    async with monitored_dependency("itinerary_service"):
        return await get_itinerary_service()


async def get_memory_service_monitored() -> MemoryService:
    """Get memory service with monitoring."""
    async with monitored_dependency("memory_service"):
        return await get_memory_service()


async def get_trip_service_monitored() -> TripService:
    """Get trip service with monitoring."""
    async with monitored_dependency("trip_service"):
        return await get_trip_service()


async def get_user_service_monitored() -> UserService:
    """Get user service with monitoring."""
    async with monitored_dependency("user_service"):
        return await get_user_service()


async def get_api_key_service_monitored() -> ApiKeyService:
    """Get API key service with monitoring."""
    return await get_api_key_service()


# === Testing Utilities ===


class DependencyOverride:
    """Context manager for overriding dependencies in tests."""

    def __init__(self):
        self._overrides: dict[str, any] = {}
        self._original_dependencies: dict[str, any] = {}

    def override(self, dependency_name: str, mock_instance):
        """Override a dependency with a mock instance."""
        self._overrides[dependency_name] = mock_instance

    async def __aenter__(self):
        """Enter the override context."""
        # Store original dependency functions
        globals_dict = globals()
        for name, mock in self._overrides.items():
            if f"get_{name}" in globals_dict:
                self._original_dependencies[name] = globals_dict[f"get_{name}"]
                # Replace with a lambda that returns the mock
                globals_dict[f"get_{name}"] = lambda m=mock: m
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the override context."""
        # Restore original dependencies
        globals_dict = globals()
        for name, original in self._original_dependencies.items():
            globals_dict[f"get_{name}"] = original
        self._overrides.clear()
        self._original_dependencies.clear()


def create_dependency_override() -> DependencyOverride:
    """Create a new dependency override context manager."""
    return DependencyOverride()


# === Background Task Dependencies ===


@asynccontextmanager
async def get_background_db_session():
    """Get a database session for background tasks."""
    async with monitored_dependency("background_database"):
        db = await get_database_service()
        try:
            yield db
        finally:
            # Perform any cleanup needed for background tasks
            pass


@asynccontextmanager
async def get_background_cache_session():
    """Get a cache session for background tasks."""
    async with monitored_dependency("background_cache"):
        cache = await get_cache_service()
        try:
            yield cache
        finally:
            # Perform any cleanup needed for background tasks
            pass


# === Dependency Health Endpoints ===


def get_all_dependency_health() -> dict[str, DependencyHealth]:
    """Get health status for all tracked dependencies."""
    return _dependency_health.copy()


def reset_dependency_health():
    """Reset all dependency health tracking (useful for tests)."""
    global _dependency_health, _circuit_breakers
    _dependency_health.clear()
    _circuit_breakers.clear()


# Modern Annotated dependency types for 2025 best practices
SettingsDep = Annotated[Settings, Depends(get_settings_dependency)]
DatabaseDep = Annotated[DatabaseService, Depends(get_db)]
CacheDep = Annotated[CacheService, Depends(get_cache_service_dep)]
SessionMemoryDep = Annotated[SessionMemory, Depends(get_session_memory)]
MCPManagerDep = Annotated[MCPManager, Depends(get_mcp_manager)]

# Request-scoped dependencies
RequestScopeDep = Annotated[RequestScope, Depends(get_request_scope)]
DatabaseSessionDep = Annotated[DatabaseService, Depends(get_db_session)]

# Principal-based authentication dependencies
CurrentPrincipalDep = Annotated[Principal | None, Depends(get_current_principal)]
RequiredPrincipalDep = Annotated[Principal, Depends(require_principal)]
UserPrincipalDep = Annotated[Principal, Depends(require_user_principal)]
AgentPrincipalDep = Annotated[Principal, Depends(require_agent_principal)]

# Enhanced business service dependencies with monitoring
AccommodationServiceDep = Annotated[
    AccommodationService, Depends(get_accommodation_service_monitored)
]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service_monitored)]
DestinationServiceDep = Annotated[
    DestinationService, Depends(get_destination_service_monitored)
]
FlightServiceDep = Annotated[FlightService, Depends(get_flight_service_monitored)]
ItineraryServiceDep = Annotated[
    ItineraryService, Depends(get_itinerary_service_monitored)
]
ApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service_monitored)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service_monitored)]
TripServiceDep = Annotated[TripService, Depends(get_trip_service_monitored)]
UserServiceDep = Annotated[UserService, Depends(get_user_service_monitored)]

# Legacy compatibility (maintained for backward compatibility)
LegacyAccommodationServiceDep = Annotated[
    AccommodationService, Depends(get_accommodation_service)
]
LegacyChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
LegacyDestinationServiceDep = Annotated[
    DestinationService, Depends(get_destination_service)
]
LegacyFlightServiceDep = Annotated[FlightService, Depends(get_flight_service)]
LegacyItineraryServiceDep = Annotated[ItineraryService, Depends(get_itinerary_service)]
LegacyApiKeyServiceDep = Annotated[ApiKeyService, Depends(get_api_key_service)]
LegacyMemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
LegacyTripServiceDep = Annotated[TripService, Depends(get_trip_service)]
LegacyUserServiceDep = Annotated[UserService, Depends(get_user_service)]

# Dependency health monitoring
DependencyHealthDep = Annotated[
    Dict[str, DependencyHealth], Depends(get_all_dependency_health)
]
