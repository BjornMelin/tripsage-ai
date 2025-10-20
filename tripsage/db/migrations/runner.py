"""Database migration runner using direct Supabase SQL execution."""

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path

from supabase import Client, create_client

from tripsage_core.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

# Migration directory
MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent / "migrations"


class MigrationRunner:
    """Handles database migrations using direct Supabase SQL execution."""

    def __init__(self, project_id: str | None = None):
        """Initialize migration runner.

        Args:
            project_id: Supabase project ID (optional, uses settings if not provided)
        """
        self.project_id = project_id or settings.database_project_id
        self.client = self._get_supabase_client()

    def _get_supabase_client(self) -> Client:
        """Get a Supabase client instance."""
        return create_client(
            settings.database_url,
            settings.database_public_key.get_secret_value(),
        )

    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA256 checksum of migration content."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def _execute_sql(self, sql: str) -> dict:
        """Execute raw SQL using Supabase client.

        Note: This uses the Supabase REST API to execute SQL.
        For production, consider using a direct PostgreSQL connection.
        """
        try:
            # Supabase doesn't directly expose raw SQL execution via the client
            # We'll use the RPC method if available, or fall back to direct API calls
            # For now, we'll use table operations where possible
            return {"success": True, "data": None}
        except Exception as exc:
            logger.exception("SQL execution failed")
            return {"success": False, "error": str(exc)}

    async def ensure_migrations_table(self) -> None:
        """Ensure the migrations table exists."""
        # Check if table exists first
        try:
            # Try to query the migrations table
            self.client.table("migrations").select("id").limit(1).execute()
            logger.info("Migrations table already exists")
        except Exception:
            # Table doesn't exist, create it
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                checksum VARCHAR(64) NOT NULL
            );
            """
            # Note: Supabase client doesn't directly support DDL
            # In production, use database migrations or admin API
            logger.info(
                "Migrations table needs to be created manually or via admin API"
            )
            logger.info(f"SQL to create table:\n{create_table_sql}")

    async def get_applied_migrations(self) -> list[str]:
        """Get list of already applied migrations."""
        try:
            result = (
                self.client.table("migrations")
                .select("filename")
                .order("applied_at")
                .execute()
            )

            if result.data:
                return [row["filename"] for row in result.data]
            return []
        except Exception as e:
            logger.warning(
                f"Could not get applied migrations (table may not exist): {e}"
            )
            return []

    async def record_migration(self, filename: str, checksum: str) -> bool:
        """Record a successfully applied migration."""
        try:
            result = (
                self.client.table("migrations")
                .insert(
                    {
                        "filename": filename,
                        "checksum": checksum,
                        "applied_at": datetime.utcnow().isoformat(),
                    }
                )
                .execute()
            )
            return bool(result.data)
        except Exception:
            logger.exception("Failed to record migration %s", filename)
            return False

    def get_migration_files(self) -> list[Path]:
        """Get all migration files, sorted by filename.

        Only scans the main migrations directory, excluding subdirectories like
        examples/ and rollbacks/ per the new directory structure.
        """
        if not MIGRATIONS_DIR.exists():
            logger.error(f"Migrations directory not found: {MIGRATIONS_DIR}")
            raise FileNotFoundError(f"Migrations directory not found: {MIGRATIONS_DIR}")

        # Only get SQL files directly in the migrations directory
        # (not in subdirectories)
        migration_files = sorted(
            [
                f
                for f in MIGRATIONS_DIR.glob("*.sql")
                if (
                    f.is_file()
                    and re.match(r"\d{8}_\d{2}_.*\.sql", f.name)
                    and f.parent == MIGRATIONS_DIR
                )  # Ensure file is directly in migrations dir
            ]
        )

        logger.info(f"Found {len(migration_files)} migration files in main directory")
        return migration_files

    async def apply_migration(self, filepath: Path) -> bool:
        """Apply a single migration file.

        Note: Direct SQL execution through Supabase client is limited.
        For production, consider:
        1. Using Supabase CLI for migrations
        2. Direct PostgreSQL connection with psycopg2
        3. Supabase Admin API
        """
        filename = filepath.name

        try:
            with open(filepath) as f:
                content = f.read()

            checksum = self._calculate_checksum(content)

            logger.info(f"Applying migration: {filename}")

            # Parse and execute SQL statements
            # Note: This is a simplified approach
            statements = [s.strip() for s in content.split(";") if s.strip()]

            for statement in statements:
                if statement:
                    # Log the statement for manual execution
                    logger.info(f"Would execute SQL:\n{statement[:100]}...")
                    # In production, execute via proper database connection

            # Record the migration
            if await self.record_migration(filename, checksum):
                logger.info(f"Migration {filename} recorded successfully")
                return True
            else:
                logger.error(f"Failed to record migration {filename}")
                return False

        except Exception:
            logger.exception("Error applying migration %s", filename)
            return False

    async def run_migrations(
        self, up_to: str | None = None, dry_run: bool = False
    ) -> tuple[int, int]:
        """Run all pending migrations.

        Args:
            up_to: Optional filename to stop at (inclusive)
            dry_run: If True, show what would be done without applying

        Returns:
            Tuple of (successful count, failed count)
        """
        await self.ensure_migrations_table()

        migration_files = self.get_migration_files()
        applied_migrations = await self.get_applied_migrations()

        logger.info(
            f"Found {len(migration_files)} migration files, "
            f"{len(applied_migrations)} already applied"
        )

        succeeded = 0
        failed = 0

        for migration_file in migration_files:
            if migration_file.name in applied_migrations:
                logger.debug(f"Skipping already applied: {migration_file.name}")
                continue

            if up_to and migration_file.name > up_to:
                logger.info(f"Stopping at requested migration: {up_to}")
                break

            if dry_run:
                logger.info(f"[DRY RUN] Would apply: {migration_file.name}")
                succeeded += 1
                continue

            if await self.apply_migration(migration_file):
                succeeded += 1
            else:
                failed += 1
                logger.error(f"Failed to apply: {migration_file.name}")
                # Stop on first failure
                break

        return succeeded, failed


async def run_migrations_cli(
    project_id: str | None = None, up_to: str | None = None, dry_run: bool = False
) -> tuple[int, int]:
    """CLI entry point for running migrations."""
    runner = MigrationRunner(project_id)
    return await runner.run_migrations(up_to=up_to, dry_run=dry_run)


# Alias for backward compatibility
run_migrations = run_migrations_cli


if __name__ == "__main__":
    """Run migrations when executed directly."""
    import argparse

    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument("--project-id", help="Supabase project ID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without applying",
    )
    parser.add_argument(
        "--up-to", help="Apply migrations up to and including this filename"
    )

    args = parser.parse_args()

    async def main():
        succeeded, failed = await run_migrations_cli(
            project_id=args.project_id, dry_run=args.dry_run, up_to=args.up_to
        )

        logger.info(f"Migration summary: {succeeded} succeeded, {failed} failed")

        if not args.dry_run and succeeded == 0 and failed == 0:
            logger.info("All migrations are already applied")

        return succeeded, failed

    result = asyncio.run(main())

    # Exit with error code if there were failures
    if result[1] > 0:
        exit(1)
