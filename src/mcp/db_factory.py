"""
Database MCP client factory for TripSage.

This module provides a factory for creating and managing database MCP client instances
based on the application's environment (development or production).
"""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, Field

from ..utils.logging import get_module_logger
from ..utils.settings import settings
from .neon.client import NeonMCPClient, NeonService
from .neon.client import get_client as get_neon_client
from .supabase.client import (
    SupabaseMCPClient,
    SupabaseService,
)
from .supabase.client import (
    get_client as get_supabase_client,
)

# Configure logging
logger = get_module_logger(__name__)


class Environment(str, Enum):
    """Valid environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseModel):
    """Database configuration parameters."""

    environment: str = Field(
        default=Environment.DEVELOPMENT,
        description=(
            "The environment to use (development, testing, staging, production)"
        ),
    )


def get_mcp_client(
    environment: Optional[str] = None,
) -> Union[NeonMCPClient, SupabaseMCPClient]:
    """
    Get the appropriate database MCP client based on the environment.

    Args:
        environment: The environment to get the client for.
                    If None, uses the environment from settings.

    Returns:
        A database MCP client instance (either NeonMCPClient or SupabaseMCPClient)
    """
    if environment is None:
        environment = settings.environment

    if environment.lower() in [Environment.DEVELOPMENT, Environment.TESTING]:
        logger.info(f"Using NeonMCPClient for {environment} environment")
        return get_neon_client()
    else:
        logger.info(f"Using SupabaseMCPClient for {environment} environment")
        return get_supabase_client()


def get_mcp_service(
    environment: Optional[str] = None,
) -> Union[NeonService, SupabaseService]:
    """
    Get the appropriate database MCP service based on the environment.

    Args:
        environment: The environment to get the service for.
                    If None, uses the environment from settings.

    Returns:
        A database MCP service instance (either NeonService or SupabaseService)
    """
    if environment is None:
        environment = settings.environment

    if environment.lower() in [Environment.DEVELOPMENT, Environment.TESTING]:
        logger.info(f"Using NeonService for {environment} environment")
        return NeonService()
    else:
        logger.info(f"Using SupabaseService for {environment} environment")
        return SupabaseService()


class DatabaseMCPFactory:
    """Factory class for database MCP clients and services."""

    @staticmethod
    def get_client(
        environment: Optional[str] = None,
    ) -> Union[NeonMCPClient, SupabaseMCPClient]:
        """
        Get the appropriate database MCP client based on the environment.

        Args:
            environment: The environment to get the client for.
                        If None, uses the environment from settings.

        Returns:
            A database MCP client instance (either NeonMCPClient or SupabaseMCPClient)
        """
        return get_mcp_client(environment)

    @staticmethod
    def get_service(
        environment: Optional[str] = None,
    ) -> Union[NeonService, SupabaseService]:
        """
        Get the appropriate database MCP service based on the environment.

        Args:
            environment: The environment to get the service for.
                        If None, uses the environment from settings.

        Returns:
            A database MCP service instance (either NeonService or SupabaseService)
        """
        return get_mcp_service(environment)

    @staticmethod
    def get_development_client() -> NeonMCPClient:
        """
        Get the Neon MCP client for development environment.

        Returns:
            A NeonMCPClient instance
        """
        return get_neon_client()

    @staticmethod
    def get_development_service() -> NeonService:
        """
        Get the Neon MCP service for development environment.

        Returns:
            A NeonService instance
        """
        return NeonService()

    @staticmethod
    def get_production_client() -> SupabaseMCPClient:
        """
        Get the Supabase MCP client for production environment.

        Returns:
            A SupabaseMCPClient instance
        """
        return get_supabase_client()

    @staticmethod
    def get_production_service() -> SupabaseService:
        """
        Get the Supabase MCP service for production environment.

        Returns:
            A SupabaseService instance
        """
        return SupabaseService()


# Create a singleton instance for easy access
db_mcp_factory = DatabaseMCPFactory()
