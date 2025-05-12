"""
High-level service for Neon database operations in TripSage.
"""

import uuid
from typing import Any, Dict, List, Optional

from ...utils.logging import get_module_logger
from ...utils.settings import settings
from .client import NeonMCPClient, get_client

logger = get_module_logger(__name__)


class NeonService:
    """High-level service for Neon database operations in TripSage."""

    def __init__(self, client: Optional[NeonMCPClient] = None):
        """Initialize the Neon Service.

        Args:
            client: NeonMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or get_client()
        logger.info("Initialized Neon Service")

    async def create_development_branch(
        self, project_id: Optional[str] = None, branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a development branch for isolating database changes.

        Args:
            project_id: The project ID (uses default if not provided)
            branch_name: Optional branch name (will generate one if not provided)

        Returns:
            Dictionary with branch information
        """
        try:
            # Use the configured default project ID if not provided
            if not project_id:
                project_id = (
                    settings.neon_mcp.default_project_id
                    if hasattr(settings, "neon_mcp")
                    else None
                )
                if not project_id:
                    projects_response = await self.client.list_projects()
                    if (
                        projects_response.projects
                        and len(projects_response.projects) > 0
                    ):
                        project_id = projects_response.projects[0].id
                    else:
                        # No projects found, create one
                        project_response = await self.client.create_project(
                            "tripsage-development"
                        )
                        project_id = project_response.project.id

            # Generate a branch name if not provided
            if not branch_name:
                branch_name = f"dev-{uuid.uuid4().hex[:8]}"

            # Create the branch
            branch_response = await self.client.create_branch(project_id, branch_name)

            # Get connection string for the branch
            conn_response = await self.client.get_connection_string(
                project_id, branch_response.branch.id
            )

            return {
                "project_id": project_id,
                "branch": branch_response.branch.model_dump(),
                "connection_string": conn_response.connection_string,
            }
        except Exception as e:
            logger.error(f"Error creating development branch: {str(e)}")
            return {
                "error": f"Failed to create development branch: {str(e)}",
                "project_id": project_id,
                "branch_name": branch_name,
            }

    async def apply_migrations(
        self,
        project_id: str,
        branch_id: str,
        migrations: List[str],
        database_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Apply database migrations to a specific branch.

        Args:
            project_id: The project ID
            branch_id: The branch ID
            migrations: List of SQL migration statements
            database_name: Optional database name

        Returns:
            Dictionary with migration results
        """
        try:
            # Execute the migrations as a transaction
            result = await self.client.run_sql_transaction(
                project_id, migrations, database_name, branch_id
            )

            return {
                "project_id": project_id,
                "branch_id": branch_id,
                "migrations_applied": len(migrations),
                "result": result.model_dump(),
            }
        except Exception as e:
            logger.error(f"Error applying migrations: {str(e)}")
            return {
                "error": f"Failed to apply migrations: {str(e)}",
                "project_id": project_id,
                "branch_id": branch_id,
            }

    async def get_default_project(self) -> Dict[str, Any]:
        """Get or create the default Neon project.

        Returns:
            Dictionary with project information
        """
        try:
            # Check for default project ID in settings
            if hasattr(settings, "neon_mcp") and settings.neon_mcp.default_project_id:
                project_id = settings.neon_mcp.default_project_id
                project_response = await self.client.describe_project(project_id)
                return project_response.project.model_dump()

            # List projects and use the first one
            projects_response = await self.client.list_projects()
            if projects_response.projects and len(projects_response.projects) > 0:
                return projects_response.projects[0].model_dump()

            # No projects found, create one
            project_response = await self.client.create_project("tripsage-default")
            return project_response.project.model_dump()
        except Exception as e:
            logger.error(f"Error getting default project: {str(e)}")
            return {"error": f"Failed to get default project: {str(e)}"}

    async def get_database_schema(
        self,
        project_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the database schema for a Neon project.

        Args:
            project_id: The project ID (uses default if not provided)
            branch_id: Optional branch ID (uses main branch if not provided)
            database_name: Optional database name (uses default if not provided)

        Returns:
            Dictionary with database schema information
        """
        try:
            # Get default project if not provided
            if not project_id:
                project = await self.get_default_project()
                if "error" in project:
                    return project
                project_id = project["id"]

            # Get tables
            tables_response = await self.client.get_database_tables(
                project_id, branch_id, database_name
            )

            # Get detailed schema for each table
            table_schemas = {}
            for table in tables_response.tables:
                schema_response = await self.client.describe_table_schema(
                    project_id, table.name, branch_id, database_name
                )
                table_schemas[table.name] = schema_response.model_dump()

            return {
                "project_id": project_id,
                "branch_id": branch_id,
                "database_name": database_name,
                "tables": [table.model_dump() for table in tables_response.tables],
                "table_schemas": table_schemas,
            }
        except Exception as e:
            logger.error(f"Error getting database schema: {str(e)}")
            return {
                "error": f"Failed to get database schema: {str(e)}",
                "project_id": project_id,
                "branch_id": branch_id,
                "database_name": database_name,
            }


def get_service() -> NeonService:
    """Get a Neon Service instance.

    Returns:
        NeonService instance
    """
    return NeonService(get_client())
