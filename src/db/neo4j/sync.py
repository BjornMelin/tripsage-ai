"""
Neo4j synchronization with relational database.

This module provides utilities to synchronize data between the Neo4j knowledge graph
and the Supabase relational database, ensuring consistency across the dual storage
architecture.
"""

from datetime import datetime
from typing import Any, Dict

from src.db.client import db_client
from src.db.neo4j.client import neo4j_client
from src.db.neo4j.exceptions import Neo4jError
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


async def sync_destinations_to_knowledge_graph() -> Dict[str, int]:
    """Synchronize destinations from Supabase to Neo4j knowledge graph.

    This function fetches all destinations from the relational database
    and ensures they exist in the knowledge graph with proper relationships.

    Returns:
        Statistics dictionary with counts of created and updated entities
    """
    try:
        # Initialize clients
        await neo4j_client.initialize()

        # Get all destinations from Supabase
        query = """
        SELECT * FROM destinations
        """
        rel_destinations = await db_client.execute_query(query)

        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "relationships_created": 0,
        }

        # Process each destination
        for rel_dest in rel_destinations:
            try:
                # Convert to Neo4j format
                neo4j_dest = _convert_rel_to_neo4j_destination(rel_dest)

                # Sync destination
                destination, created = (
                    await neo4j_client.sync_destination_from_relational(neo4j_dest)
                )

                if created:
                    stats["created"] += 1
                    logger.info(
                        f"Created destination in knowledge graph: {destination.name}"
                    )
                else:
                    stats["updated"] += 1
                    logger.info(
                        f"Updated destination in knowledge graph: {destination.name}"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to sync destination {rel_dest.get('name')}: {str(e)}"
                )
                stats["failed"] += 1

        # Sync relationships between destinations
        await _sync_destination_relationships()

        # Log statistics
        logger.info(
            f"Sync complete: {stats['created']} created, {stats['updated']} updated, "
            f"{stats['failed']} failed"
        )

        return stats

    except Exception as e:
        logger.error(f"Destination synchronization failed: {str(e)}")
        raise


async def sync_trips_to_knowledge_graph() -> Dict[str, int]:
    """Synchronize trips from Supabase to Neo4j knowledge graph.

    This function fetches all trips from the relational database
    and ensures they exist in the knowledge graph with proper relationships
    to destinations, accommodations, and transportation.

    Returns:
        Statistics dictionary with counts of created and updated entities
    """
    try:
        # Initialize clients
        await neo4j_client.initialize()

        # Get all trips from Supabase
        trip_query = """
        SELECT 
            t.id,
            t.title,
            t.description,
            t.start_date,
            t.end_date,
            t.budget,
            t.status,
            t.created_at,
            t.updated_at,
            u.name as user_name,
            u.id as user_id
        FROM trips t
        JOIN users u ON t.user_id = u.id
        """
        rel_trips = await db_client.execute_query(trip_query)

        stats = {
            "trips_created": 0,
            "trips_updated": 0,
            "users_created": 0,
            "relationships_created": 0,
            "failed": 0,
        }

        # Process each trip
        for rel_trip in rel_trips:
            try:
                # First ensure the user exists in Neo4j
                user_result = await _ensure_user_exists(
                    rel_trip["user_id"], rel_trip["user_name"]
                )
                if user_result["created"]:
                    stats["users_created"] += 1

                # Create or update trip
                trip_id = rel_trip["id"]

                # Check if trip already exists
                query = """
                MATCH (t:Trip {id: $id})
                RETURN count(t) > 0 AS exists
                """

                result = await neo4j_client.execute_query(query, {"id": trip_id})
                trip_exists = result[0]["exists"] if result else False

                # Prepare trip properties
                trip_props = {
                    "id": trip_id,
                    "title": rel_trip["title"],
                    "description": rel_trip["description"] or "",
                    "start_date": (
                        rel_trip["start_date"].isoformat()
                        if rel_trip["start_date"]
                        else None
                    ),
                    "end_date": (
                        rel_trip["end_date"].isoformat()
                        if rel_trip["end_date"]
                        else None
                    ),
                    "budget": float(rel_trip["budget"]) if rel_trip["budget"] else 0,
                    "status": rel_trip["status"],
                    "created_at": (
                        rel_trip["created_at"].isoformat()
                        if rel_trip["created_at"]
                        else datetime.utcnow().isoformat()
                    ),
                    "updated_at": (
                        rel_trip["updated_at"].isoformat()
                        if rel_trip["updated_at"]
                        else datetime.utcnow().isoformat()
                    ),
                }

                if trip_exists:
                    # Update existing trip
                    update_query = """
                    MATCH (t:Trip {id: $id})
                    SET t = $properties
                    RETURN t
                    """

                    await neo4j_client.execute_query(
                        update_query, {"id": trip_id, "properties": trip_props}
                    )

                    stats["trips_updated"] += 1
                    logger.info(f"Updated trip in knowledge graph: {trip_id}")
                else:
                    # Create new trip
                    create_query = """
                    CREATE (t:Trip $properties)
                    RETURN t
                    """

                    await neo4j_client.execute_query(
                        create_query, {"properties": trip_props}
                    )

                    stats["trips_created"] += 1
                    logger.info(f"Created trip in knowledge graph: {trip_id}")

                # Create relationship between user and trip if it doesn't exist
                user_trip_query = """
                MATCH (u:User {id: $user_id}), (t:Trip {id: $trip_id})
                MERGE (u)-[r:PLANNED]->(t)
                RETURN count(r) AS rel_count
                """

                result = await neo4j_client.execute_query(
                    user_trip_query,
                    {"user_id": rel_trip["user_id"], "trip_id": trip_id},
                )

                if result and result[0]["rel_count"] > 0:
                    stats["relationships_created"] += 1

                # Now get the trip's destinations, accommodations, etc.
                await _link_trip_to_destinations(trip_id)

            except Exception as e:
                logger.error(f"Failed to sync trip {rel_trip.get('id')}: {str(e)}")
                stats["failed"] += 1

        # Log statistics
        logger.info(
            f"Trip sync complete: {stats['trips_created']} created, "
            f"{stats['trips_updated']} updated, {stats['failed']} failed"
        )

        return stats

    except Exception as e:
        logger.error(f"Trip synchronization failed: {str(e)}")
        raise


async def _ensure_user_exists(user_id: str, user_name: str) -> Dict[str, bool]:
    """Ensure user exists in Neo4j.

    Args:
        user_id: User ID
        user_name: User name

    Returns:
        Dictionary with created status
    """
    try:
        # Check if user exists
        query = """
        MATCH (u:User {id: $id})
        RETURN count(u) > 0 AS exists
        """

        result = await neo4j_client.execute_query(query, {"id": user_id})
        user_exists = result[0]["exists"] if result else False

        if not user_exists:
            # Create user
            create_query = """
            CREATE (u:User {
                id: $id,
                name: $name,
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN u
            """

            await neo4j_client.execute_query(
                create_query, {"id": user_id, "name": user_name}
            )

            return {"created": True}

        return {"created": False}

    except Exception as e:
        logger.error(f"Failed to ensure user exists: {str(e)}")
        raise


async def _link_trip_to_destinations(trip_id: str) -> int:
    """Link trip to its destinations.

    Args:
        trip_id: Trip ID

    Returns:
        Number of relationships created
    """
    try:
        # Get trip destinations from itinerary items
        query = """
        SELECT location FROM itinerary_items 
        WHERE trip_id = $trip_id
        """

        locations = await db_client.execute_query(query, {"trip_id": trip_id})
        relationships_created = 0

        for location_record in locations:
            location = location_record.get("location")
            if not location:
                continue

            # Try to find this destination in Neo4j
            dest_query = """
            MATCH (d:Destination)
            WHERE d.name = $location OR d.city = $location
            RETURN d.name AS name
            """

            dest_result = await neo4j_client.execute_query(
                dest_query, {"location": location}
            )

            if dest_result:
                dest_name = dest_result[0]["name"]

                # Create relationship between trip and destination
                rel_query = """
                MATCH (t:Trip {id: $trip_id}), (d:Destination {name: $dest_name})
                MERGE (t)-[r:INCLUDES]->(d)
                RETURN count(r) AS rel_count
                """

                result = await neo4j_client.execute_query(
                    rel_query, {"trip_id": trip_id, "dest_name": dest_name}
                )

                if result and result[0]["rel_count"] > 0:
                    relationships_created += 1

        return relationships_created

    except Exception as e:
        logger.error(f"Failed to link trip to destinations: {str(e)}")
        return 0


async def _sync_destination_relationships() -> int:
    """Synchronize relationships between destinations.

    Returns:
        Number of relationships created
    """
    try:
        # For now, we'll use a simple approach based on flights/transportation
        # Get all transportation records that connect destinations
        query = """
        SELECT 
            origin, 
            destination,
            type,
            price
        FROM transportation
        """

        transportations = await db_client.execute_query(query)
        relationships_created = 0

        for transport in transportations:
            origin = transport.get("origin")
            destination = transport.get("destination")

            if not origin or not destination:
                continue

            # Create relationship between destinations
            properties = {
                "transport_type": transport.get("type", "unknown"),
                "price": float(transport.get("price", 0)),
                "last_updated": datetime.utcnow().isoformat(),
            }

            # First try exact match on destination names
            try:
                success = await neo4j_client.create_destination_relationship(
                    from_destination=origin,
                    relationship_type="CONNECTED_TO",
                    to_destination=destination,
                    properties=properties,
                )

                if success:
                    relationships_created += 1
                    continue
            except Neo4jError:
                # Destinations might not exist with these exact names
                pass

            # If that fails, try to match by city names
            try:
                # Find destinations by city names
                origin_query = """
                MATCH (d:Destination)
                WHERE d.city = $city
                RETURN d.name AS name
                LIMIT 1
                """

                dest_query = """
                MATCH (d:Destination)
                WHERE d.city = $city
                RETURN d.name AS name
                LIMIT 1
                """

                origin_result = await neo4j_client.execute_query(
                    origin_query, {"city": origin}
                )

                dest_result = await neo4j_client.execute_query(
                    dest_query, {"city": destination}
                )

                if origin_result and dest_result:
                    origin_name = origin_result[0]["name"]
                    dest_name = dest_result[0]["name"]

                    success = await neo4j_client.create_destination_relationship(
                        from_destination=origin_name,
                        relationship_type="CONNECTED_TO",
                        to_destination=dest_name,
                        properties=properties,
                    )

                    if success:
                        relationships_created += 1
            except Neo4jError:
                # Continue to next transportation record
                pass

        return relationships_created

    except Exception as e:
        logger.error(f"Failed to sync destination relationships: {str(e)}")
        return 0


def _convert_rel_to_neo4j_destination(rel_dest: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a relational destination to Neo4j format.

    Args:
        rel_dest: Relational destination record

    Returns:
        Neo4j destination data
    """
    # Get common fields
    neo4j_dest = {
        "name": rel_dest.get("name"),
        "country": rel_dest.get("country", "Unknown"),
        "type": rel_dest.get("type", "city"),
        "description": rel_dest.get("description", ""),
    }

    # Optional fields
    if "region" in rel_dest:
        neo4j_dest["region"] = rel_dest["region"]

    if "city" in rel_dest:
        neo4j_dest["city"] = rel_dest["city"]

    # Handle coordinates if available
    if "latitude" in rel_dest and "longitude" in rel_dest:
        neo4j_dest["latitude"] = float(rel_dest["latitude"])
        neo4j_dest["longitude"] = float(rel_dest["longitude"])

    # Cost information
    if "cost_level" in rel_dest:
        neo4j_dest["cost_level"] = int(rel_dest["cost_level"])

    # Safety information
    if "safety_rating" in rel_dest:
        neo4j_dest["safety_rating"] = float(rel_dest["safety_rating"])

    # Popular activities/interests
    if "popular_for" in rel_dest and rel_dest["popular_for"]:
        neo4j_dest["popular_for"] = rel_dest["popular_for"]

    # Add timestamps
    neo4j_dest["created_at"] = rel_dest.get("created_at", datetime.utcnow()).isoformat()
    neo4j_dest["updated_at"] = rel_dest.get("updated_at", datetime.utcnow()).isoformat()

    return neo4j_dest
