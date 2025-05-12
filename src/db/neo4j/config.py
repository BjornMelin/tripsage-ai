"""
Configuration for Neo4j database connection.

This module provides configuration for connecting to Neo4j database,
using the centralized settings system.
"""

from typing import Any, Dict

from src.utils.logging import get_module_logger
from src.utils.settings import settings

logger = get_module_logger(__name__)


class Neo4jConfig:
    """Configuration for Neo4j connection."""

    def __init__(self):
        """Initialize the Neo4j configuration from centralized settings."""
        # Neo4j connection settings
        self.uri = settings.neo4j.uri
        self.user = settings.neo4j.user
        self.password = settings.neo4j.password.get_secret_value()
        self.database = settings.neo4j.database

        # Connection pool settings
        self.max_connection_lifetime = settings.neo4j.max_connection_lifetime
        self.max_connection_pool_size = settings.neo4j.max_connection_pool_size
        self.connection_acquisition_timeout = settings.neo4j.connection_acquisition_timeout

        # Query settings
        self.default_query_timeout = settings.neo4j.default_query_timeout

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.uri:
            raise ValueError("Neo4j URI is required")

        if not self.user:
            raise ValueError("Neo4j user is required")

        if not self.password:
            raise ValueError("Neo4j password is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.

        Returns:
            Dictionary with configuration values
        """
        return {
            "uri": self.uri,
            "user": self.user,
            "password": "****" if self.password else None,
            "database": self.database,
            "max_connection_lifetime": self.max_connection_lifetime,
            "max_connection_pool_size": self.max_connection_pool_size,
            "connection_acquisition_timeout": self.connection_acquisition_timeout,
            "default_query_timeout": self.default_query_timeout,
        }


# Create a singleton instance
neo4j_config = Neo4jConfig()