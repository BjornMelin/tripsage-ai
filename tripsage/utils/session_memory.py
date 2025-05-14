"""
Session memory utilities for TripSage.

This module provides utilities for initializing and updating session memory
using the Neo4j Memory MCP.
"""

from typing import Any, Dict, List, Optional

from tripsage.tools.memory_tools import (
    add_entity_observations,
    create_knowledge_entities,
    create_knowledge_relations,
    get_entity_details,
    search_knowledge_graph,
)
from tripsage.tools.schemas.memory import Entity, Observation, Relation
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


async def initialize_session_memory(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Initialize session memory by retrieving relevant knowledge.

    This function retrieves user preferences, past trips, and other relevant
    knowledge from the Neo4j Memory MCP to initialize the session memory.

    Args:
        user_id: Optional user ID

    Returns:
        Dictionary with session memory data
    """
    logger.info("Initializing session memory")

    session_data = {
        "user": None,
        "preferences": {},
        "recent_trips": [],
        "popular_destinations": [],
    }

    # Retrieve user information if available
    if user_id:
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
            trip_search_result = await search_knowledge_graph(f"User:{user_id} PLANS")
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

    # Get popular destinations - skipped for now as it requires a custom endpoint
    # This would normally use a special endpoint that doesn't follow the standard MCP pattern

    return session_data


async def update_session_memory(
    user_id: str, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update session memory with new knowledge.

    This function updates the knowledge graph with new information
    learned during the session.

    Args:
        user_id: User ID
        updates: Dictionary with updates

    Returns:
        Dictionary with update status
    """
    logger.info(f"Updating session memory for user {user_id}")

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


async def store_session_summary(
    user_id: str,
    summary: str,
    session_id: str,
) -> Dict[str, Any]:
    """Store session summary in the knowledge graph.

    This function stores a summary of the session in the knowledge graph.

    Args:
        user_id: User ID
        summary: Session summary
        session_id: Session ID

    Returns:
        Dictionary with status
    """
    logger.info(f"Storing session summary for user {user_id}")

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
