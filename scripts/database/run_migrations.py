#!/usr/bin/env python
"""Script to run database migrations for TripSage.

This script runs all pending SQL migrations. Neo4j has been replaced with Mem0
direct SDK integration, so only SQL migrations are supported.
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
from tripsage.db.migrations import run_migrations
from tripsage_core.utils.logging_utils import configure_logging


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

    args = parser.parse_args()

    logger.info("Running SQL migrations...")
    succeeded, failed = await run_migrations(
        project_id=args.project_id, up_to=args.up_to, dry_run=args.dry_run
    )
    logger.info("SQL migrations completed: %s succeeded, %s failed", succeeded, failed)

    if failed > 0:
        logger.exception("Some migrations failed")
        sys.exit(1)
    elif succeeded == 0:
        logger.info("No migrations were applied")
    else:
        logger.info("Successfully applied %s migrations", succeeded)


if __name__ == "__main__":
    asyncio.run(main())
