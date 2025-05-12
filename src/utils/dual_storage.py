"""
Dual storage strategy for TripSage.

This module provides utilities for implementing the dual storage strategy,
where structured data is stored in Supabase and relationships/unstructured
data is stored in Neo4j via the Memory MCP.
"""

from typing import Any, Dict

from src.db.client import db_client
from src.mcp.memory.client import memory_client
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


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

    # Step 2: Store unstructured data and relationships in Neo4j via Memory MCP
    logger.info("Storing unstructured trip data in Neo4j via Memory MCP")
    await memory_client.initialize()

    # Extract destinations, accommodations, activities, etc.
    destinations = trip_data.get("destinations", [])
    accommodations = trip_data.get("accommodations", [])
    activities = trip_data.get("activities", [])
    events = trip_data.get("events", [])
    transportation = trip_data.get("transportation", [])

    # Prepare entities for Neo4j
    entities = []

    # Add trip entity
    trip_observations = [
        f"Trip from {trip_data.get('start_date')} to {trip_data.get('end_date')}",
        f"Budget: ${trip_data.get('budget')}",
    ]
    if trip_data.get("description"):
        trip_observations.append(trip_data.get("description"))

    entities.append(
        {
            "name": f"Trip:{trip_id}",
            "entityType": "Trip",
            "observations": trip_observations,
        }
    )

    # Add user entity if not exists
    entities.append(
        {
            "name": f"User:{user_id}",
            "entityType": "User",
            "observations": ["TripSage user"],
        }
    )

    # Add destinations
    destination_names = []
    for destination in destinations:
        dest_name = destination.get("name")
        if not dest_name:
            continue

        destination_names.append(dest_name)

        # Prepare observations
        observations = []
        if destination.get("description"):
            observations.append(destination.get("description"))
        if destination.get("country"):
            observations.append(f"Located in {destination.get('country')}")

        entities.append(
            {
                "name": dest_name,
                "entityType": "Destination",
                "observations": observations,
                "country": destination.get("country", "Unknown"),
                "type": destination.get("type", "city"),
            }
        )

    # Add accommodations
    accommodation_names = []
    for accommodation in accommodations:
        acc_name = accommodation.get("name")
        if not acc_name:
            continue

        accommodation_names.append(acc_name)

        # Prepare observations
        observations = []
        if accommodation.get("description"):
            observations.append(accommodation.get("description"))

        entities.append(
            {
                "name": acc_name,
                "entityType": "Accommodation",
                "observations": observations,
                "destination": accommodation.get("destination"),
                "type": accommodation.get("type", "hotel"),
            }
        )

    # Add activities
    activity_names = []
    for activity in activities:
        act_name = activity.get("name")
        if not act_name:
            continue

        activity_names.append(act_name)

        # Prepare observations
        observations = []
        if activity.get("description"):
            observations.append(activity.get("description"))

        entities.append(
            {
                "name": act_name,
                "entityType": "Activity",
                "observations": observations,
                "destination": activity.get("destination"),
                "type": activity.get("type", "attraction"),
            }
        )

    # Add events
    event_names = []
    for event in events:
        event_name = event.get("name")
        if not event_name:
            continue

        event_names.append(event_name)

        # Prepare observations
        observations = []
        if event.get("description"):
            observations.append(event.get("description"))

        entities.append(
            {
                "name": event_name,
                "entityType": "Event",
                "observations": observations,
                "destination": event.get("destination"),
                "type": event.get("type", "cultural"),
            }
        )

    # Add transportation
    transportation_names = []
    for trans in transportation:
        trans_name = trans.get("name")
        if not trans_name:
            continue

        transportation_names.append(trans_name)

        # Prepare observations
        observations = []
        if trans.get("description"):
            observations.append(trans.get("description"))

        entities.append(
            {
                "name": trans_name,
                "entityType": "Transportation",
                "observations": observations,
                "origin": trans.get("origin"),
                "destination": trans.get("destination"),
                "type": trans.get("type", "flight"),
            }
        )

    # Store entities in Neo4j via Memory MCP
    created_entities = await memory_client.create_entities(entities)

    # Create relationships
    relations = []

    # User plans Trip
    relations.append(
        {
            "from": f"User:{user_id}",
            "relationType": "PLANS",
            "to": f"Trip:{trip_id}",
        }
    )

    # Trip includes Destinations
    for dest_name in destination_names:
        relations.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": dest_name,
            }
        )

    # Trip includes Accommodations
    for acc_name in accommodation_names:
        relations.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": acc_name,
            }
        )

        # Find destination for this accommodation
        for accommodation in accommodations:
            if accommodation.get("name") == acc_name and accommodation.get(
                "destination"
            ):
                relations.append(
                    {
                        "from": acc_name,
                        "relationType": "LOCATED_IN",
                        "to": accommodation.get("destination"),
                    }
                )

    # Trip includes Activities
    for act_name in activity_names:
        relations.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": act_name,
            }
        )

        # Find destination for this activity
        for activity in activities:
            if activity.get("name") == act_name and activity.get("destination"):
                relations.append(
                    {
                        "from": act_name,
                        "relationType": "TAKES_PLACE_IN",
                        "to": activity.get("destination"),
                    }
                )

    # Trip includes Events
    for event_name in event_names:
        relations.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": event_name,
            }
        )

        # Find destination for this event
        for event in events:
            if event.get("name") == event_name and event.get("destination"):
                relations.append(
                    {
                        "from": event_name,
                        "relationType": "TAKES_PLACE_IN",
                        "to": event.get("destination"),
                    }
                )

    # Trip includes Transportation
    for trans_name in transportation_names:
        relations.append(
            {
                "from": f"Trip:{trip_id}",
                "relationType": "INCLUDES",
                "to": trans_name,
            }
        )

        # Find origin and destination for this transportation
        for trans in transportation:
            if trans.get("name") == trans_name:
                if trans.get("origin"):
                    relations.append(
                        {
                            "from": trans_name,
                            "relationType": "DEPARTS_FROM",
                            "to": trans.get("origin"),
                        }
                    )
                if trans.get("destination"):
                    relations.append(
                        {
                            "from": trans_name,
                            "relationType": "ARRIVES_AT",
                            "to": trans.get("destination"),
                        }
                    )

    # Store relationships in Neo4j via Memory MCP
    created_relations = await memory_client.create_relations(relations)

    return {
        "supabase_id": trip_id,
        "neo4j_entities": len(created_entities),
        "neo4j_relations": len(created_relations),
    }


async def retrieve_trip_with_dual_storage(
    trip_id: str, include_graph: bool = False
) -> Dict[str, Any]:
    """Retrieve trip data using the dual storage strategy.

    This function retrieves structured trip data from Supabase and
    relationships/unstructured data from Neo4j via the Memory MCP.

    Args:
        trip_id: Trip ID
        include_graph: Whether to include the knowledge graph

    Returns:
        Dictionary with trip data from both storage systems
    """
    # Step 1: Retrieve structured data from Supabase
    logger.info(f"Retrieving structured trip data from Supabase for trip {trip_id}")

    db_trip = await db_client.trips.get(trip_id)
    if not db_trip:
        logger.error(f"Trip {trip_id} not found in Supabase")
        raise ValueError(f"Trip {trip_id} not found")

    # Step 2: Retrieve related entities from Neo4j via Memory MCP
    logger.info(
        f"Retrieving unstructured trip data from Neo4j via Memory MCP for "
        f"trip {trip_id}"
    )
    await memory_client.initialize()

    # Get trip entity
    trip_nodes = await memory_client.open_nodes([f"Trip:{trip_id}"])
    if not trip_nodes:
        logger.warning(f"Trip {trip_id} not found in Neo4j")
        trip_node = None
    else:
        trip_node = trip_nodes[0]

    # Combine data
    result = {
        **db_trip,
        "knowledge_graph": {
            "trip_node": trip_node,
        },
    }

    # Include full graph if requested
    if include_graph:
        logger.info(f"Retrieving full knowledge graph for trip {trip_id}")
        # Search for all nodes connected to this trip
        search_result = await memory_client.search_nodes(f"Trip:{trip_id}")

        # Get detailed information for each node
        if search_result:
            node_names = [
                node.get("name") for node in search_result if node.get("name")
            ]
            detailed_nodes = await memory_client.open_nodes(node_names)
            result["knowledge_graph"]["nodes"] = detailed_nodes

    return result


async def update_trip_with_dual_storage(
    trip_id: str, trip_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Update trip data using the dual storage strategy.

    This function updates structured trip data in Supabase and
    relationships/unstructured data in Neo4j via the Memory MCP.

    Args:
        trip_id: Trip ID
        trip_data: Updated trip data

    Returns:
        Dictionary with update status
    """
    # Step 1: Update structured data in Supabase
    logger.info(f"Updating structured trip data in Supabase for trip {trip_id}")

    # Extract structured data for Supabase
    structured_data = {}
    if "title" in trip_data:
        structured_data["title"] = trip_data["title"]
    if "description" in trip_data:
        structured_data["description"] = trip_data["description"]
    if "start_date" in trip_data:
        structured_data["start_date"] = trip_data["start_date"]
    if "end_date" in trip_data:
        structured_data["end_date"] = trip_data["end_date"]
    if "budget" in trip_data:
        structured_data["budget"] = trip_data["budget"]
    if "status" in trip_data:
        structured_data["status"] = trip_data["status"]

    # Update in Supabase
    if structured_data:
        db_trip = await db_client.trips.update(trip_id, structured_data)
        if not db_trip:
            logger.error(f"Trip {trip_id} not found in Supabase")
            raise ValueError(f"Trip {trip_id} not found")

    # Step 2: Update unstructured data in Neo4j via Memory MCP
    logger.info(
        f"Updating unstructured trip data in Neo4j via Memory MCP for trip {trip_id}"
    )
    await memory_client.initialize()

    # Get trip entity
    trip_nodes = await memory_client.open_nodes([f"Trip:{trip_id}"])
    if not trip_nodes:
        logger.warning(f"Trip {trip_id} not found in Neo4j")
    else:
        # Update trip observations if description changed
        if "description" in trip_data:
            # Create new observations
            observations = [
                f"Trip from {trip_data.get('start_date', db_trip.get('start_date'))} "
                f"to {trip_data.get('end_date', db_trip.get('end_date'))}",
                f"Budget: ${trip_data.get('budget', db_trip.get('budget'))}",
                trip_data["description"],
            ]

            # Add observations to trip entity
            await memory_client.add_observations(
                [
                    {
                        "entityName": f"Trip:{trip_id}",
                        "contents": observations,
                    }
                ]
            )

    return {
        "supabase_updated": bool(structured_data),
        "neo4j_updated": "description" in trip_data,
    }


async def delete_trip_with_dual_storage(trip_id: str) -> Dict[str, Any]:
    """Delete trip data using the dual storage strategy.

    This function deletes structured trip data from Supabase and
    relationships/unstructured data from Neo4j via the Memory MCP.

    Args:
        trip_id: Trip ID

    Returns:
        Dictionary with deletion status
    """
    # Step 1: Delete structured data from Supabase
    logger.info(f"Deleting structured trip data from Supabase for trip {trip_id}")

    deleted = await db_client.trips.delete(trip_id)
    if not deleted:
        logger.error(f"Trip {trip_id} not found in Supabase")
        raise ValueError(f"Trip {trip_id} not found")

    # Step 2: Delete unstructured data from Neo4j via Memory MCP
    logger.info(
        f"Deleting unstructured trip data from Neo4j via Memory MCP for trip {trip_id}"
    )
    await memory_client.initialize()

    # Delete trip entity
    deleted_entities = await memory_client.delete_entities([f"Trip:{trip_id}"])

    return {
        "supabase_deleted": True,
        "neo4j_deleted": bool(deleted_entities),
    }
