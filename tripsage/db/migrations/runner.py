"""SQL database migration runner using Supabase MCP."""

import asyncio
import re
from pathlib import Path
from typing import List, Optional, Tuple

from tripsage.config.mcp_settings import mcp_settings
from tripsage.mcp_abstraction.exceptions import MCPIntegrationError
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.logging import configure_logging

logger = configure_logging(__name__)

# Migration directory
MIGRATIONS_DIR = Path(__file__).parent.parent.parent.parent / "migrations"


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


async def get_applied_migrations(mcp_manager: MCPManager, project_id: str) -> List[str]:
    """
    Get list of migrations that have already been applied.

    Args:
        mcp_manager: The MCP manager instance.
        project_id: The Supabase project ID.

    Returns:
        List of applied migration filenames.
    """
    try:
        # Check if migrations table exists
        tables_query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' AND tablename = 'migrations';
        """

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": tables_query},
        )

        if not result.result.get("rows"):
            # Create migrations table if it doesn't exist
            logger.info("Creating migrations table")
            create_table_query = """
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await mcp_manager.call_tool(
                integration_name="supabase",
                tool_name="execute_sql",
                tool_args={"project_id": project_id, "sql": create_table_query},
            )
            return []

        # Get list of applied migrations
        get_migrations_query = "SELECT filename FROM migrations ORDER BY applied_at;"

        result = await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": get_migrations_query},
        )

        if not result.result.get("rows"):
            return []

        return [row["filename"] for row in result.result["rows"]]

    except MCPIntegrationError as e:
        logger.error(f"Error checking applied migrations: {e}")
        raise


async def apply_migration(
    mcp_manager: MCPManager, project_id: str, filename: str, content: str
) -> bool:
    """
    Apply a single migration to the database.

    Args:
        mcp_manager: The MCP manager instance.
        project_id: The Supabase project ID.
        filename: Name of the migration file.
        content: SQL content of the migration.

    Returns:
        True if the migration was successfully applied, False otherwise.
    """
    try:
        # Apply the migration using Supabase MCP's apply_migration method
        logger.info(f"Applying migration: {filename}")

        # Split content into individual queries if necessary
        # Simple approach - could be enhanced for more complex queries
        queries = [q.strip() for q in content.split(";") if q.strip()]

        for query in queries:
            result = await mcp_manager.call_tool(
                integration_name="supabase",
                tool_name="execute_sql",
                tool_args={"project_id": project_id, "sql": query},
            )

            if result.error:
                logger.error(f"Error applying query in {filename}: {result.error}")
                return False

        # Record the migration in the migrations table
        record_query = f"""
        INSERT INTO migrations (filename, applied_at)
        VALUES ('{filename}', NOW());
        """

        await mcp_manager.call_tool(
            integration_name="supabase",
            tool_name="execute_sql",
            tool_args={"project_id": project_id, "sql": record_query},
        )

        logger.info(f"Migration {filename} applied successfully")
        return True

    except MCPIntegrationError as e:
        logger.error(f"Error applying migration {filename}: {e}")
        return False


async def run_migrations(
    project_id: Optional[str] = None, up_to: Optional[str] = None, dry_run: bool = False
) -> Tuple[int, int]:
    """
    Run all pending migrations in order.

    Args:
        project_id: Supabase project ID. If not provided, will use default from settings.
        up_to: Optional filename to stop at (inclusive).
        dry_run: If True, don't actually apply migrations, just log what would be done.

    Returns:
        Tuple of (number of successful migrations, number of failed migrations)
    """
    # Get project ID from settings if not provided
    if not project_id:
        if mcp_settings.SUPABASE_PROJECT_ID:
            project_id = mcp_settings.SUPABASE_PROJECT_ID
        else:
            raise ValueError(
                "Supabase project ID not provided and not found in settings"
            )

    # Initialize MCP manager
    mcp_manager = await MCPManager.get_instance(mcp_settings.dict())

    try:
        migration_files = get_migration_files()
        applied_migrations = await get_applied_migrations(mcp_manager, project_id)

        logger.info(
            f"Found {len(migration_files)} migration files, "
            f"{len(applied_migrations)} already applied"
        )

        succeeded = 0
        failed = 0

        for migration_file in migration_files:
            if migration_file.name in applied_migrations:
                logger.debug(
                    f"Skipping already applied migration: {migration_file.name}"
                )
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
                    mcp_manager, project_id, migration_file.name, content
                ):
                    succeeded += 1
                else:
                    failed += 1
                    logger.error(f"Failed to apply migration: {migration_file.name}")
            except Exception as e:
                failed += 1
                logger.error(f"Error processing migration {migration_file.name}: {e}")

        return succeeded, failed

    finally:
        # Cleanup MCP manager
        await mcp_manager.cleanup()


if __name__ == "__main__":
    """
    Run migrations when the script is executed directly.
    
    Example usage:
        python -m tripsage.db.migrations.runner
    """
    import argparse

    parser = argparse.ArgumentParser(description="Apply database migrations")
    parser.add_argument("--project-id", help="Supabase project ID")
    parser.add_argument(
        "--dry-run", action="store_true", help="Don't actually apply migrations"
    )
    parser.add_argument(
        "--up-to", help="Apply migrations up to and including this filename"
    )
    args = parser.parse_args()

    async def main():
        succeeded, failed = await run_migrations(
            project_id=args.project_id, dry_run=args.dry_run, up_to=args.up_to
        )
        logger.info(f"Migration completed: {succeeded} succeeded, {failed} failed")
        return succeeded, failed

    result = asyncio.run(main())

    if result[1] > 0:  # If there were failures
        exit(1)
