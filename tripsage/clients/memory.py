"""Memory MCP client implementation."""

from typing import Any

from tripsage.clients.base import BaseMCPClient
from tripsage.tools.schemas.memory import (
    CreateEntitiesRequest,
    CreateEntitiesResponse,
    CreateRelationsRequest,
    CreateRelationsResponse,
    ReadGraphRequest,
    ReadGraphResponse,
    SearchNodesRequest,
    SearchNodesResponse,
)


class MemoryMCPClient(BaseMCPClient[Any, Any]):
    """Client for Memory MCP services."""

    async def create_entities(
        self, request: CreateEntitiesRequest
    ) -> CreateEntitiesResponse:
        """Create entities in the knowledge graph.

        Args:
            request: The create entities request.

        Returns:
            Create entities response.
        """
        return await self.call_mcp("create_entities", request)

    async def create_relations(
        self, request: CreateRelationsRequest
    ) -> CreateRelationsResponse:
        """Create relations in the knowledge graph.

        Args:
            request: The create relations request.

        Returns:
            Create relations response.
        """
        return await self.call_mcp("create_relations", request)

    async def search_nodes(self, request: SearchNodesRequest) -> SearchNodesResponse:
        """Search for nodes in the knowledge graph.

        Args:
            request: The search nodes request.

        Returns:
            Search nodes response.
        """
        return await self.call_mcp("search_nodes", request)

    async def read_graph(self, request: ReadGraphRequest) -> ReadGraphResponse:
        """Read the entire knowledge graph.

        Args:
            request: The read graph request.

        Returns:
            Read graph response.
        """
        return await self.call_mcp("read_graph", request)
