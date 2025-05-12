"""
Neo4j constraints migrations.

This module provides functions to create database constraints for Neo4j,
ensuring data integrity for the knowledge graph.
"""

from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


def create_constraints(connection) -> bool:
    """Create Neo4j constraints.

    Args:
        connection: Neo4j connection instance

    Returns:
        True if successful

    Raises:
        Neo4jQueryError: If constraint creation fails
    """
    # Define constraints
    constraints = [
        # Uniqueness constraints
        """
        CREATE CONSTRAINT destination_name_unique IF NOT EXISTS
        FOR (d:Destination)
        REQUIRE d.name IS UNIQUE
        """,
        """
        CREATE CONSTRAINT user_email_unique IF NOT EXISTS
        FOR (u:User)
        REQUIRE u.email IS UNIQUE
        """,
        """
        CREATE CONSTRAINT trip_id_unique IF NOT EXISTS
        FOR (t:Trip)
        REQUIRE t.id IS UNIQUE
        """,
        # Existence constraints
        """
        CREATE CONSTRAINT destination_country_exists IF NOT EXISTS
        FOR (d:Destination)
        REQUIRE d.country IS NOT NULL
        """,
        """
        CREATE CONSTRAINT user_name_exists IF NOT EXISTS
        FOR (u:User)
        REQUIRE u.name IS NOT NULL
        """,
    ]

    # Create each constraint
    for constraint in constraints:
        try:
            connection.run_query(constraint)
            logger.info("Created constraint: %s", constraint.strip().splitlines()[1])
        except Exception as e:
            logger.error(
                "Failed to create constraint: %s - Error: %s",
                constraint.strip().splitlines()[1],
                str(e),
            )
            raise

    logger.info("All Neo4j constraints created successfully")
    return True
