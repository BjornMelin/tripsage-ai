"""
Database utilities for TripSage.

This module provides utilities for working with databases via MCP clients.
"""

from enum import Enum
from typing import Dict, Optional

from .logging import get_logger
from .settings import settings

logger = get_logger(__name__)


class Environment(str, Enum):
    """Valid environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


def get_db_settings(environment: Optional[str] = None) -> Dict[str, str]:
    """Get database connection settings based on environment.

    Args:
        environment: The environment to get settings for.
                    If None, uses the environment from settings.

    Returns:
        Dictionary with database connection parameters
    """
    if environment is None:
        environment = settings.environment

    env = environment.lower()

    # Use Neon for development/testing
    if env in [Environment.DEVELOPMENT.value, Environment.TESTING.value]:
        logger.info(f"Using Neon database for {environment} environment")
        return {
            "endpoint": settings.database.neon.endpoint,
            "project_id": settings.database.neon.project_id or "",
            "connection_string": (
                settings.database.neon.connection_string.get_secret_value()
                if settings.database.neon.connection_string
                else ""
            ),
        }
    # Use Supabase for staging/production
    else:
        logger.info(f"Using Supabase database for {environment} environment")
        return {
            "endpoint": settings.database.supabase.endpoint,
            "project_url": settings.database.supabase.project_url or "",
            "api_key": (
                settings.database.supabase.api_key.get_secret_value()
                if settings.database.supabase.api_key
                else ""
            ),
        }


class DatabaseConnectionFactory:
    """Factory for creating database connections."""

    @staticmethod
    def get_connection_params(environment: Optional[str] = None) -> Dict[str, str]:
        """Get connection parameters for the specified environment.

        Args:
            environment: Environment to get connection for.
                        If None, uses the environment from settings.

        Returns:
            Dictionary with connection parameters
        """
        return get_db_settings(environment)
