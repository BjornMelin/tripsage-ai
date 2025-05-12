"""
Neon DB MCP Client implementation for TripSage.

This module provides a client for interacting with the Neon DB MCP Server,
which offers PostgreSQL database management focused on development environments.
"""

import json
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import ValidationError

from agents import function_tool

from ...cache.redis_cache import redis_cache
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..fastmcp import FastMCPClient
from .models import (
    # Base models
    BaseParams,
    BaseResponse,
    # Branch models
    BranchResponse,
    # Connection string models
    ConnectionStringParams,
    ConnectionStringResponse,
    CreateBranchParams,
    # Project models
    CreateProjectParams,
    DeleteBranchParams,
    DeleteProjectParams,
    DescribeBranchParams,
    DescribeProjectParams,
    # Table models
    DescribeTableSchemaParams,
    DescribeTableSchemaResponse,
    GetDatabaseTablesParams,
    GetDatabaseTablesResponse,
    ListProjectsParams,
    ProjectListResponse,
    ProjectResponse,
    # SQL models
    RunSQLParams,
    RunSQLTransactionParams,
    SQLResponse,
)

logger = get_module_logger(__name__)

P = TypeVar("P", bound=BaseParams)
R = TypeVar("R", bound=BaseResponse)


class NeonMCPClient(FastMCPClient, Generic[P, R]):
    """Client for the Neon MCP Server focused on development environments."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        use_cache: bool = True,
    ):
        """Initialize the Neon MCP Client.

        Args:
            endpoint: MCP server endpoint URL (defaults to config value)
            api_key: API key for authentication (defaults to config value)
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
        """
        if endpoint is None:
            endpoint = (
                settings.neon_mcp.endpoint
                if hasattr(settings, "neon_mcp")
                else "http://localhost:8099"
            )

        api_key = api_key or (
            settings.neon_mcp.api_key if hasattr(settings, "neon_mcp") else None
        )

        super().__init__(
            server_name="Neon",
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
            params: Parameters for the tool call (Pydantic model)
            response_model: Pydantic model for validating the response
            skip_cache: Whether to skip the cache
            cache_key: Optional cache key
            cache_ttl: Optional cache TTL

        Returns:
            Validated response

        Raises:
            MCPError: If the request fails
        """
        try:
            # Convert parameters to dict
            params_dict = params.model_dump(by_alias=True)

            # Call the tool
            response = await self.call_tool(
                tool_name,
                {"params": params_dict},
                skip_cache=skip_cache,
                cache_key=cache_key,
                cache_ttl=cache_ttl,
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            try:
                # Attempt strict validation
                validated_response = response_model.model_validate(response)
            except ValidationError:
                # Fallback to non-strict validation if strict fails
                try:
                    validated_response = response_model.model_validate(
                        response, strict=False
                    )
                    logger.warning(
                        f"Non-strict validation used for {tool_name} response"
                    )
                except ValidationError as e:
                    logger.error(f"Validation error in {tool_name} response: {str(e)}")
                    raise MCPError(
                        message=f"Invalid response from {tool_name}: {str(e)}",
                        server=self.server_name,
                        tool=tool_name,
                        params=params_dict,
                    ) from e

            return validated_response
        except Exception as e:
            if not isinstance(e, MCPError):
                logger.error(f"Error calling {tool_name}: {str(e)}")
                raise MCPError(
                    message=f"Failed to call {tool_name}: {str(e)}",
                    server=self.server_name,
                    tool=tool_name,
                    params=params.model_dump()
                    if hasattr(params, "model_dump")
                    else params,
                ) from e
            raise

    # Project Operations

    @function_tool
    @redis_cache.cached("neon_projects", 600)  # Cache for 10 minutes
    async def list_projects(self, skip_cache: bool = False) -> ProjectListResponse:
        """List all Neon projects in your account.

        Args:
            skip_cache: Whether to skip the cache and fetch fresh data

        Returns:
            ProjectListResponse with project information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = ListProjectsParams()
            return await self._call_validate_tool(
                "list_projects", params, ProjectListResponse, skip_cache=skip_cache
            )
        except Exception as e:
            logger.error(f"Error listing Neon projects: {str(e)}")
            raise MCPError(
                message=f"Failed to list Neon projects: {str(e)}",
                server=self.server_name,
                tool="list_projects",
                params={},
            ) from e

    @function_tool
    async def create_project(self, name: Optional[str] = None) -> ProjectResponse:
        """Create a new Neon project.

        Args:
            name: Optional name for the project

        Returns:
            ProjectResponse with newly created project information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = CreateProjectParams(name=name)

            response = await self._call_validate_tool(
                "create_project", params, ProjectResponse
            )

            # Invalidate the projects cache
            await redis_cache.invalidate_pattern("neon_projects*")

            return response
        except Exception as e:
            logger.error(f"Error creating Neon project: {str(e)}")
            raise MCPError(
                message=f"Failed to create Neon project: {str(e)}",
                server=self.server_name,
                tool="create_project",
                params={"name": name},
            ) from e

    @function_tool
    async def describe_project(self, project_id: str) -> ProjectResponse:
        """Get details for a specific Neon project.

        Args:
            project_id: The ID of the project to describe

        Returns:
            ProjectResponse with project details

        Raises:
            MCPError: If the request fails
        """
        try:
            params = DescribeProjectParams(project_id=project_id)
            return await self._call_validate_tool(
                "describe_project", params, ProjectResponse
            )
        except Exception as e:
            logger.error(f"Error describing Neon project: {str(e)}")
            raise MCPError(
                message=f"Failed to describe Neon project: {str(e)}",
                server=self.server_name,
                tool="describe_project",
                params={"project_id": project_id},
            ) from e

    @function_tool
    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a Neon project.

        Args:
            project_id: The ID of the project to delete

        Returns:
            Dictionary with deletion status

        Raises:
            MCPError: If the request fails
        """
        try:
            _params = DeleteProjectParams(project_id=project_id)

            response = await self.call_tool(
                "delete_project", {"params": {"projectId": project_id}}
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            # Invalidate the projects cache
            await redis_cache.invalidate_pattern("neon_projects*")

            return response
        except Exception as e:
            logger.error(f"Error deleting Neon project: {str(e)}")
            raise MCPError(
                message=f"Failed to delete Neon project: {str(e)}",
                server=self.server_name,
                tool="delete_project",
                params={"project_id": project_id},
            ) from e

    # SQL Operations

    @function_tool
    async def run_sql(
        self,
        project_id: str,
        sql: str,
        database_name: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> SQLResponse:
        """Execute a SQL statement against a Neon database.

        Args:
            project_id: The ID of the project
            sql: The SQL query to execute
            database_name: Optional database name (defaults to neondb)
            branch_id: Optional branch ID (defaults to main branch)

        Returns:
            SQLResponse with query results

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters with Pydantic model
            params = RunSQLParams(
                project_id=project_id,
                sql=sql,
                database_name=database_name,
                branch_id=branch_id,
            )

            return await self._call_validate_tool("run_sql", params, SQLResponse)
        except ValueError as e:
            # Handle validation errors specifically
            logger.error(f"Validation error in run_sql parameters: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for SQL execution: {str(e)}",
                server=self.server_name,
                tool="run_sql",
                params={
                    "project_id": project_id,
                    "sql": sql,
                    "database_name": database_name,
                    "branch_id": branch_id,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error executing SQL on Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to execute SQL on Neon: {str(e)}",
                server=self.server_name,
                tool="run_sql",
                params={
                    "project_id": project_id,
                    "sql": sql,
                    "database_name": database_name,
                    "branch_id": branch_id,
                },
            ) from e

    @function_tool
    async def run_sql_transaction(
        self,
        project_id: str,
        sql_statements: List[str],
        database_name: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> SQLResponse:
        """Execute a SQL transaction against a Neon database.

        Args:
            project_id: The ID of the project
            sql_statements: List of SQL statements to execute
            database_name: Optional database name (defaults to neondb)
            branch_id: Optional branch ID (defaults to main branch)

        Returns:
            SQLResponse with transaction results

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters with Pydantic model
            params = RunSQLTransactionParams(
                project_id=project_id,
                sql_statements=sql_statements,
                database_name=database_name,
                branch_id=branch_id,
            )

            return await self._call_validate_tool(
                "run_sql_transaction", params, SQLResponse
            )
        except ValueError as e:
            # Handle validation errors specifically
            logger.error(
                f"Validation error in run_sql_transaction parameters: {str(e)}"
            )
            raise MCPError(
                message=f"Invalid parameters for SQL transaction: {str(e)}",
                server=self.server_name,
                tool="run_sql_transaction",
                params={
                    "project_id": project_id,
                    "sql_statements": sql_statements,
                    "database_name": database_name,
                    "branch_id": branch_id,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error executing SQL transaction on Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to execute SQL transaction on Neon: {str(e)}",
                server=self.server_name,
                tool="run_sql_transaction",
                params={
                    "project_id": project_id,
                    "sql_statements": sql_statements,
                    "database_name": database_name,
                    "branch_id": branch_id,
                },
            ) from e

    # Branch Operations

    @function_tool
    async def create_branch(
        self, project_id: str, branch_name: Optional[str] = None
    ) -> BranchResponse:
        """Create a new branch in a Neon project.

        Args:
            project_id: The ID of the project
            branch_name: Optional name for the branch

        Returns:
            BranchResponse with branch information

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters with Pydantic model
            params = CreateBranchParams(project_id=project_id, branch_name=branch_name)

            return await self._call_validate_tool(
                "create_branch", params, BranchResponse
            )
        except ValueError as e:
            # Handle validation errors specifically
            logger.error(f"Validation error in create_branch parameters: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for branch creation: {str(e)}",
                server=self.server_name,
                tool="create_branch",
                params={"project_id": project_id, "branch_name": branch_name},
            ) from e
        except Exception as e:
            logger.error(f"Error creating branch in Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to create branch in Neon: {str(e)}",
                server=self.server_name,
                tool="create_branch",
                params={"project_id": project_id, "branch_name": branch_name},
            ) from e

    @function_tool
    async def describe_branch(
        self, project_id: str, branch_id: str, database_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get a tree view of objects in a branch.

        Args:
            project_id: The ID of the project
            branch_id: The ID of the branch
            database_name: Optional database name

        Returns:
            Dictionary with branch objects

        Raises:
            MCPError: If the request fails
        """
        try:
            params = DescribeBranchParams(
                project_id=project_id, branch_id=branch_id, database_name=database_name
            )

            response = await self.call_tool(
                "describe_branch", {"params": params.model_dump(by_alias=True)}
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
        except Exception as e:
            logger.error(f"Error describing branch in Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to describe branch in Neon: {str(e)}",
                server=self.server_name,
                tool="describe_branch",
                params={
                    "project_id": project_id,
                    "branch_id": branch_id,
                    "database_name": database_name,
                },
            ) from e

    @function_tool
    async def delete_branch(self, project_id: str, branch_id: str) -> Dict[str, Any]:
        """Delete a branch from a Neon project.

        Args:
            project_id: The ID of the project
            branch_id: The ID of the branch to delete

        Returns:
            Dictionary with deletion status

        Raises:
            MCPError: If the request fails
        """
        try:
            params = DeleteBranchParams(project_id=project_id, branch_id=branch_id)

            response = await self.call_tool(
                "delete_branch",
                {"params": params.model_dump(by_alias=True)},
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
        except Exception as e:
            logger.error(f"Error deleting branch in Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to delete branch in Neon: {str(e)}",
                server=self.server_name,
                tool="delete_branch",
                params={"project_id": project_id, "branch_id": branch_id},
            ) from e

    # Connection Operations

    @function_tool
    async def get_connection_string(
        self,
        project_id: str,
        branch_id: Optional[str] = None,
        database_name: Optional[str] = None,
        role_name: Optional[str] = None,
        compute_id: Optional[str] = None,
    ) -> ConnectionStringResponse:
        """Get a PostgreSQL connection string for a Neon database.

        Args:
            project_id: The ID of the project
            branch_id: Optional branch ID
            database_name: Optional database name
            role_name: Optional role name
            compute_id: Optional compute ID

        Returns:
            ConnectionStringResponse with connection string

        Raises:
            MCPError: If the request fails
        """
        try:
            # Validate parameters with Pydantic model
            params = ConnectionStringParams(
                project_id=project_id,
                branch_id=branch_id,
                database_name=database_name,
                role_name=role_name,
                compute_id=compute_id,
            )

            return await self._call_validate_tool(
                "get_connection_string", params, ConnectionStringResponse
            )
        except ValueError as e:
            # Handle validation errors specifically
            logger.error(
                f"Validation error in get_connection_string parameters: {str(e)}"
            )
            raise MCPError(
                message=f"Invalid parameters for connection string retrieval: {str(e)}",
                server=self.server_name,
                tool="get_connection_string",
                params={
                    "project_id": project_id,
                    "branch_id": branch_id,
                    "database_name": database_name,
                    "role_name": role_name,
                    "compute_id": compute_id,
                },
            ) from e
        except Exception as e:
            logger.error(f"Error getting connection string from Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to get connection string from Neon: {str(e)}",
                server=self.server_name,
                tool="get_connection_string",
                params={
                    "project_id": project_id,
                    "branch_id": branch_id,
                    "database_name": database_name,
                    "role_name": role_name,
                    "compute_id": compute_id,
                },
            ) from e

    # Database Schema Operations

    @function_tool
    async def get_database_tables(
        self,
        project_id: str,
        branch_id: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> GetDatabaseTablesResponse:
        """Get all tables in a Neon database.

        Args:
            project_id: The ID of the project
            branch_id: Optional branch ID
            database_name: Optional database name

        Returns:
            GetDatabaseTablesResponse with table information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = GetDatabaseTablesParams(
                project_id=project_id, branch_id=branch_id, database_name=database_name
            )

            return await self._call_validate_tool(
                "get_database_tables", params, GetDatabaseTablesResponse
            )
        except Exception as e:
            logger.error(f"Error getting database tables from Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to get database tables from Neon: {str(e)}",
                server=self.server_name,
                tool="get_database_tables",
                params={
                    "project_id": project_id,
                    "branch_id": branch_id,
                    "database_name": database_name,
                },
            ) from e

    @function_tool
    async def describe_table_schema(
        self,
        project_id: str,
        table_name: str,
        branch_id: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> DescribeTableSchemaResponse:
        """Describe the schema of a table in a Neon database.

        Args:
            project_id: The ID of the project
            table_name: The name of the table
            branch_id: Optional branch ID
            database_name: Optional database name

        Returns:
            DescribeTableSchemaResponse with table schema

        Raises:
            MCPError: If the request fails
        """
        try:
            params = DescribeTableSchemaParams(
                project_id=project_id,
                table_name=table_name,
                branch_id=branch_id,
                database_name=database_name,
            )

            return await self._call_validate_tool(
                "describe_table_schema", params, DescribeTableSchemaResponse
            )
        except Exception as e:
            logger.error(f"Error describing table schema in Neon: {str(e)}")
            raise MCPError(
                message=f"Failed to describe table schema in Neon: {str(e)}",
                server=self.server_name,
                tool="describe_table_schema",
                params={
                    "project_id": project_id,
                    "table_name": table_name,
                    "branch_id": branch_id,
                    "database_name": database_name,
                },
            ) from e


# Initialize global client instance
neon_client = NeonMCPClient()


def get_client() -> NeonMCPClient:
    """Get a Neon MCP Client instance.

    Returns:
        NeonMCPClient instance
    """
    return neon_client
