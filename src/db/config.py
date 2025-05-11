"""
Database configuration for TripSage.

This module contains the configuration settings for database connections,
supporting both Supabase and Neon database providers.
"""

import os
from enum import Enum
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr

# Load environment variables
load_dotenv()


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
    url: str = Field(env="SUPABASE_URL")
    anon_key: SecretStr = Field(env="SUPABASE_ANON_KEY")
    service_role_key: Optional[SecretStr] = Field(
        env="SUPABASE_SERVICE_ROLE_KEY", default=None
    )
    timeout: float = Field(default=60.0, env="SUPABASE_TIMEOUT")
    auto_refresh_token: bool = Field(default=True, env="SUPABASE_AUTO_REFRESH_TOKEN")
    persist_session: bool = Field(default=True, env="SUPABASE_PERSIST_SESSION")


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
    connection_string: str = Field(env="NEON_CONNECTION_STRING")
    min_pool_size: int = Field(default=1, env="NEON_MIN_POOL_SIZE")
    max_pool_size: int = Field(default=10, env="NEON_MAX_POOL_SIZE")
    max_inactive_connection_lifetime: float = Field(
        default=300.0, env="NEON_MAX_INACTIVE_CONNECTION_LIFETIME"
    )


class DatabaseConfig(BaseModel):
    """
    Database configuration model.

    Attributes:
        provider: The database provider to use (supabase or neon).
        supabase: Supabase configuration settings.
        neon: Neon configuration settings.
    """
    provider: DatabaseProvider = Field(
        default=DatabaseProvider.SUPABASE,
        env="DB_PROVIDER"
    )
    supabase: Optional[SupabaseConfig] = None
    neon: Optional[NeonConfig] = None

    class Config:
        validate_assignment = True


# Create the configuration instance
def create_config() -> DatabaseConfig:
    """
    Create and return the database configuration based on environment variables.
    
    Returns:
        A DatabaseConfig instance with the appropriate provider configuration.
    """
    provider = os.getenv("DB_PROVIDER", "supabase").lower()
    
    if provider == DatabaseProvider.NEON and os.getenv("NEON_CONNECTION_STRING"):
        return DatabaseConfig(
            provider=DatabaseProvider.NEON,
            neon=NeonConfig(
                connection_string=os.getenv("NEON_CONNECTION_STRING", ""),
                min_pool_size=int(os.getenv("NEON_MIN_POOL_SIZE", "1")),
                max_pool_size=int(os.getenv("NEON_MAX_POOL_SIZE", "10")),
                max_inactive_connection_lifetime=float(
                    os.getenv("NEON_MAX_INACTIVE_CONNECTION_LIFETIME", "300.0")
                )
            )
        )
    else:
        # Default to Supabase if no valid Neon configuration found
        return DatabaseConfig(
            provider=DatabaseProvider.SUPABASE,
            supabase=SupabaseConfig(
                url=os.getenv("SUPABASE_URL", ""),
                anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
                service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
                timeout=float(os.getenv("SUPABASE_TIMEOUT", "60.0")),
                auto_refresh_token=os.getenv("SUPABASE_AUTO_REFRESH_TOKEN", "True").lower() == "true",
                persist_session=os.getenv("SUPABASE_PERSIST_SESSION", "True").lower() == "true"
            )
        )


# Instance for easy importing
config = create_config()