"""
Database configuration for TripSage.

This module contains the configuration settings for database connections,
supporting both Supabase and Neon database providers, now using the centralized
settings system.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, SecretStr

from src.utils.settings import settings


class DatabaseProvider(str, Enum):
    """Enum representing supported database providers."""

    SUPABASE = "supabase"
    NEON = "neon"


class SupabaseConfig(BaseModel):
    """
    Supabase-specific configuration.

    Attributes:
        url: The URL of the Supabase project.
        anon_key: The anonymous key for the Supabase project.
        service_role_key: The service role key for the Supabase project (optional).
        timeout: Timeout in seconds for Supabase operations.
        auto_refresh_token: Whether to automatically refresh the token.
        persist_session: Whether to persist the session.
    """

    url: str
    anon_key: SecretStr
    service_role_key: Optional[SecretStr] = None
    timeout: float = 60.0
    auto_refresh_token: bool = True
    persist_session: bool = True


class NeonConfig(BaseModel):
    """
    Neon-specific configuration.

    Attributes:
        connection_string: PostgreSQL connection string for Neon database.
        min_pool_size: Minimum number of connections in the pool.
        max_pool_size: Maximum number of connections in the pool.
        max_inactive_connection_lifetime: How long an inactive connection
                                        remains in the pool before being closed.
    """

    connection_string: str
    min_pool_size: int = 1
    max_pool_size: int = 10
    max_inactive_connection_lifetime: float = 300.0


class DatabaseConfig(BaseModel):
    """
    Database configuration model.

    Attributes:
        provider: The database provider to use (supabase or neon).
        supabase: Supabase configuration settings.
        neon: Neon configuration settings.
    """

    provider: DatabaseProvider
    supabase: Optional[SupabaseConfig] = None
    neon: Optional[NeonConfig] = None

    class Config:
        validate_assignment = True


# Create the configuration instance
def create_config() -> DatabaseConfig:
    """
    Create and return the database configuration from centralized settings.

    Returns:
        A DatabaseConfig instance with the appropriate provider configuration.
    """
    provider = settings.database.db_provider.lower()

    if provider == DatabaseProvider.NEON.value and settings.database.neon_connection_string:
        return DatabaseConfig(
            provider=DatabaseProvider.NEON,
            neon=NeonConfig(
                connection_string=str(settings.database.neon_connection_string),
                min_pool_size=settings.database.neon_min_pool_size,
                max_pool_size=settings.database.neon_max_pool_size,
                max_inactive_connection_lifetime=settings.database.neon_max_inactive_connection_lifetime,
            ),
        )
    else:
        # Default to Supabase if no valid Neon configuration found
        return DatabaseConfig(
            provider=DatabaseProvider.SUPABASE,
            supabase=SupabaseConfig(
                url=settings.database.supabase_url,
                anon_key=settings.database.supabase_anon_key,
                service_role_key=settings.database.supabase_service_role_key,
                timeout=settings.database.supabase_timeout,
                auto_refresh_token=settings.database.supabase_auto_refresh_token,
                persist_session=settings.database.supabase_persist_session,
            ),
        )


# Instance for easy importing
config = create_config()