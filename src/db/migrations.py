"""
Migration runner for TripSage database.

This module provides functionality to apply SQL migrations to the database,
supporting both Supabase and Neon providers.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from src.db.client import get_db_client
from src.utils.logging import configure_logging

# Configure logging
logger = configure_logging(__name__)

# Migration directory
MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


def get_migration_files() -> List[Path]:
    """
    Get all migration files in the migrations directory, sorted by filename.

    Returns:
        List of paths to migration files.
    """
    if not MIGRATIONS_DIR.exists():
        logger.error(f"Migrations directory not found: {MIGRATIONS_DIR}")
        raise FileNotFoundError(f"Migrations directory not found: {MIGRATIONS_DIR}")

    migration_files = sorted(
        [
            f
            for f in MIGRATIONS_DIR.glob("*.sql")
            if re.match(r"\d{8}_\d{2}_.*\.sql", f.name)
        ]
    )

    logger.info(f"Found {len(migration_files)} migration files")
    return migration_files


async def get_applied_migrations(service_key: bool = True) -> List[str]:
    """
    Get list of migrations that have already been applied.

    Args:
        service_key: Whether to use the service role key for database access.

    Returns:
        List of applied migration filenames.
    """
    # Get database client
    db_client = await get_db_client(use_service_key=service_key)

    try:
        # Check if migrations table exists
        tables_exist = await db_client.tables_exist(["migrations"])

        if not tables_exist.get("migrations", False):
            # Create migrations table if it doesn't exist
            logger.info("Creating migrations table")
            query = """
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await db_client.execute_sql(query)
            return []

        # Get list of applied migrations
        result = db_client.table("migrations").select("filename").execute()

        if not result.get("data"):
            return []

        return [m["filename"] for m in result.get("data", [])]
    except Exception as e:
        logger.error(f"Error checking applied migrations: {e}")
        # If the table doesn't exist, we'll assume no migrations have been applied
        if 'relation "migrations" does not exist' in str(e):
            logger.info("Migrations table does not exist. Will create it.")
            return []
        raise


async def apply_migration(
    filename: str, content: str, service_key: bool = True
) -> bool:
    """
    Apply a single migration to the database.

    Args:
        filename: Name of the migration file.
        content: SQL content of the migration.
        service_key: Whether to use the service role key for database access.

    Returns:
        True if the migration was successfully applied, False otherwise.
    """
    db_client = await get_db_client(use_service_key=service_key)

    try:
        # Execute the migration SQL
        logger.info(f"Applying migration: {filename}")
        await db_client.execute_sql(content)

        # Record the migration in the migrations table
        db_client.table("migrations").insert(
            {"filename": filename, "applied_at": "now()"}
        ).execute()

        logger.info(f"Migration {filename} applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migration {filename}: {e}")
        return False


async def run_migrations(
    service_key: bool = True, up_to: Optional[str] = None, dry_run: bool = False
) -> Tuple[int, int]:
    """
    Run all pending migrations in order.

    Args:
        service_key: Whether to use the service role key for database access.
        up_to: Optional filename to stop at (inclusive).
        dry_run: If True, don't actually apply migrations, just log what would be done.

    Returns:
        Tuple of (number of successful migrations, number of failed migrations)
    """
    migration_files = get_migration_files()
    applied_migrations = await get_applied_migrations(service_key=service_key)

    logger.info(
        f"Found {len(migration_files)} migration files, "
        f"{len(applied_migrations)} already applied"
    )

    succeeded = 0
    failed = 0

    for migration_file in migration_files:
        if migration_file.name in applied_migrations:
            logger.debug(f"Skipping already applied migration: {migration_file.name}")
            continue

        if up_to and migration_file.name > up_to:
            logger.info(f"Stopping at requested migration: {up_to}")
            break

        logger.info(f"Processing migration: {migration_file.name}")
        if dry_run:
            logger.info(f"[DRY RUN] Would apply migration: {migration_file.name}")
            succeeded += 1
            continue

        try:
            with open(migration_file, "r") as f:
                content = f.read()

            if await apply_migration(
                migration_file.name, content, service_key=service_key
            ):
                succeeded += 1
            else:
                failed += 1
                logger.error(f"Failed to apply migration: {migration_file.name}")
        except Exception as e:
            failed += 1
            logger.error(f"Error processing migration {migration_file.name}: {e}")

    return succeeded, failed


if __name__ == "__main__":
    """
    Run migrations when the script is executed directly.
    
    Example usage:
        python -m src.db.migrations
    """
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually apply migrations"
    )
    parser.add_argument(
        "--up-to", help="Apply migrations up to and including this filename"
    )
    args = parser.parse_args()

    async def main():
        succeeded, failed = await run_migrations(dry_run=args.dry_run, up_to=args.up_to)
        logger.info(f"Migration completed: {succeeded} succeeded, {failed} failed")
        return succeeded, failed

    result = asyncio.run(main())

    if result[1] > 0:  # If there were failures
        exit(1)
