"""
Database provider factory for TripSage.

This module provides a factory for creating and managing database provider instances
based on the application's configuration.
"""

from typing import Optional

from src.db.config import DatabaseProvider as ProviderType
from src.db.config import config
from src.db.providers import DatabaseProvider, NeonProvider, SupabaseProvider
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Global provider instance
_provider: Optional[DatabaseProvider] = None


def create_provider() -> DatabaseProvider:
    """
    Create a database provider instance based on the configuration.

    Note: This function is synchronous and only creates a provider instance
    without connecting to the database. Use await provider.connect() to
    establish a database connection.

    Returns:
        An unconnected DatabaseProvider instance for the configured provider.

    Raises:
        ValueError: If the configured provider is not supported or misconfigured.
    """
    if config.provider == ProviderType.SUPABASE:
        if not config.supabase:
            raise ValueError("Supabase configuration is missing")

        return SupabaseProvider(
            url=config.supabase.url,
            key=(
                config.supabase.service_role_key.get_secret_value()
                if config.supabase.service_role_key
                else config.supabase.anon_key.get_secret_value()
            ),
            options={
                "auto_refresh_token": config.supabase.auto_refresh_token,
                "persist_session": config.supabase.persist_session,
                "timeout": config.supabase.timeout,
            },
        )
    elif config.provider == ProviderType.NEON:
        if not config.neon:
            raise ValueError("Neon configuration is missing")

        return NeonProvider(
            connection_string=config.neon.connection_string,
            min_size=config.neon.min_pool_size,
            max_size=config.neon.max_pool_size,
            max_inactive_connection_lifetime=config.neon.max_inactive_connection_lifetime,
        )
    else:
        raise ValueError(f"Unsupported database provider: {config.provider}")


def get_provider(force_new: bool = False) -> DatabaseProvider:
    """
    Get or create a database provider instance.

    Note: This function is synchronous and only returns a provider instance
    without ensuring it's connected to the database. Use await provider.connect()
    to establish a database connection if needed.

    Args:
        force_new: If True, create a new provider instance even if one already exists.

    Returns:
        A DatabaseProvider instance (may not be connected).

    Raises:
        ValueError: If the configured provider is not supported.
    """
    global _provider

    if _provider is None or force_new:
        logger.info(f"Creating new {config.provider} database provider")
        _provider = create_provider()

    return _provider


def reset_provider() -> None:
    """
    Reset the global provider instance.

    Note: This function is synchronous and only resets the provider instance
    without properly closing database connections. Use await provider.disconnect()
    before calling this function to properly close connections.
    """
    global _provider
    _provider = None
    logger.debug("Database provider has been reset")
