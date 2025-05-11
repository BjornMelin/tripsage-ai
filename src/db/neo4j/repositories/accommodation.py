"""
Accommodation repository for Neo4j.

This module provides a repository implementation for Accommodation entities in Neo4j.
"""

from typing import List, Optional

from src.db.neo4j.repositories.base import BaseNeo4jRepository
from src.db.neo4j.schemas.accommodation import Accommodation
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class AccommodationRepository(BaseNeo4jRepository[Accommodation]):
    """Repository for Accommodation entities in Neo4j."""

    def __init__(self):
        """Initialize the repository."""
        super().__init__(entity_class=Accommodation, label="Accommodation")

    async def find_by_destination(self, destination_name: str) -> List[Accommodation]:
        """Find accommodations by destination.

        Args:
            destination_name: Destination name

        Returns:
            List of accommodations at the specified destination
        """
        try:
            # Build Cypher query
            query = """
            MATCH (a:Accommodation)
            WHERE a.destination = $destination_name
            RETURN a
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"destination_name": destination_name}
            )

            # Convert to accommodations
            accommodations = []
            for record in result:
                accommodation = Accommodation.from_neo4j_node(record["a"])
                accommodations.append(accommodation)

            return accommodations

        except Exception as e:
            logger.error("Failed to find accommodations by destination: %s", str(e))
            raise

    async def find_by_type(
        self, accommodation_type: str, destination: Optional[str] = None
    ) -> List[Accommodation]:
        """Find accommodations by type, optionally at a specific destination.

        Args:
            accommodation_type: Accommodation type
            destination: Optional destination name

        Returns:
            List of matching accommodations
        """
        try:
            # Build parameters
            parameters = {"accommodation_type": accommodation_type}
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "a.type = $accommodation_type AND a.destination = $destination"
                )
            else:
                where_clause = "a.type = $accommodation_type"

            # Build Cypher query
            query = f"""
            MATCH (a:Accommodation)
            WHERE {where_clause}
            RETURN a
            ORDER BY a.rating DESC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to accommodations
            accommodations = []
            for record in result:
                accommodation = Accommodation.from_neo4j_node(record["a"])
                accommodations.append(accommodation)

            return accommodations

        except Exception as e:
            logger.error("Failed to find accommodations by type: %s", str(e))
            raise

    async def create_accommodation_destination_relationship(
        self, accommodation_name: str, destination_name: str
    ) -> bool:
        """Create a relationship between an accommodation and a destination.

        Args:
            accommodation_name: Accommodation name
            destination_name: Destination name

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build Cypher query
            query = """
            MATCH (a:Accommodation {name: $accommodation_name})
            MATCH (d:Destination {name: $destination_name})
            CREATE (a)-[r:LOCATED_IN]->(d)
            RETURN r
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query,
                parameters={
                    "accommodation_name": accommodation_name,
                    "destination_name": destination_name,
                },
            )

            return len(result) > 0

        except Exception as e:
            logger.error(
                "Failed to create accommodation-destination relationship: %s", str(e)
            )
            raise

    async def find_by_price_range(
        self, min_price: float, max_price: float, destination: Optional[str] = None
    ) -> List[Accommodation]:
        """Find accommodations within a price range.

        Args:
            min_price: Minimum price per night
            max_price: Maximum price per night
            destination: Optional destination name

        Returns:
            List of matching accommodations
        """
        try:
            # Build parameters
            parameters = {"min_price": min_price, "max_price": max_price}
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "a.price_per_night >= $min_price AND "
                    "a.price_per_night <= $max_price"
                )
            else:
                where_clause = (
                    "a.price_per_night >= $min_price AND "
                    "a.price_per_night <= $max_price"
                )

            # Build Cypher query
            query = f"""
            MATCH (a:Accommodation)
            WHERE {where_clause}
            RETURN a
            ORDER BY a.price_per_night ASC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to accommodations
            accommodations = []
            for record in result:
                accommodation = Accommodation.from_neo4j_node(record["a"])
                accommodations.append(accommodation)

            return accommodations

        except Exception as e:
            logger.error("Failed to find accommodations by price range: %s", str(e))
            raise

    async def find_with_amenities(
        self, amenities: List[str], destination: Optional[str] = None
    ) -> List[Accommodation]:
        """Find accommodations with specific amenities.

        Args:
            amenities: List of required amenities
            destination: Optional destination name

        Returns:
            List of matching accommodations
        """
        try:
            # Build parameters
            parameters = {"amenities": amenities}
            if destination:
                parameters["destination"] = destination
                where_clause = (
                    "ALL(amenity IN $amenities WHERE amenity IN a.amenities) "
                    "AND a.destination = $destination"
                )
            else:
                where_clause = (
                    "ALL(amenity IN $amenities WHERE amenity IN a.amenities)"
                )

            # Build Cypher query
            query = f"""
            MATCH (a:Accommodation)
            WHERE {where_clause}
            RETURN a
            ORDER BY a.rating DESC
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to accommodations
            accommodations = []
            for record in result:
                accommodation = Accommodation.from_neo4j_node(record["a"])
                accommodations.append(accommodation)

            return accommodations

        except Exception as e:
            logger.error("Failed to find accommodations with amenities: %s", str(e))
            raise
