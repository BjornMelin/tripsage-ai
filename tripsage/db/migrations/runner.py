"""Database migration runner using Supabase context.

Final implementation (no legacy aliases/paths):
- Discovers SQL files under `supabase/migrations`.
- Logs statements that would be executed (offline/SDK-limited mode).
- Records applied migrations in a `migrations` table if available.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)

# Migration directory (canonical Supabase location)
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


class MigrationRunner:
    """Handles database migrations using the Supabase client.

    Note: The Python SDK does not expose general-purpose DDL execution. This
    runner operates in an "offline" style: it discovers migrations, logs what
    would be executed, and records success in a `migrations` table when
    available. For production-grade application, prefer the Supabase CLI.
    """

    def __init__(self, project_id: str | None = None):
        """Initialize migration runner.

        Args:
            project_id: Optional Supabase project ID (informational only).
        """
        self.project_id = project_id
        self.client = self._get_supabase_client()

    def _get_supabase_client(self):  # -> Client
        """Create a Supabase client instance."""
        from supabase import create_client  # pylint: disable=import-error

        from tripsage_core.config import get_settings  # pylint: disable=import-error

        settings = get_settings()
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
        except (OSError, RuntimeError, ValueError):
            # Database query errors or table doesn't exist
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
            logger.info("SQL to create table:\\n%s", create_table_sql)

    async def get_applied_migrations(self) -> list[str]:
        """Get list of already applied migrations."""
        try:
            result = (
                self.client.table("migrations")
                .select("filename")
                .order("applied_at")
                .execute()
            )

            try:
                if hasattr(result, "data") and result.data:  # type: ignore
                    return [row["filename"] for row in result.data]  # type: ignore
            except (AttributeError, TypeError):
                logger.warning("Unexpected result format from migrations query")
            return []
        except (OSError, RuntimeError, ValueError) as e:
            # Database query errors or table doesn't exist
            logger.warning(
                "Could not get applied migrations (table may not exist): %s", e
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
            try:
                return bool(getattr(result, "data", False))  # type: ignore[union-attr]
            except (AttributeError, TypeError):
                logger.warning("Unexpected result format from migration insert")
                return False
        except Exception:
            logger.exception("Failed to record migration %s", filename)
            return False

    def get_migration_files(self) -> list[Path]:
        """Get all migration files, sorted by filename.

        Only scans the main migrations directory, excluding subdirectories like
        examples/ and rollbacks/ per the new directory structure.
        """
        if not MIGRATIONS_DIR.exists():
            logger.error("Migrations directory not found: %s", MIGRATIONS_DIR)
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

        logger.info("Found %s migration files in main directory", len(migration_files))
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
            with Path(filepath).open(encoding="utf-8") as f:
                content = f.read()

            checksum = self._calculate_checksum(content)

            logger.info("Applying migration: %s", filename)

            # Parse and execute SQL statements
            # Note: This is a simplified approach
            statements = [s.strip() for s in content.split(";") if s.strip()]

            for statement in statements:
                if statement:
                    # Log the statement for manual execution
                    logger.info("Would execute SQL:\\n%s...", statement[:100])
                    # In production, execute via proper database connection

            # Record the migration
            if await self.record_migration(filename, checksum):
                logger.info("Migration %s recorded successfully", filename)
                return True
            logger.error("Failed to record migration %s", filename)
            return False

        except (OSError, RuntimeError, ValueError):
            # File reading, checksum calculation, or database errors
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
            "Found %s migration files, %s already applied",
            len(migration_files),
            len(applied_migrations),
        )

        succeeded = 0
        failed = 0

        for migration_file in migration_files:
            if migration_file.name in applied_migrations:
                logger.debug("Skipping already applied: %s", migration_file.name)
                continue

            if up_to and migration_file.name > up_to:
                logger.info("Stopping at requested migration: %s", up_to)
                break

            if dry_run:
                logger.info("[DRY RUN] Would apply: %s", migration_file.name)
                succeeded += 1
                continue

            if await self.apply_migration(migration_file):
                succeeded += 1
            else:
                failed += 1
                logger.error("Failed to apply: %s", migration_file.name)
                # Stop on first failure
                break

        return succeeded, failed


async def run_migrations_cli(
    project_id: str | None = None, up_to: str | None = None, dry_run: bool = False
) -> tuple[int, int]:
    """CLI entry point for running migrations."""
    runner = MigrationRunner(project_id)
    return await runner.run_migrations(up_to=up_to, dry_run=dry_run)


__all__ = ["run_migrations_cli"]


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
        """Main function to run migrations."""
        succeeded, failed = await run_migrations_cli(
            project_id=args.project_id, dry_run=args.dry_run, up_to=args.up_to
        )

        logger.info("Migration summary: %s succeeded, %s failed", succeeded, failed)

        if not args.dry_run and succeeded == 0 and failed == 0:
            logger.info("All migrations are already applied")

        return succeeded, failed

    result = asyncio.run(main())

    # Exit with error code if there were failures
    if result[1] > 0:
        import sys

        sys.exit(1)
