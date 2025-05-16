#!/usr/bin/env python
"""
Initialize TripSage databases using MCP-based approach.

This script initializes both SQL and Neo4j databases with:
- Tables and schema (SQL)
- Constraints and indexes (Neo4j)
- Sample data (optional)
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

# Configure logging
logger = configure_logging("init_database")


async def check_sql_connection(mcp_manager: MCPManager, project_id: str) -> bool:
    """Check SQL database connection."""
    try:
        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": "SELECT version();"},
        )

        if result.result and "rows" in result.result:
            version = result.result["rows"][0]["version"]
            logger.info(f"Connected to SQL database: {version}")
            return True

        logger.error("Failed to connect to SQL database")
        return False

    except Exception as e:
        logger.error(f"SQL connection check failed: {e}")
        return False


async def check_neo4j_connection(mcp_manager: MCPManager) -> bool:
    """Check Neo4j database connection."""
    try:
        result = await mcp_manager.call_tool(
            integration_name="memory", tool_name="read_graph", tool_args={}
        )

        if result.result:
            node_count = len(result.result.get("entities", []))
            logger.info(f"Connected to Neo4j database: {node_count} entities found")
            return True

        logger.error("Failed to connect to Neo4j database")
        return False

    except Exception as e:
        logger.error(f"Neo4j connection check failed: {e}")
        return False


async def init_sql_database(mcp_manager: MCPManager, project_id: str) -> bool:
    """Initialize SQL database with basic schema."""
    logger.info("Initializing SQL database...")

    try:
        # Create users table if not exists
        create_users_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            preferences JSONB DEFAULT '{}'::jsonb,
            role TEXT DEFAULT 'user'
        );
        """

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": create_users_sql},
        )

        if result.error:
            logger.error(f"Failed to create users table: {result.error}")
            return False

        # Create trips table if not exists
        create_trips_sql = """
        CREATE TABLE IF NOT EXISTS trips (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            status TEXT DEFAULT 'planning',
            budget DECIMAL(10, 2),
            currency TEXT DEFAULT 'USD',
            travelers_count INTEGER DEFAULT 1,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb
        );
        """

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": create_trips_sql},
        )

        if result.error:
            logger.error(f"Failed to create trips table: {result.error}")
            return False

        logger.info("SQL database initialized successfully")
        return True

    except Exception as e:
        logger.error(f"SQL initialization failed: {e}")
        return False


async def init_neo4j_database(mcp_manager: MCPManager) -> bool:
    """Initialize Neo4j database with basic schema."""
    logger.info("Initializing Neo4j database...")

    try:
        # Create root entity to ensure graph exists
        root_entity = {
            "name": "TripSage_Root",
            "entityType": "System",
            "observations": [
                "version:1.0",
                "description:TripSage travel planning knowledge graph",
                "created_at:" + str(asyncio.get_event_loop().time()),
            ],
        }

        result = await mcp_manager.call_tool(
            integration_name="memory",
            tool_name="create_entities",
            tool_args={"entities": [root_entity]},
        )

        if result.error:
            logger.error(f"Failed to create root entity: {result.error}")
            return False

        logger.info("Neo4j database initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Neo4j initialization failed: {e}")
        return False


async def load_sample_data(mcp_manager: MCPManager, project_id: str) -> bool:
    """Load sample data into databases."""
    logger.info("Loading sample data...")

    try:
        # Add sample user to SQL
        sample_user_sql = """
        INSERT INTO users (email, username, full_name, preferences)
        VALUES ('demo@tripsage.ai', 'demo_user', 'Demo User', '{"currency": "USD", "language": "en"}')
        ON CONFLICT (email) DO NOTHING
        RETURNING id;
        """

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": sample_user_sql},
        )

        if result.error:
            logger.warning(f"Sample user creation error: {result.error}")

        # Add sample destinations to Neo4j
        sample_destinations = [
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
                    "description:Japan's capital, blending traditional and modern culture",
                ],
            },
            {
                "name": "New York City",
                "entityType": "Destination",
                "observations": [
                    "country:USA",
                    "latitude:40.7128",
                    "longitude:-74.0060",
                    "timezone:America/New_York",
                    "currency:USD",
                    "language:English",
                    "description:The Big Apple, a global hub of culture and commerce",
                ],
            },
        ]

        result = await mcp_manager.call_tool(
            integration_name="memory",
            tool_name="create_entities",
            tool_args={"entities": sample_destinations},
        )

        if result.error:
            logger.warning(f"Sample destinations creation error: {result.error}")

        logger.info("Sample data loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Sample data loading failed: {e}")
        return False


async def main():
    """Main database initialization function."""
    parser = argparse.ArgumentParser(description="Initialize TripSage databases")
    parser.add_argument(
        "--project-id",
        help="Supabase project ID (will use environment variable if not provided)",
    )
    parser.add_argument(
        "--skip-sql", action="store_true", help="Skip SQL database initialization"
    )
    parser.add_argument(
        "--skip-neo4j", action="store_true", help="Skip Neo4j database initialization"
    )
    parser.add_argument(
        "--load-sample-data",
        action="store_true",
        help="Load sample data into databases",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check database connections, don't initialize",
    )
    args = parser.parse_args()

    # Get project ID
    project_id = args.project_id or mcp_settings.SUPABASE_PROJECT_ID
    if not project_id and not args.skip_sql:
        logger.error("Supabase project ID not provided and not found in settings")
        sys.exit(1)

    # Initialize MCP manager
    mcp_manager = await MCPManager.get_instance(mcp_settings.dict())

    try:
        # Check connections
        sql_connected = False
        neo4j_connected = False

        if not args.skip_sql:
            sql_connected = await check_sql_connection(mcp_manager, project_id)
            if not sql_connected:
                logger.error("Failed to connect to SQL database")
                if not args.check_only:
                    sys.exit(1)

        if not args.skip_neo4j:
            neo4j_connected = await check_neo4j_connection(mcp_manager)
            if not neo4j_connected:
                logger.error("Failed to connect to Neo4j database")
                if not args.check_only:
                    sys.exit(1)

        if args.check_only:
            logger.info("Connection check completed")
            return

        # Initialize databases
        if not args.skip_sql and sql_connected:
            success = await init_sql_database(mcp_manager, project_id)
            if not success:
                logger.error("SQL database initialization failed")
                sys.exit(1)

        if not args.skip_neo4j and neo4j_connected:
            success = await init_neo4j_database(mcp_manager)
            if not success:
                logger.error("Neo4j database initialization failed")
                sys.exit(1)

        # Load sample data if requested
        if args.load_sample_data:
            await load_sample_data(mcp_manager, project_id)

        logger.info("Database initialization completed successfully")

    finally:
        # Cleanup MCP manager
        await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
