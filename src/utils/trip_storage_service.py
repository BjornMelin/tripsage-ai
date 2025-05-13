"""
Trip Storage Service implementation for TripSage.

This module provides a concrete implementation of the dual storage service pattern
for Trip entities, storing structured data in Supabase and relationships/unstructured
data in Neo4j via the Memory MCP.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.db.client import db_client
from src.mcp.memory.client import memory_client
from src.utils.decorators import ensure_memory_client_initialized
from src.utils.dual_storage_service import DualStorageService
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class TripPrimaryModel(BaseModel):
    """Model for Trip data in the primary database (Supabase)."""

    id: Optional[str] = None
    user_id: str
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    budget: Optional[float] = None
    status: str = "planning"


class TripGraphModel(BaseModel):
    """Model for Trip data in the graph database (Neo4j)."""

    name: str
    entityType: str = "Trip"
    observations: List[str]


class TripStorageService(DualStorageService[TripPrimaryModel, TripGraphModel]):
    """Service for storing and retrieving Trip data using the dual storage strategy."""

    def __init__(self):
        """Initialize the Trip Storage Service."""
        super().__init__(primary_client=db_client, graph_client=memory_client)

    async def _store_in_primary(self, data: Dict[str, Any]) -> str:
        """Store structured trip data in Supabase.

        Args:
            data: Trip data dictionary

        Returns:
            Trip ID

        Raises:
            ValueError: If trip creation fails
        """
        # Extract structured data for Supabase
        structured_data = {
            "user_id": data.get("user_id"),
            "title": data.get("title"),
            "description": data.get("description"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "budget": data.get("budget"),
            "status": data.get("status", "planning"),
        }

        # Store in Supabase
        db_trip = await db_client.trips.create(structured_data)
        trip_id = db_trip.get("id")

        if not trip_id:
            logger.error("Failed to create trip in Supabase")
            raise ValueError("Failed to create trip in database")

        return trip_id

    @ensure_memory_client_initialized
    async def _create_graph_entities(
        self, trip_data: Dict[str, Any], trip_id: str
    ) -> List[Dict[str, Any]]:
        """Create entities for the trip in Neo4j.

        Args:
            trip_data: Trip data dictionary
            trip_id: Trip ID

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
        user_id = trip_data.get("user_id")
        if user_id:
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
            entity = self._create_destination_entity(destination)
            if entity:
                entities_to_create.append(entity)

        # Add accommodations
        accommodations = trip_data.get("accommodations", [])
        for accommodation in accommodations:
            entity = self._create_accommodation_entity(accommodation)
            if entity:
                entities_to_create.append(entity)

        # Add activities
        activities = trip_data.get("activities", [])
        for activity in activities:
            entity = self._create_activity_entity(activity)
            if entity:
                entities_to_create.append(entity)

        # Add events
        events = trip_data.get("events", [])
        for event in events:
            entity = self._create_event_entity(event)
            if entity:
                entities_to_create.append(entity)

        # Add transportation
        transportation = trip_data.get("transportation", [])
        for transport in transportation:
            entity = self._create_transportation_entity(transport)
            if entity:
                entities_to_create.append(entity)

        # Create all entities in Neo4j
        if entities_to_create:
            entities = await memory_client.create_entities(entities_to_create)

        return entities

    def _create_destination_entity(
        self, destination: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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

    def _create_accommodation_entity(
        self,
        accommodation: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
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

    def _create_activity_entity(
        self, activity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
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

    def _create_event_entity(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

    def _create_transportation_entity(
        self,
        transport: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
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
    async def _create_graph_relations(
        self,
        trip_data: Dict[str, Any],
        trip_id: str,
        created_entities: List[Dict[str, Any]],
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
            entity["name"]
            for entity in created_entities
            if entity.get("entityType") == "Destination"
        ]
        accommodations = [
            entity["name"]
            for entity in created_entities
            if entity.get("entityType") == "Accommodation"
        ]
        activities = [
            entity["name"]
            for entity in created_entities
            if entity.get("entityType") == "Activity"
        ]
        events = [
            entity["name"]
            for entity in created_entities
            if entity.get("entityType") == "Event"
        ]
        transportation = [
            entity["name"]
            for entity in created_entities
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
                if (
                    acc_data["name"] in accommodations
                    and acc_data["destination"] in destinations
                ):
                    relations_to_create.append(
                        {
                            "from": acc_data["name"],
                            "relationType": "LOCATED_IN",
                            "to": acc_data["destination"],
                        }
                    )

        for act_data in trip_data.get("activities", []):
            if act_data.get("name") and act_data.get("destination"):
                if (
                    act_data["name"] in activities
                    and act_data["destination"] in destinations
                ):
                    relations_to_create.append(
                        {
                            "from": act_data["name"],
                            "relationType": "LOCATED_IN",
                            "to": act_data["destination"],
                        }
                    )

        for event_data in trip_data.get("events", []):
            if event_data.get("name") and event_data.get("destination"):
                if (
                    event_data["name"] in events
                    and event_data["destination"] in destinations
                ):
                    relations_to_create.append(
                        {
                            "from": event_data["name"],
                            "relationType": "LOCATED_IN",
                            "to": event_data["destination"],
                        }
                    )

        # Transportation connections
        for transport_data in trip_data.get("transportation", []):
            if (
                transport_data.get("name")
                and transport_data.get("from_destination")
                and transport_data.get("to_destination")
            ):
                transport_name = transport_data["name"]
                from_dest = transport_data["from_destination"]
                to_dest = transport_data["to_destination"]

                if (
                    transport_name in transportation
                    and from_dest in destinations
                    and to_dest in destinations
                ):
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

    async def _retrieve_from_primary(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve structured trip data from Supabase.

        Args:
            trip_id: Trip ID

        Returns:
            Trip data from Supabase
        """
        return await db_client.trips.get(trip_id)

    @ensure_memory_client_initialized
    async def _retrieve_from_graph(
        self, trip_id: str, include_graph: bool = False
    ) -> Dict[str, Any]:
        """Retrieve graph data for the trip from Neo4j.

        Args:
            trip_id: Trip ID
            include_graph: Whether to include the full knowledge graph

        Returns:
            Trip data from Neo4j
        """
        # Get trip node
        trip_node = (await memory_client.open_nodes([f"Trip:{trip_id}"]))[0]

        result = {"trip_node": trip_node}

        # Get full graph if requested
        if include_graph:
            graph_nodes = await memory_client.search_nodes(f"Trip:{trip_id}")
            result["nodes"] = graph_nodes

        return result

    async def _combine_data(
        self, primary_data: Dict[str, Any], graph_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine data from Supabase and Neo4j.

        Args:
            primary_data: Data from Supabase
            graph_data: Data from Neo4j

        Returns:
            Combined trip data
        """
        # Start with primary data
        result = primary_data.copy()

        # Add knowledge graph data
        result["knowledge_graph"] = graph_data

        return result

    async def _update_in_primary(self, trip_id: str, data: Dict[str, Any]) -> bool:
        """Update structured trip data in Supabase.

        Args:
            trip_id: Trip ID
            data: Updated trip data

        Returns:
            Whether the update was successful
        """
        # Extract structured data for update
        structured_data = {}
        for field in [
            "title",
            "description",
            "start_date",
            "end_date",
            "budget",
            "status",
        ]:
            if field in data:
                structured_data[field] = data[field]

        if not structured_data:
            logger.warning("No structured data to update")
            return False

        # Update in Supabase
        try:
            await db_client.trips.update(trip_id, structured_data)
            return True
        except Exception as e:
            logger.error(f"Error updating trip in Supabase: {str(e)}")
            return False

    @ensure_memory_client_initialized
    async def _update_in_graph(self, trip_id: str, data: Dict[str, Any]) -> bool:
        """Update graph data for the trip in Neo4j.

        Args:
            trip_id: Trip ID
            data: Updated trip data

        Returns:
            Whether the update was successful
        """
        # Get trip node
        trip_nodes = await memory_client.open_nodes([f"Trip:{trip_id}"])
        if not trip_nodes:
            logger.warning(f"Trip node not found for ID {trip_id}")
            return False

        # Create new observations from updated data
        new_observations = []

        if "title" in data:
            new_observations.append(f"Title: {data['title']}")

        if "description" in data and data["description"]:
            new_observations.append(data["description"])

        if "start_date" in data and "end_date" in data:
            new_observations.append(
                f"Trip from {data['start_date']} to {data['end_date']}"
            )

        if "budget" in data:
            new_observations.append(f"Budget: ${data['budget']}")

        if "status" in data:
            new_observations.append(f"Status: {data['status']}")

        # Add new observations to the trip node
        if new_observations:
            await memory_client.add_observations(
                [
                    {
                        "entityName": f"Trip:{trip_id}",
                        "contents": new_observations,
                    }
                ]
            )
            return True

        return False

    async def _delete_from_primary(self, trip_id: str) -> bool:
        """Delete trip from Supabase.

        Args:
            trip_id: Trip ID

        Returns:
            Whether the deletion was successful
        """
        try:
            await db_client.trips.delete(trip_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting trip from Supabase: {str(e)}")
            return False

    @ensure_memory_client_initialized
    async def _delete_from_graph(self, trip_id: str) -> bool:
        """Delete trip from Neo4j.

        Args:
            trip_id: Trip ID

        Returns:
            Whether the deletion was successful
        """
        try:
            await memory_client.delete_entities([f"Trip:{trip_id}"])
            return True
        except Exception as e:
            logger.error(f"Error deleting trip from Neo4j: {str(e)}")
            return False
