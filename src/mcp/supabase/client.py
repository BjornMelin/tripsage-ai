"""
Supabase MCP Client implementation for TripSage.

This module provides a client for interacting with the Supabase MCP Server,
which offers PostgreSQL database management focused on production environments.
"""

from typing import Any, Dict, List, Optional, Union
import json
import uuid

from agents import function_tool
from pydantic import Field, BaseModel, ConfigDict

from ...cache.redis_cache import redis_cache
from ...utils.settings import settings
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..fastmcp import FastMCPClient

logger = get_module_logger(__name__)


class SupabaseMCPClient(FastMCPClient):
    """Client for the Supabase MCP Server focused on production environments."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        use_cache: bool = True,
    ):
        """Initialize the Supabase MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        if endpoint is None:
            endpoint = (
                settings.supabase_mcp.endpoint
                if hasattr(settings, "supabase_mcp")
                else "http://localhost:8098"
            )

        api_key = api_key or (
            settings.supabase_mcp.api_key if hasattr(settings, "supabase_mcp") else None
        )

        super().__init__(
            server_name="Supabase",
            endpoint=endpoint,
            api_key=api_key,
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=300,  # 5 minutes
        )

    @function_tool
    @redis_cache.cached("supabase_organizations", 1800)  # Cache for 30 minutes
    async def list_organizations(self, skip_cache: bool = False) -> Dict[str, Any]:
        """Lists all organizations that the user is a member of.

        Args:
            skip_cache: Whether to skip the cache and fetch fresh data

        Returns:
            Dictionary with organization information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_organizations", 
                {}, 
                skip_cache=skip_cache
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase organizations: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase organizations: {str(e)}",
                server=self.server_name,
                tool="list_organizations",
                params={},
            ) from e

    @function_tool
    async def get_organization(self, id: str) -> Dict[str, Any]:
        """Gets details for an organization. Includes subscription plan.

        Args:
            id: The organization ID

        Returns:
            Dictionary with organization details

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool("get_organization", {"id": id})
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error getting Supabase organization: {str(e)}")
            raise MCPError(
                message=f"Failed to get Supabase organization: {str(e)}",
                server=self.server_name,
                tool="get_organization",
                params={"id": id},
            ) from e

    @function_tool
    @redis_cache.cached("supabase_projects", 600)  # Cache for 10 minutes
    async def list_projects(self, skip_cache: bool = False) -> Dict[str, Any]:
        """Lists all Supabase projects for the user.

        Args:
            skip_cache: Whether to skip the cache and fetch fresh data

        Returns:
            Dictionary with project information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_projects", 
                {}, 
                skip_cache=skip_cache
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase projects: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase projects: {str(e)}",
                server=self.server_name,
                tool="list_projects",
                params={},
            ) from e

    @function_tool
    async def get_project(self, id: str) -> Dict[str, Any]:
        """Gets details for a Supabase project.

        Args:
            id: The project ID

        Returns:
            Dictionary with project details

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool("get_project", {"id": id})
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error getting Supabase project: {str(e)}")
            raise MCPError(
                message=f"Failed to get Supabase project: {str(e)}",
                server=self.server_name,
                tool="get_project",
                params={"id": id},
            ) from e

    @function_tool
    async def get_cost(
        self, 
        type: str, 
        organization_id: str
    ) -> Dict[str, Any]:
        """Gets the cost of creating a new project or branch.

        Args:
            type: The type of resource to get cost for ('project' or 'branch')
            organization_id: The organization ID

        Returns:
            Dictionary with cost information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "get_cost", 
                {"type": type, "organization_id": organization_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error getting Supabase cost: {str(e)}")
            raise MCPError(
                message=f"Failed to get Supabase cost: {str(e)}",
                server=self.server_name,
                tool="get_cost",
                params={"type": type, "organization_id": organization_id},
            ) from e

    @function_tool
    async def confirm_cost(
        self, 
        type: str, 
        recurrence: str, 
        amount: float
    ) -> Dict[str, Any]:
        """Ask the user to confirm their understanding of the cost of creating a new project or branch.

        Args:
            type: The type of resource ('project' or 'branch')
            recurrence: The recurrence of the cost ('hourly' or 'monthly')
            amount: The cost amount

        Returns:
            Dictionary with confirmation ID

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "confirm_cost", 
                {
                    "type": type, 
                    "recurrence": recurrence, 
                    "amount": amount
                }
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error confirming Supabase cost: {str(e)}")
            raise MCPError(
                message=f"Failed to confirm Supabase cost: {str(e)}",
                server=self.server_name,
                tool="confirm_cost",
                params={
                    "type": type, 
                    "recurrence": recurrence, 
                    "amount": amount
                },
            ) from e

    @function_tool
    async def create_project(
        self, 
        name: str, 
        organization_id: str, 
        confirm_cost_id: str,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new Supabase project.

        Args:
            name: The name of the project
            organization_id: The organization ID
            confirm_cost_id: The cost confirmation ID from confirm_cost
            region: The region to create the project in (optional)

        Returns:
            Dictionary with project information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "name": name, 
                "organization_id": organization_id, 
                "confirm_cost_id": confirm_cost_id
            }
            
            if region:
                params["region"] = region
                
            response = await self.call_tool("create_project", params)
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
            
            # Invalidate projects cache
            await redis_cache.invalidate_pattern("supabase_projects*")
                
            return response
        except Exception as e:
            logger.error(f"Error creating Supabase project: {str(e)}")
            raise MCPError(
                message=f"Failed to create Supabase project: {str(e)}",
                server=self.server_name,
                tool="create_project",
                params={
                    "name": name, 
                    "organization_id": organization_id, 
                    "confirm_cost_id": confirm_cost_id,
                    "region": region
                },
            ) from e

    @function_tool
    async def pause_project(self, project_id: str) -> Dict[str, Any]:
        """Pauses a Supabase project.

        Args:
            project_id: The ID of the project to pause

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "pause_project", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error pausing Supabase project: {str(e)}")
            raise MCPError(
                message=f"Failed to pause Supabase project: {str(e)}",
                server=self.server_name,
                tool="pause_project",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def restore_project(self, project_id: str) -> Dict[str, Any]:
        """Restores a Supabase project.

        Args:
            project_id: The ID of the project to restore

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "restore_project", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error restoring Supabase project: {str(e)}")
            raise MCPError(
                message=f"Failed to restore Supabase project: {str(e)}",
                server=self.server_name,
                tool="restore_project",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def list_tables(
        self, 
        project_id: str, 
        schemas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Lists all tables in one or more schemas.

        Args:
            project_id: The ID of the project
            schemas: List of schemas to include (defaults to ["public"])

        Returns:
            Dictionary with table information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {"project_id": project_id}
            
            if schemas:
                params["schemas"] = schemas
                
            response = await self.call_tool("list_tables", params)
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase tables: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase tables: {str(e)}",
                server=self.server_name,
                tool="list_tables",
                params={
                    "project_id": project_id,
                    "schemas": schemas
                },
            ) from e

    @function_tool
    async def list_extensions(self, project_id: str) -> Dict[str, Any]:
        """Lists all extensions in the database.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with extension information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_extensions", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase extensions: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase extensions: {str(e)}",
                server=self.server_name,
                tool="list_extensions",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def list_migrations(self, project_id: str) -> Dict[str, Any]:
        """Lists all migrations in the database.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with migration information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_migrations", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase migrations: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase migrations: {str(e)}",
                server=self.server_name,
                tool="list_migrations",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def apply_migration(
        self, 
        project_id: str, 
        name: str, 
        query: str
    ) -> Dict[str, Any]:
        """Applies a migration to the database.

        Args:
            project_id: The ID of the project
            name: The name of the migration in snake_case
            query: The SQL query to apply

        Returns:
            Dictionary with migration status

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "apply_migration", 
                {
                    "project_id": project_id, 
                    "name": name, 
                    "query": query
                }
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error applying Supabase migration: {str(e)}")
            raise MCPError(
                message=f"Failed to apply Supabase migration: {str(e)}",
                server=self.server_name,
                tool="apply_migration",
                params={
                    "project_id": project_id, 
                    "name": name, 
                    "query": query
                },
            ) from e

    @function_tool
    async def execute_sql(self, project_id: str, query: str) -> Dict[str, Any]:
        """Executes raw SQL in the Postgres database.

        Args:
            project_id: The ID of the project
            query: The SQL query to execute

        Returns:
            Dictionary with query results

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "execute_sql", 
                {"project_id": project_id, "query": query}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error executing SQL on Supabase: {str(e)}")
            raise MCPError(
                message=f"Failed to execute SQL on Supabase: {str(e)}",
                server=self.server_name,
                tool="execute_sql",
                params={"project_id": project_id, "query": query},
            ) from e

    @function_tool
    async def list_edge_functions(self, project_id: str) -> Dict[str, Any]:
        """Lists all Edge Functions in a Supabase project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with edge function information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_edge_functions", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase edge functions: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase edge functions: {str(e)}",
                server=self.server_name,
                tool="list_edge_functions",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def deploy_edge_function(
        self, 
        project_id: str, 
        name: str, 
        files: List[Dict[str, str]],
        entrypoint_path: str = "index.ts",
        import_map_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deploys an Edge Function to a Supabase project.

        Args:
            project_id: The ID of the project
            name: The name of the function
            files: List of file objects with name and content properties
            entrypoint_path: The entrypoint path (defaults to index.ts)
            import_map_path: Optional import map path

        Returns:
            Dictionary with deployment status

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "project_id": project_id, 
                "name": name, 
                "files": files,
                "entrypoint_path": entrypoint_path
            }
            
            if import_map_path:
                params["import_map_path"] = import_map_path
                
            response = await self.call_tool("deploy_edge_function", params)
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error deploying Supabase edge function: {str(e)}")
            raise MCPError(
                message=f"Failed to deploy Supabase edge function: {str(e)}",
                server=self.server_name,
                tool="deploy_edge_function",
                params={
                    "project_id": project_id, 
                    "name": name, 
                    "files": [{"name": f["name"], "content_length": len(f["content"])} for f in files],
                    "entrypoint_path": entrypoint_path,
                    "import_map_path": import_map_path
                },
            ) from e

    @function_tool
    async def get_logs(self, project_id: str, service: str) -> Dict[str, Any]:
        """Gets logs for a Supabase project by service type.

        Args:
            project_id: The ID of the project
            service: The service to fetch logs for (api, postgres, auth, etc.)

        Returns:
            Dictionary with logs

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "get_logs", 
                {"project_id": project_id, "service": service}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error getting Supabase logs: {str(e)}")
            raise MCPError(
                message=f"Failed to get Supabase logs: {str(e)}",
                server=self.server_name,
                tool="get_logs",
                params={"project_id": project_id, "service": service},
            ) from e

    @function_tool
    async def get_project_url(self, project_id: str) -> Dict[str, Any]:
        """Gets the API URL for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with project URL

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "get_project_url", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error getting Supabase project URL: {str(e)}")
            raise MCPError(
                message=f"Failed to get Supabase project URL: {str(e)}",
                server=self.server_name,
                tool="get_project_url",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def get_anon_key(self, project_id: str) -> Dict[str, Any]:
        """Gets the anonymous API key for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with anonymous key

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "get_anon_key", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error getting Supabase anonymous key: {str(e)}")
            raise MCPError(
                message=f"Failed to get Supabase anonymous key: {str(e)}",
                server=self.server_name,
                tool="get_anon_key",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def create_branch(
        self,
        project_id: str,
        confirm_cost_id: str,
        name: str = "develop"
    ) -> Dict[str, Any]:
        """Creates a development branch on a Supabase project.

        Args:
            project_id: The ID of the project
            confirm_cost_id: The cost confirmation ID
            name: Optional name for the branch (defaults to "develop")

        Returns:
            Dictionary with branch information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "create_branch", 
                {
                    "project_id": project_id, 
                    "confirm_cost_id": confirm_cost_id,
                    "name": name
                }
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error creating Supabase branch: {str(e)}")
            raise MCPError(
                message=f"Failed to create Supabase branch: {str(e)}",
                server=self.server_name,
                tool="create_branch",
                params={
                    "project_id": project_id, 
                    "confirm_cost_id": confirm_cost_id,
                    "name": name
                },
            ) from e

    @function_tool
    async def list_branches(self, project_id: str) -> Dict[str, Any]:
        """Lists all development branches of a Supabase project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with branch information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_branches", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error listing Supabase branches: {str(e)}")
            raise MCPError(
                message=f"Failed to list Supabase branches: {str(e)}",
                server=self.server_name,
                tool="list_branches",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def delete_branch(self, branch_id: str) -> Dict[str, Any]:
        """Deletes a development branch.

        Args:
            branch_id: The ID of the branch to delete

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "delete_branch", 
                {"branch_id": branch_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error deleting Supabase branch: {str(e)}")
            raise MCPError(
                message=f"Failed to delete Supabase branch: {str(e)}",
                server=self.server_name,
                tool="delete_branch",
                params={"branch_id": branch_id},
            ) from e

    @function_tool
    async def merge_branch(self, branch_id: str) -> Dict[str, Any]:
        """Merges a development branch to the main branch.

        Args:
            branch_id: The ID of the branch to merge

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "merge_branch", 
                {"branch_id": branch_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error merging Supabase branch: {str(e)}")
            raise MCPError(
                message=f"Failed to merge Supabase branch: {str(e)}",
                server=self.server_name,
                tool="merge_branch",
                params={"branch_id": branch_id},
            ) from e

    @function_tool
    async def reset_branch(
        self, 
        branch_id: str,
        migration_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resets migrations of a development branch.

        Args:
            branch_id: The ID of the branch to reset
            migration_version: Optional migration version to reset to

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {"branch_id": branch_id}
            
            if migration_version:
                params["migration_version"] = migration_version
                
            response = await self.call_tool("reset_branch", params)
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error resetting Supabase branch: {str(e)}")
            raise MCPError(
                message=f"Failed to reset Supabase branch: {str(e)}",
                server=self.server_name,
                tool="reset_branch",
                params={
                    "branch_id": branch_id,
                    "migration_version": migration_version
                },
            ) from e

    @function_tool
    async def rebase_branch(self, branch_id: str) -> Dict[str, Any]:
        """Rebases a development branch on the main branch.

        Args:
            branch_id: The ID of the branch to rebase

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "rebase_branch", 
                {"branch_id": branch_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error rebasing Supabase branch: {str(e)}")
            raise MCPError(
                message=f"Failed to rebase Supabase branch: {str(e)}",
                server=self.server_name,
                tool="rebase_branch",
                params={"branch_id": branch_id},
            ) from e

    @function_tool
    async def generate_typescript_types(self, project_id: str) -> Dict[str, Any]:
        """Generates TypeScript types for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with TypeScript types

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "generate_typescript_types", 
                {"project_id": project_id}
            )
            
            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)
                
            return response
        except Exception as e:
            logger.error(f"Error generating TypeScript types: {str(e)}")
            raise MCPError(
                message=f"Failed to generate TypeScript types: {str(e)}",
                server=self.server_name,
                tool="generate_typescript_types",
                params={"project_id": project_id},
            ) from e


class SupabaseService:
    """High-level service for Supabase database operations in TripSage."""

    def __init__(self, client: Optional[SupabaseMCPClient] = None):
        """Initialize the Supabase Service.

        Args:
            client: SupabaseMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or supabase_client
        logger.info("Initialized Supabase Service")

    async def get_default_project(self) -> Dict[str, Any]:
        """Get the default Supabase project ID, creating one if needed.

        Returns:
            Dictionary with project information
        """
        try:
            # Check for default project ID in settings
            if settings.supabase_mcp.default_project_id:
                project_id = settings.supabase_mcp.default_project_id
                project = await self.client.get_project(project_id)
                return project
            
            # List projects and use the first one
            projects = await self.client.list_projects()
            if projects.get("projects") and len(projects["projects"]) > 0:
                return projects["projects"][0]
            
            # No projects found, need to create one
            # First, list organizations
            orgs = await self.client.list_organizations()
            if not orgs.get("organizations") or len(orgs["organizations"]) == 0:
                return {"error": "No organizations found to create project"}
            
            org_id = orgs["organizations"][0]["id"]
            
            # Get cost information
            cost_info = await self.client.get_cost("project", org_id)
            
            # Confirm cost
            confirmation = await self.client.confirm_cost(
                "project", 
                cost_info.get("recurrence", "monthly"), 
                cost_info.get("amount", 0)
            )
            
            # Create project
            project = await self.client.create_project(
                "tripsage-production",
                org_id,
                confirmation.get("id")
            )
            
            return project
        except Exception as e:
            logger.error(f"Error getting default project: {str(e)}")
            return {"error": f"Failed to get default project: {str(e)}"}

    async def apply_migrations(
        self, 
        project_id: str,
        migrations: List[str],
        migration_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Apply migrations to a Supabase project.

        Args:
            project_id: The ID of the project
            migrations: List of SQL migration statements
            migration_names: Optional list of migration names (generated if not provided)

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
            for i, (migration, name) in enumerate(zip(migrations, migration_names)):
                result = await self.client.apply_migration(
                    project_id, 
                    name, 
                    migration
                )
                results.append(result)
            
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
        self, 
        project_id: Optional[str] = None, 
        branch_name: str = "develop"
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
                if settings.supabase_mcp.default_project_id:
                    project_id = settings.supabase_mcp.default_project_id
                else:
                    default_project = await self.get_default_project()
                    if "error" in default_project:
                        return default_project
                    project_id = default_project.get("id")
            
            # Get cost information
            orgs = await self.client.list_organizations()
            if not orgs.get("organizations") or len(orgs["organizations"]) == 0:
                return {"error": "No organizations found to get cost information"}
            
            org_id = orgs["organizations"][0]["id"]
            
            cost_info = await self.client.get_cost("branch", org_id)
            
            # Confirm cost
            confirmation = await self.client.confirm_cost(
                "branch", 
                cost_info.get("recurrence", "hourly"), 
                cost_info.get("amount", 0)
            )
            
            # Create branch
            branch = await self.client.create_branch(
                project_id,
                confirmation.get("id"),
                branch_name
            )
            
            return branch
        except Exception as e:
            logger.error(f"Error creating development branch: {str(e)}")
            return {
                "error": f"Failed to create development branch: {str(e)}",
                "project_id": project_id,
                "branch_name": branch_name,
            }


# Initialize global client instance
supabase_client = SupabaseMCPClient()


def get_client() -> SupabaseMCPClient:
    """Get a Supabase MCP Client instance.

    Returns:
        SupabaseMCPClient instance
    """
    return supabase_client


def get_service() -> SupabaseService:
    """Get a Supabase Service instance.

    Returns:
        SupabaseService instance
    """
    return SupabaseService(supabase_client)