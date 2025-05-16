"""Create Neo4j indexes for TripSage."""

from typing import Any
import asyncio

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)


async def apply(mcp_manager: MCPManager) -> None:
    """Apply index migrations."""
    logger.info("Creating Neo4j indexes for TripSage...")
    
    # Note: Memory MCP doesn't directly support Cypher indexes
    # We'll create entities that represent these indexes for documentation
    
    index_entities = [
        {
            "name": "Index_Destination_Country",
            "entityType": "DatabaseIndex",
            "observations": [
                "type:btree",
                "node_label:Destination",
                "property:country",
                "purpose:exact_lookups",
                "cypher:CREATE INDEX destination_country_index IF NOT EXISTS FOR (d:Destination) ON (d.country)"
            ]
        },
        {
            "name": "Index_Destination_Type",
            "entityType": "DatabaseIndex",
            "observations": [
                "type:btree",
                "node_label:Destination",
                "property:type",
                "purpose:exact_lookups",
                "cypher:CREATE INDEX destination_type_index IF NOT EXISTS FOR (d:Destination) ON (d.type)"
            ]
        },
        {
            "name": "Index_Trip_UserId",
            "entityType": "DatabaseIndex",
            "observations": [
                "type:btree",
                "node_label:Trip",
                "property:user_id",
                "purpose:user_trips_lookup",
                "cypher:CREATE INDEX trip_user_id_index IF NOT EXISTS FOR (t:Trip) ON (t.user_id)"
            ]
        },
        {
            "name": "Index_Destination_Description",
            "entityType": "DatabaseIndex",
            "observations": [
                "type:fulltext",
                "node_label:Destination",
                "property:description",
                "purpose:text_search",
                "cypher:CREATE TEXT INDEX destination_description_index IF NOT EXISTS FOR (d:Destination) ON (d.description)"
            ]
        },
        {
            "name": "Index_Destination_Location",
            "entityType": "DatabaseIndex",
            "observations": [
                "type:composite",
                "node_label:Destination",
                "properties:latitude,longitude",
                "purpose:geospatial_lookups",
                "cypher:CREATE INDEX destination_location_index IF NOT EXISTS FOR (d:Destination) ON (d.latitude, d.longitude)"
            ]
        }
    ]
    
    # Create the index documentation entities
    result = await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_entities",
        tool_args={"entities": index_entities}
    )
    
    if result.error:
        raise Exception(f"Failed to create index entities: {result.error}")
    
    logger.info("Neo4j indexes documentation created successfully")
    logger.warning("Note: Actual index performance depends on the underlying Neo4j instance")


async def rollback(mcp_manager: MCPManager) -> None:
    """Rollback index migrations."""
    logger.info("Rolling back Neo4j indexes...")
    
    # Remove index documentation entities
    index_names = [
        "Index_Destination_Country",
        "Index_Destination_Type",
        "Index_Trip_UserId",
        "Index_Destination_Description",
        "Index_Destination_Location"
    ]
    
    for name in index_names:
        try:
            await mcp_manager.call_tool(
                integration_name="memory",
                tool_name="delete_entities",
                tool_args={"entityNames": [name]}
            )
        except Exception as e:
            logger.warning(f"Failed to delete index entity {name}: {e}")
    
    logger.info("Index rollback completed")


if __name__ == "__main__":
    """Test the migration."""
    from tripsage.config.mcp_settings import mcp_settings
    
    async def test():
        mcp_manager = await MCPManager.get_instance(mcp_settings.dict())
        try:
            await apply(mcp_manager)
            logger.info("Index migration test completed successfully")
        finally:
            await mcp_manager.cleanup()
    
    asyncio.run(test())