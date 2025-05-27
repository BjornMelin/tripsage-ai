"""
Database initialization module for TripSage using MCP-based approach.

This module provides functionality to initialize both SQL and Neo4j databases
using the appropriate MCP servers (Supabase MCP and Memory MCP).
"""

import asyncio
from typing import Any, Dict, Optional

from tripsage.config.mcp_settings import mcp_settings
from tripsage.db.migrations import run_migrations, run_neo4j_migrations
from tripsage.db.migrations.neo4j_runner import initialize_neo4j_schema
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)


async def initialize_databases(
    run_migrations_on_startup: bool = False,
    verify_connections: bool = True,
    init_neo4j_schema: bool = False,
    project_id: Optional[str] = None,
) -> bool:
    """
    Initialize database connections and ensure databases are properly set up.

    Args:
        run_migrations_on_startup: Whether to run migrations on startup.
        verify_connections: Whether to verify database connections.
        init_neo4j_schema: Whether to initialize Neo4j schema.
        project_id: Supabase project ID (uses settings if not provided).

    Returns:
        True if databases were successfully initialized, False otherwise.
    """
    logger.info("Initializing database connections via MCP")

    # Get project ID from settings if not provided
    if not project_id:
        project_id = mcp_settings.SUPABASE_PROJECT_ID
        if not project_id:
            logger.error("Supabase project ID not provided and not found in settings")
            return False

    # Initialize MCP manager
    mcp_manager = await MCPManager.get_instance(mcp_settings.model_dump())

    try:
        # Verify SQL connection
        if verify_connections:
            logger.info("Verifying SQL database connection...")
            result = await mcp_manager.call_tool(
                integration_name="supabase",
                tool_name="execute_sql",
                tool_args={"project_id": project_id, "sql": "SELECT version();"},
            )

            if result.error:
                logger.error(f"SQL connection verification failed: {result.error}")
                return False

            logger.info("SQL database connection verified")

        # Verify Neo4j connection
        if verify_connections:
            logger.info("Verifying Neo4j database connection...")
            result = await mcp_manager.call_tool(
                integration_name="memory", tool_name="read_graph", tool_args={}
            )

            if result.error:
                logger.error(f"Neo4j connection verification failed: {result.error}")
                return False

            logger.info("Neo4j database connection verified")

        # Initialize Neo4j schema if requested
        if init_neo4j_schema:
            logger.info("Initializing Neo4j schema...")

            await initialize_neo4j_schema(mcp_manager)

        # Run migrations if requested
        if run_migrations_on_startup:
            logger.info("Running database migrations...")

            # Run SQL migrations
            sql_succeeded, sql_failed = await run_migrations(project_id=project_id)
            logger.info(
                f"SQL migrations: {sql_succeeded} succeeded, {sql_failed} failed"
            )

            # Run Neo4j migrations
            neo4j_succeeded, neo4j_failed = await run_neo4j_migrations()
            logger.info(
                f"Neo4j migrations: {neo4j_succeeded} succeeded, {neo4j_failed} failed"
            )

            if sql_failed > 0 or neo4j_failed > 0:
                logger.warning("Some migrations failed")
                return False

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error initializing databases: {e}")
        return False
    finally:
        await mcp_manager.cleanup()


async def verify_database_schema(project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify that the database schema is correctly set up.

    Args:
        project_id: Supabase project ID (uses settings if not provided).

    Returns:
        Dictionary with verification results for each database.
    """
    if not project_id:
        project_id = mcp_settings.SUPABASE_PROJECT_ID

    mcp_manager = await MCPManager.get_instance(mcp_settings.model_dump())
    results = {"sql": {}, "neo4j": {}}

    try:
        # Check SQL tables
        table_query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename IN ('users', 'trips', 'migrations');
        """

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": table_query},
        )

        if result.result and "rows" in result.result:
            existing_tables = [row["tablename"] for row in result.result["rows"]]
            results["sql"]["tables"] = existing_tables
            results["sql"]["missing_tables"] = [
                t for t in ["users", "trips", "migrations"] if t not in existing_tables
            ]

        # Check Neo4j entities
        result = await mcp_manager.call_tool(
            integration_name="memory",
            tool_name="search_nodes",
            tool_args={"query": "SchemaDefinition"},
        )

        if result.result and "entities" in result.result:
            schema_entities = [
                e["name"]
                for e in result.result["entities"]
                if e.get("entityType") == "SchemaDefinition"
            ]
            results["neo4j"]["schema_entities"] = schema_entities
            results["neo4j"]["initialized"] = len(schema_entities) > 0

        return results

    except Exception as e:
        logger.error(f"Error verifying database schema: {e}")
        return {"error": str(e)}
    finally:
        await mcp_manager.cleanup()


async def create_sample_data(project_id: Optional[str] = None) -> bool:
    """
    Create sample data in both databases for testing.

    Args:
        project_id: Supabase project ID (uses settings if not provided).

    Returns:
        True if sample data was created successfully.
    """
    if not project_id:
        project_id = mcp_settings.SUPABASE_PROJECT_ID

    mcp_manager = await MCPManager.get_instance(mcp_settings.model_dump())

    try:
        # Create sample user in SQL
        user_sql = """
        INSERT INTO users (email, username, full_name, preferences)
        VALUES ('test@example.com', 'test_user', 'Test User', '{"theme": "light"}')
        ON CONFLICT (email) DO UPDATE SET updated_at = NOW()
        RETURNING id;
        """

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": user_sql},
        )

        if result.error:
            logger.error(f"Failed to create sample user: {result.error}")
            return False

        # Create sample destinations in Neo4j
        destinations = [
            {
                "name": "London",
                "entityType": "Destination",
                "observations": [
                    "country:UK",
                    "latitude:51.5074",
                    "longitude:-0.1278",
                    "timezone:Europe/London",
                    "currency:GBP",
                    "description:Historic capital of the United Kingdom",
                ],
            },
            {
                "name": "Sydney",
                "entityType": "Destination",
                "observations": [
                    "country:Australia",
                    "latitude:-33.8688",
                    "longitude:151.2093",
                    "timezone:Australia/Sydney",
                    "currency:AUD",
                    "description:Australia's largest city and economic hub",
                ],
            },
        ]

        result = await mcp_manager.call_tool(
            integration_name="memory",
            tool_name="create_entities",
            tool_args={"entities": destinations},
        )

        if result.error:
            logger.error(f"Failed to create sample destinations: {result.error}")
            return False

        logger.info("Sample data created successfully")
        return True

    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        return False
    finally:
        await mcp_manager.cleanup()


if __name__ == "__main__":
    """
    Run database initialization when the script is executed directly.
    
    Example usage:
        python -m tripsage.db.initialize
    """
    import argparse

    parser = argparse.ArgumentParser(description="Initialize TripSage databases")
    parser.add_argument(
        "--run-migrations", action="store_true", help="Run migrations on startup"
    )
    parser.add_argument(
        "--init-neo4j", action="store_true", help="Initialize Neo4j schema"
    )
    parser.add_argument(
        "--verify-schema", action="store_true", help="Verify database schema"
    )
    parser.add_argument(
        "--create-sample-data", action="store_true", help="Create sample data"
    )
    parser.add_argument("--project-id", help="Supabase project ID")
    args = parser.parse_args()

    async def main():
        if args.verify_schema:
            results = await verify_database_schema(project_id=args.project_id)
            print("Schema verification results:")
            print(results)
            return

        if args.create_sample_data:
            success = await create_sample_data(project_id=args.project_id)
            if success:
                print("Sample data created successfully")
            else:
                print("Failed to create sample data")
                exit(1)
            return

        result = await initialize_databases(
            run_migrations_on_startup=args.run_migrations,
            init_neo4j_schema=args.init_neo4j,
            project_id=args.project_id,
        )

        if result:
            print("Database initialization completed successfully")
        else:
            print("Database initialization failed")
            exit(1)

    asyncio.run(main())
