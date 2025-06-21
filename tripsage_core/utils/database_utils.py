"""
Database utilities for TripSage Core.

This module provides utilities for working with Supabase database via MCP clients.
Consolidated to use Supabase only for all environments for improved performance,
cost savings, and simplified architecture.
"""

from typing import Dict

from tripsage_core.config import get_settings
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_supabase_settings() -> Dict[str, str]:
    """Get Supabase database connection settings.

    Returns:
        Dictionary with Supabase connection parameters
    """
    settings = get_settings()
    logger.info("Using Supabase database (consolidated architecture)")
    return {
        "supabase_url": settings.database_url,
        "supabase_anon_key": (settings.database_public_key.get_secret_value() if settings.database_public_key else ""),
        "supabase_service_role_key": (
            settings.database_service_key.get_secret_value() if settings.database_service_key else ""
        ),
        "supabase_timeout": "60.0",  # Default timeout
        "pgvector_enabled": "true",  # Default enabled
        "vector_dimensions": "1536",  # Default OpenAI embedding dimensions
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
            "enabled": True,  # Default enabled for modern config
            "dimensions": 1536,  # Default OpenAI embedding dimensions
            "distance_function": "cosine",  # Default distance function
            "index_type": "hnsw",  # Default index type for optimal performance
        }
