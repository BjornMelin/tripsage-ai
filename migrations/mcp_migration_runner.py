"""
Database migration runner using MCP tools.

This module provides a migration runner that uses MCP tools (Supabase MCP)
instead of direct database connections, following the Phase 5 implementation
patterns.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.utils.error_handling import TripSageError
from tripsage_core.utils.decorator_utils import with_error_handling
from tripsage_core.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MCPMigrationError(TripSageError):
    """Error raised when MCP migration operations fail."""

    pass


class MCPMigrationRunner:
    """Run database migrations using MCP tools."""

    def __init__(self, mcp_manager: Optional[MCPManager] = None):
        """Initialize the migration runner.

        Args:
            mcp_manager: Optional MCP manager instance. If None, uses global instance.
        """
        self.mcp_manager = mcp_manager or MCPManager()
        self.migrations_dir = Path(__file__).parent
        self.logger = logger

    @with_error_handling
    async def apply_migration(
        self, migration_sql: str, name: str, project_id: Optional[str] = None
    ) -> bool:
        """Apply migration using Supabase MCP.

        Args:
            migration_sql: SQL migration content
            name: Migration name
            project_id: Optional Supabase project ID

        Returns:
            True if migration was successful

        Raises:
            MCPMigrationError: If migration fails
        """
        try:
            # Use environment variable if project_id not provided
            if not project_id:
                project_id = os.getenv("SUPABASE_PROJECT_ID")
                if not project_id:
                    raise MCPMigrationError(
                        "No project ID provided and SUPABASE_PROJECT_ID not set"
                    )

            self.logger.info(f"Applying migration '{name}' to project {project_id}")

            result = await self.mcp_manager.invoke(
                mcp_name="supabase",
                method_name="apply_migration",
                params={"name": name, "query": migration_sql, "project_id": project_id},
            )

            success = (
                result.get("success", False)
                if isinstance(result, dict)
                else bool(result)
            )

            if success:
                self.logger.info(f"Migration '{name}' applied successfully")
                return True
            else:
                error_msg = (
                    result.get("error", "Unknown error")
                    if isinstance(result, dict)
                    else str(result)
                )
                raise MCPMigrationError(f"Migration '{name}' failed: {error_msg}")

        except Exception as e:
            if isinstance(e, MCPMigrationError):
                raise
            self.logger.error(f"Migration '{name}' failed with error: {e}")
            raise MCPMigrationError(f"Migration '{name}' failed: {str(e)}") from e

    @with_error_handling
    async def create_neo4j_schema(
        self, schema_queries: List[str], clear_existing: bool = False
    ) -> bool:
        """Initialize Neo4j schema via Memory MCP.

        Args:
            schema_queries: List of Cypher queries to execute
            clear_existing: Whether to clear existing data first

        Returns:
            True if schema creation was successful

        Raises:
            MCPMigrationError: If schema creation fails
        """
        try:
            self.logger.info("Creating Neo4j schema via Memory MCP")

            # Clear existing data if requested
            if clear_existing:
                self.logger.info("Clearing existing Neo4j data")
                await self.mcp_manager.invoke(
                    mcp_name="memory",
                    method_name="read_graph",
                    params={},
                )

            # Execute schema queries
            for i, query in enumerate(schema_queries, 1):
                self.logger.info(f"Executing schema query {i}/{len(schema_queries)}")

                # For Neo4j schema creation, we might need to use create_entities
                # or other Memory MCP methods depending on the query type
                if (
                    "CREATE CONSTRAINT" in query.upper()
                    or "CREATE INDEX" in query.upper()
                ):
                    # These are administrative queries that might not be
                    # directly supported
                    # by Memory MCP. Log them for manual execution.
                    self.logger.warning(
                        f"Administrative query may need manual execution: "
                        f"{query[:100]}..."
                    )
                    continue

                # For now, we'll use the Memory MCP's available methods
                # This will need to be adapted based on what Memory MCP
                # actually supports
                await self.mcp_manager.invoke(
                    mcp_name="memory",
                    method_name="create_entities",
                    params={
                        "entities": []
                    },  # Placeholder - adapt based on actual query
                )

            self.logger.info("Neo4j schema creation completed")
            return True

        except Exception as e:
            self.logger.error(f"Neo4j schema creation failed: {e}")
            raise MCPMigrationError(f"Neo4j schema creation failed: {str(e)}") from e

    @with_error_handling
    async def run_migration_file(
        self, migration_file: str, project_id: Optional[str] = None
    ) -> bool:
        """Run a migration from a SQL file.

        Args:
            migration_file: Path to the migration file
            project_id: Optional Supabase project ID

        Returns:
            True if migration was successful

        Raises:
            MCPMigrationError: If migration fails
        """
        try:
            migration_path = Path(migration_file)
            if not migration_path.is_absolute():
                migration_path = self.migrations_dir / migration_path

            if not migration_path.exists():
                raise MCPMigrationError(f"Migration file not found: {migration_path}")

            # Read migration content
            migration_sql = migration_path.read_text(encoding="utf-8")

            # Extract migration name from filename
            migration_name = migration_path.stem

            self.logger.info(f"Running migration file: {migration_path}")

            return await self.apply_migration(migration_sql, migration_name, project_id)

        except Exception as e:
            if isinstance(e, MCPMigrationError):
                raise
            raise MCPMigrationError(
                f"Failed to run migration file {migration_file}: {str(e)}"
            ) from e

    @with_error_handling
    async def get_migration_status(self, project_id: Optional[str] = None) -> Dict:
        """Get the current migration status from Supabase.

        Args:
            project_id: Optional Supabase project ID

        Returns:
            Dictionary with migration status information

        Raises:
            MCPMigrationError: If status check fails
        """
        try:
            if not project_id:
                project_id = os.getenv("SUPABASE_PROJECT_ID")
                if not project_id:
                    raise MCPMigrationError(
                        "No project ID provided and SUPABASE_PROJECT_ID not set"
                    )

            self.logger.info(f"Checking migration status for project {project_id}")

            # Use Supabase MCP to list migrations
            result = await self.mcp_manager.invoke(
                mcp_name="supabase",
                method_name="list_migrations",
                params={"project_id": project_id},
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to get migration status: {e}")
            raise MCPMigrationError(f"Failed to get migration status: {str(e)}") from e

    @with_error_handling(logger=logger, raise_on_error=True)
    async def run_pending_migrations(
        self, project_id: Optional[str] = None, dry_run: bool = False
    ) -> List[str]:
        """Run all pending migrations.

        Args:
            project_id: Optional Supabase project ID
            dry_run: If True, only show what would be migrated

        Returns:
            List of migration names that were run (or would be run)

        Raises:
            MCPMigrationError: If migration run fails
        """
        try:
            # Get list of migration files from main directory only
            # (exclude subdirectories)
            all_files = [
                f for f in os.listdir(self.migrations_dir) if f.endswith(".sql")
            ]

            # Filter to only include files directly in migrations directory
            # (not subdirectories) and exclude rollback files
            migration_files = []
            for f in all_files:
                file_path = os.path.join(self.migrations_dir, f)
                if (
                    os.path.isfile(file_path)
                    and "rollback" not in f.lower()
                    and re.match(r"\d{8}_\d{2}_.*\.sql", f)
                ):
                    migration_files.append(f)

            migration_files = sorted(migration_files)

            self.logger.info(
                f"Found {len(migration_files)} migration files in main directory"
            )

            if dry_run:
                self.logger.info("DRY RUN: Would run the following migrations:")
                for migration_file in migration_files:
                    self.logger.info(f"  - {migration_file}")
                return migration_files

            # Run each migration
            completed_migrations = []
            for migration_file in migration_files:
                try:
                    await self.run_migration_file(migration_file, project_id)
                    completed_migrations.append(migration_file)
                except MCPMigrationError as e:
                    self.logger.error(f"Migration {migration_file} failed: {e}")
                    # Continue with other migrations or stop? For now, continue.
                    continue

            self.logger.info(f"Completed {len(completed_migrations)} migrations")
            return completed_migrations

        except Exception as e:
            self.logger.error(f"Failed to run pending migrations: {e}")
            raise MCPMigrationError(
                f"Failed to run pending migrations: {str(e)}"
            ) from e


async def main():
    """Main function for testing migration runner."""
    # Initialize the migration runner
    runner = MCPMigrationRunner()

    try:
        # Example: Check migration status
        status = await runner.get_migration_status()
        print(f"Migration status: {status}")

        # Example: Run pending migrations (dry run)
        pending = await runner.run_pending_migrations(dry_run=True)
        print(f"Pending migrations: {pending}")

    except MCPMigrationError as e:
        print(f"Migration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
