#!/usr/bin/env python
"""
Script to run database migrations for TripSage.

This script runs all pending migrations in the migrations directory.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.db.migrations import run_migrations
from src.utils.logging import configure_logging

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
        "--no-service-key",
        action="store_true",
        help="Don't use the service role key for migrations (not recommended)",
    )
    args = parser.parse_args()

    logger.info("Running migrations...")
    succeeded, failed = run_migrations(
        service_key=not args.no_service_key, up_to=args.up_to, dry_run=args.dry_run
    )

    logger.info(f"Migration completed: {succeeded} succeeded, {failed} failed")

    if failed > 0:
        logger.error("Some migrations failed")
        sys.exit(1)
    elif succeeded == 0:
        logger.info("No migrations were applied")
    else:
        logger.info(f"Successfully applied {succeeded} migrations")


if __name__ == "__main__":
    asyncio.run(main())
