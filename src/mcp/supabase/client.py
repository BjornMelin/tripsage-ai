"""
Supabase MCP Client implementation for TripSage.

This module provides a client for interacting with the Supabase MCP Server,
which offers PostgreSQL database management focused on production environments.
"""

import json
from typing import Generic, List, Optional, TypeVar

from pydantic import ValidationError

from agents import function_tool

from ...cache.redis_cache import redis_cache
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..fastmcp import FastMCPClient
from .models import (
    ApplyMigrationParams,
    ApplyMigrationResponse,
    # Base models
    BaseParams,
    BaseResponse,
    ConfirmCostParams,
    ConfirmCostResponse,
    # Branch models
    CreateBranchParams,
    CreateBranchResponse,
    CreateProjectParams,
    CreateProjectResponse,
    DeleteBranchParams,
    DeleteBranchResponse,
    DeployEdgeFunctionParams,
    DeployEdgeFunctionResponse,
    ExecuteSQLParams,
    ExecuteSQLResponse,
    FileObject,
    GenerateTypescriptTypesParams,
    GenerateTypescriptTypesResponse,
    GetAnonKeyParams,
    GetAnonKeyResponse,
    GetCostParams,
    GetCostResponse,
    GetLogsParams,
    GetLogsResponse,
    GetOrganizationParams,
    GetOrganizationResponse,
    GetProjectParams,
    GetProjectResponse,
    GetProjectUrlParams,
    GetProjectUrlResponse,
    ListBranchesParams,
    ListBranchesResponse,
    ListEdgeFunctionsParams,
    ListEdgeFunctionsResponse,
    ListExtensionsParams,
    ListExtensionsResponse,
    ListMigrationsParams,
    ListMigrationsResponse,
    # Organization models
    ListOrganizationsParams,
    ListOrganizationsResponse,
    # Project models
    ListProjectsParams,
    ListProjectsResponse,
    # Database models
    ListTablesParams,
    ListTablesResponse,
    MergeBranchParams,
    MergeBranchResponse,
    PauseProjectParams,
    PauseProjectResponse,
    RebaseBranchParams,
    RebaseBranchResponse,
    ResetBranchParams,
    ResetBranchResponse,
    RestoreProjectParams,
    RestoreProjectResponse,
)

logger = get_module_logger(__name__)

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResponse)


class SupabaseMCPClient(FastMCPClient, Generic[P, R]):
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

    async def _call_validate_tool(
        self,
        tool_name: str,
        params: P,
        response_model: type[R],
        skip_cache: bool = False,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> R:
        """Call a tool and validate both parameters and response.

        Args:
            tool_name: Name of the tool to call
            params: Validated parameters model
            response_model: Response model class for validation
            skip_cache: Whether to skip the cache
            cache_key: Optional cache key
            cache_ttl: Optional cache TTL in seconds

        Returns:
            Validated response model

        Raises:
            MCPError: If request fails
            ValidationError: If response validation fails
        """
        try:
            # Convert params to dict for the tool call
            params_dict = params.model_dump(exclude_none=True)

            response = await self.call_tool(
                tool_name,
                params_dict,
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            # Validate response with the provided model
            try:
                validated_response = response_model.model_validate(response)
                return validated_response
            except ValidationError as e:
                logger.warning(f"Response validation error for {tool_name}: {str(e)}")
                # If validation fails, return original response as fallback
                return response_model.model_validate(response, strict=False)

        except ValidationError as e:
            logger.error(f"Validation error in {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Validation error in {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params.model_dump() if params else {},
            ) from e
        except Exception as e:
            logger.error(f"Error in {tool_name}: {str(e)}")
            raise MCPError(
                message=f"Failed to execute {tool_name}: {str(e)}",
                server=self.server_name,
                tool=tool_name,
                params=params.model_dump() if params else {},
            ) from e

    # =====================
    # Organization Methods
    # =====================

    @function_tool
    @redis_cache.cached("supabase_organizations", 1800)  # Cache for 30 minutes
    async def list_organizations(
        self, skip_cache: bool = False
    ) -> ListOrganizationsResponse:
        """Lists all organizations that the user is a member of.

        Args:
            skip_cache: Whether to skip the cache and fetch fresh data

        Returns:
            Dictionary with organization information

        Raises:
            MCPError: If the request fails
        """
        params = ListOrganizationsParams()
        return await self._call_validate_tool(
            "list_organizations",
            params,
            ListOrganizationsResponse,
            skip_cache=skip_cache,
        )

    @function_tool
    async def get_organization(self, id: str) -> GetOrganizationResponse:
        """Gets details for an organization. Includes subscription plan.

        Args:
            id: The organization ID

        Returns:
            Dictionary with organization details

        Raises:
            MCPError: If the request fails
        """
        params = GetOrganizationParams(id=id)
        return await self._call_validate_tool(
            "get_organization",
            params,
            GetOrganizationResponse,
        )

    @function_tool
    async def get_cost(self, type: str, organization_id: str) -> GetCostResponse:
        """Gets the cost of creating a new project or branch.

        Args:
            type: The type of resource to get cost for ('project' or 'branch')
            organization_id: The organization ID

        Returns:
            Dictionary with cost information

        Raises:
            MCPError: If the request fails
        """
        params = GetCostParams(type=type, organization_id=organization_id)
        return await self._call_validate_tool(
            "get_cost",
            params,
            GetCostResponse,
        )

    @function_tool
    async def confirm_cost(
        self, type: str, recurrence: str, amount: float
    ) -> ConfirmCostResponse:
        """Ask the user to confirm their understanding of the cost of
        creating a new project or branch.

        Args:
            type: The type of resource ('project' or 'branch')
            recurrence: The recurrence of the cost ('hourly' or 'monthly')
            amount: The cost amount

        Returns:
            Dictionary with confirmation ID

        Raises:
            MCPError: If the request fails
        """
        params = ConfirmCostParams(
            type=type,
            recurrence=recurrence,
            amount=amount,
        )
        return await self._call_validate_tool(
            "confirm_cost",
            params,
            ConfirmCostResponse,
        )

    # =====================
    # Project Methods
    # =====================

    @function_tool
    @redis_cache.cached("supabase_projects", 600)  # Cache for 10 minutes
    async def list_projects(self, skip_cache: bool = False) -> ListProjectsResponse:
        """Lists all Supabase projects for the user.

        Args:
            skip_cache: Whether to skip the cache and fetch fresh data

        Returns:
            Dictionary with project information

        Raises:
            MCPError: If the request fails
        """
        params = ListProjectsParams()
        return await self._call_validate_tool(
            "list_projects",
            params,
            ListProjectsResponse,
            skip_cache=skip_cache,
        )

    @function_tool
    async def get_project(self, id: str) -> GetProjectResponse:
        """Gets details for a Supabase project.

        Args:
            id: The project ID

        Returns:
            Dictionary with project details

        Raises:
            MCPError: If the request fails
        """
        params = GetProjectParams(id=id)
        return await self._call_validate_tool(
            "get_project",
            params,
            GetProjectResponse,
        )

    @function_tool
    async def create_project(
        self,
        name: str,
        organization_id: str,
        confirm_cost_id: str,
        region: Optional[str] = None,
    ) -> CreateProjectResponse:
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
        params = CreateProjectParams(
            name=name,
            organization_id=organization_id,
            confirm_cost_id=confirm_cost_id,
            region=region,
        )

        result = await self._call_validate_tool(
            "create_project",
            params,
            CreateProjectResponse,
        )

        # Invalidate projects cache
        await redis_cache.invalidate_pattern("supabase_projects*")

        return result

    @function_tool
    async def pause_project(self, project_id: str) -> PauseProjectResponse:
        """Pauses a Supabase project.

        Args:
            project_id: The ID of the project to pause

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        params = PauseProjectParams(project_id=project_id)
        return await self._call_validate_tool(
            "pause_project",
            params,
            PauseProjectResponse,
        )

    @function_tool
    async def restore_project(self, project_id: str) -> RestoreProjectResponse:
        """Restores a Supabase project.

        Args:
            project_id: The ID of the project to restore

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        params = RestoreProjectParams(project_id=project_id)
        return await self._call_validate_tool(
            "restore_project",
            params,
            RestoreProjectResponse,
        )

    @function_tool
    async def get_project_url(self, project_id: str) -> GetProjectUrlResponse:
        """Gets the API URL for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with project URL

        Raises:
            MCPError: If the request fails
        """
        params = GetProjectUrlParams(project_id=project_id)
        return await self._call_validate_tool(
            "get_project_url",
            params,
            GetProjectUrlResponse,
        )

    @function_tool
    async def get_anon_key(self, project_id: str) -> GetAnonKeyResponse:
        """Gets the anonymous API key for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with anonymous key

        Raises:
            MCPError: If the request fails
        """
        params = GetAnonKeyParams(project_id=project_id)
        return await self._call_validate_tool(
            "get_anon_key",
            params,
            GetAnonKeyResponse,
        )

    @function_tool
    async def generate_typescript_types(
        self, project_id: str
    ) -> GenerateTypescriptTypesResponse:
        """Generates TypeScript types for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with TypeScript types

        Raises:
            MCPError: If the request fails
        """
        params = GenerateTypescriptTypesParams(project_id=project_id)
        return await self._call_validate_tool(
            "generate_typescript_types",
            params,
            GenerateTypescriptTypesResponse,
        )

    # =====================
    # Database Methods
    # =====================

    @function_tool
    async def list_tables(
        self, project_id: str, schemas: Optional[List[str]] = None
    ) -> ListTablesResponse:
        """Lists all tables in one or more schemas.

        Args:
            project_id: The ID of the project
            schemas: List of schemas to include (defaults to ["public"])

        Returns:
            Dictionary with table information

        Raises:
            MCPError: If the request fails
        """
        params = ListTablesParams(project_id=project_id, schemas=schemas)
        return await self._call_validate_tool(
            "list_tables",
            params,
            ListTablesResponse,
        )

    @function_tool
    async def list_extensions(self, project_id: str) -> ListExtensionsResponse:
        """Lists all extensions in the database.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with extension information

        Raises:
            MCPError: If the request fails
        """
        params = ListExtensionsParams(project_id=project_id)
        return await self._call_validate_tool(
            "list_extensions",
            params,
            ListExtensionsResponse,
        )

    @function_tool
    async def list_migrations(self, project_id: str) -> ListMigrationsResponse:
        """Lists all migrations in the database.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with migration information

        Raises:
            MCPError: If the request fails
        """
        params = ListMigrationsParams(project_id=project_id)
        return await self._call_validate_tool(
            "list_migrations",
            params,
            ListMigrationsResponse,
        )

    @function_tool
    async def apply_migration(
        self, project_id: str, name: str, query: str
    ) -> ApplyMigrationResponse:
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
        params = ApplyMigrationParams(
            project_id=project_id,
            name=name,
            query=query,
        )
        return await self._call_validate_tool(
            "apply_migration",
            params,
            ApplyMigrationResponse,
        )

    @function_tool
    async def execute_sql(self, project_id: str, query: str) -> ExecuteSQLResponse:
        """Executes raw SQL in the Postgres database.

        Args:
            project_id: The ID of the project
            query: The SQL query to execute

        Returns:
            Dictionary with query results

        Raises:
            MCPError: If the request fails
        """
        params = ExecuteSQLParams(project_id=project_id, query=query)
        return await self._call_validate_tool(
            "execute_sql",
            params,
            ExecuteSQLResponse,
        )

    @function_tool
    async def list_edge_functions(self, project_id: str) -> ListEdgeFunctionsResponse:
        """Lists all Edge Functions in a Supabase project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with edge function information

        Raises:
            MCPError: If the request fails
        """
        params = ListEdgeFunctionsParams(project_id=project_id)
        return await self._call_validate_tool(
            "list_edge_functions",
            params,
            ListEdgeFunctionsResponse,
        )

    @function_tool
    async def deploy_edge_function(
        self,
        project_id: str,
        name: str,
        files: List[dict],
        entrypoint_path: str = "index.ts",
        import_map_path: Optional[str] = None,
    ) -> DeployEdgeFunctionResponse:
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
        # Convert dict files to FileObject models
        file_objects = [FileObject(**file) for file in files]

        params = DeployEdgeFunctionParams(
            project_id=project_id,
            name=name,
            files=file_objects,
            entrypoint_path=entrypoint_path,
            import_map_path=import_map_path,
        )
        return await self._call_validate_tool(
            "deploy_edge_function",
            params,
            DeployEdgeFunctionResponse,
        )

    @function_tool
    async def get_logs(self, project_id: str, service: str) -> GetLogsResponse:
        """Gets logs for a Supabase project by service type.

        Args:
            project_id: The ID of the project
            service: The service to fetch logs for (api, postgres, auth, etc.)

        Returns:
            Dictionary with logs

        Raises:
            MCPError: If the request fails
        """
        params = GetLogsParams(project_id=project_id, service=service)
        return await self._call_validate_tool(
            "get_logs",
            params,
            GetLogsResponse,
        )

    # =====================
    # Branch Methods
    # =====================

    @function_tool
    async def create_branch(
        self, project_id: str, confirm_cost_id: str, name: str = "develop"
    ) -> CreateBranchResponse:
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
        params = CreateBranchParams(
            project_id=project_id,
            confirm_cost_id=confirm_cost_id,
            name=name,
        )
        return await self._call_validate_tool(
            "create_branch",
            params,
            CreateBranchResponse,
        )

    @function_tool
    async def list_branches(self, project_id: str) -> ListBranchesResponse:
        """Lists all development branches of a Supabase project.

        Args:
            project_id: The ID of the project

        Returns:
            Dictionary with branch information

        Raises:
            MCPError: If the request fails
        """
        params = ListBranchesParams(project_id=project_id)
        return await self._call_validate_tool(
            "list_branches",
            params,
            ListBranchesResponse,
        )

    @function_tool
    async def delete_branch(self, branch_id: str) -> DeleteBranchResponse:
        """Deletes a development branch.

        Args:
            branch_id: The ID of the branch to delete

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        params = DeleteBranchParams(branch_id=branch_id)
        return await self._call_validate_tool(
            "delete_branch",
            params,
            DeleteBranchResponse,
        )

    @function_tool
    async def merge_branch(self, branch_id: str) -> MergeBranchResponse:
        """Merges a development branch to the main branch.

        Args:
            branch_id: The ID of the branch to merge

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        params = MergeBranchParams(branch_id=branch_id)
        return await self._call_validate_tool(
            "merge_branch",
            params,
            MergeBranchResponse,
        )

    @function_tool
    async def reset_branch(
        self, branch_id: str, migration_version: Optional[str] = None
    ) -> ResetBranchResponse:
        """Resets migrations of a development branch.

        Args:
            branch_id: The ID of the branch to reset
            migration_version: Optional migration version to reset to

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        params = ResetBranchParams(
            branch_id=branch_id,
            migration_version=migration_version,
        )
        return await self._call_validate_tool(
            "reset_branch",
            params,
            ResetBranchResponse,
        )

    @function_tool
    async def rebase_branch(self, branch_id: str) -> RebaseBranchResponse:
        """Rebases a development branch on the main branch.

        Args:
            branch_id: The ID of the branch to rebase

        Returns:
            Dictionary with operation status

        Raises:
            MCPError: If the request fails
        """
        params = RebaseBranchParams(branch_id=branch_id)
        return await self._call_validate_tool(
            "rebase_branch",
            params,
            RebaseBranchResponse,
        )


# Initialize global client instance
supabase_client = SupabaseMCPClient()


def get_client() -> SupabaseMCPClient:
    """Get a Supabase MCP Client instance.

    Returns:
        SupabaseMCPClient instance
    """
    return supabase_client
