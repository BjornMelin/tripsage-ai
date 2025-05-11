"""
Configuration for Neo4j database connection.

This module provides configuration for connecting to Neo4j database,
with settings loaded from environment variables via the application's
configuration system.
"""

from typing import Any, Dict

from src.utils.config import get_config
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class Neo4jConfig:
    """Configuration for Neo4j connection."""

    def __init__(self):
        """Initialize the Neo4j configuration from environment variables."""
        # Get base configuration
        config = get_config()

        # Neo4j connection settings
        self.uri = config.get("NEO4J_URI", "bolt://localhost:7687")
        self.user = config.get("NEO4J_USER", "neo4j")
        self.password = config.get("NEO4J_PASSWORD", "")
        self.database = config.get("NEO4J_DATABASE", "neo4j")

        # Connection pool settings
        self.max_connection_lifetime = int(
            config.get("NEO4J_MAX_CONNECTION_LIFETIME", 3600)
        )
        self.max_connection_pool_size = int(
            config.get("NEO4J_MAX_CONNECTION_POOL_SIZE", 50)
        )
        self.connection_acquisition_timeout = int(
            config.get("NEO4J_CONNECTION_ACQUISITION_TIMEOUT", 60)
        )

        # Query settings
        self.default_query_timeout = int(config.get("NEO4J_DEFAULT_QUERY_TIMEOUT", 60))

    def validate(self) -> None:
        """Validate the configuration.

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.uri:
            raise ValueError("NEO4J_URI is required")

        if not self.user:
            raise ValueError("NEO4J_USER is required")

        if not self.password:
            raise ValueError("NEO4J_PASSWORD is required")

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
