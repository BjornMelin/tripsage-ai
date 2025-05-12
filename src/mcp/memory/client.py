"""
Memory MCP client.

This module provides a client implementation for accessing the Memory MCP
service, which interfaces with the Neo4j knowledge graph.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar, cast

from pydantic import ValidationError

from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..base_mcp_client import BaseMCPClient
from .models import (
    AddObservationsParams,
    AddObservationsResponse,
    CreateEntitiesParams,
    CreateEntitiesResponse,
    CreateRelationsParams,
    CreateRelationsResponse,
    DeleteEntitiesParams,
    DeleteEntitiesResponse,
    DeleteObservationsParams,
    DeleteObservationsResponse,
    DeleteRelationsParams,
    DeleteRelationsResponse,
    Entity,
    GraphResponse,
    Observation,
    OpenNodesParams,
    OpenNodesResponse,
    Relation,
    SearchNodesParams,
    SearchNodesResponse,
)

logger = get_module_logger(__name__)

# Define generic types for parameter and response models
P = TypeVar("P")
R = TypeVar("R")


class MemoryMCPClient(BaseMCPClient, Generic[P, R]):
    """Client for the Memory MCP server.

    This client interfaces with the Memory MCP server, which provides
    knowledge graph operations for storing travel-related data.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        use_cache: bool = True,
    ):
        """Initialize the Memory MCP client.

        Args:
            endpoint: API endpoint for the Memory MCP server (defaults to settings)
            api_key: API key for authentication (defaults to settings)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        if endpoint is None:
            endpoint = settings.memory_mcp.endpoint

        if api_key is None and settings.memory_mcp.api_key:
            api_key = settings.memory_mcp.api_key.get_secret_value()

        super().__init__(
            server_name="Memory",
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
        )

        logger.debug("Initialized Memory MCP client for %s", endpoint)
        self._initialized = False

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: P,
        response_model: type[R],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Call a tool and validate both parameters and response.

        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool (validated Pydantic model)
            response_model: Response model to validate the response
            skip_cache: Whether to skip the cache
            cache_key: Custom cache key
            cache_ttl: Custom cache TTL in seconds

        Returns:
            Validated response

        Raises:
            MCPError: If the request fails or validation fails
        """
        try:
            # Convert parameters to dict using model_dump() for Pydantic v2
            params_dict = (
                params.model_dump(exclude_none=True)
                if hasattr(params, "model_dump")
                else params
            )

            # Call the tool
            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            try:
                # Validate response
                validated_response = response_model.model_validate(response)
                return validated_response
            except ValidationError as e:
                logger.warning(f"Response validation failed for {tool_name}: {str(e)}")
                # Return the raw response if validation fails
                # This is to ensure backward compatibility
                return cast(R, response)
        except ValidationError as e:
            logger.error(f"Parameter validation failed for {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e
        except Exception as e:
            logger.error(f"Error calling {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Failed to call {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params,
            ) from e

    async def initialize(self) -> None:
        """Initialize the memory client.

        This ensures that the knowledge graph is properly initialized.
        """
        if not self._initialized:
            self._initialized = True
            logger.info("Memory MCP client initialized successfully")

    async def create_entities(
        self, entities: List[Dict[str, Any]]
    ) -> CreateEntitiesResponse:
        """Create multiple entities in the knowledge graph.

        Args:
            entities: List of entity data dictionaries, each containing 'name',
                'entityType', and 'observations'

        Returns:
            CreateEntitiesResponse with the created entities and status message

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Convert raw entities to Pydantic models
            entity_models = [Entity.model_validate(entity) for entity in entities]

            # Create the params model
            params = CreateEntitiesParams(entities=entity_models)

            # Call with validation
            response = await self._call_validate_tool(
                "create_entities", params, CreateEntitiesResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in create_entities: {str(e)}")
            raise MCPError(
                message=f"Invalid entity data: {str(e)}",
                server=self.server_name,
                tool="create_entities",
                params={"entities": entities},
            ) from e
        except Exception as e:
            logger.error(f"Error creating entities: {str(e)}")
            raise MCPError(
                message=f"Failed to create entities: {str(e)}",
                server=self.server_name,
                tool="create_entities",
                params={"entities": entities},
            ) from e

    async def create_relations(
        self, relations: List[Dict[str, Any]]
    ) -> CreateRelationsResponse:
        """Create relations between entities in the knowledge graph.

        Args:
            relations: List of relation dictionaries, each containing 'from',
                'relationType', and 'to'

        Returns:
            CreateRelationsResponse with the created relations and status message

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Convert raw relations to Pydantic models
            relation_models = [
                Relation.model_validate(relation) for relation in relations
            ]

            # Create the params model
            params = CreateRelationsParams(relations=relation_models)

            # Call with validation
            response = await self._call_validate_tool(
                "create_relations", params, CreateRelationsResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in create_relations: {str(e)}")
            raise MCPError(
                message=f"Invalid relation data: {str(e)}",
                server=self.server_name,
                tool="create_relations",
                params={"relations": relations},
            ) from e
        except Exception as e:
            logger.error(f"Error creating relations: {str(e)}")
            raise MCPError(
                message=f"Failed to create relations: {str(e)}",
                server=self.server_name,
                tool="create_relations",
                params={"relations": relations},
            ) from e

    async def add_observations(
        self, observations: List[Dict[str, Any]]
    ) -> AddObservationsResponse:
        """Add observations to existing entities.

        Args:
            observations: List of observation dictionaries, each containing
                'entityName' and 'contents' (list of strings)

        Returns:
            AddObservationsResponse with the updated entities and status message

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Convert raw observations to Pydantic models
            observation_models = [
                Observation.model_validate(obs) for obs in observations
            ]

            # Create the params model
            params = AddObservationsParams(observations=observation_models)

            # Call with validation
            response = await self._call_validate_tool(
                "add_observations", params, AddObservationsResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in add_observations: {str(e)}")
            raise MCPError(
                message=f"Invalid observation data: {str(e)}",
                server=self.server_name,
                tool="add_observations",
                params={"observations": observations},
            ) from e
        except Exception as e:
            logger.error(f"Error adding observations: {str(e)}")
            raise MCPError(
                message=f"Failed to add observations: {str(e)}",
                server=self.server_name,
                tool="add_observations",
                params={"observations": observations},
            ) from e

    async def delete_entities(self, entity_names: List[str]) -> DeleteEntitiesResponse:
        """Delete entities from the knowledge graph.

        Args:
            entity_names: List of entity names to delete

        Returns:
            DeleteEntitiesResponse with the deleted count and status message

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Create the params model
            params = DeleteEntitiesParams(entityNames=entity_names)

            # Call with validation
            response = await self._call_validate_tool(
                "delete_entities", params, DeleteEntitiesResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in delete_entities: {str(e)}")
            raise MCPError(
                message=f"Invalid entity names: {str(e)}",
                server=self.server_name,
                tool="delete_entities",
                params={"entityNames": entity_names},
            ) from e
        except Exception as e:
            logger.error(f"Error deleting entities: {str(e)}")
            raise MCPError(
                message=f"Failed to delete entities: {str(e)}",
                server=self.server_name,
                tool="delete_entities",
                params={"entityNames": entity_names},
            ) from e

    async def delete_observations(
        self, deletions: List[Dict[str, Any]]
    ) -> DeleteObservationsResponse:
        """Delete specific observations from entities in the knowledge graph.

        Args:
            deletions: List of dictionaries, each containing 'entityName' and
                'contents' (observations to delete)

        Returns:
            DeleteObservationsResponse with the updated entities and status message

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Convert raw deletions to Pydantic models
            deletion_models = [
                Observation.model_validate(deletion) for deletion in deletions
            ]

            # Create the params model
            params = DeleteObservationsParams(deletions=deletion_models)

            # Call with validation
            response = await self._call_validate_tool(
                "delete_observations", params, DeleteObservationsResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in delete_observations: {str(e)}")
            raise MCPError(
                message=f"Invalid deletion data: {str(e)}",
                server=self.server_name,
                tool="delete_observations",
                params={"deletions": deletions},
            ) from e
        except Exception as e:
            logger.error(f"Error deleting observations: {str(e)}")
            raise MCPError(
                message=f"Failed to delete observations: {str(e)}",
                server=self.server_name,
                tool="delete_observations",
                params={"deletions": deletions},
            ) from e

    async def delete_relations(
        self, relations: List[Dict[str, Any]]
    ) -> DeleteRelationsResponse:
        """Delete relations from the knowledge graph.

        Args:
            relations: List of relation dictionaries, each containing 'from',
                'relationType', and 'to'

        Returns:
            DeleteRelationsResponse with the deleted count and status message

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Convert raw relations to Pydantic models
            relation_models = [
                Relation.model_validate(relation) for relation in relations
            ]

            # Create the params model
            params = DeleteRelationsParams(relations=relation_models)

            # Call with validation
            response = await self._call_validate_tool(
                "delete_relations", params, DeleteRelationsResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in delete_relations: {str(e)}")
            raise MCPError(
                message=f"Invalid relation data: {str(e)}",
                server=self.server_name,
                tool="delete_relations",
                params={"relations": relations},
            ) from e
        except Exception as e:
            logger.error(f"Error deleting relations: {str(e)}")
            raise MCPError(
                message=f"Failed to delete relations: {str(e)}",
                server=self.server_name,
                tool="delete_relations",
                params={"relations": relations},
            ) from e

    async def read_graph(self) -> GraphResponse:
        """Read the entire knowledge graph.

        Returns:
            GraphResponse containing entities and relations

        Raises:
            MCPError: If the MCP request fails
        """
        try:
            # No parameters for this request
            params = {}

            # Call with validation
            response = await self._call_validate_tool(
                "read_graph", params, GraphResponse
            )

            return response
        except Exception as e:
            logger.error(f"Error reading graph: {str(e)}")
            raise MCPError(
                message=f"Failed to read knowledge graph: {str(e)}",
                server=self.server_name,
                tool="read_graph",
                params={},
            ) from e

    async def search_nodes(self, query: str) -> SearchNodesResponse:
        """Search for nodes in the knowledge graph.

        Args:
            query: Search query string

        Returns:
            SearchNodesResponse with matching entities

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Create the params model
            params = SearchNodesParams(query=query)

            # Call with validation
            response = await self._call_validate_tool(
                "search_nodes", params, SearchNodesResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in search_nodes: {str(e)}")
            raise MCPError(
                message=f"Invalid search query: {str(e)}",
                server=self.server_name,
                tool="search_nodes",
                params={"query": query},
            ) from e
        except Exception as e:
            logger.error(f"Error searching nodes: {str(e)}")
            raise MCPError(
                message=f"Failed to search nodes: {str(e)}",
                server=self.server_name,
                tool="search_nodes",
                params={"query": query},
            ) from e

    async def open_nodes(self, names: List[str]) -> OpenNodesResponse:
        """Get detailed information about specific nodes.

        Args:
            names: List of node names to retrieve

        Returns:
            OpenNodesResponse with the requested entities

        Raises:
            MCPError: If the MCP request fails or validation fails
        """
        try:
            # Create the params model
            params = OpenNodesParams(names=names)

            # Call with validation
            response = await self._call_validate_tool(
                "open_nodes", params, OpenNodesResponse
            )

            return response
        except ValidationError as e:
            logger.error(f"Validation error in open_nodes: {str(e)}")
            raise MCPError(
                message=f"Invalid node names: {str(e)}",
                server=self.server_name,
                tool="open_nodes",
                params={"names": names},
            ) from e
        except Exception as e:
            logger.error(f"Error opening nodes: {str(e)}")
            raise MCPError(
                message=f"Failed to open nodes: {str(e)}",
                server=self.server_name,
                tool="open_nodes",
                params={"names": names},
            ) from e


# Singleton instance
memory_client = MemoryMCPClient()


# Function to get the client instance
def get_client() -> MemoryMCPClient:
    """Get the singleton Memory MCP client instance.

    Returns:
        MemoryMCPClient instance
    """
    return memory_client
