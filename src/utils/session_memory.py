"""
Session memory utilities for TripSage.

This module provides utilities for initializing and updating session memory
using the Neo4j Memory MCP.
"""

from typing import Any, Dict, List, Optional

from src.mcp.memory.client import memory_client
from src.utils.decorators import ensure_memory_client_initialized
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


@ensure_memory_client_initialized
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
        user_nodes = await memory_client.open_nodes([f"User:{user_id}"])
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
            trip_search = await memory_client.search_nodes(f"User:{user_id} PLANS")
            if trip_search:
                # Get trip IDs
                trip_names = [
                    node.get("name")
                    for node in trip_search
                    if node.get("name", "").startswith("Trip:")
                ]

                # Get trip details
                if trip_names:
                    trips = await memory_client.open_nodes(trip_names)
                    session_data["recent_trips"] = trips

    # Get popular destinations
    try:
        stats = await memory_client._make_request(
            method="GET",
            endpoint="_resource/memory://destinations/popular",
        )
        session_data["popular_destinations"] = stats
    except Exception as e:
        logger.warning(f"Failed to retrieve popular destinations: {str(e)}")

    return session_data


@ensure_memory_client_initialized
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
    user_nodes = await memory_client.open_nodes([f"User:{user_id}"])

    if not user_nodes:
        # Create user entity
        await memory_client.create_entities(
            [
                {
                    "name": f"User:{user_id}",
                    "entityType": "User",
                    "observations": ["TripSage user"],
                }
            ]
        )
        result["entities_created"] += 1

    # Add preference observations
    preference_observations = []
    for category, preference in preferences.items():
        preference_observations.append(f"Prefers {preference} for {category}")

    if preference_observations:
        await memory_client.add_observations(
            [
                {
                    "entityName": f"User:{user_id}",
                    "contents": preference_observations,
                }
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
                    existing = await memory_client.open_nodes([entity_name])
                    if not existing:
                        # Create entity with a generic type
                        entity_type = fact.get(
                            "fromType" if entity_name == fact["from"] else "toType",
                            "Entity",
                        )
                        await memory_client.create_entities(
                            [
                                {
                                    "name": entity_name,
                                    "entityType": entity_type,
                                    "observations": [
                                        f"Learned during session with "
                                        f"user {user_id}"
                                    ],
                                }
                            ]
                        )
                        result["entities_created"] += 1

            # Create relationship
            await memory_client.create_relations(
                [
                    {
                        "from": fact["from"],
                        "relationType": fact["relationType"],
                        "to": fact["to"],
                    }
                ]
            )
            result["relations_created"] += 1


@ensure_memory_client_initialized
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
    session_entity = await memory_client.create_entities(
        [
            {
                "name": f"Session:{session_id}",
                "entityType": "Session",
                "observations": [summary],
            }
        ]
    )

    # Create relationship between user and session
    session_relation = await memory_client.create_relations(
        [
            {
                "from": f"User:{user_id}",
                "relationType": "PARTICIPATED_IN",
                "to": f"Session:{session_id}",
            }
        ]
    )

    return {
        "session_entity": session_entity[0] if session_entity else None,
        "session_relation": session_relation[0] if session_relation else None,
    }