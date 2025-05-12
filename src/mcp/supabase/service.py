"""
High-level service for Supabase database operations in TripSage.
"""

import uuid
from typing import Any, Dict, List, Optional

from ...utils.logging import get_module_logger
from ...utils.settings import settings
from .client import SupabaseMCPClient, get_client

logger = get_module_logger(__name__)


class SupabaseService:
    """High-level service for Supabase database operations in TripSage."""

    def __init__(self, client: Optional[SupabaseMCPClient] = None):
        """Initialize the Supabase Service.

        Args:
            client: SupabaseMCPClient instance. If not provided, uses the default client
        """
        self.client = client or get_client()
        logger.info("Initialized Supabase Service")

    async def get_default_project(self) -> Dict[str, Any]:
        """Get the default Supabase project ID, creating one if needed.

        Returns:
            Dictionary with project information
        """
        try:
            # Check for default project ID in settings
            if (
                hasattr(settings, "supabase_mcp")
                and settings.supabase_mcp.default_project_id
            ):
                project_id = settings.supabase_mcp.default_project_id
                project = await self.client.get_project(project_id)
                return project.model_dump()

            # List projects and use the first one
            projects_response = await self.client.list_projects()
            if projects_response.projects and len(projects_response.projects) > 0:
                return projects_response.projects[0].model_dump()

            # No projects found, need to create one
            # First, list organizations
            orgs_response = await self.client.list_organizations()
            if not orgs_response.organizations or len(orgs_response.organizations) == 0:
                return {"error": "No organizations found to create project"}

            org_id = orgs_response.organizations[0].id

            # Get cost information
            cost_info = await self.client.get_cost("project", org_id)

            # Confirm cost
            confirmation = await self.client.confirm_cost(
                "project", cost_info.recurrence, cost_info.amount
            )

            # Create project
            project = await self.client.create_project(
                "tripsage-production", org_id, confirmation.id
            )

            return project.model_dump()
        except Exception as e:
            logger.error(f"Error getting default project: {str(e)}")
            return {"error": f"Failed to get default project: {str(e)}"}

    async def apply_migrations(
        self,
        project_id: str,
        migrations: List[str],
        migration_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Apply migrations to a Supabase project.

        Args:
            project_id: The ID of the project
            migrations: List of SQL migration statements
            migration_names: Optional list of migration names
                (generated if not provided)

        Returns:
            Dictionary with migration results
        """
        try:
            results = []

            # If no names provided, generate them
            if not migration_names:
                migration_names = [
                    f"migration_{i:03d}_{uuid.uuid4().hex[:8]}"
                    for i in range(len(migrations))
                ]

            # Apply each migration
            for migration, name in zip(migrations, migration_names, strict=True):
                result = await self.client.apply_migration(project_id, name, migration)
                results.append(result.model_dump())

            return {
                "project_id": project_id,
                "migrations_applied": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"Error applying migrations: {str(e)}")
            return {
                "error": f"Failed to apply migrations: {str(e)}",
                "project_id": project_id,
            }

    async def create_development_branch(
        self, project_id: Optional[str] = None, branch_name: str = "develop"
    ) -> Dict[str, Any]:
        """Create a development branch for a Supabase project.

        Args:
            project_id: The ID of the project (uses default if not provided)
            branch_name: Name for the branch (defaults to "develop")

        Returns:
            Dictionary with branch information
        """
        try:
            # Get project ID if not provided
            if not project_id:
                if (
                    hasattr(settings, "supabase_mcp")
                    and settings.supabase_mcp.default_project_id
                ):
                    project_id = settings.supabase_mcp.default_project_id
                else:
                    default_project = await self.get_default_project()
                    if "error" in default_project:
                        return default_project
                    project_id = default_project.get("id")

            # Get cost information
            orgs_response = await self.client.list_organizations()
            if not orgs_response.organizations or len(orgs_response.organizations) == 0:
                return {"error": "No organizations found to get cost information"}

            org_id = orgs_response.organizations[0].id

            cost_info = await self.client.get_cost("branch", org_id)

            # Confirm cost
            confirmation = await self.client.confirm_cost(
                "branch", cost_info.recurrence, cost_info.amount
            )

            # Create branch
            branch = await self.client.create_branch(
                project_id, confirmation.id, branch_name
            )

            return branch.model_dump()
        except Exception as e:
            logger.error(f"Error creating development branch: {str(e)}")
            return {
                "error": f"Failed to create development branch: {str(e)}",
                "project_id": project_id,
                "branch_name": branch_name,
            }


def get_service() -> SupabaseService:
    """Get a Supabase Service instance.

    Returns:
        SupabaseService instance
    """
    return SupabaseService(get_client())
