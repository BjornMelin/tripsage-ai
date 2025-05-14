"""
Supabase database tools for TripSage agents.

This module provides function tools for interacting with Supabase database operations
using the OpenAI Agents SDK, following the direct MCP call pattern.
"""

from typing import Any, Dict, List, Optional

from openai_agents_sdk import function_tool
from pydantic import BaseModel, Field

from tripsage.tools.schemas.supabase import (
    ApplyMigrationResponse,
    ConfirmCostResponse,
    CreateBranchResponse,
    CreateProjectResponse,
    DeleteBranchResponse,
    ExecuteSQLResponse,
    GetAnonKeyResponse,
    GetCostResponse,
    GetOrganizationResponse,
    GetProjectResponse,
    GetProjectUrlResponse,
    ListBranchesResponse,
    ListExtensionsResponse,
    ListOrganizationsResponse,
    ListProjectsResponse,
    ListTablesResponse,
    MergeBranchResponse,
    PauseProjectResponse,
    RebaseBranchResponse,
    ResetBranchResponse,
    RestoreProjectResponse,
)
from tripsage.utils.client_utils import validate_and_call_mcp_tool
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger
from tripsage.utils.settings import settings

logger = get_logger(__name__)


class FileObject(BaseModel):
    """Represents a file with name and content."""

    name: str = Field(..., description="The name of the file")
    content: str = Field(..., description="The content of the file")


@function_tool
@with_error_handling
async def list_organizations() -> Dict[str, Any]:
    """Lists all organizations that the user is a member of.

    Returns:
        Dictionary with organization information

    Raises:
        MCPError: If the request fails
    """
    logger.info("Listing Supabase organizations")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="list_organizations",
        params={},
        response_model=ListOrganizationsResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    # Format the response for agent consumption
    organizations = []
    for org in result.organizations:
        organizations.append(
            {
                "id": org.id,
                "name": org.name,
                "created_at": org.created_at,
                "billing_email": org.billing_email,
            }
        )

    return {"organizations": organizations, "count": len(organizations)}


@function_tool
@with_error_handling
async def get_organization(id: str) -> Dict[str, Any]:
    """Gets details for an organization. Includes subscription plan.

    Args:
        id: The organization ID

    Returns:
        Dictionary with organization details

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Getting organization details for ID: {id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="get_organization",
        params={"id": id},
        response_model=GetOrganizationResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {
        "id": result.id,
        "name": result.name,
        "created_at": result.created_at,
        "billing_email": result.billing_email,
        "subscription": result.subscription,
    }


@function_tool
@with_error_handling
async def list_projects() -> Dict[str, Any]:
    """Lists all Supabase projects for the user.

    Returns:
        Dictionary with project information

    Raises:
        MCPError: If the request fails
    """
    logger.info("Listing Supabase projects")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="list_projects",
        params={},
        response_model=ListProjectsResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    # Format the response for agent consumption
    projects = []
    for project in result.projects:
        projects.append(
            {
                "id": project.id,
                "name": project.name,
                "organization_id": project.organization_id,
                "created_at": project.created_at,
                "status": project.status,
            }
        )

    return {"projects": projects, "count": len(projects)}


@function_tool
@with_error_handling
async def get_project(id: str) -> Dict[str, Any]:
    """Gets details for a Supabase project.

    Args:
        id: The project ID

    Returns:
        Dictionary with project details

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Getting project details for ID: {id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="get_project",
        params={"id": id},
        response_model=GetProjectResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {
        "id": result.id,
        "name": result.name,
        "organization_id": result.organization_id,
        "created_at": result.created_at,
        "status": result.status,
        "db_host": result.db_host,
        "db_port": result.db_port,
        "db_name": result.db_name,
        "db_user": result.db_user,
        "region": result.region,
    }


@function_tool
@with_error_handling
async def get_cost(type: str, organization_id: str) -> Dict[str, Any]:
    """Gets the cost of creating a new project or branch.

    Args:
        type: The type of resource to get cost for ('project' or 'branch')
        organization_id: The organization ID

    Returns:
        Dictionary with cost information

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Getting cost for {type} in organization: {organization_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="get_cost",
        params={"type": type, "organization_id": organization_id},
        response_model=GetCostResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"amount": result.amount, "recurrence": result.recurrence}


@function_tool
@with_error_handling
async def confirm_cost(type: str, recurrence: str, amount: float) -> Dict[str, Any]:
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
    logger.info(f"Confirming {recurrence} cost of {amount} for {type}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="confirm_cost",
        params={"type": type, "recurrence": recurrence, "amount": amount},
        response_model=ConfirmCostResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id}


@function_tool
@with_error_handling
async def create_project(
    name: str,
    organization_id: str,
    confirm_cost_id: str,
    region: Optional[str] = None,
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
    logger.info(f"Creating project '{name}' in organization: {organization_id}")

    params = {
        "name": name,
        "organization_id": organization_id,
        "confirm_cost_id": confirm_cost_id,
    }

    if region:
        params["region"] = region

    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="create_project",
        params=params,
        response_model=CreateProjectResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {
        "id": result.id,
        "name": result.name,
        "organization_id": result.organization_id,
        "created_at": result.created_at,
        "status": result.status,
        "region": result.region,
    }


@function_tool
@with_error_handling
async def list_tables(
    project_id: str, schemas: Optional[List[str]] = None
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
    logger.info(f"Listing tables for project: {project_id}")

    params = {"project_id": project_id}
    if schemas:
        params["schemas"] = schemas

    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="list_tables",
        params=params,
        response_model=ListTablesResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    # Format the response for agent consumption
    tables = []
    for table in result.tables:
        tables.append(
            {"name": table.name, "schema": table.schema, "comment": table.comment}
        )

    return {"tables": tables, "count": len(tables)}


@function_tool
@with_error_handling
async def list_extensions(project_id: str) -> Dict[str, Any]:
    """Lists all extensions in the database.

    Args:
        project_id: The ID of the project

    Returns:
        Dictionary with extension information

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Listing extensions for project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="list_extensions",
        params={"project_id": project_id},
        response_model=ListExtensionsResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    # Format the response for agent consumption
    extensions = []
    for ext in result.extensions:
        extensions.append(
            {
                "name": ext.name,
                "schema": ext.schema,
                "version": ext.version,
                "enabled": ext.enabled,
            }
        )

    return {"extensions": extensions, "count": len(extensions)}


@function_tool
@with_error_handling
async def execute_sql(project_id: str, query: str) -> Dict[str, Any]:
    """Executes raw SQL in the Postgres database.

    Args:
        project_id: The ID of the project
        query: The SQL query to execute

    Returns:
        Dictionary with query results

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Executing SQL query on project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="execute_sql",
        params={"project_id": project_id, "query": query},
        response_model=ExecuteSQLResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    # Format the column data
    columns = [{"name": col.name, "type": col.type} for col in result.columns]

    # Format the row data
    rows = [row.model_dump() for row in result.rows]

    return {"columns": columns, "rows": rows, "count": len(rows)}


@function_tool
@with_error_handling
async def apply_migration(project_id: str, name: str, query: str) -> Dict[str, Any]:
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
    logger.info(f"Applying migration '{name}' to project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="apply_migration",
        params={"project_id": project_id, "name": name, "query": query},
        response_model=ApplyMigrationResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {
        "id": result.id,
        "name": result.name,
        "version": result.version,
        "applied_at": result.applied_at,
    }


@function_tool
@with_error_handling
async def get_project_url(project_id: str) -> Dict[str, Any]:
    """Gets the API URL for a project.

    Args:
        project_id: The ID of the project

    Returns:
        Dictionary with project URL

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Getting API URL for project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="get_project_url",
        params={"project_id": project_id},
        response_model=GetProjectUrlResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"url": result.url}


@function_tool
@with_error_handling
async def get_anon_key(project_id: str) -> Dict[str, Any]:
    """Gets the anonymous API key for a project.

    Args:
        project_id: The ID of the project

    Returns:
        Dictionary with anonymous key

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Getting anonymous API key for project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="get_anon_key",
        params={"project_id": project_id},
        response_model=GetAnonKeyResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"key": result.key}


@function_tool
@with_error_handling
async def create_branch(
    project_id: str, confirm_cost_id: str, name: str = "develop"
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
    logger.info(f"Creating branch '{name}' for project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="create_branch",
        params={
            "project_id": project_id,
            "confirm_cost_id": confirm_cost_id,
            "name": name,
        },
        response_model=CreateBranchResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {
        "id": result.id,
        "name": result.name,
        "project_id": result.project_id,
        "created_at": result.created_at,
        "status": result.status,
    }


@function_tool
@with_error_handling
async def list_branches(project_id: str) -> Dict[str, Any]:
    """Lists all development branches of a Supabase project.

    Args:
        project_id: The ID of the project

    Returns:
        Dictionary with branch information

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Listing branches for project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="list_branches",
        params={"project_id": project_id},
        response_model=ListBranchesResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    # Format the response for agent consumption
    branches = []
    for branch in result.branches:
        branches.append(
            {
                "id": branch.id,
                "name": branch.name,
                "project_id": branch.project_id,
                "created_at": branch.created_at,
                "status": branch.status,
            }
        )

    return {"branches": branches, "count": len(branches)}


@function_tool
@with_error_handling
async def merge_branch(branch_id: str) -> Dict[str, Any]:
    """Merges a development branch to the main branch.

    Args:
        branch_id: The ID of the branch to merge

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Merging branch: {branch_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="merge_branch",
        params={"branch_id": branch_id},
        response_model=MergeBranchResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id, "status": result.status}


@function_tool
@with_error_handling
async def delete_branch(branch_id: str) -> Dict[str, Any]:
    """Deletes a development branch.

    Args:
        branch_id: The ID of the branch to delete

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Deleting branch: {branch_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="delete_branch",
        params={"branch_id": branch_id},
        response_model=DeleteBranchResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id, "status": result.status}


@function_tool
@with_error_handling
async def reset_branch(
    branch_id: str, migration_version: Optional[str] = None
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
    logger.info(f"Resetting branch: {branch_id}")

    params = {"branch_id": branch_id}
    if migration_version:
        params["migration_version"] = migration_version

    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="reset_branch",
        params=params,
        response_model=ResetBranchResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id, "status": result.status}


@function_tool
@with_error_handling
async def rebase_branch(branch_id: str) -> Dict[str, Any]:
    """Rebases a development branch on the main branch.

    Args:
        branch_id: The ID of the branch to rebase

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Rebasing branch: {branch_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="rebase_branch",
        params={"branch_id": branch_id},
        response_model=RebaseBranchResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id, "status": result.status}


@function_tool
@with_error_handling
async def pause_project(project_id: str) -> Dict[str, Any]:
    """Pauses a Supabase project.

    Args:
        project_id: The ID of the project to pause

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Pausing project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="pause_project",
        params={"project_id": project_id},
        response_model=PauseProjectResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id, "status": result.status}


@function_tool
@with_error_handling
async def restore_project(project_id: str) -> Dict[str, Any]:
    """Restores a Supabase project.

    Args:
        project_id: The ID of the project to restore

    Returns:
        Dictionary with operation status

    Raises:
        MCPError: If the request fails
    """
    logger.info(f"Restoring project: {project_id}")
    result = await validate_and_call_mcp_tool(
        endpoint=settings.supabase_mcp.endpoint,
        tool_name="restore_project",
        params={"project_id": project_id},
        response_model=RestoreProjectResponse,
        timeout=settings.supabase_mcp.timeout,
        server_name="Supabase MCP",
    )

    return {"id": result.id, "status": result.status}
