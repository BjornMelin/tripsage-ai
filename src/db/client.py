"""
Database client module for TripSage.

This module provides a unified interface for connecting to and interacting with
the database, abstracting away the specific provider implementation details.
"""

import logging
from typing import Any, Dict, Optional

from src.db.factory import get_provider, reset_provider
from src.db.providers import DatabaseProvider
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)


async def create_db_client(use_service_key: bool = False) -> DatabaseProvider:
    """
    Create and connect to a database client.
    
    Args:
        use_service_key: Whether to use the service role key for Supabase.
                        This parameter is ignored for Neon.
    
    Returns:
        A connected database provider instance.
        
    Raises:
        Exception: If the connection fails.
    """
    provider = get_provider(force_new=True)
    
    try:
        await provider.connect()
        logger.info(f"Connected to database successfully")
        return provider
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def get_db_client(use_service_key: bool = False) -> DatabaseProvider:
    """
    Get or create a database client.
    
    Args:
        use_service_key: Whether to use the service role key for Supabase.
                        This parameter is ignored for Neon.
    
    Returns:
        A connected database provider.
        
    Raises:
        Exception: If the connection fails.
    """
    provider = get_provider()
    
    if not provider.is_connected:
        await provider.connect()
    
    return provider


async def close_db_client() -> None:
    """Close the database client connection."""
    provider = get_provider()
    
    if provider.is_connected:
        await provider.disconnect()
    
    # Reset the provider to ensure it will be reinitialized on next use
    reset_provider()
    logger.info("Database client connection closed")


# Legacy compatibility functions for Supabase client
# These will be deprecated in future versions but are maintained for backward compatibility

def create_supabase_client(
    url: Optional[str] = None,
    key: Optional[str] = None,
    use_service_key: bool = False,
    **options: Dict[str, Any],
) -> Any:
    """
    Create a new database client.

    DEPRECATED: This synchronous function is maintained for backward compatibility
    and delegates to the new provider system. It does NOT actually connect to the database.
    Use async create_db_client() instead.

    WARNING: This function only returns a provider instance without connecting to the database.
    You must manually connect using await provider.connect().

    Args:
        url: The database URL (ignored, use environment variables instead).
        key: The API key (ignored, use environment variables instead).
        use_service_key: Whether to use the service role key.
        **options: Additional options to pass to the client.

    Returns:
        An unconnected database provider instance.

    Raises:
        ValueError: If the provider configuration is invalid.
    """
    logger.warning(
        "create_supabase_client is deprecated, use create_db_client instead"
    )
    provider = get_provider()
    return provider


def get_supabase_client(use_service_key: bool = False) -> Any:
    """
    Get or create a database client.

    DEPRECATED: This synchronous function is maintained for backward compatibility
    and delegates to the new provider system. It does NOT ensure the provider is connected.
    Use async get_db_client() instead.

    WARNING: This function only returns a provider instance without ensuring connection.
    You must manually connect using await provider.connect() if not already connected.

    Args:
        use_service_key: Whether to use the service role key.

    Returns:
        A database provider instance (may not be connected).

    Raises:
        ValueError: If the provider configuration is invalid.
    """
    logger.warning(
        "get_supabase_client is deprecated, use get_db_client instead"
    )
    return get_provider()


def reset_client() -> None:
    """
    Reset the database client.

    DEPRECATED: This synchronous function is maintained for backward compatibility
    and delegates to the new provider system.

    WARNING: This function only resets the provider instance without properly closing connections.
    Use async close_db_client() followed by reset_provider() instead.
    """
    logger.warning(
        "reset_client is deprecated, use async close_db_client() followed by reset_provider() instead"
    )
    reset_provider()