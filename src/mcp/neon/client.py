"""
Neon DB MCP Client implementation for TripSage.

This module provides a client for interacting with the Neon DB MCP Server,
which offers PostgreSQL database management focused on development environments.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from agents import function_tool

from ...cache.redis_cache import redis_cache
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ...utils.settings import settings
from ..fastmcp import FastMCPClient

logger = get_module_logger(__name__)


class NeonMCPClient(FastMCPClient):
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

    @function_tool
    @redis_cache.cached("neon_projects", 600)  # Cache for 10 minutes
    async def list_projects(self, skip_cache: bool = False) -> Dict[str, Any]:
        """List all Neon projects in your account.

        Args:
            skip_cache: Whether to skip the cache and fetch fresh data

        Returns:
            Dictionary with project information

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "list_projects", {"params": {}}, skip_cache=skip_cache
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
        except Exception as e:
            logger.error(f"Error listing Neon projects: {str(e)}")
            raise MCPError(
                message=f"Failed to list Neon projects: {str(e)}",
                server=self.server_name,
                tool="list_projects",
                params={},
            ) from e

    @function_tool
    async def create_project(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Neon project.

        Args:
            name: Optional name for the project

        Returns:
            Dictionary with project information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {"params": {}}
            if name:
                params["params"]["name"] = name

            response = await self.call_tool("create_project", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

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
    async def describe_project(self, project_id: str) -> Dict[str, Any]:
        """Get details for a specific Neon project.

        Args:
            project_id: The ID of the project to describe

        Returns:
            Dictionary with project details

        Raises:
            MCPError: If the request fails
        """
        try:
            response = await self.call_tool(
                "describe_project", {"params": {"projectId": project_id}}
            )

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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

    @function_tool
    async def run_sql(
        self,
        project_id: str,
        sql: str,
        database_name: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a SQL statement against a Neon database.

        Args:
            project_id: The ID of the project
            sql: The SQL query to execute
            database_name: Optional database name (defaults to neondb)
            branch_id: Optional branch ID (defaults to main branch)

        Returns:
            Dictionary with query results

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "params": {
                    "projectId": project_id,
                    "sql": sql,
                }
            }

            if database_name:
                params["params"]["databaseName"] = database_name

            if branch_id:
                params["params"]["branchId"] = branch_id

            response = await self.call_tool("run_sql", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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
    ) -> Dict[str, Any]:
        """Execute a SQL transaction against a Neon database.

        Args:
            project_id: The ID of the project
            sql_statements: List of SQL statements to execute
            database_name: Optional database name (defaults to neondb)
            branch_id: Optional branch ID (defaults to main branch)

        Returns:
            Dictionary with transaction results

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "params": {
                    "projectId": project_id,
                    "sqlStatements": sql_statements,
                }
            }

            if database_name:
                params["params"]["databaseName"] = database_name

            if branch_id:
                params["params"]["branchId"] = branch_id

            response = await self.call_tool("run_sql_transaction", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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

    @function_tool
    async def create_branch(
        self, project_id: str, branch_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new branch in a Neon project.

        Args:
            project_id: The ID of the project
            branch_name: Optional name for the branch

        Returns:
            Dictionary with branch information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "params": {
                    "projectId": project_id,
                }
            }

            if branch_name:
                params["params"]["branchName"] = branch_name

            response = await self.call_tool("create_branch", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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
            params = {
                "params": {
                    "projectId": project_id,
                    "branchId": branch_id,
                }
            }

            if database_name:
                params["params"]["databaseName"] = database_name

            response = await self.call_tool("describe_branch", params)

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
            response = await self.call_tool(
                "delete_branch",
                {"params": {"projectId": project_id, "branchId": branch_id}},
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

    @function_tool
    async def get_connection_string(
        self,
        project_id: str,
        branch_id: Optional[str] = None,
        database_name: Optional[str] = None,
        role_name: Optional[str] = None,
        compute_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a PostgreSQL connection string for a Neon database.

        Args:
            project_id: The ID of the project
            branch_id: Optional branch ID
            database_name: Optional database name
            role_name: Optional role name
            compute_id: Optional compute ID

        Returns:
            Dictionary with connection string

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "params": {
                    "projectId": project_id,
                }
            }

            if branch_id:
                params["params"]["branchId"] = branch_id

            if database_name:
                params["params"]["databaseName"] = database_name

            if role_name:
                params["params"]["roleName"] = role_name

            if compute_id:
                params["params"]["computeId"] = compute_id

            response = await self.call_tool("get_connection_string", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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

    @function_tool
    async def get_database_tables(
        self,
        project_id: str,
        branch_id: Optional[str] = None,
        database_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all tables in a Neon database.

        Args:
            project_id: The ID of the project
            branch_id: Optional branch ID
            database_name: Optional database name

        Returns:
            Dictionary with table information

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "params": {
                    "projectId": project_id,
                }
            }

            if branch_id:
                params["params"]["branchId"] = branch_id

            if database_name:
                params["params"]["databaseName"] = database_name

            response = await self.call_tool("get_database_tables", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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
    ) -> Dict[str, Any]:
        """Describe the schema of a table in a Neon database.

        Args:
            project_id: The ID of the project
            table_name: The name of the table
            branch_id: Optional branch ID
            database_name: Optional database name

        Returns:
            Dictionary with table schema

        Raises:
            MCPError: If the request fails
        """
        try:
            params = {
                "params": {
                    "projectId": project_id,
                    "tableName": table_name,
                }
            }

            if branch_id:
                params["params"]["branchId"] = branch_id

            if database_name:
                params["params"]["databaseName"] = database_name

            response = await self.call_tool("describe_table_schema", params)

            # Parse response if it's a string
            if isinstance(response, str):
                response = json.loads(response)

            return response
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


class NeonService:
    """High-level service for Neon database operations in TripSage."""

    def __init__(self, client: Optional[NeonMCPClient] = None):
        """Initialize the Neon Service.

        Args:
            client: NeonMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or neon_client
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
                project_id = settings.neon_mcp.default_project_id
                if not project_id:
                    projects = await self.client.list_projects()
                    if projects.get("projects") and len(projects["projects"]) > 0:
                        project_id = projects["projects"][0].get("id")
                    else:
                        # No projects found, create one
                        project = await self.client.create_project(
                            "tripsage-development"
                        )
                        project_id = project.get("project", {}).get("id")

            # Generate a branch name if not provided
            if not branch_name:
                branch_name = f"dev-{uuid.uuid4().hex[:8]}"

            # Create the branch
            branch = await self.client.create_branch(project_id, branch_name)

            # Get connection string for the branch
            conn_info = await self.client.get_connection_string(
                project_id, branch.get("branch", {}).get("id")
            )

            return {
                "project_id": project_id,
                "branch": branch.get("branch", {}),
                "connection_string": conn_info.get("connectionString"),
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
                "result": result,
            }
        except Exception as e:
            logger.error(f"Error applying migrations: {str(e)}")
            return {
                "error": f"Failed to apply migrations: {str(e)}",
                "project_id": project_id,
                "branch_id": branch_id,
            }


# Initialize global client instance
neon_client = NeonMCPClient()


def get_client() -> NeonMCPClient:
    """Get a Neon MCP Client instance.

    Returns:
        NeonMCPClient instance
    """
    return neon_client


def get_service() -> NeonService:
    """Get a Neon Service instance.

    Returns:
        NeonService instance
    """
    return NeonService(neon_client)
