"""Initialize TripSage travel domain schema in Neo4j."""

import asyncio

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)


async def apply(mcp_manager: MCPManager) -> None:
    """Apply the schema initialization migration."""
    logger.info("Initializing TripSage travel domain schema...")

    # Create core entity types for the travel domain
    entities = [
        {
            "name": "Destination_Schema",
            "entityType": "SchemaDefinition",
            "observations": [
                "entity_type:Destination",
                "required_fields:name,country,latitude,longitude",
                "optional_fields:timezone,currency,language,description,population",
                "relationships:has_accommodation,has_activity,has_event,connected_by_transport",
            ],
        },
        {
            "name": "Accommodation_Schema",
            "entityType": "SchemaDefinition",
            "observations": [
                "entity_type:Accommodation",
                "required_fields:name,address,price_per_night",
                "optional_fields:rating,amenities,room_types,check_in_time,check_out_time",
                "relationships:located_in,near_activity,bookable_through",
            ],
        },
        {
            "name": "Transportation_Schema",
            "entityType": "SchemaDefinition",
            "observations": [
                "entity_type:Transportation",
                "required_fields:mode,origin,destination,price",
                "optional_fields:carrier,departure_time,arrival_time,duration,class,stops",
                "relationships:connects_destinations,operated_by,bookable_through",
            ],
        },
        {
            "name": "Activity_Schema",
            "entityType": "SchemaDefinition",
            "observations": [
                "entity_type:Activity",
                "required_fields:name,location,category",
                "optional_fields:duration,price,rating,description,operating_hours",
                "relationships:available_at,suitable_for,bookable_through",
            ],
        },
        {
            "name": "Event_Schema",
            "entityType": "SchemaDefinition",
            "observations": [
                "entity_type:Event",
                "required_fields:name,location,start_date,end_date",
                "optional_fields:category,price,capacity,description,organizer",
                "relationships:happens_at,related_to_activity,bookable_through",
            ],
        },
        {
            "name": "Trip_Schema",
            "entityType": "SchemaDefinition",
            "observations": [
                "entity_type:Trip",
                "required_fields:user_id,start_date,end_date,status",
                "optional_fields:title,budget,travelers_count,notes",
                "relationships:includes_destination,has_accommodation,uses_transportation,includes_activity",
            ],
        },
    ]

    # Create the schema entities
    result = await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_entities",
        tool_args={"entities": entities},
    )

    if result.error:
        raise Exception(f"Failed to create schema entities: {result.error}")

    # Create example entities to establish the graph structure
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
                "description:The capital of France, known for its art, "
                "fashion, and culture",
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
            ],
        },
    ]

    result = await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_entities",
        tool_args={"entities": example_entities},
    )

    if result.error:
        logger.warning(f"Failed to create example entities: {result.error}")

    # Create relationships
    relations = [
        {"from": "Eiffel Tower", "to": "Paris", "relationType": "available_at"}
    ]

    result = await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_relations",
        tool_args={"relations": relations},
    )

    if result.error:
        logger.warning(f"Failed to create example relations: {result.error}")

    logger.info("Travel domain schema initialized successfully")


async def rollback(mcp_manager: MCPManager) -> None:
    """Rollback the schema initialization migration."""
    logger.info("Rolling back travel domain schema...")

    # Since we can't easily delete all entities, we'll just log a warning
    logger.warning("Rollback not fully implemented - manual cleanup may be required")


if __name__ == "__main__":
    """Test the migration."""
    from tripsage.config.mcp_settings import mcp_settings

    async def test():
        mcp_manager = await MCPManager.get_instance(mcp_settings.dict())
        try:
            await apply(mcp_manager)
            logger.info("Migration test completed successfully")
        finally:
            await mcp_manager.cleanup()

    asyncio.run(test())
