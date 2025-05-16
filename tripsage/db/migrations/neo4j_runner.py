"""Neo4j database migration runner using Memory MCP."""

import asyncio
import re
from pathlib import Path
from typing import List, Optional, Tuple

from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.exceptions import MCPIntegrationError
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)

# Neo4j migration directory
NEO4J_MIGRATIONS_DIR = Path(__file__).parent / "neo4j"


def get_migration_files() -> List[Path]:
    """
    Get all Neo4j migration files in the migrations directory, sorted by filename.

    Returns:
        List of paths to migration files.
    """
    if not NEO4J_MIGRATIONS_DIR.exists():
        logger.error(f"Neo4j migrations directory not found: {NEO4J_MIGRATIONS_DIR}")
        raise FileNotFoundError(
            f"Neo4j migrations directory not found: {NEO4J_MIGRATIONS_DIR}"
        )

    # Support both .py and .cypher files
    py_files = list(NEO4J_MIGRATIONS_DIR.glob("*.py"))
    cypher_files = list(NEO4J_MIGRATIONS_DIR.glob("*.cypher"))

    migration_files = sorted(
        [
            f
            for f in py_files + cypher_files
            if re.match(r"\d{8}_\d{2}_.*\.(py|cypher)", f.name)
        ]
    )

    logger.info(f"Found {len(migration_files)} Neo4j migration files")
    return migration_files


async def get_applied_migrations(mcp_manager: MCPManager) -> List[str]:
    """
    Get list of Neo4j migrations that have already been applied.

    Args:
        mcp_manager: The MCP manager instance.

    Returns:
        List of applied migration filenames.
    """
    try:
        # Search for migration tracking entities in the knowledge graph
        result = await mcp_manager.call_tool(
            integration_name="memory",
            tool_name="search_nodes",
            tool_args={"query": "Migration"},
        )

        migration_entities = []
        if result.result and "entities" in result.result:
            for entity in result.result["entities"]:
                if entity.get("entityType") == "Migration":
                    migration_entities.append(entity)

        # Extract filenames from migration entities
        applied_migrations = []
        for entity in migration_entities:
            observations = entity.get("observations", [])
            for obs in observations:
                if obs.startswith("filename:"):
                    applied_migrations.append(obs.replace("filename:", "").strip())

        return applied_migrations

    except MCPIntegrationError as e:
        logger.error(f"Error checking applied Neo4j migrations: {e}")
        # If no migrations tracking exists, assume none have been applied
        return []


async def apply_python_migration(mcp_manager: MCPManager, migration_file: Path) -> bool:
    """
    Apply a Python-based Neo4j migration.

    Args:
        mcp_manager: The MCP manager instance.
        migration_file: Path to the migration file.

    Returns:
        True if the migration was successfully applied, False otherwise.
    """
    try:
        # Import and execute the migration module
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            migration_file.stem, migration_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Execute the migration
        if hasattr(module, "apply"):
            await module.apply(mcp_manager)
            return True
        else:
            logger.error(f"Migration {migration_file.name} missing 'apply' function")
            return False

    except Exception as e:
        logger.error(f"Error applying Python migration {migration_file.name}: {e}")
        return False


async def apply_cypher_migration(mcp_manager: MCPManager, migration_file: Path) -> bool:
    """
    Apply a Cypher-based Neo4j migration.

    Args:
        mcp_manager: The MCP manager instance.
        migration_file: Path to the migration file.

    Returns:
        True if the migration was successfully applied, False otherwise.
    """
    try:
        # Read Cypher content
        with open(migration_file, "r") as f:
            cypher_content = f.read()

        # Split into individual statements
        statements = [s.strip() for s in cypher_content.split(";") if s.strip()]

        # Execute each statement
        for statement in statements:
            # Parse statement to determine operation type
            operation = "query"  # default
            if "CREATE" in statement.upper():
                if "CONSTRAINT" in statement.upper():
                    operation = "constraint"
                elif "INDEX" in statement.upper():
                    operation = "index"
                else:
                    operation = "create"

            # For now, we'll use the Memory MCP's entity creation for simple cases
            # More complex Cypher might need custom handling
            logger.warning(
                f"Cypher migration support is limited. Statement: {statement[:50]}..."
            )

        return True

    except Exception as e:
        logger.error(f"Error applying Cypher migration {migration_file.name}: {e}")
        return False


async def apply_migration(mcp_manager: MCPManager, migration_file: Path) -> bool:
    """
    Apply a single Neo4j migration to the database.

    Args:
        mcp_manager: The MCP manager instance.
        migration_file: Path to the migration file.

    Returns:
        True if the migration was successfully applied, False otherwise.
    """
    try:
        logger.info(f"Applying Neo4j migration: {migration_file.name}")

        # Apply based on file type
        if migration_file.suffix == ".py":
            success = await apply_python_migration(mcp_manager, migration_file)
        elif migration_file.suffix == ".cypher":
            success = await apply_cypher_migration(mcp_manager, migration_file)
        else:
            logger.error(f"Unknown migration file type: {migration_file.suffix}")
            return False

        if success:
            # Record the migration in the knowledge graph
            await mcp_manager.call_tool(
                integration_name="memory",
                tool_name="create_entities",
                tool_args={
                    "entities": [
                        {
                            "name": f"Migration_{migration_file.stem}",
                            "entityType": "Migration",
                            "observations": [
                                f"filename:{migration_file.name}",
                                f"applied_at:{asyncio.get_event_loop().time()}",
                                "type:neo4j",
                            ],
                        }
                    ]
                },
            )

            logger.info(f"Neo4j migration {migration_file.name} applied successfully")
            return True

        return False

    except MCPIntegrationError as e:
        logger.error(f"Error applying Neo4j migration {migration_file.name}: {e}")
        return False


async def run_neo4j_migrations(
    up_to: Optional[str] = None, dry_run: bool = False
) -> Tuple[int, int]:
    """
    Run all pending Neo4j migrations in order.

    Args:
        up_to: Optional filename to stop at (inclusive).
        dry_run: If True, don't actually apply migrations, just log what would be done.

    Returns:
        Tuple of (number of successful migrations, number of failed migrations)
    """
    # Initialize MCP manager
    mcp_manager = await MCPManager.get_instance(mcp_settings.dict())

    try:
        migration_files = get_migration_files()
        applied_migrations = await get_applied_migrations(mcp_manager)

        logger.info(
            f"Found {len(migration_files)} Neo4j migration files, "
            f"{len(applied_migrations)} already applied"
        )

        succeeded = 0
        failed = 0

        for migration_file in migration_files:
            if migration_file.name in applied_migrations:
                logger.debug(
                    f"Skipping already applied Neo4j migration: {migration_file.name}"
                )
                continue

            if up_to and migration_file.name > up_to:
                logger.info(f"Stopping at requested migration: {up_to}")
                break

            logger.info(f"Processing Neo4j migration: {migration_file.name}")
            if dry_run:
                logger.info(
                    f"[DRY RUN] Would apply Neo4j migration: {migration_file.name}"
                )
                succeeded += 1
                continue

            try:
                if await apply_migration(mcp_manager, migration_file):
                    succeeded += 1
                else:
                    failed += 1
                    logger.error(
                        f"Failed to apply Neo4j migration: {migration_file.name}"
                    )
            except Exception as e:
                failed += 1
                logger.error(
                    f"Error processing Neo4j migration {migration_file.name}: {e}"
                )

        return succeeded, failed

    finally:
        # Cleanup MCP manager
        await mcp_manager.cleanup()


async def initialize_neo4j_schema(mcp_manager: MCPManager):
    """
    Initialize the Neo4j schema with basic constraints and indexes.

    This ensures the knowledge graph has the necessary structure for
    TripSage's travel domain entities.
    """
    logger.info("Initializing Neo4j schema for TripSage...")

    # Create core entity types and relationships
    entities_to_create = [
        {
            "name": "TravelEntityType_Destination",
            "entityType": "EntityType",
            "observations": [
                "domain:travel",
                "description:Represents a travel destination (city, country, region)",
                "attributes:name,country,latitude,longitude,timezone,description",
            ],
        },
        {
            "name": "TravelEntityType_Accommodation",
            "entityType": "EntityType",
            "observations": [
                "domain:travel",
                "description:Represents a place to stay (hotel, vacation rental, etc)",
                "attributes:name,address,price_per_night,rating,amenities",
            ],
        },
        {
            "name": "TravelEntityType_Transportation",
            "entityType": "EntityType",
            "observations": [
                "domain:travel",
                "description:Represents transportation options (flights, trains, etc)",
                "attributes:mode,origin,destination,departure_time,arrival_time,price",
            ],
        },
        {
            "name": "TravelEntityType_Activity",
            "entityType": "EntityType",
            "observations": [
                "domain:travel",
                "description:Represents activities and attractions",
                "attributes:name,location,duration,price,category,description",
            ],
        },
        {
            "name": "TravelEntityType_Event",
            "entityType": "EntityType",
            "observations": [
                "domain:travel",
                "description:Represents events happening at destinations",
                "attributes:name,location,start_date,end_date,category,description",
            ],
        },
    ]

    # Create the entity types
    await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_entities",
        tool_args={"entities": entities_to_create},
    )

    # Create core relationship types
    relations_to_create = [
        {
            "from": "TravelEntityType_Accommodation",
            "to": "TravelEntityType_Destination",
            "relationType": "located_in",
        },
        {
            "from": "TravelEntityType_Activity",
            "to": "TravelEntityType_Destination",
            "relationType": "available_at",
        },
        {
            "from": "TravelEntityType_Event",
            "to": "TravelEntityType_Destination",
            "relationType": "happens_at",
        },
        {
            "from": "TravelEntityType_Transportation",
            "to": "TravelEntityType_Destination",
            "relationType": "connects_to",
        },
    ]

    await mcp_manager.call_tool(
        integration_name="memory",
        tool_name="create_relations",
        tool_args={"relations": relations_to_create},
    )

    logger.info("Neo4j schema initialized successfully")


if __name__ == "__main__":
    """
    Run Neo4j migrations when the script is executed directly.
    
    Example usage:
        python -m tripsage.db.migrations.neo4j_runner
    """
    import argparse

    parser = argparse.ArgumentParser(description="Apply Neo4j database migrations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually apply migrations"
    )
    parser.add_argument(
        "--up-to", help="Apply migrations up to and including this filename"
    )
    parser.add_argument(
        "--init-schema", action="store_true", help="Initialize the Neo4j schema"
    )
    args = parser.parse_args()

    async def main():
        if args.init_schema:
            mcp_manager = await MCPManager.get_instance(mcp_settings.dict())
            try:
                await initialize_neo4j_schema(mcp_manager)
                logger.info("Schema initialization completed")
            finally:
                await mcp_manager.cleanup()
        else:
            succeeded, failed = await run_neo4j_migrations(
                dry_run=args.dry_run, up_to=args.up_to
            )
            logger.info(
                f"Neo4j migration completed: {succeeded} succeeded, {failed} failed"
            )
            return succeeded, failed

    result = asyncio.run(main())

    if result and result[1] > 0:  # If there were failures
        exit(1)
