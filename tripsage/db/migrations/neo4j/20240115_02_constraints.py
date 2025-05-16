"""Create Neo4j constraints for TripSage."""

import asyncio

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)


async def apply(mcp_manager: MCPManager) -> None:
    """Apply constraint migrations."""
    logger.info("Creating Neo4j constraints for TripSage...")

    # Note: Memory MCP doesn't directly support Cypher constraints
    # We'll create entities that represent these constraints for documentation

    constraint_entities = [
        {
            "name": "Constraint_Destination_Name_Unique",
            "entityType": "DatabaseConstraint",
            "observations": [
                "type:uniqueness",
                "node_label:Destination",
                "property:name",
                "cypher:CREATE CONSTRAINT destination_name_unique IF NOT EXISTS FOR (d:Destination) REQUIRE d.name IS UNIQUE",
            ],
        },
        {
            "name": "Constraint_User_Email_Unique",
            "entityType": "DatabaseConstraint",
            "observations": [
                "type:uniqueness",
                "node_label:User",
                "property:email",
                "cypher:CREATE CONSTRAINT user_email_unique IF NOT EXISTS FOR (u:User) REQUIRE u.email IS UNIQUE",
            ],
        },
        {
            "name": "Constraint_Trip_Id_Unique",
            "entityType": "DatabaseConstraint",
            "observations": [
                "type:uniqueness",
                "node_label:Trip",
                "property:id",
                "cypher:CREATE CONSTRAINT trip_id_unique IF NOT EXISTS FOR (t:Trip) REQUIRE t.id IS UNIQUE",
            ],
        },
        {
            "name": "Constraint_Destination_Country_Exists",
            "entityType": "DatabaseConstraint",
            "observations": [
                "type:existence",
                "node_label:Destination",
                "property:country",
                "cypher:CREATE CONSTRAINT destination_country_exists IF NOT EXISTS FOR (d:Destination) REQUIRE d.country IS NOT NULL",
            ],
        },
        {
            "name": "Constraint_User_Name_Exists",
            "entityType": "DatabaseConstraint",
            "observations": [
                "type:existence",
                "node_label:User",
                "property:name",
                "cypher:CREATE CONSTRAINT user_name_exists IF NOT EXISTS FOR (u:User) REQUIRE u.name IS NOT NULL",
            ],
        },
    ]

    # Create the constraint documentation entities
    result = await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_entities",
        tool_args={"entities": constraint_entities},
    )

    if result.error:
        raise Exception(f"Failed to create constraint entities: {result.error}")

    logger.info("Neo4j constraints documentation created successfully")
    logger.warning(
        "Note: Actual constraint enforcement depends on the underlying Neo4j instance"
    )


async def rollback(mcp_manager: MCPManager) -> None:
    """Rollback constraint migrations."""
    logger.info("Rolling back Neo4j constraints...")

    # Remove constraint documentation entities
    constraint_names = [
        "Constraint_Destination_Name_Unique",
        "Constraint_User_Email_Unique",
        "Constraint_Trip_Id_Unique",
        "Constraint_Destination_Country_Exists",
        "Constraint_User_Name_Exists",
    ]

    for name in constraint_names:
        try:
            await mcp_manager.call_tool(
                integration_name="memory",
                tool_name="delete_entities",
                tool_args={"entityNames": [name]},
            )
        except Exception as e:
            logger.warning(f"Failed to delete constraint entity {name}: {e}")

    logger.info("Constraint rollback completed")


if __name__ == "__main__":
    """Test the migration."""
    from tripsage.config.mcp_settings import mcp_settings

    async def test():
        mcp_manager = await MCPManager.get_instance(mcp_settings.dict())
        try:
            await apply(mcp_manager)
            logger.info("Constraint migration test completed successfully")
        finally:
            await mcp_manager.cleanup()

    asyncio.run(test())
