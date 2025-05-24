"""
Neo4j Schema Initialization using Memory MCP.

This module provides Neo4j schema initialization using the Memory MCP
following Phase 5 implementation patterns.
"""

import asyncio
from typing import Dict, Optional

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.decorators import with_error_handling
from tripsage.utils.error_handling import TripSageError
from tripsage.utils.logging import get_logger

logger = get_logger(__name__)


class Neo4jSchemaError(TripSageError):
    """Error raised when Neo4j schema operations fail."""

    pass


class Neo4jSchemaInitializer:
    """Initialize Neo4j schema using Memory MCP."""

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """Initialize the schema initializer.

        Args:
            mcp_manager: Optional MCP manager instance. If None, uses global instance.
        """
        self.mcp_manager = mcp_manager or MCPManager()
        self.logger = logger

    @with_error_handling
    async def create_schema_entities(self) -> bool:
        """Create schema definition entities in Neo4j via Memory MCP.

        Returns:
            True if schema entities were created successfully

        Raises:
            Neo4jSchemaError: If schema creation fails
        """
        try:
            self.logger.info("Creating Neo4j schema entities via Memory MCP")

            # Define the travel domain schema entities
            schema_entities = [
                {
                    "name": "User_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:User",
                        "required_fields:id,email,created_at",
                        "optional_fields:display_name,preferences,travel_style",
                        "relationships:owns_trip,has_preferences,member_of_group",
                        "description:User entity for TripSage platform",
                    ],
                },
                {
                    "name": "Destination_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:Destination",
                        "required_fields:name,country,latitude,longitude",
                        "optional_fields:timezone,currency,language,description,population,climate",
                        "relationships:has_accommodation,has_activity,has_event,connected_by_transport",
                        "description:Geographic destination for travel planning",
                    ],
                },
                {
                    "name": "Accommodation_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:Accommodation",
                        "required_fields:name,address,type,price_per_night",
                        "optional_fields:rating,amenities,room_types,check_in_time,check_out_time,cancellation_policy",
                        "relationships:located_in,near_activity,bookable_through,reviewed_by",
                        "description:Lodging options for travelers",
                    ],
                },
                {
                    "name": "Transportation_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:Transportation",
                        "required_fields:mode,origin,destination,price",
                        "optional_fields:carrier,departure_time,arrival_time,duration,class,stops,booking_reference",
                        "relationships:connects_destinations,operated_by,bookable_through,used_in_trip",
                        "description:Transportation options between destinations",
                    ],
                },
                {
                    "name": "Activity_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:Activity",
                        "required_fields:name,location,category",
                        "optional_fields:duration,price,rating,description,operating_hours,seasonal_availability",
                        "relationships:available_at,suitable_for,bookable_through,included_in_trip",
                        "description:Activities and attractions at destinations",
                    ],
                },
                {
                    "name": "Event_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:Event",
                        "required_fields:name,location,start_date,end_date",
                        "optional_fields:category,price,capacity,description,organizer,ticket_url",
                        "relationships:happens_at,related_to_activity,bookable_through,interests_user",
                        "description:Time-specific events and festivals",
                    ],
                },
                {
                    "name": "Trip_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:Trip",
                        "required_fields:id,user_id,start_date,end_date,status",
                        "optional_fields:title,budget,travelers_count,notes,privacy_level",
                        "relationships:includes_destination,has_accommodation,uses_transportation,includes_activity,shared_with",
                        "description:User trip plans and itineraries",
                    ],
                },
                {
                    "name": "Chat_Session_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:ChatSession",
                        "required_fields:id,user_id,created_at",
                        "optional_fields:title,context,agent_type,ended_at",
                        "relationships:belongs_to_user,generated_trip,used_tools,continued_from",
                        "description:AI chat sessions for trip planning",
                    ],
                },
                {
                    "name": "Search_Result_Schema",
                    "entityType": "SchemaDefinition",
                    "observations": [
                        "entity_type:SearchResult",
                        "required_fields:query,result_type,data,timestamp",
                        "optional_fields:price,availability,rating,source,cached_until",
                        "relationships:requested_by_user,related_to_destination,saved_to_trip",
                        "description:Cached search results from MCP tools",
                    ],
                },
            ]

            # Create schema entities using Memory MCP
            result = await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="create_entities",
                params={"entities": schema_entities},
            )

            self.logger.info("Schema entities created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create schema entities: {e}")
            raise Neo4jSchemaError(f"Failed to create schema entities: {str(e)}") from e

    @with_error_handling(logger=logger, raise_on_error=True)
    async def create_relationship_schemas(self) -> bool:
        """Create relationship type schemas in Neo4j.

        Returns:
            True if relationship schemas were created successfully

        Raises:
            Neo4jSchemaError: If relationship schema creation fails
        """
        try:
            self.logger.info("Creating relationship schemas")

            # Define relationship type entities
            relationship_entities = [
                {
                    "name": "Relationship_Types",
                    "entityType": "RelationshipSchema",
                    "observations": [
                        "owns_trip:User->Trip",
                        "includes_destination:Trip->Destination",
                        "has_accommodation:Destination->Accommodation",
                        "has_activity:Destination->Activity",
                        "connects_destinations:Transportation->Destination",
                        "available_at:Activity->Destination",
                        "located_in:Accommodation->Destination",
                        "uses_transportation:Trip->Transportation",
                        "includes_activity:Trip->Activity",
                        "books_accommodation:Trip->Accommodation",
                        "belongs_to_user:ChatSession->User",
                        "generated_trip:ChatSession->Trip",
                        "requested_by_user:SearchResult->User",
                        "related_to_destination:SearchResult->Destination",
                        "saved_to_trip:SearchResult->Trip",
                    ],
                },
            ]

            # Create relationship schemas
            result = await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="create_entities",
                params={"entities": relationship_entities},
            )

            self.logger.info("Relationship schemas created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create relationship schemas: {e}")
            raise Neo4jSchemaError(
                f"Failed to create relationship schemas: {str(e)}"
            ) from e

    @with_error_handling
    async def create_example_data(self) -> bool:
        """Create example data to establish graph structure.

        Returns:
            True if example data was created successfully

        Raises:
            Neo4jSchemaError: If example data creation fails
        """
        try:
            self.logger.info("Creating example data for graph structure")

            # Create example entities
            example_entities = [
                {
                    "name": "Paris",
                    "entityType": "Destination",
                    "observations": [
                        "country:France",
                        "latitude:48.8566",
                        "longitude:2.3522",
                        "timezone:Europe/Paris",
                        "currency:EUR",
                        "language:French",
                        "description:The capital of France, known for its art, fashion, and culture",
                        "climate:temperate oceanic",
                    ],
                },
                {
                    "name": "Tokyo",
                    "entityType": "Destination",
                    "observations": [
                        "country:Japan",
                        "latitude:35.6762",
                        "longitude:139.6503",
                        "timezone:Asia/Tokyo",
                        "currency:JPY",
                        "language:Japanese",
                        "description:Japan's bustling capital, blending traditional and modern culture",
                        "climate:humid subtropical",
                    ],
                },
                {
                    "name": "Eiffel Tower",
                    "entityType": "Activity",
                    "observations": [
                        "location:Paris",
                        "category:Landmark",
                        "price:28.30",
                        "duration:2-3 hours",
                        "rating:4.5",
                        "description:Iconic iron lattice tower on the Champ de Mars",
                        "operating_hours:09:30-23:45",
                    ],
                },
                {
                    "name": "Hotel de la Paix",
                    "entityType": "Accommodation",
                    "observations": [
                        "address:123 Rue de la Paix, Paris",
                        "type:Hotel",
                        "price_per_night:150.00",
                        "rating:4.2",
                        "amenities:WiFi,Breakfast,Concierge",
                        "check_in_time:15:00",
                        "check_out_time:11:00",
                    ],
                },
            ]

            # Create example entities
            result = await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="create_entities",
                params={"entities": example_entities},
            )

            # Create example relationships
            example_relations = [
                {"from": "Eiffel Tower", "to": "Paris", "relationType": "available_at"},
                {
                    "from": "Hotel de la Paix",
                    "to": "Paris",
                    "relationType": "located_in",
                },
                {"from": "Paris", "to": "Eiffel Tower", "relationType": "has_activity"},
                {
                    "from": "Paris",
                    "to": "Hotel de la Paix",
                    "relationType": "has_accommodation",
                },
            ]

            result = await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="create_relations",
                params={"relations": example_relations},
            )

            self.logger.info("Example data created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create example data: {e}")
            raise Neo4jSchemaError(f"Failed to create example data: {str(e)}") from e

    @with_error_handling
    async def initialize_complete_schema(self, include_examples: bool = True) -> bool:
        """Initialize the complete Neo4j schema.

        Args:
            include_examples: Whether to include example data

        Returns:
            True if schema initialization was successful

        Raises:
            Neo4jSchemaError: If schema initialization fails
        """
        try:
            self.logger.info("Starting complete Neo4j schema initialization")

            # Create schema entities
            await self.create_schema_entities()

            # Create relationship schemas
            await self.create_relationship_schemas()

            # Create example data if requested
            if include_examples:
                await self.create_example_data()

            self.logger.info(
                "Complete Neo4j schema initialization completed successfully"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize complete schema: {e}")
            raise Neo4jSchemaError(
                f"Failed to initialize complete schema: {str(e)}"
            ) from e

    @with_error_handling
    async def verify_schema(self) -> Dict:
        """Verify the schema by reading the graph structure.

        Returns:
            Dictionary with schema verification results

        Raises:
            Neo4jSchemaError: If schema verification fails
        """
        try:
            self.logger.info("Verifying Neo4j schema")

            # Read the graph to verify schema
            result = await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="read_graph",
                params={},
            )

            # Search for schema entities
            schema_search = await self.mcp_manager.invoke(
                mcp_name="memory",
                method_name="search_nodes",
                params={"query": "SchemaDefinition"},
            )

            verification_result = {
                "graph_structure": result,
                "schema_entities": schema_search,
                "timestamp": asyncio.get_event_loop().time(),
            }

            self.logger.info("Schema verification completed")
            return verification_result

        except Exception as e:
            self.logger.error(f"Failed to verify schema: {e}")
            raise Neo4jSchemaError(f"Failed to verify schema: {str(e)}") from e


async def main():
    """Main function for testing schema initialization."""
    # Initialize the schema initializer
    initializer = Neo4jSchemaInitializer()

    try:
        # Initialize complete schema
        await initializer.initialize_complete_schema(include_examples=True)
        print("✅ Schema initialization completed successfully")

        # Verify schema
        verification = await initializer.verify_schema()
        print(
            f"✅ Schema verification completed: {len(verification.get('schema_entities', []))} schema entities found"
        )

    except Neo4jSchemaError as e:
        print(f"❌ Schema error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
