"""
Dual storage strategy for TripSage.

This module provides utilities for implementing the dual storage strategy,
where structured data is stored in Supabase and relationships/unstructured
data is stored in Neo4j via the Memory MCP.
"""

from typing import Any, Dict, List, Optional

from src.db.client import db_client
from src.mcp.memory.client import memory_client
from src.utils.decorators import ensure_memory_client_initialized
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


@ensure_memory_client_initialized
async def store_trip_with_dual_storage(
    trip_data: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Store trip data using the dual storage strategy.

    This function stores structured trip data in Supabase and
    relationships/unstructured data in Neo4j via the Memory MCP.

    Args:
        trip_data: Trip data dictionary
        user_id: User ID

    Returns:
        Dictionary with IDs from both storage systems
    """
    # Step 1: Store structured data in Supabase
    logger.info("Storing structured trip data in Supabase")
    trip_id = await _store_trip_in_supabase(trip_data, user_id)

    # Step 2: Store unstructured data and relationships in Neo4j via Memory MCP
    logger.info("Storing unstructured trip data in Neo4j via Memory MCP")
    
    # Create core trip entities
    created_entities = await _create_trip_entities(trip_data, trip_id, user_id)
    
    # Create related entities and relationships
    created_relations = await _create_trip_relations(
        trip_data, trip_id, created_entities
    )

    return {
        "trip_id": trip_id,
        "entities_created": len(created_entities),
        "relations_created": len(created_relations),
        "supabase": {"id": trip_id},
        "neo4j": {
            "entities": created_entities,
            "relations": created_relations,
        },
    }


async def _store_trip_in_supabase(
    trip_data: Dict[str, Any], user_id: str
) -> str:
    """Store structured trip data in Supabase.

    Args:
        trip_data: Trip data dictionary
        user_id: User ID

    Returns:
        Trip ID
    
    Raises:
        ValueError: If trip creation fails
    """
    # Extract structured data for Supabase
    structured_data = {
        "user_id": user_id,
        "title": trip_data.get("title"),
        "description": trip_data.get("description"),
        "start_date": trip_data.get("start_date"),
        "end_date": trip_data.get("end_date"),
        "budget": trip_data.get("budget"),
        "status": trip_data.get("status", "planning"),
    }

    # Store in Supabase
    db_trip = await db_client.trips.create(structured_data)
    trip_id = db_trip.get("id")

    if not trip_id:
        logger.error("Failed to create trip in Supabase")
        raise ValueError("Failed to create trip in database")
    
    return trip_id


@ensure_memory_client_initialized
async def _create_trip_entities(
    trip_data: Dict[str, Any], trip_id: str, user_id: str
) -> List[Dict[str, Any]]:
    """Create entities for the trip in Neo4j.

    Args:
        trip_data: Trip data dictionary
        trip_id: Trip ID
        user_id: User ID

    Returns:
        List of created entities
    """
    entities = []
    entities_to_create = []

    # Add trip entity
    trip_observations = [
        f"Trip from {trip_data.get('start_date')} to {trip_data.get('end_date')}",
        f"Budget: ${trip_data.get('budget')}",
    ]
    if trip_data.get("description"):
        trip_observations.append(trip_data.get("description"))

    entities_to_create.append(
        {
            "name": f"Trip:{trip_id}",
            "entityType": "Trip",
            "observations": trip_observations,
        }
    )

    # Add user entity if not exists
    entities_to_create.append(
        {
            "name": f"User:{user_id}",
            "entityType": "User",
            "observations": ["TripSage user"],
        }
    )

    # Add destinations
    destinations = trip_data.get("destinations", [])
    for destination in destinations:
        entity = _create_destination_entity(destination)
        if entity:
            entities_to_create.append(entity)

    # Add accommodations
    accommodations = trip_data.get("accommodations", [])
    for accommodation in accommodations:
        entity = _create_accommodation_entity(accommodation)
        if entity:
            entities_to_create.append(entity)

    # Add activities
    activities = trip_data.get("activities", [])
    for activity in activities:
        entity = _create_activity_entity(activity)
        if entity:
            entities_to_create.append(entity)
    
    # Add events
    events = trip_data.get("events", [])
    for event in events:
        entity = _create_event_entity(event)
        if entity:
            entities_to_create.append(entity)
    
    # Add transportation
    transportation = trip_data.get("transportation", [])
    for transport in transportation:
        entity = _create_transportation_entity(transport)
        if entity:
            entities_to_create.append(entity)

    # Create all entities in Neo4j
    if entities_to_create:
        entities = await memory_client.create_entities(entities_to_create)
    
    return entities


def _create_destination_entity(destination: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a destination entity.

    Args:
        destination: Destination data

    Returns:
        Destination entity or None if invalid
    """
    dest_name = destination.get("name")
    if not dest_name:
        return None

    # Prepare observations
    observations = []
    if destination.get("description"):
        observations.append(destination.get("description"))
    if destination.get("country"):
        observations.append(f"Located in {destination.get('country')}")

    return {
        "name": dest_name,
        "entityType": "Destination",
        "observations": observations,
        "country": destination.get("country", "Unknown"),
        "type": destination.get("type", "city"),
    }


def _create_accommodation_entity(accommodation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create an accommodation entity.

    Args:
        accommodation: Accommodation data

    Returns:
        Accommodation entity or None if invalid
    """
    acc_name = accommodation.get("name")
    if not acc_name:
        return None

    # Prepare observations
    observations = []
    if accommodation.get("description"):
        observations.append(accommodation.get("description"))
    if accommodation.get("address"):
        observations.append(f"Located at {accommodation.get('address')}")
    if accommodation.get("price"):
        observations.append(f"Price: ${accommodation.get('price')} per night")

    return {
        "name": acc_name,
        "entityType": "Accommodation",
        "observations": observations,
        "destination": accommodation.get("destination"),
        "type": accommodation.get("type", "hotel"),
    }


def _create_activity_entity(activity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create an activity entity.

    Args:
        activity: Activity data

    Returns:
        Activity entity or None if invalid
    """
    act_name = activity.get("name")
    if not act_name:
        return None

    # Prepare observations
    observations = []
    if activity.get("description"):
        observations.append(activity.get("description"))
    if activity.get("duration"):
        observations.append(f"Duration: {activity.get('duration')}")
    if activity.get("price"):
        observations.append(f"Price: ${activity.get('price')}")

    return {
        "name": act_name,
        "entityType": "Activity",
        "observations": observations,
        "destination": activity.get("destination"),
        "type": activity.get("type", "attraction"),
    }


def _create_event_entity(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create an event entity.

    Args:
        event: Event data

    Returns:
        Event entity or None if invalid
    """
    event_name = event.get("name")
    if not event_name:
        return None

    # Prepare observations
    observations = []
    if event.get("description"):
        observations.append(event.get("description"))
    if event.get("start_time") and event.get("end_time"):
        observations.append(
            f"From {event.get('start_time')} to {event.get('end_time')}"
        )
    if event.get("location"):
        observations.append(f"Located at {event.get('location')}")

    return {
        "name": event_name,
        "entityType": "Event",
        "observations": observations,
        "destination": event.get("destination"),
        "type": event.get("type", "event"),
    }


def _create_transportation_entity(transport: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a transportation entity.

    Args:
        transport: Transportation data

    Returns:
        Transportation entity or None if invalid
    """
    transport_name = transport.get("name")
    if not transport_name:
        return None

    # Prepare observations
    observations = []
    if transport.get("description"):
        observations.append(transport.get("description"))
    if transport.get("departure_time") and transport.get("arrival_time"):
        observations.append(
            f"Departure: {transport.get('departure_time')}, "
            f"Arrival: {transport.get('arrival_time')}"
        )
    if transport.get("price"):
        observations.append(f"Price: ${transport.get('price')}")

    return {
        "name": transport_name,
        "entityType": "Transportation",
        "observations": observations,
        "from_destination": transport.get("from_destination"),
        "to_destination": transport.get("to_destination"),
        "type": transport.get("type", "flight"),
    }


@ensure_memory_client_initialized
async def _create_trip_relations(
    trip_data: Dict[str, Any], trip_id: str, created_entities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Create relationships for the trip in Neo4j.

    Args:
        trip_data: Trip data dictionary
        trip_id: Trip ID
        created_entities: List of created entities

    Returns:
        List of created relations
    """
    relations_to_create = []
    
    # User-Trip relation
    user_id = trip_data.get("user_id")
    if user_id:
        relations_to_create.append(
            {
                "from": f"User:{user_id}",
                "relationType": "PLANS",
                "to": f"Trip:{trip_id}",
            }
        )
    
    # Extract entity names by type for convenience
    destinations = [
        entity["name"] for entity in created_entities 
        if entity.get("entityType") == "Destination"
    ]
    accommodations = [
        entity["name"] for entity in created_entities 
        if entity.get("entityType") == "Accommodation"
    ]
    activities = [
        entity["name"] for entity in created_entities 
        if entity.get("entityType") == "Activity"
    ]
    events = [
        entity["name"] for entity in created_entities 
        if entity.get("entityType") == "Event"
    ]
    transportation = [
        entity["name"] for entity in created_entities 
        if entity.get("entityType") == "Transportation"
    ]
    
    # Trip-Destination relations
    for dest_name in destinations:
        relations_to_create.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": dest_name,
            }
        )
    
    # Trip-Accommodation relations
    for acc_name in accommodations:
        relations_to_create.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": acc_name,
            }
        )
    
    # Trip-Activity relations
    for act_name in activities:
        relations_to_create.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": act_name,
            }
        )
    
    # Trip-Event relations
    for event_name in events:
        relations_to_create.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": event_name,
            }
        )
    
    # Trip-Transportation relations
    for transport_name in transportation:
        relations_to_create.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": transport_name,
            }
        )
    
    # Create additional entity relationships based on their connections
    # (e.g., Activity-Destination, Accommodation-Destination)
    for acc_data in trip_data.get("accommodations", []):
        if acc_data.get("name") and acc_data.get("destination"):
            if acc_data["name"] in accommodations and acc_data["destination"] in destinations:
                relations_to_create.append(
                    {
                        "from": acc_data["name"],
                        "relationType": "LOCATED_IN",
                        "to": acc_data["destination"],
                    }
                )
    
    for act_data in trip_data.get("activities", []):
        if act_data.get("name") and act_data.get("destination"):
            if act_data["name"] in activities and act_data["destination"] in destinations:
                relations_to_create.append(
                    {
                        "from": act_data["name"],
                        "relationType": "LOCATED_IN",
                        "to": act_data["destination"],
                    }
                )
    
    for event_data in trip_data.get("events", []):
        if event_data.get("name") and event_data.get("destination"):
            if event_data["name"] in events and event_data["destination"] in destinations:
                relations_to_create.append(
                    {
                        "from": event_data["name"],
                        "relationType": "LOCATED_IN",
                        "to": event_data["destination"],
                    }
                )
    
    # Transportation connections
    for transport_data in trip_data.get("transportation", []):
        if (transport_data.get("name") and 
            transport_data.get("from_destination") and 
            transport_data.get("to_destination")):
            
            transport_name = transport_data["name"]
            from_dest = transport_data["from_destination"]
            to_dest = transport_data["to_destination"]
            
            if (transport_name in transportation and 
                from_dest in destinations and 
                to_dest in destinations):
                
                relations_to_create.append(
                    {
                        "from": transport_name,
                        "relationType": "DEPARTS_FROM",
                        "to": from_dest,
                    }
                )
                
                relations_to_create.append(
                    {
                        "from": transport_name,
                        "relationType": "ARRIVES_AT",
                        "to": to_dest,
                    }
                )
                
                # Also add direct connection between destinations
                relations_to_create.append(
                    {
                        "from": from_dest,
                        "relationType": "CONNECTED_TO",
                        "to": to_dest,
                    }
                )
    
    # Create all relations in Neo4j
    relations = []
    if relations_to_create:
        relations = await memory_client.create_relations(relations_to_create)
    
    return relations