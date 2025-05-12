"""
Activity repository for Neo4j.

This module provides a repository implementation for Activity entities in Neo4j.
"""

from typing import List, Optional

from src.db.neo4j.repositories.base import BaseNeo4jRepository
from src.db.neo4j.schemas.activity import Activity
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class ActivityRepository(BaseNeo4jRepository[Activity]):
    """Repository for Activity entities in Neo4j."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(entity_class=Activity, label="Activity")

    async def find_by_destination(self, destination_name: str) -> List[Activity]:
        """Find activities by destination.

        Args:
            destination_name: Destination name

        Returns:
            List of activities at the specified destination
        """
        try:
            # Build Cypher query
            query = """
            MATCH (a:Activity)
            WHERE a.destination = $destination_name
            RETURN a
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"destination_name": destination_name}
            )

            # Convert to activities
            activities = []
            for record in result:
                activity = Activity.from_neo4j_node(record["a"])
                activities.append(activity)

            return activities

        except Exception as e:
            logger.error("Failed to find activities by destination: %s", str(e))
            raise

    async def find_by_type(
        self, activity_type: str, destination: Optional[str] = None
    ) -> List[Activity]:
        """Find activities by type, optionally at a specific destination.

        Args:
            activity_type: Activity type
            destination: Optional destination name

        Returns:
            List of matching activities
        """
        try:
            # Build parameters
            parameters = {"activity_type": activity_type}
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "a.type = $activity_type AND a.destination = $destination"
                )
            else:
                where_clause = "a.type = $activity_type"

            # Build Cypher query
            query = f"""
            MATCH (a:Activity)
            WHERE {where_clause}
            RETURN a
            ORDER BY a.rating DESC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to activities
            activities = []
            for record in result:
                activity = Activity.from_neo4j_node(record["a"])
                activities.append(activity)

            return activities

        except Exception as e:
            logger.error("Failed to find activities by type: %s", str(e))
            raise

    async def create_activity_destination_relationship(
        self, activity_name: str, destination_name: str
    ) -> bool:
        """Create a relationship between an activity and a destination.

        Args:
            activity_name: Activity name
            destination_name: Destination name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build Cypher query
            query = """
            MATCH (a:Activity {name: $activity_name})
            MATCH (d:Destination {name: $destination_name})
            CREATE (a)-[r:LOCATED_IN]->(d)
            RETURN r
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "activity_name": activity_name,
                    "destination_name": destination_name,
                },
            )

            return len(result) > 0

        except Exception as e:
            logger.error(
                "Failed to create activity-destination relationship: %s", str(e)
            )
            raise

    async def find_by_price_range(
        self, min_price: float, max_price: float, destination: Optional[str] = None
    ) -> List[Activity]:
        """Find activities within a price range.

        Args:
            min_price: Minimum price
            max_price: Maximum price
            destination: Optional destination name

        Returns:
            List of matching activities
        """
        try:
            # Build parameters
            parameters = {"min_price": min_price, "max_price": max_price}
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "a.price >= $min_price AND a.price <= $max_price "
                    "AND a.destination = $destination"
                )
            else:
                where_clause = "a.price >= $min_price AND a.price <= $max_price"

            # Build Cypher query
            query = f"""
            MATCH (a:Activity)
            WHERE {where_clause}
            RETURN a
            ORDER BY a.price ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to activities
            activities = []
            for record in result:
                activity = Activity.from_neo4j_node(record["a"])
                activities.append(activity)

            return activities

        except Exception as e:
            logger.error("Failed to find activities by price range: %s", str(e))
            raise

    async def find_top_rated(
        self, limit: int = 10, destination: Optional[str] = None
    ) -> List[Activity]:
        """Find top-rated activities.

        Args:
            limit: Maximum number of activities to return
            destination: Optional destination name

        Returns:
            List of top-rated activities
        """
        try:
            # Build parameters
            parameters = {"limit": limit}
            if destination:
                parameters["destination"] = destination
                where_clause = "a.destination = $destination AND a.rating IS NOT NULL"
            else:
                where_clause = "a.rating IS NOT NULL"

            # Build Cypher query
            query = f"""
            MATCH (a:Activity)
            WHERE {where_clause}
            RETURN a
            ORDER BY a.rating DESC
            LIMIT $limit
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to activities
            activities = []
            for record in result:
                activity = Activity.from_neo4j_node(record["a"])
                activities.append(activity)

            return activities

        except Exception as e:
            logger.error("Failed to find top-rated activities: %s", str(e))
            raise
