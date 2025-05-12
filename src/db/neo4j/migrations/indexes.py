"""
Neo4j indexes migrations.

This module provides functions to create database indexes for Neo4j,
improving query performance for the knowledge graph.
"""

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


def create_indexes(connection) -> bool:
    """Create Neo4j indexes.

    Args:
        connection: Neo4j connection instance

    Returns:
        True if successful

    Raises:
        Neo4jQueryError: If index creation fails
    """
    # Define indexes
    indexes = [
        # B-tree indexes for exact lookups
        """
        CREATE INDEX destination_country_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.country)
        """,
        """
        CREATE INDEX destination_type_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.type)
        """,
        """
        CREATE INDEX trip_user_id_index IF NOT EXISTS
        FOR (t:Trip)
        ON (t.user_id)
        """,
        # Text indexes for text search
        """
        CREATE TEXT INDEX destination_description_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.description)
        """,
        # Composite indexes
        """
        CREATE INDEX destination_location_index IF NOT EXISTS
        FOR (d:Destination)
        ON (d.latitude, d.longitude)
        """,
    ]

    # Create each index
    for index in indexes:
        try:
            connection.run_query(index)
            logger.info("Created index: %s", index.strip().splitlines()[1])
        except Exception as e:
            logger.error(
                "Failed to create index: %s - Error: %s",
                index.strip().splitlines()[1],
                str(e),
            )
            raise

    logger.info("All Neo4j indexes created successfully")
    return True
