"""
Memory MCP client.

This module provides a client implementation for accessing the Memory MCP
service, which interfaces with the Neo4j knowledge graph.
"""

from typing import Any, Dict, List, Optional

from src.db.neo4j.client import neo4j_client
from src.mcp.base_mcp_client import BaseMcpClient
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)


class MemoryClient(BaseMcpClient):
    """Client for interacting with the Memory MCP service."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize the Memory MCP client.

        Args:
            base_url: Optional base URL of the Memory MCP service
        """
        super().__init__(base_url=base_url, service_name="memory")
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the memory client.

        This ensures that the knowledge graph is properly initialized.
        """
        if not self._initialized:
            await neo4j_client.initialize()
            self._initialized = True
            logger.info("Memory client initialized successfully")

    async def create_entities(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create multiple entities in the knowledge graph.

        Args:
            entities: List of entity data dictionaries, each containing 'name',
                'entityType', and 'observations'

        Returns:
            List of created entities with their IDs
        """
        created_entities = []

        for entity_data in entities:
            entity_type = entity_data.get("entityType")
            entity_name = entity_data.get("name")
            
            if not entity_type or not entity_name:
                logger.warning("Entity missing required fields: type and name")
                continue

            # Process entity based on its type
            if entity_type == "Destination":
                # Convert to destination format
                destination_data = {
                    "name": entity_name,
                    "country": entity_data.get("country", "Unknown"),
                    "type": entity_data.get("type", "city"),
                    "description": "\n".join(entity_data.get("observations", [])),
                }

                # If coordinates are provided
                if "latitude" in entity_data and "longitude" in entity_data:
                    destination_data["latitude"] = entity_data["latitude"]
                    destination_data["longitude"] = entity_data["longitude"]

                # Add any additional properties
                for key, value in entity_data.items():
                    if key not in [
                        "name",
                        "entityType",
                        "observations",
                        "latitude",
                        "longitude",
                    ]:
                        destination_data[key] = value

                # Create destination
                destination = await neo4j_client.add_destination(destination_data)

                # Convert back to entity format for response
                created_entities.append(
                    {
                        "id": destination.name,
                        "name": destination.name,
                        "entityType": "Destination",
                        "observations": (
                            [destination.description] if destination.description else []
                        ),
                    }
                )
            
            elif entity_type == "Activity":
                # Convert to activity format
                activity_data = {
                    "name": entity_name,
                    "destination": entity_data.get("destination", "Unknown"),
                    "type": entity_data.get("type", "attraction"),
                    "description": "\n".join(entity_data.get("observations", [])),
                }
                
                # Add other properties
                for key, value in entity_data.items():
                    if key not in ["name", "entityType", "observations"]:
                        activity_data[key] = value
                
                # Create activity
                activity = await neo4j_client.add_activity(activity_data)
                
                # Convert back to entity format for response
                created_entities.append(
                    {
                        "id": activity.name,
                        "name": activity.name,
                        "entityType": "Activity",
                        "observations": (
                            [activity.description] if activity.description else []
                        ),
                    }
                )
                
                # Create relationship with destination if specified
                if "destination" in activity_data:
                    try:
                        await neo4j_client.activity_repo.create_activity_destination_relationship(
                            activity_name=activity.name,
                            destination_name=activity_data["destination"]
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to create activity-destination relationship: {str(e)}"
                        )
            
            elif entity_type == "Accommodation":
                # Convert to accommodation format
                accommodation_data = {
                    "name": entity_name,
                    "destination": entity_data.get("destination", "Unknown"),
                    "type": entity_data.get("type", "hotel"),
                    "description": "\n".join(entity_data.get("observations", [])),
                }
                
                # Add other properties
                for key, value in entity_data.items():
                    if key not in ["name", "entityType", "observations"]:
                        accommodation_data[key] = value
                
                # Create accommodation
                accommodation = await neo4j_client.add_accommodation(accommodation_data)
                
                # Convert back to entity format for response
                created_entities.append(
                    {
                        "id": accommodation.name,
                        "name": accommodation.name,
                        "entityType": "Accommodation",
                        "observations": (
                            [accommodation.description] if accommodation.description else []
                        ),
                    }
                )
                
                # Create relationship with destination if specified
                if "destination" in accommodation_data:
                    try:
                        await neo4j_client.accommodation_repo.create_accommodation_destination_relationship(
                            accommodation_name=accommodation.name,
                            destination_name=accommodation_data["destination"]
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to create accommodation-destination relationship: {str(e)}"
                        )
            
            elif entity_type == "Event":
                # Convert to event format
                event_data = {
                    "name": entity_name,
                    "destination": entity_data.get("destination", "Unknown"),
                    "type": entity_data.get("type", "cultural"),
                    "description": "\n".join(entity_data.get("observations", [])),
                }
                
                # Add other properties
                for key, value in entity_data.items():
                    if key not in ["name", "entityType", "observations"]:
                        event_data[key] = value
                
                # Create event
                event = await neo4j_client.add_event(event_data)
                
                # Convert back to entity format for response
                created_entities.append(
                    {
                        "id": event.name,
                        "name": event.name,
                        "entityType": "Event",
                        "observations": (
                            [event.description] if event.description else []
                        ),
                    }
                )
                
                # Create relationship with destination if specified
                if "destination" in event_data:
                    try:
                        await neo4j_client.event_repo.create_event_destination_relationship(
                            event_name=event.name,
                            destination_name=event_data["destination"]
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to create event-destination relationship: {str(e)}"
                        )
            
            elif entity_type == "Transportation":
                # Convert to transportation format
                transportation_data = {
                    "name": entity_name,
                    "type": entity_data.get("type", "flight"),
                }
                
                # Add origin and destination if available
                if "origin" in entity_data:
                    transportation_data["origin"] = entity_data["origin"]
                if "destination" in entity_data:
                    transportation_data["destination"] = entity_data["destination"]
                
                # Add description from observations
                if entity_data.get("observations"):
                    transportation_data["description"] = "\n".join(entity_data.get("observations", []))
                
                # Add other properties
                for key, value in entity_data.items():
                    if key not in ["name", "entityType", "observations", "origin", "destination"]:
                        transportation_data[key] = value
                
                # Create transportation
                transportation = await neo4j_client.add_transportation(transportation_data)
                
                # Convert back to entity format for response
                created_entities.append(
                    {
                        "id": transportation.name,
                        "name": transportation.name,
                        "entityType": "Transportation",
                        "observations": (
                            [transportation.description] if hasattr(transportation, "description") and transportation.description else []
                        ),
                    }
                )
                
                # Create route relationships if origin and destination are specified
                if "origin" in transportation_data and "destination" in transportation_data:
                    try:
                        await neo4j_client.transportation_repo.create_route_relationship(
                            transportation_id=transportation.name,
                            origin_destination=transportation_data["origin"],
                            target_destination=transportation_data["destination"]
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to create transportation route relationships: {str(e)}"
                        )
            else:
                # For other entity types not fully implemented
                logger.warning(f"Entity type {entity_type} not fully supported yet")

                # Use generic query for other entity types
                query = f"""
                CREATE (e:{entity_type} {{name: $name}})
                SET e.created_at = datetime(),
                    e.updated_at = datetime()
                RETURN e
                """

                _result = await neo4j_client.execute_query(
                    query, {"name": entity_data.get("name")}
                )

                created_entities.append(
                    {
                        "id": entity_data.get("name"),
                        "name": entity_data.get("name"),
                        "entityType": entity_type,
                        "observations": entity_data.get("observations", []),
                    }
                )

        return created_entities

    async def create_relations(
        self, relations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create relations between entities in the knowledge graph.

        Args:
            relations: List of relation dictionaries, each containing 'from',
                'relationType', and 'to'

        Returns:
            List of created relations
        """
        created_relations = []

        for relation in relations:
            from_entity = relation.get("from")
            to_entity = relation.get("to")
            relation_type = relation.get("relationType")

            if not all([from_entity, to_entity, relation_type]):
                logger.warning("Skipping relation with missing required fields")
                continue

            # Create the relationship
            # This uses a generic approach that works for all entity types
            query = f"""
            MATCH (a {{name: $from_name}}), (b {{name: $to_name}})
            CREATE (a)-[r:{relation_type}]->(b)
            SET r.created_at = datetime()
            RETURN a.name as from_name, b.name as to_name, type(r) as relation_type
            """

            result = await neo4j_client.execute_query(
                query, {"from_name": from_entity, "to_name": to_entity}
            )

            if result:
                created_relations.append(
                    {
                        "from": result[0]["from_name"],
                        "relationType": result[0]["relation_type"],
                        "to": result[0]["to_name"],
                    }
                )

        return created_relations

    async def add_observations(
        self, observations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add observations to existing entities.

        Args:
            observations: List of observation dictionaries, each containing
                'entityName' and 'contents' (list of strings)

        Returns:
            List of updated entities
        """
        updated_entities = []

        for observation_data in observations:
            entity_name = observation_data.get("entityName")
            contents = observation_data.get("contents", [])

            if not entity_name or not contents:
                logger.warning("Skipping observation with missing required fields")
                continue

            # First, find the entity and its type
            query = """
            MATCH (e {name: $name})
            RETURN labels(e)[0] as entity_type
            """

            result = await neo4j_client.execute_query(query, {"name": entity_name})

            if not result:
                logger.warning(f"Entity {entity_name} not found")
                continue

            entity_type = result[0]["entity_type"]

            # For Destination entities, we append to description
            if entity_type == "Destination":
                # Get current entity
                destination = await neo4j_client.get_destination(entity_name)

                if destination:
                    # Prepare update data
                    update_data = destination.dict()

                    # Append observations to description
                    current_description = update_data.get("description", "")
                    new_description = current_description + "\n" + "\n".join(contents)
                    update_data["description"] = new_description.strip()

                    # Update destination
                    updated = await neo4j_client.update_destination(
                        entity_name, update_data
                    )

                    if updated:
                        updated_entities.append(
                            {
                                "name": entity_name,
                                "entityType": "Destination",
                                "observations": contents,
                            }
                        )
            else:
                # For other entity types, we use a generic approach
                # Add observations as properties
                property_updates = []
                for i, _content in enumerate(contents):
                    property_updates.append(f"e.observation_{i+1} = ${i}")

                property_params = {
                    str(i): content for i, content in enumerate(contents)
                }
                property_params["name"] = entity_name

                query = f"""
                MATCH (e:{entity_type} {{name: $name}})
                SET e.updated_at = datetime(),
                    {", ".join(property_updates)}
                RETURN e
                """

                result = await neo4j_client.execute_query(query, property_params)

                if result:
                    updated_entities.append(
                        {
                            "name": entity_name,
                            "entityType": entity_type,
                            "observations": contents,
                        }
                    )

        return updated_entities

    async def delete_entities(self, entity_names: List[str]) -> List[str]:
        """Delete entities from the knowledge graph.

        Args:
            entity_names: List of entity names to delete

        Returns:
            List of deleted entity names
        """
        deleted_entities = []

        for name in entity_names:
            # Check if it's a destination
            destination = await neo4j_client.get_destination(name)

            if destination:
                # Delete destination
                success = await neo4j_client.delete_destination(name)
                if success:
                    deleted_entities.append(name)
            else:
                # For non-destination entities, use generic query
                query = """
                MATCH (e {name: $name})
                DETACH DELETE e
                RETURN count(*) as deleted
                """

                result = await neo4j_client.execute_query(query, {"name": name})

                if result and result[0]["deleted"] > 0:
                    deleted_entities.append(name)

        return deleted_entities

    async def delete_relations(
        self, relations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Delete relations from the knowledge graph.

        Args:
            relations: List of relation dictionaries, each containing 'from',
                'relationType', and 'to'

        Returns:
            List of deleted relations
        """
        deleted_relations = []

        for relation in relations:
            from_entity = relation.get("from")
            to_entity = relation.get("to")
            relation_type = relation.get("relationType")

            if not all([from_entity, to_entity, relation_type]):
                logger.warning("Skipping relation with missing required fields")
                continue

            # Delete the relationship
            query = f"""
            MATCH (a {{name: $from_name}})-[r:{relation_type}]->(b {{name: $to_name}})
            DELETE r
            RETURN count(*) as deleted
            """

            result = await neo4j_client.execute_query(
                query, {"from_name": from_entity, "to_name": to_entity}
            )

            if result and result[0]["deleted"] > 0:
                deleted_relations.append(relation)

        return deleted_relations

    async def delete_observations(
        self, deletions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Delete specific observations from entities.

        Args:
            deletions: List of dictionaries, each containing 'entityName' and
                'observations' to delete

        Returns:
            List of updated entities
        """
        # This is a bit tricky since observations are stored differently
        # based on entity type. For simplicity, we'll handle Destination
        # differently than other types.
        updated_entities = []

        for deletion in deletions:
            entity_name = deletion.get("entityName")
            observations_to_delete = deletion.get("observations", [])

            if not entity_name or not observations_to_delete:
                continue

            # Check if it's a destination
            destination = await neo4j_client.get_destination(entity_name)

            if destination and destination.description:
                # For destinations, observations are in the description
                lines = destination.description.split("\n")

                # Remove lines that match observations to delete
                updated_lines = [
                    line for line in lines if line not in observations_to_delete
                ]

                # Update destination
                update_data = destination.dict()
                update_data["description"] = "\n".join(updated_lines)

                updated = await neo4j_client.update_destination(
                    entity_name, update_data
                )

                if updated:
                    updated_entities.append(
                        {
                            "name": entity_name,
                            "entityType": "Destination",
                            "deletedObservations": observations_to_delete,
                        }
                    )
            else:
                # For other entity types, it's more complex and depends on how
                # observations were stored. This is a simplified approach.
                query = """
                MATCH (e {name: $name})
                RETURN labels(e)[0] as entity_type
                """

                result = await neo4j_client.execute_query(query, {"name": entity_name})

                if result:
                    entity_type = result[0]["entity_type"]

                    # Generic approach: set observation properties to null
                    # This is a simplification and might not be ideal
                    query = f"""
                    MATCH (e:{entity_type} {{name: $name}})
                    SET e.updated_at = datetime()
                    """

                    for i in range(len(observations_to_delete)):
                        query += f", e.observation_{i+1} = NULL"

                    await neo4j_client.execute_query(query, {"name": entity_name})

                    updated_entities.append(
                        {
                            "name": entity_name,
                            "entityType": entity_type,
                            "deletedObservations": observations_to_delete,
                        }
                    )

        return updated_entities

    async def read_graph(self) -> Dict[str, Any]:
        """Read the entire knowledge graph.

        Returns:
            Dictionary containing entities and relations
        """
        # Get graph statistics
        stats = await neo4j_client.get_graph_statistics()

        # Fetch entities by type
        entities_query = """
        MATCH (e)
        RETURN e, labels(e)[0] as entity_type
        LIMIT 1000  // Safety limit
        """

        entities_result = await neo4j_client.execute_query(entities_query)

        # Process entities
        entities = []
        for record in entities_result:
            entity = record["e"]
            entity_type = record["entity_type"]

            # Extract observations based on entity type
            observations = []
            if entity_type == "Destination" and entity.get("description"):
                observations = entity["description"].split("\n")
            else:
                # For other types, look for observation properties
                for key, value in entity.items():
                    if key.startswith("observation_") and value:
                        observations.append(value)

            entities.append(
                {
                    "name": entity.get("name"),
                    "entityType": entity_type,
                    "observations": observations,
                }
            )

        # Fetch relations
        relations_query = """
        MATCH (a)-[r]->(b)
        RETURN a.name as from_name, type(r) as relation_type, b.name as to_name
        LIMIT 10000  // Safety limit
        """

        relations_result = await neo4j_client.execute_query(relations_query)

        # Process relations
        relations = []
        for record in relations_result:
            relations.append(
                {
                    "from": record["from_name"],
                    "relationType": record["relation_type"],
                    "to": record["to_name"],
                }
            )

        return {"entities": entities, "relations": relations, "statistics": stats}

    async def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """Search for nodes in the knowledge graph.

        Args:
            query: Search query string

        Returns:
            List of matching nodes
        """
        # Use the knowledge graph search
        search_results = await neo4j_client.run_knowledge_graph_search(query)

        # Convert to standardized format
        nodes = []
        for result in search_results:
            # Extract observations based on entity type
            observations = []
            if result.get("description"):
                observations = [result["description"]]

            nodes.append(
                {
                    "name": result.get("name"),
                    "type": result.get("type"),
                    "observations": observations,
                    "score": result.get("score"),
                }
            )

        return nodes

    async def open_nodes(self, names: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information about specific nodes.

        Args:
            names: List of node names to retrieve

        Returns:
            List of node details
        """
        nodes = []

        for name in names:
            # Check if it's a destination first
            destination = await neo4j_client.get_destination(name)

            if destination:
                # Convert to node format
                observations = []
                if destination.description:
                    observations = [destination.description]

                nodes.append(
                    {
                        "name": destination.name,
                        "type": "Destination",
                        "observations": observations,
                        "properties": {
                            "country": destination.country,
                            "type": destination.type,
                            "region": destination.region,
                            "city": destination.city,
                            "safety_rating": destination.safety_rating,
                            "cost_level": destination.cost_level,
                        },
                    }
                )
            else:
                # Check for other entity types
                entity_found = False
                
                # Check if it's an activity
                activity = await neo4j_client.get_activity(name)
                if activity:
                    entity_found = True
                    observations = []
                    if activity.description:
                        observations = [activity.description]
                    
                    nodes.append(
                        {
                            "name": activity.name,
                            "type": "Activity",
                            "observations": observations,
                            "properties": {
                                "destination": activity.destination,
                                "type": activity.type,
                                "rating": activity.rating,
                                "price": activity.price,
                                "duration": activity.duration,
                            },
                        }
                    )
                
                # Check if it's an accommodation
                if not entity_found:
                    accommodation = await neo4j_client.get_accommodation(name)
                    if accommodation:
                        entity_found = True
                        observations = []
                        if accommodation.description:
                            observations = [accommodation.description]
                        
                        nodes.append(
                            {
                                "name": accommodation.name,
                                "type": "Accommodation",
                                "observations": observations,
                                "properties": {
                                    "destination": accommodation.destination,
                                    "type": accommodation.type,
                                    "rating": accommodation.rating,
                                    "price_per_night": accommodation.price_per_night,
                                    "address": accommodation.address,
                                },
                            }
                        )
                
                # Check if it's an event
                if not entity_found:
                    event = await neo4j_client.get_event(name)
                    if event:
                        entity_found = True
                        observations = []
                        if event.description:
                            observations = [event.description]
                        
                        nodes.append(
                            {
                                "name": event.name,
                                "type": "Event",
                                "observations": observations,
                                "properties": {
                                    "destination": event.destination,
                                    "type": event.type,
                                    "start_date": event.start_date,
                                    "end_date": event.end_date,
                                    "venue": event.venue,
                                    "ticket_price": event.ticket_price,
                                },
                            }
                        )
                
                # Check if it's a transportation
                if not entity_found:
                    transportation = await neo4j_client.get_transportation(name)
                    if transportation:
                        entity_found = True
                        observations = []
                        if hasattr(transportation, "description") and transportation.description:
                            observations = [transportation.description]
                        
                        nodes.append(
                            {
                                "name": transportation.name,
                                "type": "Transportation",
                                "observations": observations,
                                "properties": {
                                    "type": transportation.type,
                                    "origin": transportation.origin if hasattr(transportation, "origin") else None,
                                    "destination": transportation.destination if hasattr(transportation, "destination") else None,
                                    "price": transportation.price if hasattr(transportation, "price") else None,
                                    "duration": transportation.duration if hasattr(transportation, "duration") else None,
                                },
                            }
                        )
                
                # Try generic entity lookup if not found
                if not entity_found:
                    query = """
                    MATCH (e {name: $name})
                    RETURN e, labels(e)[0] as entity_type
                    """

                    result = await neo4j_client.execute_query(query, {"name": name})

                    if result:
                        entity = result[0]["e"]
                        entity_type = result[0]["entity_type"]

                        # Extract observations
                        observations = []
                        for key, value in entity.items():
                            if key.startswith("observation_") and value:
                                observations.append(value)

                        # Extract other properties
                        properties = {}
                        for key, value in entity.items():
                            if not key.startswith("observation_") and key not in [
                                "name",
                                "created_at",
                                "updated_at",
                            ]:
                                properties[key] = value

                        nodes.append(
                            {
                                "name": name,
                                "type": entity_type,
                                "observations": observations,
                                "properties": properties,
                            }
                        )

        return nodes


# Create a singleton instance
memory_client = MemoryClient()