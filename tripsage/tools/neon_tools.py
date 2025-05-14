"""
Neon database tools for TripSage agents.

This module provides function tools for interacting with Neon database operations
using the OpenAI Agents SDK, following the direct MCP call pattern.
"""

from typing import Any, Dict, List, Optional

from openai_agents_sdk import function_tool

from tripsage.tools.schemas.neon import (
    BranchResponse,
    ConnectionStringResponse,
    DescribeTableSchemaResponse,
    GetDatabaseTablesResponse,
    ProjectListResponse,
    ProjectResponse,
    SQLResponse,
)
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger
from tripsage.utils.settings import settings

logger = get_logger(__name__)


# Project Operations


@function_tool
@with_error_handling
async def list_projects(skip_cache: bool = False) -> Dict[str, Any]:
    """List all Neon projects in your account.

    Args:
        skip_cache: Whether to skip the cache and fetch fresh data

    Returns:
        Dictionary with project information

    Raises:
        MCPError: If the request fails
    """
    logger.info("Listing Neon projects")

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="list_projects",
        params={"params": {}},
        response_model=ProjectListResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    # Format projects for agent consumption
    projects = []
    for project in result.projects:
        projects.append(
            {
                "id": project.id,
                "name": project.name,
                "region_id": project.region_id,
                "pg_version": project.pg_version,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
            }
        )

    return {"projects": projects, "count": len(projects)}


@function_tool
@with_error_handling
async def create_project(name: Optional[str] = None) -> Dict[str, Any]:
    """Create a new Neon project.

    Args:
        name: Optional name for the project

    Returns:
        Dictionary with project information

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Creating Neon project: {name if name else 'unnamed'}")

    params = {"params": {}}
    if name:
        params["params"]["name"] = name

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="create_project",
        params=params,
        response_model=ProjectResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {
        "id": result.project.id,
        "name": result.project.name,
        "region_id": result.project.region_id,
        "pg_version": result.project.pg_version,
        "created_at": result.project.created_at,
        "updated_at": result.project.updated_at,
    }


@function_tool
@with_error_handling
async def describe_project(project_id: str) -> Dict[str, Any]:
    """Get details for a specific Neon project.

    Args:
        project_id: The ID of the project to describe

    Returns:
        Dictionary with project details

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Getting details for Neon project: {project_id}")

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="describe_project",
        params={"params": {"projectId": project_id}},
        response_model=ProjectResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {
        "id": result.project.id,
        "name": result.project.name,
        "region_id": result.project.region_id,
        "pg_version": result.project.pg_version,
        "created_at": result.project.created_at,
        "updated_at": result.project.updated_at,
    }


@function_tool
@with_error_handling
async def delete_project(project_id: str) -> Dict[str, Any]:
    """Delete a Neon project.

    Args:
        project_id: The ID of the project to delete

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Deleting Neon project: {project_id}")

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="delete_project",
        params={"params": {"projectId": project_id}},
        response_model=Dict[str, Any],
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {"success": True, "message": "Project deleted successfully"}


# SQL Operations


@function_tool
@with_error_handling
async def run_sql(
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
    logger.info(f"Executing SQL query on Neon project: {project_id}")

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

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="run_sql",
        params=params,
        response_model=SQLResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    # Format results for agent consumption
    formatted_results = []
    for sql_result in result.results:
        formatted_results.append(
            {
                "rows": sql_result.rows,
                "row_count": sql_result.rowCount,
                "command": sql_result.command,
            }
        )

    return {
        "results": formatted_results,
        "success": True,
        "count": len(formatted_results),
    }


@function_tool
@with_error_handling
async def run_sql_transaction(
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
    logger.info(f"Executing SQL transaction on Neon project: {project_id}")

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

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="run_sql_transaction",
        params=params,
        response_model=SQLResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    # Format results for agent consumption
    formatted_results = []
    for sql_result in result.results:
        formatted_results.append(
            {
                "rows": sql_result.rows,
                "row_count": sql_result.rowCount,
                "command": sql_result.command,
            }
        )

    return {
        "results": formatted_results,
        "success": True,
        "count": len(formatted_results),
    }


# Branch Operations


@function_tool
@with_error_handling
async def create_branch(
    project_id: str, branch_name: Optional[str] = None
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
    logger.info(f"Creating branch in Neon project: {project_id}")

    params = {
        "params": {
            "projectId": project_id,
        }
    }

    if branch_name:
        params["params"]["branchName"] = branch_name

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="create_branch",
        params=params,
        response_model=BranchResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {
        "id": result.branch.id,
        "project_id": result.branch.project_id,
        "name": result.branch.name,
        "parent_id": result.branch.parent_id,
        "parent_lsn": result.branch.parent_lsn,
        "created_at": result.branch.created_at,
        "updated_at": result.branch.updated_at,
    }


@function_tool
@with_error_handling
async def describe_branch(
    project_id: str, branch_id: str, database_name: Optional[str] = None
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
    logger.info(f"Describing branch {branch_id} in Neon project: {project_id}")

    params = {
        "params": {
            "projectId": project_id,
            "branchId": branch_id,
        }
    }

    if database_name:
        params["params"]["databaseName"] = database_name

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="describe_branch",
        params=params,
        response_model=Dict[str, Any],
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return result


@function_tool
@with_error_handling
async def delete_branch(project_id: str, branch_id: str) -> Dict[str, Any]:
    """Delete a branch from a Neon project.

    Args:
        project_id: The ID of the project
        branch_id: The ID of the branch to delete

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Deleting branch {branch_id} from Neon project: {project_id}")

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="delete_branch",
        params={"params": {"projectId": project_id, "branchId": branch_id}},
        response_model=Dict[str, Any],
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {"success": True, "message": "Branch deleted successfully"}


# Connection Operations


@function_tool
@with_error_handling
async def get_connection_string(
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
    logger.info(f"Getting connection string for Neon project: {project_id}")

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

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="get_connection_string",
        params=params,
        response_model=ConnectionStringResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {
        "connection_string": result.connection_string,
    }


# Database Schema Operations


@function_tool
@with_error_handling
async def get_database_tables(
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
    logger.info(f"Getting database tables for Neon project: {project_id}")

    params = {
        "params": {
            "projectId": project_id,
        }
    }

    if branch_id:
        params["params"]["branchId"] = branch_id

    if database_name:
        params["params"]["databaseName"] = database_name

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="get_database_tables",
        params=params,
        response_model=GetDatabaseTablesResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    # Format tables for agent consumption
    tables = []
    for table in result.tables:
        tables.append(
            {
                "name": table.name,
                "schema": table.schema,
                "columns": table.columns,
            }
        )

    return {"tables": tables, "count": len(tables)}


@function_tool
@with_error_handling
async def describe_table_schema(
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
    logger.info(
        f"Describing schema for table {table_name} in Neon project: {project_id}"
    )

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

    result = await validate_and_call_mcp_tool(
        endpoint=settings.neon_mcp.endpoint,
        tool_name="describe_table_schema",
        params=params,
        response_model=DescribeTableSchemaResponse,
        timeout=settings.neon_mcp.timeout,
        server_name="Neon MCP",
    )

    return {
        "columns": result.columns,
        "constraints": result.constraints or [],
        "indexes": result.indexes or [],
    }
