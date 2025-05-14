"""
Memory tools for TripSage agents.

This module provides function tools that wrap the Neo4j Memory MCP
client for use with the OpenAI Agents SDK.
"""

from typing import Any, Dict, List, Optional

from openai_agents_sdk import function_tool
from pydantic import BaseModel, Field

from tripsage.tools.schemas.memory import (
    AddObservationsResponse,
    CreateEntitiesResponse,
    CreateRelationsResponse,
    DeleteEntitiesResponse,
    DeleteObservationsResponse,
    DeleteRelationsResponse,
    Entity,
    GraphResponse,
    Observation,
    OpenNodesResponse,
    Relation,
    SearchNodesResponse,
)
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger
from tripsage.utils.settings import settings

# Set up logger
logger = get_logger(__name__)


class DeletionRequest(BaseModel):
    """Deletion request model for Memory MCP."""

    entityName: str = Field(..., description="Entity name")
    observations: List[str] = Field(..., description="Observations to delete")


@function_tool
@with_error_handling
async def get_knowledge_graph() -> Dict[str, Any]:
    """Retrieve the entire knowledge graph.

    Returns:
        The knowledge graph with entities and relations.
    """
    try:
        logger.info("Reading knowledge graph")

        # Call the MCP to read the graph
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="read_graph",
            params={},
            response_model=GraphResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {
            "entities": result.entities,
            "relations": result.relations,
            "statistics": getattr(result, "statistics", {}),
        }

    except Exception as e:
        logger.error(f"Error reading knowledge graph: {str(e)}")
        raise


@function_tool
@with_error_handling
async def search_knowledge_graph(query: str) -> Dict[str, Any]:
    """Search the knowledge graph for entities matching a query.

    Args:
        query: Search query string

    Returns:
        List of matching entities
    """
    try:
        logger.info(f"Searching knowledge graph with query: {query}")

        # Call the MCP to search nodes
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="search_nodes",
            params={"query": query},
            response_model=SearchNodesResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"nodes": result.results, "count": result.count}

    except Exception as e:
        logger.error(f"Error searching knowledge graph: {str(e)}")
        raise


@function_tool
@with_error_handling
async def get_entity_details(names: List[str]) -> Dict[str, Any]:
    """Get detailed information about specific entities.

    Args:
        names: List of entity names

    Returns:
        Dictionary with entity details
    """
    try:
        logger.info(f"Getting entity details for: {names}")

        # Call the MCP to open nodes
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="open_nodes",
            params={"names": names},
            response_model=OpenNodesResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"entities": result.entities, "count": result.count}

    except Exception as e:
        logger.error(f"Error getting entity details: {str(e)}")
        raise


@function_tool
@with_error_handling
async def create_knowledge_entities(entities: List[Entity]) -> Dict[str, Any]:
    """Create new entities in the knowledge graph.

    Args:
        entities: List of entities to create

    Returns:
        List of created entities
    """
    try:
        logger.info(f"Creating {len(entities)} entities")

        # Convert to dictionary format
        entity_dicts = [entity.model_dump(by_alias=True) for entity in entities]

        # Call the MCP to create entities
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="create_entities",
            params={"entities": entity_dicts},
            response_model=CreateEntitiesResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"entities": result.entities, "message": result.message}

    except Exception as e:
        logger.error(f"Error creating entities: {str(e)}")
        raise


@function_tool
@with_error_handling
async def create_knowledge_relations(relations: List[Relation]) -> Dict[str, Any]:
    """Create new relations between entities in the knowledge graph.

    Args:
        relations: List of relations to create

    Returns:
        List of created relations
    """
    try:
        logger.info(f"Creating {len(relations)} relations")

        # Convert to dictionary format
        relation_dicts = [relation.model_dump(by_alias=True) for relation in relations]

        # Call the MCP to create relations
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="create_relations",
            params={"relations": relation_dicts},
            response_model=CreateRelationsResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"relations": result.relations, "message": result.message}

    except Exception as e:
        logger.error(f"Error creating relations: {str(e)}")
        raise


@function_tool
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
    try:
        logger.info(f"Adding observations to {len(observations)} entities")

        # Convert to dictionary format
        observation_dicts = [obs.model_dump() for obs in observations]

        # Call the MCP to add observations
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="add_observations",
            params={"observations": observation_dicts},
            response_model=AddObservationsResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"entities": result.updated_entities, "message": result.message}

    except Exception as e:
        logger.error(f"Error adding observations: {str(e)}")
        raise


@function_tool
@with_error_handling
async def delete_knowledge_entities(entity_names: List[str]) -> Dict[str, Any]:
    """Delete entities from the knowledge graph.

    Args:
        entity_names: List of entity names to delete

    Returns:
        Number of deleted entities
    """
    try:
        logger.info(f"Deleting {len(entity_names)} entities")

        # Call the MCP to delete entities
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="delete_entities",
            params={"entityNames": entity_names},
            response_model=DeleteEntitiesResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"deleted": result.deleted_count, "message": result.message}

    except Exception as e:
        logger.error(f"Error deleting entities: {str(e)}")
        raise


@function_tool
@with_error_handling
async def delete_knowledge_relations(relations: List[Relation]) -> Dict[str, Any]:
    """Delete relations from the knowledge graph.

    Args:
        relations: List of relations to delete

    Returns:
        Number of deleted relations
    """
    try:
        logger.info(f"Deleting {len(relations)} relations")

        # Convert to dictionary format
        relation_dicts = [relation.model_dump(by_alias=True) for relation in relations]

        # Call the MCP to delete relations
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="delete_relations",
            params={"relations": relation_dicts},
            response_model=DeleteRelationsResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"deleted": result.deleted_count, "message": result.message}

    except Exception as e:
        logger.error(f"Error deleting relations: {str(e)}")
        raise


@function_tool
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
    try:
        logger.info(f"Deleting observations from {len(deletions)} entities")

        # Convert to dictionary format
        deletion_dicts = [deletion.model_dump() for deletion in deletions]

        # Call the MCP to delete observations
        result = await validate_and_call_mcp_tool(
            endpoint=settings.memory_mcp.endpoint,
            tool_name="delete_observations",
            params={"deletions": deletion_dicts},
            response_model=DeleteObservationsResponse,
            timeout=settings.memory_mcp.timeout,
            server_name="Memory MCP",
        )

        return {"entities": result.updated_entities, "message": result.message}

    except Exception as e:
        logger.error(f"Error deleting observations: {str(e)}")
        raise


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
    try:
        logger.info(f"Initializing agent memory for user: {user_id}")

        session_data = {
            "user": None,
            "preferences": {},
            "recent_trips": [],
            "popular_destinations": [],
        }

        # Retrieve user information if available
        if user_id:
            # Get user entity details
            user_nodes_result = await get_entity_details([f"User:{user_id}"])
            user_nodes = user_nodes_result.get("entities", [])

            if user_nodes:
                session_data["user"] = user_nodes[0]

                # Extract user preferences from observations
                preferences = {}
                for observation in user_nodes[0].get("observations", []):
                    if observation.startswith("Prefers "):
                        parts = observation.replace("Prefers ", "").split(" for ")
                        if len(parts) == 2:
                            preference_value, category = parts
                            preferences[category] = preference_value

                session_data["preferences"] = preferences

                # Find user's recent trips
                trip_search_result = await search_knowledge_graph(
                    f"User:{user_id} PLANS"
                )
                trip_search = trip_search_result.get("nodes", [])

                if trip_search:
                    # Get trip IDs
                    trip_names = [
                        node.get("name")
                        for node in trip_search
                        if node.get("name", "").startswith("Trip:")
                    ]

                    # Get trip details
                    if trip_names:
                        trips_result = await get_entity_details(trip_names)
                        session_data["recent_trips"] = trips_result.get("entities", [])

        # Get popular destinations
        try:
            # This is a special endpoint that doesn't follow the standard MCP pattern
            # We'll handle it differently or implement a custom MCP tool for it
            # For now we'll skip it to avoid errors
            pass

        except Exception as e:
            logger.warning(f"Failed to retrieve popular destinations: {str(e)}")

        return session_data

    except Exception as e:
        logger.error(f"Error initializing agent memory: {str(e)}")
        raise


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
    try:
        logger.info(f"Updating agent memory for user: {user_id}")

        result = {
            "entities_created": 0,
            "relations_created": 0,
            "observations_added": 0,
        }

        # Process user preferences
        if "preferences" in updates:
            await _update_user_preferences(user_id, updates["preferences"], result)

        # Process learned facts
        if "learned_facts" in updates:
            await _create_fact_relationships(user_id, updates["learned_facts"], result)

        return result

    except Exception as e:
        logger.error(f"Error updating agent memory: {str(e)}")
        raise


async def _update_user_preferences(
    user_id: str, preferences: Dict[str, str], result: Dict[str, int]
) -> None:
    """Update user preferences in the knowledge graph.

    Args:
        user_id: User ID
        preferences: Dictionary of preferences
        result: Result dictionary to update
    """
    # Get or create user entity
    user_nodes_result = await get_entity_details([f"User:{user_id}"])
    user_nodes = user_nodes_result.get("entities", [])

    if not user_nodes:
        # Create user entity
        create_result = await create_knowledge_entities(
            [
                Entity(
                    name=f"User:{user_id}",
                    entityType="User",
                    observations=["TripSage user"],
                )
            ]
        )
        result["entities_created"] += 1

    # Add preference observations
    preference_observations = []
    for category, preference in preferences.items():
        preference_observations.append(f"Prefers {preference} for {category}")

    if preference_observations:
        add_result = await add_entity_observations(
            [
                Observation(
                    entityName=f"User:{user_id}",
                    contents=preference_observations,
                )
            ]
        )
        result["observations_added"] += len(preference_observations)


async def _create_fact_relationships(
    user_id: str, facts: List[Dict[str, str]], result: Dict[str, int]
) -> None:
    """Create relationships for new facts in the knowledge graph.

    Args:
        user_id: User ID
        facts: List of fact dictionaries
        result: Result dictionary to update
    """
    for fact in facts:
        if "from" in fact and "to" in fact and "relationType" in fact:
            # Create entities if they don't exist
            for entity_name in [fact["from"], fact["to"]]:
                if ":" not in entity_name:  # Not a prefixed entity like User:123
                    # Check if entity exists
                    existing_result = await get_entity_details([entity_name])
                    existing = existing_result.get("entities", [])

                    if not existing:
                        # Create entity with a generic type
                        entity_type = fact.get(
                            "fromType" if entity_name == fact["from"] else "toType",
                            "Entity",
                        )
                        create_result = await create_knowledge_entities(
                            [
                                Entity(
                                    name=entity_name,
                                    entityType=entity_type,
                                    observations=[
                                        f"Learned during session with user {user_id}"
                                    ],
                                )
                            ]
                        )
                        result["entities_created"] += 1

            # Create relationship
            relation_result = await create_knowledge_relations(
                [
                    Relation(
                        from_=fact["from"],
                        relationType=fact["relationType"],
                        to=fact["to"],
                    )
                ]
            )
            result["relations_created"] += 1


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
    try:
        logger.info(f"Saving session summary for user: {user_id}")

        # Create session entity
        session_entity_result = await create_knowledge_entities(
            [
                Entity(
                    name=f"Session:{session_id}",
                    entityType="Session",
                    observations=[summary],
                )
            ]
        )

        # Create relationship between user and session
        session_relation_result = await create_knowledge_relations(
            [
                Relation(
                    from_=f"User:{user_id}",
                    relationType="PARTICIPATED_IN",
                    to=f"Session:{session_id}",
                )
            ]
        )

        return {
            "session_entity": session_entity_result.get("entities", [None])[0],
            "session_relation": session_relation_result.get("relations", [None])[0],
        }

    except Exception as e:
        logger.error(f"Error saving session summary: {str(e)}")
        raise
