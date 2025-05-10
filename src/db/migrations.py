"""
Migration runner for TripSage database.

This module provides functionality to apply SQL migrations to the Supabase database.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.db.client import create_supabase_client
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


def get_applied_migrations(service_key: bool = True) -> List[str]:
    """
    Get list of migrations that have already been applied.

    Args:
        service_key: Whether to use the service role key for database access.

    Returns:
        List of applied migration filenames.
    """
    # Use service role key by default for admin operations
    supabase = create_supabase_client(use_service_key=service_key)

    try:
        # Check if migrations table exists
        result = supabase.table("migrations").select("id").limit(1).execute()
        if result.data is None:
            # Create migrations table if it doesn't exist
            logger.info("Creating migrations table")
            query = """
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            supabase.rpc("exec_sql", {"query": query}).execute()
            return []

        # Get list of applied migrations
        result = supabase.table("migrations").select("filename").execute()
        if result.data is None:
            return []

        return [m["filename"] for m in result.data]
    except Exception as e:
        logger.error(f"Error checking applied migrations: {e}")
        # If the table doesn't exist, we'll assume no migrations have been applied
        if 'relation "migrations" does not exist' in str(e):
            logger.info("Migrations table does not exist. Will create it.")
            return []
        raise


def apply_migration(filename: str, content: str, service_key: bool = True) -> bool:
    """
    Apply a single migration to the database.

    Args:
        filename: Name of the migration file.
        content: SQL content of the migration.
        service_key: Whether to use the service role key for database access.

    Returns:
        True if the migration was successfully applied, False otherwise.
    """
    supabase = create_supabase_client(use_service_key=service_key)

    try:
        # Execute the migration SQL
        logger.info(f"Applying migration: {filename}")
        result = supabase.rpc("exec_sql", {"query": content}).execute()

        # Record the migration in the migrations table
        supabase.table("migrations").insert(
            {"filename": filename, "applied_at": "now()"}
        ).execute()

        logger.info(f"Migration {filename} applied successfully")
        return True
    except Exception as e:
        logger.error(f"Error applying migration {filename}: {e}")
        return False


def run_migrations(
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
    applied_migrations = get_applied_migrations(service_key=service_key)

    logger.info(
        f"Found {len(migration_files)} migration files, {len(applied_migrations)} already applied"
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

            if apply_migration(migration_file.name, content, service_key=service_key):
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

    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually apply migrations"
    )
    parser.add_argument(
        "--up-to", help="Apply migrations up to and including this filename"
    )
    args = parser.parse_args()

    succeeded, failed = run_migrations(dry_run=args.dry_run, up_to=args.up_to)

    logger.info(f"Migration completed: {succeeded} succeeded, {failed} failed")
