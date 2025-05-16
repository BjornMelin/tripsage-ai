"""
Memory tools for TripSage agents.

This module provides function tools that wrap the Neo4j Memory MCP
client for use with the OpenAI Agents SDK through the MCPManager abstraction layer.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents import function_tool
from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.manager import mcp_manager
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
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="read_graph",
            params={},
        )

        # Convert the result to the expected response model
        result = GraphResponse.model_validate(result)

        return {
            "entities": result.entities,
            "relations": result.relations,
            "statistics": getattr(result, "statistics", {}),
        }

    except TripSageMCPError as e:
        logger.error(f"MCP error reading knowledge graph: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="search_nodes",
            params={"query": query},
        )

        # Convert the result to the expected response model
        result = SearchNodesResponse.model_validate(result)

        return {"nodes": result.results, "count": result.count}

    except TripSageMCPError as e:
        logger.error(f"MCP error searching knowledge graph: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="open_nodes",
            params={"names": names},
        )

        # Convert the result to the expected response model
        result = OpenNodesResponse.model_validate(result)

        return {"entities": result.entities, "count": result.count}

    except TripSageMCPError as e:
        logger.error(f"MCP error getting entity details: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="create_entities",
            params={"entities": entity_dicts},
        )

        # Convert the result to the expected response model
        result = CreateEntitiesResponse.model_validate(result)

        return {"entities": result.entities, "message": result.message}

    except TripSageMCPError as e:
        logger.error(f"MCP error creating entities: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="create_relations",
            params={"relations": relation_dicts},
        )

        # Convert the result to the expected response model
        result = CreateRelationsResponse.model_validate(result)

        return {"relations": result.relations, "message": result.message}

    except TripSageMCPError as e:
        logger.error(f"MCP error creating relations: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="add_observations",
            params={"observations": observation_dicts},
        )

        # Convert the result to the expected response model
        result = AddObservationsResponse.model_validate(result)

        return {"entities": result.updated_entities, "message": result.message}

    except TripSageMCPError as e:
        logger.error(f"MCP error adding observations: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="delete_entities",
            params={"entityNames": entity_names},
        )

        # Convert the result to the expected response model
        result = DeleteEntitiesResponse.model_validate(result)

        return {"deleted": result.deleted_count, "message": result.message}

    except TripSageMCPError as e:
        logger.error(f"MCP error deleting entities: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="delete_relations",
            params={"relations": relation_dicts},
        )

        # Convert the result to the expected response model
        result = DeleteRelationsResponse.model_validate(result)

        return {"deleted": result.deleted_count, "message": result.message}

    except TripSageMCPError as e:
        logger.error(f"MCP error deleting relations: {str(e)}")
        raise
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

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="neo4j_memory",
            method_name="delete_observations",
            params={"deletions": deletion_dicts},
        )

        # Convert the result to the expected response model
        result = DeleteObservationsResponse.model_validate(result)

        return {"entities": result.updated_entities, "message": result.message}

    except TripSageMCPError as e:
        logger.error(f"MCP error deleting observations: {str(e)}")
        raise
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

    except TripSageMCPError as e:
        logger.error(f"MCP error initializing agent memory: {str(e)}")
        raise
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

    except TripSageMCPError as e:
        logger.error(f"MCP error updating agent memory: {str(e)}")
        raise
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
        await create_knowledge_entities(
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
        await add_entity_observations(
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
                        await create_knowledge_entities(
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
            await create_knowledge_relations(
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

    except TripSageMCPError as e:
        logger.error(f"MCP error saving session summary: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error saving session summary: {str(e)}")
        raise


# Domain-specific operations for TripSage

@function_tool
@with_error_handling
async def find_destinations_by_country(country: str) -> Dict[str, Any]:
    """Find destinations in a specific country using the knowledge graph.
    
    Args:
        country: The country to search for
        
    Returns:
        Dictionary with list of destinations in the country
    """
    logger.info(f"Finding destinations in country: {country}")
    
    # Search for destinations with country in their observations
    # The Memory MCP uses simple search, so we need to construct appropriate queries
    search_result = await search_knowledge_graph(f"Destination {country}")
    destinations = search_result.get("nodes", [])
    
    # Filter to ensure they are actual destination entities
    filtered_destinations = []
    for node in destinations:
        if node.get("entityType") == "Destination":
            # Check if country is mentioned in observations
            observations = node.get("observations", [])
            for obs in observations:
                if country.lower() in obs.lower():
                    filtered_destinations.append(node)
                    break
    
    return {
        "destinations": filtered_destinations,
        "count": len(filtered_destinations)
    }


@function_tool
@with_error_handling
async def find_nearby_destinations(
    latitude: float, longitude: float, radius_km: float = 50
) -> Dict[str, Any]:
    """Find destinations near a geographic location.
    
    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location  
        radius_km: Search radius in kilometers (default 50)
        
    Returns:
        Dictionary with list of nearby destinations
    """
    logger.info(f"Finding destinations near ({latitude}, {longitude}) within {radius_km}km")
    
    # Get all destinations
    graph_result = await get_knowledge_graph()
    all_entities = graph_result.get("entities", [])
    
    nearby_destinations = []
    
    for entity in all_entities:
        if entity.get("entityType") == "Destination":
            # Look for coordinates in observations
            observations = entity.get("observations", [])
            for obs in observations:
                # Simple pattern matching for coordinates
                if "coordinates" in obs.lower() or "lat" in obs.lower():
                    try:
                        # This is a simplified approach - in production, we'd have
                        # structured coordinate data in the graph
                        import re
                        coord_pattern = r'[-+]?\d*\.\d+|[-+]?\d+'
                        coords = re.findall(coord_pattern, obs)
                        if len(coords) >= 2:
                            dest_lat, dest_lon = float(coords[0]), float(coords[1])
                            
                            # Calculate distance using Haversine formula
                            distance = calculate_distance(
                                latitude, longitude, dest_lat, dest_lon
                            )
                            
                            if distance <= radius_km:
                                nearby_destinations.append({
                                    **entity,
                                    "distance_km": distance
                                })
                    except (ValueError, IndexError):
                        continue
    
    # Sort by distance
    nearby_destinations.sort(key=lambda x: x.get("distance_km", float('inf')))
    
    return {
        "destinations": nearby_destinations,
        "count": len(nearby_destinations)
    }


@function_tool
@with_error_handling
async def find_accommodations_in_destination(
    destination_name: str
) -> Dict[str, Any]:
    """Find accommodations in a specific destination.
    
    Args:
        destination_name: Name of the destination
        
    Returns:
        Dictionary with list of accommodations
    """
    logger.info(f"Finding accommodations in destination: {destination_name}")
    
    # Search for accommodations related to the destination
    search_result = await search_knowledge_graph(f"Accommodation {destination_name}")
    accommodations = search_result.get("nodes", [])
    
    # Filter for actual accommodation entities
    filtered_accommodations = []
    for node in accommodations:
        if node.get("entityType") == "Accommodation":
            # Check if destination is mentioned
            observations = node.get("observations", [])
            for obs in observations:
                if destination_name.lower() in obs.lower():
                    filtered_accommodations.append(node)
                    break
    
    return {
        "accommodations": filtered_accommodations,
        "count": len(filtered_accommodations)
    }


@function_tool
@with_error_handling
async def create_trip_entities(
    trip_id: str,
    user_id: str,
    destination: str,
    start_date: str,
    end_date: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """Create trip entities and relationships in the knowledge graph.
    
    Args:
        trip_id: Unique trip identifier
        user_id: User identifier
        destination: Trip destination
        start_date: Trip start date
        end_date: Trip end date
        details: Additional trip details
        
    Returns:
        Dictionary with created entities and relationships
    """
    logger.info(f"Creating trip entities for trip {trip_id}")
    
    # Create trip entity
    trip_observations = [
        f"Trip to {destination}",
        f"From {start_date} to {end_date}",
        f"Budget: {details.get('budget', 'Not specified')}",
        f"Travelers: {details.get('travelers', 1)}",
        f"Status: {details.get('status', 'planning')}",
        f"Type: {details.get('trip_type', 'leisure')}"
    ]
    
    entities_result = await create_knowledge_entities([
        Entity(
            name=f"Trip:{trip_id}",
            entityType="Trip",
            observations=trip_observations
        )
    ])
    
    # Create user-trip relationship
    user_trip_relation = await create_knowledge_relations([
        Relation(
            from_=f"User:{user_id}",
            relationType="PLANS",
            to=f"Trip:{trip_id}"
        )
    ])
    
    # Create trip-destination relationship
    trip_dest_relation = await create_knowledge_relations([
        Relation(
            from_=f"Trip:{trip_id}",
            relationType="TO",
            to=f"Destination:{destination}"
        )
    ])
    
    return {
        "trip_entity": entities_result.get("entities", [None])[0],
        "user_trip_relation": user_trip_relation.get("relations", [None])[0],
        "trip_destination_relation": trip_dest_relation.get("relations", [None])[0]
    }


@function_tool
@with_error_handling
async def find_popular_destinations(
    limit: int = 10
) -> Dict[str, Any]:
    """Find the most popular destinations based on trip relationships.
    
    Args:
        limit: Maximum number of destinations to return
        
    Returns:
        Dictionary with popular destinations
    """
    logger.info(f"Finding top {limit} popular destinations")
    
    # Get the full graph to analyze relationships
    graph_result = await get_knowledge_graph()
    all_entities = graph_result.get("entities", [])
    all_relations = graph_result.get("relations", [])
    
    # Count trips to each destination
    destination_counts = {}
    
    for relation in all_relations:
        if relation.get("relationType") == "TO" and "Trip:" in relation.get("from", ""):
            destination = relation.get("to")
            if destination and destination.startswith("Destination:"):
                destination_counts[destination] = destination_counts.get(destination, 0) + 1
    
    # Sort destinations by popularity
    popular_destinations = []
    for dest_name, count in sorted(
        destination_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:limit]:
        # Find the actual destination entity
        for entity in all_entities:
            if entity.get("name") == dest_name:
                popular_destinations.append({
                    **entity,
                    "trip_count": count
                })
                break
    
    return {
        "destinations": popular_destinations,
        "count": len(popular_destinations)
    }


# Helper function for distance calculation
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        
    Returns:
        Distance in kilometers
    """
    import math
    
    R = 6371  # Earth's radius in kilometers
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    
    a = (math.sin(dlat/2) * math.sin(dlat/2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(dlon/2) * math.sin(dlon/2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c