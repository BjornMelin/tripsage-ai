"""
Destination repository for Neo4j.

This module provides a repository implementation for Destination entities
in the Neo4j knowledge graph.
"""

from typing import Any, Dict, List, Optional

from src.db.neo4j.repositories.base import BaseNeo4jRepository
from src.db.neo4j.schemas.destination import Destination
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class DestinationRepository(BaseNeo4jRepository[Destination]):
    """Repository for Destination entities."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(Destination, "Destination")

    async def find_by_country(self, country: str) -> List[Destination]:
        """Find destinations by country.

        Args:
            country: The country to search for

        Returns:
            List of destinations in the country
        """
        try:
            # Build Cypher query
            query = """
            MATCH (d:Destination)
            WHERE d.country = $country
            RETURN d
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"country": country}
            )

            # Convert to entities
            destinations = []
            for record in result:
                destination = Destination.from_neo4j_node(record["d"])
                destinations.append(destination)

            return destinations

        except Exception as e:
            logger.error("Failed to find destinations by country: %s", str(e))
            raise

    async def find_nearby(
        self, latitude: float, longitude: float, distance_km: float = 50
    ) -> List[Destination]:
        """Find destinations near a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            distance_km: Maximum distance in kilometers

        Returns:
            List of nearby destinations
        """
        try:
            # Build Cypher query
            # This uses the Haversine formula to calculate distance
            query = """
            MATCH (d:Destination)
            WHERE d.latitude IS NOT NULL AND d.longitude IS NOT NULL
            WITH d,
                6371 * acos(
                    cos(radians($latitude)) *
                    cos(radians(d.latitude)) *
                    cos(radians(d.longitude) - radians($longitude)) +
                    sin(radians($latitude)) *
                    sin(radians(d.latitude))
                ) AS distance
            WHERE distance <= $distance_km
            RETURN d, distance
            ORDER BY distance
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "latitude": latitude,
                    "longitude": longitude,
                    "distance_km": distance_km,
                },
            )

            # Convert to entities
            destinations = []
            for record in result:
                destination = Destination.from_neo4j_node(record["d"])
                destinations.append(destination)

            return destinations

        except Exception as e:
            logger.error("Failed to find nearby destinations: %s", str(e))
            raise

    async def create_relationship(
        self,
        from_destination: str,
        relationship_type: str,
        to_destination: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Create a relationship between destinations.

        Args:
            from_destination: Name of the source destination
            relationship_type: Type of relationship (e.g., NEAR, CONNECTS_TO)
            to_destination: Name of the target destination
            properties: Optional relationship properties

        Returns:
            True if relationship created successfully
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (a:Destination), (b:Destination)
            WHERE a.name = $from_name AND b.name = $to_name
            CREATE (a)-[r:{relationship_type}]->(b)
            SET r = $properties
            RETURN r
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "from_name": from_destination,
                    "to_name": to_destination,
                    "properties": properties or {},
                },
            )

            return len(result) > 0

        except Exception as e:
            logger.error("Failed to create relationship: %s", str(e))
            raise

    async def find_by_popularity(
        self, min_rating: float = 3.0, limit: int = 10
    ) -> List[Destination]:
        """Find destinations by popularity rating.

        Args:
            min_rating: Minimum safety rating
            limit: Maximum number of results

        Returns:
            List of popular destinations
        """
        try:
            # Build Cypher query
            query = """
            MATCH (d:Destination)
            WHERE d.safety_rating >= $min_rating
            RETURN d
            ORDER BY d.safety_rating DESC
            LIMIT $limit
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"min_rating": min_rating, "limit": limit}
            )

            # Convert to entities
            destinations = []
            for record in result:
                destination = Destination.from_neo4j_node(record["d"])
                destinations.append(destination)

            return destinations

        except Exception as e:
            logger.error("Failed to find popular destinations: %s", str(e))
            raise

    async def search_by_interests(
        self, interests: List[str], limit: int = 10
    ) -> List[Destination]:
        """Find destinations by interests.

        Args:
            interests: List of interests
            limit: Maximum number of results

        Returns:
            List of matching destinations
        """
        try:
            # Build Cypher query
            query = """
            MATCH (d:Destination)
            WHERE ANY(interest IN $interests WHERE interest IN d.popular_for)
            RETURN d, size([x IN $interests WHERE x IN d.popular_for]) AS matches
            ORDER BY matches DESC
            LIMIT $limit
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"interests": interests, "limit": limit}
            )

            # Convert to entities
            destinations = []
            for record in result:
                destination = Destination.from_neo4j_node(record["d"])
                destinations.append(destination)

            return destinations

        except Exception as e:
            logger.error("Failed to search destinations by interests: %s", str(e))
            raise
