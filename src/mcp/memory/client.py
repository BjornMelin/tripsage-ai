"""
Memory MCP client.

This module provides a client implementation for accessing the Memory MCP
service, which interfaces with the Neo4j knowledge graph.
"""

from typing import Any, Dict, List, Optional

from src.mcp.base_mcp_client import BaseMcpClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class MemoryClient(BaseMcpClient):
    """Client for interacting with the Memory MCP service."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the Memory MCP client.

        Args:
            base_url: Optional base URL of the Memory MCP service
        """
        super().__init__(base_url=base_url, service_name="memory")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory client.

        This ensures that the knowledge graph is properly initialized.
        """
        if not self._initialized:
            self._initialized = True
            logger.info("Memory client initialized successfully")

    async def create_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create multiple entities in the knowledge graph.

        Args:
            entities: List of entity data dictionaries, each containing 'name',
                'entityType', and 'observations'

        Returns:
            List of created entities with their IDs
        """
        logger.info(f"Creating {len(entities)} entities via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="create_entities",
            data={"entities": entities},
        )
        
        return response.get("entities", [])

    async def create_relations(
        self, relations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create relations between entities in the knowledge graph.

        Args:
            relations: List of relation dictionaries, each containing 'from',
                'relationType', and 'to'

        Returns:
            List of created relations
        """
        logger.info(f"Creating {len(relations)} relations via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="create_relations",
            data={"relations": relations},
        )
        
        return response.get("relations", [])

    async def add_observations(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add observations to existing entities.

        Args:
            observations: List of observation dictionaries, each containing
                'entityName' and 'contents' (list of strings)

        Returns:
            List of updated entities
        """
        logger.info(f"Adding observations to {len(observations)} entities via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="add_observations",
            data={"observations": observations},
        )
        
        return response.get("entities", [])

    async def delete_entities(self, entity_names: List[str]) -> List[str]:
        """Delete entities from the knowledge graph.

        Args:
            entity_names: List of entity names to delete

        Returns:
            List of deleted entity names
        """
        logger.info(f"Deleting {len(entity_names)} entities via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="delete_entities",
            data={"entityNames": entity_names},
        )
        
        return response.get("deleted", [])

    async def delete_relations(
        self, relations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Delete relations from the knowledge graph.

        Args:
            relations: List of relation dictionaries, each containing 'from',
                'relationType', and 'to'

        Returns:
            List of deleted relations
        """
        logger.info(f"Deleting {len(relations)} relations via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="delete_relations",
            data={"relations": relations},
        )
        
        return response.get("deleted", [])

    async def delete_observations(
        self, deletions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Delete specific observations from entities in the knowledge graph.

        Args:
            deletions: List of dictionaries, each containing 'entityName' and
                'observations' to delete

        Returns:
            List of updated entities
        """
        logger.info(f"Deleting observations from {len(deletions)} entities via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="delete_observations",
            data={"deletions": deletions},
        )
        
        return response.get("entities", [])

    async def read_graph(self) -> Dict[str, Any]:
        """Read the entire knowledge graph.

        Returns:
            Dictionary containing entities and relations
        """
        logger.info("Reading entire knowledge graph via Memory MCP")
        
        response = await self._make_request(
            method="GET",
            endpoint="read_graph",
        )
        
        return {
            "entities": response.get("entities", []),
            "relations": response.get("relations", []),
            "statistics": response.get("statistics", {})
        }

    async def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """Search for nodes in the knowledge graph.

        Args:
            query: Search query string

        Returns:
            List of matching nodes
        """
        logger.info(f"Searching for nodes with query: {query} via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="search_nodes",
            data={"query": query},
        )
        
        return response.get("nodes", [])

    async def open_nodes(self, names: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information about specific nodes.

        Args:
            names: List of node names to retrieve

        Returns:
            List of node details
        """
        logger.info(f"Opening {len(names)} nodes via Memory MCP")
        
        response = await self._make_request(
            method="POST",
            endpoint="open_nodes",
            data={"names": names},
        )
        
        return response.get("nodes", [])


# Create a singleton instance
memory_client = MemoryClient()