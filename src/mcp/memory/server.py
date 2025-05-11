"""
Memory MCP server.

This module provides a FastMCP server implementation for the Memory MCP service,
which interfaces with the Neo4j knowledge graph to provide memory operations.
"""

from typing import Any, Dict, List

from fastmcp import Context, FastMCP
from pydantic import BaseModel, Field

from src.mcp.memory.client import memory_client
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

# Create the server with descriptive name
mcp = FastMCP(
    name="TripSage Memory MCP",
    description="Memory MCP service for knowledge graph operations",
)


# Request/Response Models
class EntityObservation(BaseModel):
    """Entity observation model."""

    entityName: str = Field(..., description="Name of the entity")
    contents: List[str] = Field(..., description="List of observation contents")


class Entity(BaseModel):
    """Entity model."""

    name: str = Field(..., description="Entity name")
    entityType: str = Field(..., description="Entity type")
    observations: List[str] = Field(
        default_factory=list, description="Entity observations"
    )


class Relation(BaseModel):
    """Relation model."""

    from_: str = Field(..., description="Source entity name", alias="from")
    relationType: str = Field(..., description="Relation type")
    to: str = Field(..., description="Target entity name")


class EntityCreateRequest(BaseModel):
    """Entity creation request model."""

    entities: List[Dict[str, Any]] = Field(
        ..., description="List of entities to create"
    )


class EntityCreateResponse(BaseModel):
    """Entity creation response model."""

    entities: List[Dict[str, Any]] = Field(..., description="List of created entities")


class RelationCreateRequest(BaseModel):
    """Relation creation request model."""

    relations: List[Dict[str, Any]] = Field(
        ..., description="List of relations to create"
    )


class RelationCreateResponse(BaseModel):
    """Relation creation response model."""

    relations: List[Dict[str, Any]] = Field(
        ..., description="List of created relations"
    )


class ObservationAddRequest(BaseModel):
    """Observation addition request model."""

    observations: List[Dict[str, Any]] = Field(
        ..., description="List of observations to add"
    )


class ObservationAddResponse(BaseModel):
    """Observation addition response model."""

    entities: List[Dict[str, Any]] = Field(..., description="List of updated entities")


class EntityDeleteRequest(BaseModel):
    """Entity deletion request model."""

    entityNames: List[str] = Field(..., description="List of entity names to delete")


class EntityDeleteResponse(BaseModel):
    """Entity deletion response model."""

    deleted: List[str] = Field(..., description="List of deleted entity names")


class RelationDeleteRequest(BaseModel):
    """Relation deletion request model."""

    relations: List[Dict[str, Any]] = Field(
        ..., description="List of relations to delete"
    )


class RelationDeleteResponse(BaseModel):
    """Relation deletion response model."""

    deleted: List[Dict[str, Any]] = Field(..., description="List of deleted relations")


class ObservationDeleteRequest(BaseModel):
    """Observation deletion request model."""

    deletions: List[Dict[str, Any]] = Field(
        ..., description="List of observations to delete"
    )


class ObservationDeleteResponse(BaseModel):
    """Observation deletion response model."""

    entities: List[Dict[str, Any]] = Field(..., description="List of updated entities")


class GraphResponse(BaseModel):
    """Graph response model."""

    entities: List[Dict[str, Any]] = Field(..., description="List of entities")
    relations: List[Dict[str, Any]] = Field(..., description="List of relations")
    statistics: Dict[str, Any] = Field(..., description="Graph statistics")


class SearchRequest(BaseModel):
    """Search request model."""

    query: str = Field(..., description="Search query")


class SearchResponse(BaseModel):
    """Search response model."""

    nodes: List[Dict[str, Any]] = Field(..., description="List of matching nodes")


class OpenNodesRequest(BaseModel):
    """Open nodes request model."""

    names: List[str] = Field(..., description="List of node names to retrieve")


class OpenNodesResponse(BaseModel):
    """Open nodes response model."""

    nodes: List[Dict[str, Any]] = Field(..., description="List of node details")


# MCP Tools
@mcp.tool()
async def create_entities(
    entities: List[Dict[str, Any]], ctx: Context
) -> EntityCreateResponse:
    """Create multiple new entities in the knowledge graph.

    Args:
        entities: List of entity data dictionaries, each containing 'name',
            'entityType', and 'observations'
        ctx: MCP context

    Returns:
        List of created entities
    """
    await ctx.info(f"Creating {len(entities)} entities")

    # Initialize the memory client
    await memory_client.initialize()

    # Create entities
    created_entities = await memory_client.create_entities(entities)

    await ctx.info(f"Created {len(created_entities)} entities successfully")

    return EntityCreateResponse(entities=created_entities)


@mcp.tool()
async def create_relations(
    relations: List[Dict[str, Any]], ctx: Context
) -> RelationCreateResponse:
    """Create multiple new relations between entities in the knowledge graph.

    Args:
        relations: List of relation dictionaries, each containing 'from',
            'relationType', and 'to'
        ctx: MCP context

    Returns:
        List of created relations
    """
    await ctx.info(f"Creating {len(relations)} relations")

    # Initialize the memory client
    await memory_client.initialize()

    # Create relations
    created_relations = await memory_client.create_relations(relations)

    await ctx.info(f"Created {len(created_relations)} relations successfully")

    return RelationCreateResponse(relations=created_relations)


@mcp.tool()
async def add_observations(
    observations: List[Dict[str, Any]], ctx: Context
) -> ObservationAddResponse:
    """Add new observations to existing entities in the knowledge graph.

    Args:
        observations: List of observation dictionaries, each containing
            'entityName' and 'contents' (list of strings)
        ctx: MCP context

    Returns:
        List of updated entities
    """
    await ctx.info(f"Adding observations to {len(observations)} entities")

    # Initialize the memory client
    await memory_client.initialize()

    # Add observations
    updated_entities = await memory_client.add_observations(observations)

    await ctx.info(
        f"Added observations to {len(updated_entities)} entities successfully"
    )

    return ObservationAddResponse(entities=updated_entities)


@mcp.tool()
async def delete_entities(entityNames: List[str], ctx: Context) -> EntityDeleteResponse:
    """Delete multiple entities and their associated relations from the knowledge graph.

    Args:
        entityNames: List of entity names to delete
        ctx: MCP context

    Returns:
        List of deleted entity names
    """
    await ctx.info(f"Deleting {len(entityNames)} entities")

    # Initialize the memory client
    await memory_client.initialize()

    # Delete entities
    deleted_entities = await memory_client.delete_entities(entityNames)

    await ctx.info(f"Deleted {len(deleted_entities)} entities successfully")

    return EntityDeleteResponse(deleted=deleted_entities)


@mcp.tool()
async def delete_relations(
    relations: List[Dict[str, Any]], ctx: Context
) -> RelationDeleteResponse:
    """Delete multiple relations from the knowledge graph.

    Args:
        relations: List of relation dictionaries, each containing 'from',
            'relationType', and 'to'
        ctx: MCP context

    Returns:
        List of deleted relations
    """
    await ctx.info(f"Deleting {len(relations)} relations")

    # Initialize the memory client
    await memory_client.initialize()

    # Delete relations
    deleted_relations = await memory_client.delete_relations(relations)

    await ctx.info(f"Deleted {len(deleted_relations)} relations successfully")

    return RelationDeleteResponse(deleted=deleted_relations)


@mcp.tool()
async def delete_observations(
    deletions: List[Dict[str, Any]], ctx: Context
) -> ObservationDeleteResponse:
    """Delete specific observations from entities in the knowledge graph.

    Args:
        deletions: List of dictionaries, each containing 'entityName' and
            'observations' to delete
        ctx: MCP context

    Returns:
        List of updated entities
    """
    await ctx.info(f"Deleting observations from {len(deletions)} entities")

    # Initialize the memory client
    await memory_client.initialize()

    # Delete observations
    updated_entities = await memory_client.delete_observations(deletions)

    await ctx.info(
        f"Deleted observations from {len(updated_entities)} entities successfully"
    )

    return ObservationDeleteResponse(entities=updated_entities)


@mcp.tool()
async def read_graph(ctx: Context) -> GraphResponse:
    """Read the entire knowledge graph.

    Args:
        ctx: MCP context

    Returns:
        Dictionary containing entities and relations
    """
    await ctx.info("Reading entire knowledge graph")

    # Initialize the memory client
    await memory_client.initialize()

    # Read graph
    graph_data = await memory_client.read_graph()

    await ctx.info(
        f"Read knowledge graph: {len(graph_data['entities'])} entities, "
        f"{len(graph_data['relations'])} relations"
    )

    return GraphResponse(**graph_data)


@mcp.tool()
async def search_nodes(query: str, ctx: Context) -> SearchResponse:
    """Search for nodes in the knowledge graph based on a query.

    Args:
        query: The search query to match against entity names, types, and content
        ctx: MCP context

    Returns:
        List of matching nodes
    """
    await ctx.info(f"Searching for nodes matching: {query}")

    # Initialize the memory client
    await memory_client.initialize()

    # Search nodes
    nodes = await memory_client.search_nodes(query)

    await ctx.info(f"Found {len(nodes)} matching nodes")

    return SearchResponse(nodes=nodes)


@mcp.tool()
async def open_nodes(names: List[str], ctx: Context) -> OpenNodesResponse:
    """Open specific nodes in the knowledge graph by their names.

    Args:
        names: List of entity names to retrieve
        ctx: MCP context

    Returns:
        List of node details
    """
    await ctx.info(f"Opening {len(names)} nodes")

    # Initialize the memory client
    await memory_client.initialize()

    # Open nodes
    nodes = await memory_client.open_nodes(names)

    await ctx.info(f"Opened {len(nodes)} nodes successfully")

    return OpenNodesResponse(nodes=nodes)


# Resources
@mcp.resource("memory://statistics")
async def get_memory_statistics():
    """Get knowledge graph statistics.

    Returns:
        Dictionary with graph statistics
    """
    # Initialize the memory client
    await memory_client.initialize()

    # Get statistics
    return await memory_client.neo4j_client.get_graph_statistics()


@mcp.resource("memory://destinations/popular")
async def get_popular_destinations():
    """Get list of popular destinations.

    Returns:
        List of popular destination names
    """
    # Initialize the memory client
    await memory_client.initialize()

    # Get popular destinations
    destinations = await memory_client.neo4j_client.find_destinations_by_popularity(
        min_rating=4.0, limit=10
    )

    return [destination.name for destination in destinations]


@mcp.resource("memory://relationship-types")
async def get_relationship_types():
    """Get list of available relationship types.

    Returns:
        List of relationship type names
    """
    # Initialize the memory client
    await memory_client.initialize()

    # Get statistics which include relationship types
    stats = await memory_client.neo4j_client.get_graph_statistics()

    return list(stats.get("relationship_types", {}).keys())


if __name__ == "__main__":
    # Run the server
    mcp.run(transport="sse", host="0.0.0.0", port=3010)
