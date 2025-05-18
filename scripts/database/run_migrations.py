#!/usr/bin/env python
"""
Script to run database migrations for TripSage using MCP-based approach.

This script runs all pending migrations for both SQL and Neo4j databases.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# These imports rely on the path adjustments above
from tripsage.db.migrations import run_migrations, run_neo4j_migrations  # noqa: E402
from tripsage.utils.logging import configure_logging  # noqa: E402

# Configure logging
logger = configure_logging("run_migrations")


async def main():
    """Run migrations."""
    parser = argparse.ArgumentParser(description="Run database migrations for TripSage")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually apply migrations, just show what would be done",
    )
    parser.add_argument(
        "--up-to", help="Apply migrations up to and including this filename"
    )
    parser.add_argument(
        "--project-id",
        help="Supabase project ID (will use environment variable if not provided)",
    )
    parser.add_argument(
        "--db-type",
        choices=["sql", "neo4j", "both"],
        default="both",
        help="Which database to migrate (default: both)",
    )
    parser.add_argument(
        "--init-neo4j",
        action="store_true",
        help="Initialize Neo4j schema before running migrations",
    )
    args = parser.parse_args()

    total_succeeded = 0
    total_failed = 0

    # Run SQL migrations if requested
    if args.db_type in ["sql", "both"]:
        logger.info("Running SQL migrations...")
        succeeded, failed = await run_migrations(
            project_id=args.project_id, up_to=args.up_to, dry_run=args.dry_run
        )
        logger.info(f"SQL migrations completed: {succeeded} succeeded, {failed} failed")
        total_succeeded += succeeded
        total_failed += failed

    # Run Neo4j migrations if requested
    if args.db_type in ["neo4j", "both"]:
        logger.info("Running Neo4j migrations...")

        # Initialize schema if requested
        if args.init_neo4j:
            from tripsage.config.mcp_settings import mcp_settings
            from tripsage.db.migrations.neo4j_runner import initialize_neo4j_schema
            from tripsage.mcp_abstraction.manager import MCPManager

            mcp_manager = await MCPManager.get_instance(mcp_settings.dict())
            try:
                await initialize_neo4j_schema(mcp_manager)
                logger.info("Neo4j schema initialized")
            finally:
                await mcp_manager.cleanup()

        succeeded, failed = await run_neo4j_migrations(
            up_to=args.up_to, dry_run=args.dry_run
        )
        logger.info(
            f"Neo4j migrations completed: {succeeded} succeeded, {failed} failed"
        )
        total_succeeded += succeeded
        total_failed += failed

    logger.info(
        f"All migrations completed: {total_succeeded} succeeded, {total_failed} failed"
    )

    if total_failed > 0:
        logger.error("Some migrations failed")
        sys.exit(1)
    elif total_succeeded == 0:
        logger.info("No migrations were applied")
    else:
        logger.info(f"Successfully applied {total_succeeded} migrations")


if __name__ == "__main__":
    asyncio.run(main())
