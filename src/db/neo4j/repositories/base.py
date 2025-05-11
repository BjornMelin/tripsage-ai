"""
Base repository for Neo4j entities.

This module provides a base repository implementation for Neo4j entities,
with common CRUD operations and query methods.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

from src.db.neo4j.connection import Neo4jConnection
from src.db.neo4j.exceptions import Neo4jQueryError
from src.utils.logging import get_module_logger

T = TypeVar("T", bound=BaseModel)
logger = get_module_logger(__name__)


class BaseNeo4jRepository(Generic[T]):
    """Base repository for Neo4j entities."""

    def __init__(self, entity_class: Type[T], label: str):
        """Initialize the repository.

        Args:
            entity_class: The Pydantic model class for entities
            label: The Neo4j node label
        """
        self.entity_class = entity_class
        self.label = label
        self.connection = Neo4jConnection()

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create

        Returns:
            The created entity with any generated fields

        Raises:
            Neo4jValidationError: If entity validation fails
            Neo4jQueryError: If creation fails
        """
        try:
            # Ensure entity has updated timestamps
            if hasattr(entity, "created_at"):
                entity.created_at = datetime.utcnow()

            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.utcnow()

            # Convert to Neo4j properties
            properties = entity.to_neo4j_properties()

            # Build Cypher query
            query = f"""
            CREATE (n:{self.label} $properties)
            RETURN n
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"properties": properties}
            )

            if not result or len(result) == 0:
                raise Neo4jQueryError(f"Failed to create {self.label}")

            # Return the created entity
            return self.entity_class.from_neo4j_node(result[0]["n"])

        except Exception as e:
            logger.error("Failed to create %s: %s", self.label, str(e))
            raise

    async def get_by_id(self, id_value: str, id_field: str = "name") -> Optional[T]:
        """Get an entity by ID.

        Args:
            id_value: The ID value to search for
            id_field: The field to use as ID (default: "name")

        Returns:
            The entity if found, None otherwise

        Raises:
            Neo4jQueryError: If query fails
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            WHERE n.{id_field} = $id_value
            RETURN n
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"id_value": id_value}
            )

            if not result or len(result) == 0:
                return None

            # Return the entity
            return self.entity_class.from_neo4j_node(result[0]["n"])

        except Exception as e:
            logger.error("Failed to get %s by ID: %s", self.label, str(e))
            raise

    async def get_all(self, limit: int = 100, skip: int = 0) -> List[T]:
        """Get all entities with pagination.

        Args:
            limit: Maximum number of entities to return
            skip: Number of entities to skip

        Returns:
            List of entities

        Raises:
            Neo4jQueryError: If query fails
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            RETURN n
            SKIP $skip
            LIMIT $limit
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"skip": skip, "limit": limit}
            )

            # Convert to entities
            entities = []
            for record in result:
                entity = self.entity_class.from_neo4j_node(record["n"])
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error("Failed to get all %s: %s", self.label, str(e))
            raise

    async def update(self, id_value: str, entity: T, id_field: str = "name") -> T:
        """Update an entity.

        Args:
            id_value: The ID value to update
            entity: The updated entity
            id_field: The field to use as ID (default: "name")

        Returns:
            The updated entity

        Raises:
            Neo4jValidationError: If entity validation fails
            Neo4jQueryError: If update fails
        """
        try:
            # Ensure entity has updated timestamp
            if hasattr(entity, "updated_at"):
                entity.updated_at = datetime.utcnow()

            # Convert to Neo4j properties
            properties = entity.to_neo4j_properties()

            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            WHERE n.{id_field} = $id_value
            SET n = $properties
            RETURN n
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"id_value": id_value, "properties": properties}
            )

            if not result or len(result) == 0:
                raise Neo4jQueryError(f"Failed to update {self.label}: Not found")

            # Return the updated entity
            return self.entity_class.from_neo4j_node(result[0]["n"])

        except Exception as e:
            logger.error("Failed to update %s: %s", self.label, str(e))
            raise

    async def delete(self, id_value: str, id_field: str = "name") -> bool:
        """Delete an entity.

        Args:
            id_value: The ID value to delete
            id_field: The field to use as ID (default: "name")

        Returns:
            True if deleted, False if not found

        Raises:
            Neo4jQueryError: If deletion fails
        """
        try:
            # Build Cypher query
            query = f"""
            MATCH (n:{self.label})
            WHERE n.{id_field} = $id_value
            DETACH DELETE n
            RETURN count(*) as deleted
            """

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters={"id_value": id_value}
            )

            # Check if anything was deleted
            return result[0]["deleted"] > 0

        except Exception as e:
            logger.error("Failed to delete %s: %s", self.label, str(e))
            raise

    async def search(self, properties: Dict[str, Any], limit: int = 100) -> List[T]:
        """Search for entities by properties.

        Args:
            properties: Properties to search for
            limit: Maximum number of entities to return

        Returns:
            List of matching entities

        Raises:
            Neo4jQueryError: If search fails
        """
        try:
            # Build Cypher query with property conditions
            conditions = []
            parameters = {}

            for key, value in properties.items():
                if value is not None:
                    conditions.append(f"n.{key} = ${key}")
                    parameters[key] = value

            where_clause = " AND ".join(conditions) if conditions else "TRUE"

            query = f"""
            MATCH (n:{self.label})
            WHERE {where_clause}
            RETURN n
            LIMIT $limit
            """

            # Add limit to parameters
            parameters["limit"] = limit

            # Execute query
            result = await self.connection.run_query_async(
                query=query, parameters=parameters
            )

            # Convert to entities
            entities = []
            for record in result:
                entity = self.entity_class.from_neo4j_node(record["n"])
                entities.append(entity)

            return entities

        except Exception as e:
            logger.error("Failed to search %s: %s", self.label, str(e))
            raise
