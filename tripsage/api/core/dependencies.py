"""
TripSage API Dependencies

Centralized dependency injection for the TripSage FastAPI application.
"""

import os
from typing import Annotated, Any, AsyncGenerator, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tripsage.api.core.config import get_settings
from tripsage.mcp_abstraction import MCPManager, mcp_manager
from tripsage.services.infrastructure.database_service import DatabaseService
from tripsage.services.infrastructure.dragonfly_service import get_cache_service
from tripsage.services.infrastructure.supabase_service import SupabaseService
from tripsage.utils.session_memory import initialize_session_memory

# Database configuration
_engine = None
_async_session_maker = None

# Security schemes
security = HTTPBearer()


def get_database_url() -> str:
    """Get database URL from environment or config."""
    # First check for Supabase environment variables
    db_url = os.getenv("SUPABASE_DB_URL")
    if db_url:
        return db_url

    # Fall back to standard PostgreSQL URL
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "tripsage")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "postgres")

    return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL logging
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_maker():
    """Get or create the async session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        engine = get_engine()
        _async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async_session_maker = get_session_maker()
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Create function for settings dependency
def get_settings_dependency():
    """Get settings dependency without function call in default argument."""
    return get_settings()


def get_mcp_manager_dependency():
    """Get the MCP manager instance as a dependency.

    Returns:
        The singleton MCP manager instance
    """
    return mcp_manager


# Session memory dependency
_session_memory = {}


def get_session_memory() -> Dict[str, Any]:
    """Get the session memory.

    This dependency provides access to temporary memory for the current session.

    Returns:
        Dictionary with session memory data
    """
    return _session_memory


async def initialize_memory_for_user(user_id: str) -> Dict[str, Any]:
    """Initialize memory for a specific user.

    Args:
        user_id: The user ID

    Returns:
        The initialized session memory
    """
    session_data = await initialize_session_memory(user_id)
    _session_memory.update(session_data)
    return _session_memory


# Create singleton dependencies
mcp_manager_dependency = Depends(get_mcp_manager_dependency)
settings_dependency = Depends(get_settings)
session_memory_dependency = Depends(get_session_memory)


# Direct service dependencies (using comprehensive API implementations)
async def get_webcrawl_service():
    """Get the direct WebCrawl service."""
    from tripsage.services.external.webcrawl_service import WebCrawlService

    return WebCrawlService()


async def get_memory_service():
    """Get the direct Memory service (Mem0)."""
    from tripsage.services.core.memory_service import TripSageMemoryService

    return TripSageMemoryService()


async def get_dragonfly_service():
    """Get DragonflyDB cache service."""
    return await get_cache_service()


async def get_google_maps_service():
    """Get the direct Google Maps service."""
    from tripsage.services.external.google_maps_service import GoogleMapsService

    return GoogleMapsService()


async def get_playwright_service():
    """Get the direct Playwright service for complex web scraping."""
    from tripsage.services.external.playwright_service import PlaywrightService

    return PlaywrightService()


async def get_weather_service():
    """Get the comprehensive OpenWeatherMap API service."""
    from tripsage.services.external.weather_service import OpenWeatherMapService

    return OpenWeatherMapService()


async def get_calendar_service():
    """Get the comprehensive Google Calendar API service."""
    from tripsage.services.external.calendar_service import GoogleCalendarService

    service = GoogleCalendarService()
    await service.initialize()
    return service


async def get_flights_service():
    """Get the comprehensive Duffel Flights API service."""
    from tripsage.services.external.flights_service import DuffelFlightsService

    return DuffelFlightsService()


async def get_time_service():
    """Get the direct Time service using Python datetime."""
    from tripsage.services.core.time_service import TimeService

    return TimeService()


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


# Authentication helper functions
async def verify_api_key(current_user=None) -> bool:
    """Verify that the user has a valid API key for chat functionality.

    For now, this is a simplified check. In a full implementation,
    this would validate specific service keys (like OpenAI) from the database.

    Args:
        current_user: Current authenticated user (optional)

    Returns:
        True if user has valid API keys
    """
    # For now, assume all users have valid API keys
    # This will be enhanced when the full BYOK system is integrated
    return True


async def get_supabase_service():
    """Get Supabase service."""
    service = SupabaseService()
    await service.connect()
    return service


async def get_database_service():
    """Get database service."""
    service = DatabaseService()
    await service.connect()
    return service


async def get_mcp_manager():
    """Get MCP manager for remaining MCP-based services."""
    return mcp_manager


# Type annotations for dependency injection
CacheService = Annotated[object, Depends(get_dragonfly_service)]
DatabaseDep = Annotated[DatabaseService, Depends(get_database_service)]
SupabaseDep = Annotated[SupabaseService, Depends(get_supabase_service)]
MCPManagerDep = Annotated[MCPManager, Depends(get_mcp_manager)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User information dictionary

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # TODO: Implement JWT token validation
        # For now, return a mock user for development
        token = credentials.credentials
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Mock user for development
        return {"id": "user_123", "email": "user@example.com", "is_active": True}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),  # noqa: B008
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.

    Args:
        request: FastAPI request object
        credentials: Optional HTTP Bearer token credentials

    Returns:
        User information dictionary or None if not authenticated
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


# Type annotations for user dependencies
CurrentUser = Annotated[dict, Depends(get_current_user)]
OptionalUser = Annotated[Optional[dict], Depends(get_optional_user)]
