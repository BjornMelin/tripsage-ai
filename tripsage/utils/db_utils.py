"""
Database utilities for TripSage.

This module provides utilities for working with Supabase database via MCP clients.
Consolidated to use Supabase only for all environments for improved performance,
cost savings, and simplified architecture.
"""

from typing import Dict

from .logging import get_logger
from tripsage.config.app_settings import settings

logger = get_logger(__name__)


def get_supabase_settings() -> Dict[str, str]:
    """Get Supabase database connection settings.

    Returns:
        Dictionary with Supabase connection parameters
    """
    logger.info("Using Supabase database (consolidated architecture)")
    return {
        "supabase_url": settings.database.supabase_url,
        "supabase_anon_key": (
            settings.database.supabase_anon_key.get_secret_value()
            if settings.database.supabase_anon_key
            else ""
        ),
        "supabase_service_role_key": (
            settings.database.supabase_service_role_key.get_secret_value()
            if settings.database.supabase_service_role_key
            else ""
        ),
        "supabase_timeout": str(settings.database.supabase_timeout),
        "pgvector_enabled": str(settings.database.pgvector_enabled),
        "vector_dimensions": str(settings.database.vector_dimensions),
    }


class DatabaseConnectionFactory:
    """Factory for creating Supabase database connections."""

    @staticmethod
    def get_connection_params() -> Dict[str, str]:
        """Get Supabase connection parameters.

        Returns:
            Dictionary with Supabase connection parameters
        """
        return get_supabase_settings()

    @staticmethod
    def get_pgvector_config() -> Dict[str, any]:
        """Get pgvector-specific configuration.

        Returns:
            Dictionary with pgvector configuration
        """
        return {
            "enabled": settings.database.pgvector_enabled,
            "dimensions": settings.database.vector_dimensions,
            "distance_function": "cosine",  # Default distance function
            "index_type": "hnsw",  # Default index type for optimal performance
        }
