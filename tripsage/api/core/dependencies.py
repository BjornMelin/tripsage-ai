"""Dependency injection utilities for FastAPI.

This module provides dependency functions that can be used with FastAPI's
Depends() function to inject services and components into endpoint handlers.
"""

import os
from typing import Any, AsyncGenerator, Dict

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tripsage.api.core.config import get_settings
from tripsage.mcp_abstraction import mcp_manager
from tripsage.utils.session_memory import initialize_session_memory

# Database configuration
_engine = None
_async_session_maker = None


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


# Weather MCP dependency
def get_weather_mcp_dep():
    """Get the weather MCP wrapper as a dependency."""

    async def _get_weather_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("weather")

    return _get_weather_mcp


# First create the functions that will be wrapped with Depends
weather_mcp_dep_fn = get_weather_mcp_dep()

# Create MCP dependencies
weather_mcp_dependency = Depends(weather_mcp_dep_fn)


# Google Maps MCP dependency
def get_google_maps_mcp_dep():
    """Get the Google Maps MCP wrapper as a dependency."""

    async def _get_google_maps_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("googlemaps")

    return _get_google_maps_mcp


# Create the Google Maps function
google_maps_mcp_dep_fn = get_google_maps_mcp_dep()

# Create Google Maps dependency
google_maps_mcp_dependency = Depends(google_maps_mcp_dep_fn)


# Time MCP dependency
def get_time_mcp_dep():
    """Get the time MCP wrapper as a dependency."""

    async def _get_time_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("time")

    return _get_time_mcp


# Create the time function
time_mcp_dep_fn = get_time_mcp_dep()

# Create time dependency
time_mcp_dependency = Depends(time_mcp_dep_fn)


# Firecrawl MCP dependency
def get_firecrawl_mcp_dep():
    """Get the Firecrawl MCP wrapper as a dependency."""

    async def _get_firecrawl_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("firecrawl")

    return _get_firecrawl_mcp


# Create the firecrawl function
firecrawl_mcp_dep_fn = get_firecrawl_mcp_dep()

# Create firecrawl dependency
firecrawl_mcp_dependency = Depends(firecrawl_mcp_dep_fn)


# Memory MCP dependency
def get_memory_mcp_dep():
    """Get the memory MCP wrapper as a dependency."""

    async def _get_memory_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("memory")

    return _get_memory_mcp


# Create the memory function
memory_mcp_dep_fn = get_memory_mcp_dep()

# Create memory dependency
memory_mcp_dependency = Depends(memory_mcp_dep_fn)


# Redis MCP dependency
def get_redis_mcp_dep():
    """Get the Redis MCP wrapper as a dependency."""

    async def _get_redis_mcp(mcp_manager=mcp_manager_dependency):
        return await mcp_manager.initialize_mcp("redis")

    return _get_redis_mcp


# Create the redis function
redis_mcp_dep_fn = get_redis_mcp_dep()

# Create redis dependency
redis_mcp_dependency = Depends(redis_mcp_dep_fn)


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
