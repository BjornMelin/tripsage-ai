#!/usr/bin/env python
"""Database initialization script for TripSage.

This script initializes the SQL database with:
- Basic schema and tables
- Sample data for testing

Note: Memory management has been migrated from Neo4j to Mem0 direct SDK integration.
"""

import asyncio
import os
import sys
from pathlib import Path


# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# These imports rely on the path adjustments above
from tripsage.mcp_abstraction.manager import MCPManager  # noqa: E402
from tripsage_core.config import get_settings  # noqa: E402
from tripsage_core.utils.logging_utils import configure_logging  # noqa: E402


# Configure logging
logger = configure_logging(__name__)


async def check_sql_connection(mcp_manager: MCPManager, project_id: str) -> bool:
    """Check SQL database connection."""
    try:
        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": "SELECT 1 as test;"},
        )

        if result.result:
            logger.info("Connected to SQL database successfully")
            return True

        logger.error("Failed to connect to SQL database")
        return False

    except Exception as e:
        logger.error(f"SQL connection check failed: {e}")
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


async def load_sample_data(mcp_manager: MCPManager, project_id: str) -> bool:
    """Load sample data into SQL database."""
    logger.info("Loading sample data...")

    try:
        # Add sample user to SQL
        sample_user_sql = """
        INSERT INTO users (email, username, full_name, preferences)
        VALUES ('demo@tripsage.ai', 'demo_user', 'Demo User', 
                '{"currency": "USD", "language": "en"}')
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

        logger.info("Sample data loaded successfully")
        return True

    except Exception as e:
        logger.error(f"Sample data loading failed: {e}")
        return False


async def main():
    """Main database initialization function."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize TripSage database")
    parser.add_argument(
        "--project-id",
        default=os.getenv("SUPABASE_PROJECT_ID", "default"),
        help="Supabase project ID",
    )
    parser.add_argument("--sample-data", action="store_true", help="Load sample data")

    args = parser.parse_args()

    logger.info("Starting database initialization...")

    try:
        # Initialize MCP manager
        settings = get_settings()
        mcp_manager = await MCPManager.get_instance(settings.model_dump())

        # Check SQL connection
        sql_connected = await check_sql_connection(mcp_manager, args.project_id)
        if not sql_connected:
            logger.error("Failed to connect to SQL database")
            return False

        # Initialize SQL database
        success = await init_sql_database(mcp_manager, args.project_id)
        if not success:
            logger.error("SQL database initialization failed")
            return False

        # Load sample data if requested
        if args.sample_data:
            success = await load_sample_data(mcp_manager, args.project_id)
            if not success:
                logger.warning("Sample data loading failed, but continuing...")

        logger.info("Database initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

    finally:
        # Clean up MCP manager
        if "mcp_manager" in locals():
            await mcp_manager.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
