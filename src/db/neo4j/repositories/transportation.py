"""
Transportation repository for Neo4j.

This module provides a repository implementation for Transportation entities in Neo4j.
"""

from datetime import datetime
from typing import List, Optional

from src.db.neo4j.repositories.base import BaseNeo4jRepository
from src.db.neo4j.schemas.transportation import Transportation
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class TransportationRepository(BaseNeo4jRepository[Transportation]):
    """Repository for Transportation entities in Neo4j."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(entity_class=Transportation, label="Transportation")

    async def find_by_type(self, transportation_type: str) -> List[Transportation]:
        """Find transportation by type.

        Args:
            transportation_type: Transportation type

        Returns:
            List of matching transportation options
        """
        try:
            # Build Cypher query
            query = """
            MATCH (t:Transportation)
            WHERE t.type = $type
            RETURN t
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"type": transportation_type}
            )

            # Convert to transportation objects
            transportation_list = []
            for record in result:
                transportation = Transportation.from_neo4j_node(record["t"])
                transportation_list.append(transportation)

            return transportation_list

        except Exception as e:
            logger.error("Failed to find transportation by type: %s", str(e))
            raise

    async def find_routes(
        self, origin: str, destination: str, transportation_type: Optional[str] = None
    ) -> List[Transportation]:
        """Find transportation routes between origin and destination.

        Args:
            origin: Origin location
            destination: Destination location
            transportation_type: Optional transportation type filter

        Returns:
            List of matching transportation options
        """
        try:
            # Build parameters and where clause
            parameters = {"origin": origin, "destination": destination}
            if transportation_type:
                parameters["type"] = transportation_type
                where_clause = (
                    "t.origin = $origin AND t.destination = $destination AND "
                    "t.type = $type"
                )
            else:
                where_clause = (
                    "t.origin = $origin AND t.destination = $destination"
                )

            # Build Cypher query
            query = f"""
            MATCH (t:Transportation)
            WHERE {where_clause}
            RETURN t
            ORDER BY t.departure_time ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to transportation objects
            transportation_list = []
            for record in result:
                transportation = Transportation.from_neo4j_node(record["t"])
                transportation_list.append(transportation)

            return transportation_list

        except Exception as e:
            logger.error("Failed to find transportation routes: %s", str(e))
            raise

    async def create_route_relationship(
        self,
        transportation_id: str,
        origin_destination: str,
        target_destination: str,
    ) -> bool:
        """Create relationships between transportation and destinations.

        Args:
            transportation_id: Transportation ID
            origin_destination: Origin destination name
            target_destination: Target destination name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build Cypher query for the relationships
            query = """
            MATCH (t:Transportation {name: $transportation_id})
            MATCH (origin:Destination {name: $origin})
            MATCH (target:Destination {name: $target})
            CREATE (t)-[r1:DEPARTS_FROM]->(origin)
            CREATE (t)-[r2:ARRIVES_AT]->(target)
            RETURN r1, r2
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "transportation_id": transportation_id,
                    "origin": origin_destination,
                    "target": target_destination,
                },
            )

            return len(result) > 0

        except Exception as e:
            logger.error("Failed to create route relationships: %s", str(e))
            raise

    async def find_by_date_range(
        self,
        origin: str,
        destination: str,
        start_date: datetime,
        end_date: datetime,
        transportation_type: Optional[str] = None,
    ) -> List[Transportation]:
        """Find transportation options within a date range.

        Args:
            origin: Origin location
            destination: Destination location
            start_date: Earliest departure date
            end_date: Latest departure date
            transportation_type: Optional transportation type filter

        Returns:
            List of matching transportation options
        """
        try:
            # Build parameters
            parameters = {
                "origin": origin,
                "destination": destination,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }

            # Build where clause
            where_clause = (
                "t.origin = $origin AND t.destination = $destination "
                "AND t.departure_time >= $start_date AND t.departure_time <= $end_date"
            )
            if transportation_type:
                parameters["type"] = transportation_type
                where_clause += " AND t.type = $type"

            # Build Cypher query
            query = f"""
            MATCH (t:Transportation)
            WHERE {where_clause}
            RETURN t
            ORDER BY t.departure_time ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to transportation objects
            transportation_list = []
            for record in result:
                transportation = Transportation.from_neo4j_node(record["t"])
                transportation_list.append(transportation)

            return transportation_list

        except Exception as e:
            logger.error("Failed to find transportation by date range: %s", str(e))
            raise

    async def find_by_price_range(
        self,
        origin: str,
        destination: str,
        min_price: float,
        max_price: float,
        transportation_type: Optional[str] = None,
    ) -> List[Transportation]:
        """Find transportation options within a price range.

        Args:
            origin: Origin location
            destination: Destination location
            min_price: Minimum price
            max_price: Maximum price
            transportation_type: Optional transportation type filter

        Returns:
            List of matching transportation options
        """
        try:
            # Build parameters
            parameters = {
                "origin": origin,
                "destination": destination,
                "min_price": min_price,
                "max_price": max_price,
            }

            # Build where clause
            where_clause = (
                "t.origin = $origin AND t.destination = $destination "
                "AND t.price >= $min_price AND t.price <= $max_price"
            )
            if transportation_type:
                parameters["type"] = transportation_type
                where_clause += " AND t.type = $type"

            # Build Cypher query
            query = f"""
            MATCH (t:Transportation)
            WHERE {where_clause}
            RETURN t
            ORDER BY t.price ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to transportation objects
            transportation_list = []
            for record in result:
                transportation = Transportation.from_neo4j_node(record["t"])
                transportation_list.append(transportation)

            return transportation_list

        except Exception as e:
            logger.error("Failed to find transportation by price range: %s", str(e))
            raise
