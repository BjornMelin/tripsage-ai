"""
Memory tools for TripSage agents.

This module provides function tools that wrap the Neo4j Memory MCP
client for use with the OpenAI Agents SDK.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents import function_tool
from src.mcp.memory.client import memory_client
from src.mcp.memory.models import (
    Entity as MemoryEntity,
)
from src.mcp.memory.models import (
    Observation as MemoryObservation,
)
from src.mcp.memory.models import (
    Relation as MemoryRelation,
)
from src.utils.decorators import ensure_memory_client_initialized, with_error_handling
from src.utils.session_memory import (
    initialize_session_memory,
    store_session_summary,
    update_session_memory,
)

# Use MCP models directly to avoid duplication
Entity = MemoryEntity
Relation = MemoryRelation
Observation = MemoryObservation


class DeletionRequest(BaseModel):
    """Deletion request model for Memory MCP."""

    entityName: str = Field(..., description="Entity name")
    observations: List[str] = Field(..., description="Observations to delete")


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def get_knowledge_graph() -> Dict[str, Any]:
    """Retrieve the entire knowledge graph.

    Returns:
        The knowledge graph with entities and relations.
    """
    # Read the entire graph
    graph_data = await memory_client.read_graph()

    return {
        "entities": graph_data.get("entities", []),
        "relations": graph_data.get("relations", []),
        "statistics": graph_data.get("statistics", {}),
    }


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def search_knowledge_graph(query: str) -> Dict[str, Any]:
    """Search the knowledge graph for entities matching a query.

    Args:
        query: Search query string

    Returns:
        List of matching entities
    """
    # Search for nodes
    nodes = await memory_client.search_nodes(query)

    return {"nodes": nodes}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def get_entity_details(names: List[str]) -> Dict[str, Any]:
    """Get detailed information about specific entities.

    Args:
        names: List of entity names

    Returns:
        Dictionary with entity details
    """
    # Get entity details
    nodes = await memory_client.open_nodes(names)

    return {"entities": nodes}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def create_knowledge_entities(entities: List[Entity]) -> Dict[str, Any]:
    """Create new entities in the knowledge graph.

    Args:
        entities: List of entities to create

    Returns:
        List of created entities
    """
    # Convert to dictionary format
    entity_dicts = [entity.model_dump(by_alias=True) for entity in entities]

    # Create entities
    created_entities = await memory_client.create_entities(entity_dicts)

    return {"entities": created_entities}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def create_knowledge_relations(relations: List[Relation]) -> Dict[str, Any]:
    """Create new relations between entities in the knowledge graph.

    Args:
        relations: List of relations to create

    Returns:
        List of created relations
    """
    # Convert to dictionary format
    relation_dicts = [relation.model_dump(by_alias=True) for relation in relations]

    # Create relations
    created_relations = await memory_client.create_relations(relation_dicts)

    return {"relations": created_relations}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def add_entity_observations(
    observations: List[Observation],
) -> Dict[str, Any]:
    """Add observations to existing entities in the knowledge graph.

    Args:
        observations: List of observations to add

    Returns:
        List of updated entities
    """
    # Convert to dictionary format
    observation_dicts = [obs.model_dump() for obs in observations]

    # Add observations
    updated_entities = await memory_client.add_observations(observation_dicts)

    return {"entities": updated_entities}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def delete_knowledge_entities(entity_names: List[str]) -> Dict[str, Any]:
    """Delete entities from the knowledge graph.

    Args:
        entity_names: List of entity names to delete

    Returns:
        List of deleted entity names
    """
    # Delete entities
    deleted_entities = await memory_client.delete_entities(entity_names)

    return {"deleted": deleted_entities}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def delete_knowledge_relations(relations: List[Relation]) -> Dict[str, Any]:
    """Delete relations from the knowledge graph.

    Args:
        relations: List of relations to delete

    Returns:
        List of deleted relations
    """
    # Convert to dictionary format
    relation_dicts = [relation.model_dump(by_alias=True) for relation in relations]

    # Delete relations
    deleted_relations = await memory_client.delete_relations(relation_dicts)

    return {"deleted": deleted_relations}


@function_tool
@ensure_memory_client_initialized
@with_error_handling
async def delete_entity_observations(
    deletions: List[DeletionRequest],
) -> Dict[str, Any]:
    """Delete specific observations from entities in the knowledge graph.

    Args:
        deletions: List of deletion requests

    Returns:
        List of updated entities
    """
    # Convert to dictionary format
    deletion_dicts = [deletion.model_dump() for deletion in deletions]

    # Delete observations
    updated_entities = await memory_client.delete_observations(deletion_dicts)

    return {"entities": updated_entities}


@function_tool
@with_error_handling
async def initialize_agent_memory(
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Initialize agent memory by retrieving relevant knowledge.

    Args:
        user_id: Optional user ID

    Returns:
        Dictionary with session memory data
    """
    # Initialize session memory
    session_data = await initialize_session_memory(user_id)

    return session_data


@function_tool
@with_error_handling
async def update_agent_memory(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update agent memory with new knowledge.

    Args:
        user_id: User ID
        updates: Dictionary with updates

    Returns:
        Dictionary with update status
    """
    # Update session memory
    result = await update_session_memory(user_id, updates)

    return result


@function_tool
@with_error_handling
async def save_session_summary(
    user_id: str, summary: str, session_id: str
) -> Dict[str, Any]:
    """Save a summary of the current session.

    Args:
        user_id: User ID
        summary: Session summary text
        session_id: Session ID

    Returns:
        Dictionary with save status
    """
    # Store session summary
    result = await store_session_summary(user_id, summary, session_id)

    return result
