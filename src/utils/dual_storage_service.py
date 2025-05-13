"""
Dual Storage Service pattern for TripSage.

This module provides a base class for implementing the dual storage strategy,
where structured data is stored in a primary database (e.g., Supabase) and
relationships/unstructured data are stored in a graph database
(e.g., Neo4j via Memory MCP).
"""

import abc
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel

from src.utils.decorators import with_error_handling
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Generic type parameters for entity types
P = TypeVar("P", bound=BaseModel)  # Primary DB model
G = TypeVar("G", bound=BaseModel)  # Graph DB model


class DualStorageService(Generic[P, G], metaclass=abc.ABCMeta):
    """Base class for dual storage services in TripSage.

    This class implements the standard operations for dual storage,
    where structured data is stored in a primary database and
    relationships/unstructured data are stored in a graph database.
    """

    def __init__(self, primary_client: Any, graph_client: Any):
        """Initialize the dual storage service.

        Args:
            primary_client: Client for the primary database (e.g., Supabase)
            graph_client: Client for the graph database (e.g., Memory MCP/Neo4j)
        """
        self.primary_client = primary_client
        self.graph_client = graph_client
        self.entity_type = self.__class__.__name__.replace("Service", "")
        logger.debug(f"Initialized {self.entity_type} dual storage service")

    @with_error_handling
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an entity using the dual storage strategy.

        Args:
            data: Entity data to store

        Returns:
            Result of the creation operation
        """
        # Step 1: Store structured data in primary database
        logger.info(f"Storing structured {self.entity_type} data in primary database")
        primary_id = await self._store_in_primary(data)

        # Step 2: Store unstructured data and relationships in graph database
        logger.info(f"Storing unstructured {self.entity_type} data in graph database")

        # Create core entities
        created_entities = await self._create_graph_entities(data, primary_id)

        # Create related entities and relationships
        created_relations = await self._create_graph_relations(
            data, primary_id, created_entities
        )

        return {
            f"{self.entity_type.lower()}_id": primary_id,
            "entities_created": len(created_entities),
            "relations_created": len(created_relations),
            "primary_db": {"id": primary_id},
            "graph_db": {
                "entities": created_entities,
                "relations": created_relations,
            },
        }

    @with_error_handling
    async def retrieve(
        self, entity_id: str, include_graph: bool = False
    ) -> Dict[str, Any]:
        """Retrieve an entity using the dual storage strategy.

        Args:
            entity_id: ID of the entity to retrieve
            include_graph: Whether to include the full knowledge graph

        Returns:
            Combined entity data from both storage systems
        """
        # Step 1: Retrieve structured data from primary database
        logger.info(
            f"Retrieving structured {self.entity_type} data from primary database"
        )
        primary_data = await self._retrieve_from_primary(entity_id)

        if not primary_data:
            logger.warning(
                f"{self.entity_type} with ID {entity_id} not found in primary database"
            )
            return {"error": f"{self.entity_type} not found"}

        # Step 2: Retrieve graph data
        logger.info(f"Retrieving graph data for {self.entity_type} {entity_id}")
        graph_data = await self._retrieve_from_graph(entity_id, include_graph)

        # Step 3: Combine the data
        combined_data = await self._combine_data(primary_data, graph_data)

        return combined_data

    @with_error_handling
    async def update(self, entity_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an entity using the dual storage strategy.

        Args:
            entity_id: ID of the entity to update
            data: Updated entity data

        Returns:
            Result of the update operation
        """
        # Step 1: Update structured data in primary database
        logger.info(f"Updating structured {self.entity_type} data in primary database")
        primary_updated = await self._update_in_primary(entity_id, data)

        # Step 2: Update graph data
        logger.info(f"Updating graph data for {self.entity_type} {entity_id}")
        graph_updated = await self._update_in_graph(entity_id, data)

        return {
            f"{self.entity_type.lower()}_id": entity_id,
            "primary_db_updated": primary_updated,
            "graph_db_updated": graph_updated,
        }

    @with_error_handling
    async def delete(self, entity_id: str) -> Dict[str, Any]:
        """Delete an entity using the dual storage strategy.

        Args:
            entity_id: ID of the entity to delete

        Returns:
            Result of the deletion operation
        """
        # Step 1: Delete from primary database
        logger.info(f"Deleting {self.entity_type} {entity_id} from primary database")
        primary_deleted = await self._delete_from_primary(entity_id)

        # Step 2: Delete from graph database
        logger.info(f"Deleting {self.entity_type} {entity_id} from graph database")
        graph_deleted = await self._delete_from_graph(entity_id)

        return {
            f"{self.entity_type.lower()}_id": entity_id,
            "primary_db_deleted": primary_deleted,
            "graph_db_deleted": graph_deleted,
        }

    @abc.abstractmethod
    async def _store_in_primary(self, data: Dict[str, Any]) -> str:
        """Store structured data in the primary database.

        Args:
            data: Entity data dictionary

        Returns:
            Entity ID
        """
        pass

    @abc.abstractmethod
    async def _create_graph_entities(
        self, data: Dict[str, Any], entity_id: str
    ) -> List[Dict[str, Any]]:
        """Create entities for the entity in the graph database.

        Args:
            data: Entity data dictionary
            entity_id: Entity ID

        Returns:
            List of created entities
        """
        pass

    @abc.abstractmethod
    async def _create_graph_relations(
        self,
        data: Dict[str, Any],
        entity_id: str,
        created_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Create relationships for the entity in the graph database.

        Args:
            data: Entity data dictionary
            entity_id: Entity ID
            created_entities: List of created entities

        Returns:
            List of created relations
        """
        pass

    @abc.abstractmethod
    async def _retrieve_from_primary(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve structured data from the primary database.

        Args:
            entity_id: Entity ID

        Returns:
            Entity data from primary database
        """
        pass

    @abc.abstractmethod
    async def _retrieve_from_graph(
        self, entity_id: str, include_graph: bool = False
    ) -> Dict[str, Any]:
        """Retrieve graph data from the graph database.

        Args:
            entity_id: Entity ID
            include_graph: Whether to include the full knowledge graph

        Returns:
            Entity data from graph database
        """
        pass

    @abc.abstractmethod
    async def _combine_data(
        self, primary_data: Dict[str, Any], graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine data from primary and graph databases.

        Args:
            primary_data: Data from primary database
            graph_data: Data from graph database

        Returns:
            Combined entity data
        """
        pass

    @abc.abstractmethod
    async def _update_in_primary(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update structured data in the primary database.

        Args:
            entity_id: Entity ID
            data: Updated entity data

        Returns:
            Whether the update was successful
        """
        pass

    @abc.abstractmethod
    async def _update_in_graph(self, entity_id: str, data: Dict[str, Any]) -> bool:
        """Update graph data in the graph database.

        Args:
            entity_id: Entity ID
            data: Updated entity data

        Returns:
            Whether the update was successful
        """
        pass

    @abc.abstractmethod
    async def _delete_from_primary(self, entity_id: str) -> bool:
        """Delete entity from the primary database.

        Args:
            entity_id: Entity ID

        Returns:
            Whether the deletion was successful
        """
        pass

    @abc.abstractmethod
    async def _delete_from_graph(self, entity_id: str) -> bool:
        """Delete entity from the graph database.

        Args:
            entity_id: Entity ID

        Returns:
            Whether the deletion was successful
        """
        pass
