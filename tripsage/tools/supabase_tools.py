"""
Supabase database tools for TripSage agents.

This module provides function tools for interacting with Supabase database operations
using the OpenAI Agents SDK, following the direct MCP call pattern.
"""

from typing import Any, Dict, List, Optional

from openai_agents_sdk import function_tool
from pydantic import BaseModel, Field

from tripsage.mcp_abstraction.manager import mcp_manager
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
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

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
        TripSageMCPError: If the request fails
    """
    logger.info("Listing Supabase organizations")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="list_organizations",
        params={},
    )

    # Convert the result to the expected response model
    result = ListOrganizationsResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Getting organization details for ID: {id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="get_organization",
        params={"id": id},
    )

    # Convert the result to the expected response model
    result = GetOrganizationResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info("Listing Supabase projects")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="list_projects",
        params={},
    )

    # Convert the result to the expected response model
    result = ListProjectsResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Getting project details for ID: {id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="get_project",
        params={"id": id},
    )

    # Convert the result to the expected response model
    result = GetProjectResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Getting cost for {type} in organization: {organization_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="get_cost",
        params={"type": type, "organization_id": organization_id},
    )

    # Convert the result to the expected response model
    result = GetCostResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Confirming {recurrence} cost of {amount} for {type}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="confirm_cost",
        params={"type": type, "recurrence": recurrence, "amount": amount},
    )

    # Convert the result to the expected response model
    result = ConfirmCostResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Creating project '{name}' in organization: {organization_id}")

    params = {
        "name": name,
        "organization_id": organization_id,
        "confirm_cost_id": confirm_cost_id,
    }

    if region:
        params["region"] = region

    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="create_project",
        params=params,
    )

    # Convert the result to the expected response model
    result = CreateProjectResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Listing tables for project: {project_id}")

    params = {"project_id": project_id}
    if schemas:
        params["schemas"] = schemas

    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="list_tables",
        params=params,
    )

    # Convert the result to the expected response model
    result = ListTablesResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Listing extensions for project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="list_extensions",
        params={"project_id": project_id},
    )

    # Convert the result to the expected response model
    result = ListExtensionsResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Executing SQL query on project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": query},
    )

    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Applying migration '{name}' to project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="apply_migration",
        params={"project_id": project_id, "name": name, "query": query},
    )

    # Convert the result to the expected response model
    result = ApplyMigrationResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Getting API URL for project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="get_project_url",
        params={"project_id": project_id},
    )

    # Convert the result to the expected response model
    result = GetProjectUrlResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Getting anonymous API key for project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="get_anon_key",
        params={"project_id": project_id},
    )

    # Convert the result to the expected response model
    result = GetAnonKeyResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Creating branch '{name}' for project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="create_branch",
        params={
            "project_id": project_id,
            "confirm_cost_id": confirm_cost_id,
            "name": name,
        },
    )

    # Convert the result to the expected response model
    result = CreateBranchResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Listing branches for project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="list_branches",
        params={"project_id": project_id},
    )

    # Convert the result to the expected response model
    result = ListBranchesResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Merging branch: {branch_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="merge_branch",
        params={"branch_id": branch_id},
    )

    # Convert the result to the expected response model
    result = MergeBranchResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Deleting branch: {branch_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="delete_branch",
        params={"branch_id": branch_id},
    )

    # Convert the result to the expected response model
    result = DeleteBranchResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Resetting branch: {branch_id}")

    params = {"branch_id": branch_id}
    if migration_version:
        params["migration_version"] = migration_version

    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="reset_branch",
        params=params,
    )

    # Convert the result to the expected response model
    result = ResetBranchResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Rebasing branch: {branch_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="rebase_branch",
        params={"branch_id": branch_id},
    )

    # Convert the result to the expected response model
    result = RebaseBranchResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Pausing project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="pause_project",
        params={"project_id": project_id},
    )

    # Convert the result to the expected response model
    result = PauseProjectResponse.model_validate(result)

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
        TripSageMCPError: If the request fails
    """
    logger.info(f"Restoring project: {project_id}")
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="restore_project",
        params={"project_id": project_id},
    )

    # Convert the result to the expected response model
    result = RestoreProjectResponse.model_validate(result)

    return {"id": result.id, "status": result.status}


# Domain-specific operations for TripSage

@function_tool
@with_error_handling
async def find_user_by_email(project_id: str, email: str) -> Dict[str, Any]:
    """Find a user by email address (case-insensitive).
    
    Args:
        project_id: The ID of the project
        email: The email address to search for
        
    Returns:
        Dictionary with user information or empty if not found
        
    Raises:
        TripSageMCPError: If the request fails
    """
    logger.info(f"Finding user by email: {email} in project: {project_id}")
    
    # Email should be case-insensitive
    email_lower = email.lower()
    
    # SQL query to find user by email
    query = """
        SELECT id, name, email, preferences_json, is_admin, is_disabled, 
               created_at, updated_at
        FROM users 
        WHERE LOWER(email) = $1
        LIMIT 1
    """.replace("$1", f"'{email_lower}'")
    
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": query},
    )
    
    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)
    
    if result.rows:
        user_data = result.rows[0].model_dump()
        return {
            "found": True,
            "user": user_data
        }
    
    return {"found": False, "user": None}


@function_tool
@with_error_handling
async def find_users_by_name_pattern(
    project_id: str, name_pattern: str
) -> Dict[str, Any]:
    """Find users by name pattern (case-insensitive).
    
    Args:
        project_id: The ID of the project
        name_pattern: The name pattern to search for (supports SQL LIKE syntax)
        
    Returns:
        Dictionary with list of matching users
        
    Raises:
        TripSageMCPError: If the request fails
    """
    logger.info(f"Finding users by name pattern: {name_pattern} in project: {project_id}")
    
    # SQL query to find users by name pattern
    query = f"""
        SELECT id, name, email, preferences_json, is_admin, is_disabled, 
               created_at, updated_at
        FROM users 
        WHERE name ILIKE '{name_pattern}'
        ORDER BY name
    """
    
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": query},
    )
    
    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)
    
    users = [row.model_dump() for row in result.rows]
    
    return {
        "users": users,
        "count": len(users)
    }


@function_tool
@with_error_handling
async def update_user_preferences(
    project_id: str, user_id: int, preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a user's preferences by merging with existing preferences.
    
    Args:
        project_id: The ID of the project
        user_id: The ID of the user to update
        preferences: The new preferences to merge with existing ones
        
    Returns:
        Dictionary with updated user information
        
    Raises:
        TripSageMCPError: If the request fails
    """
    logger.info(f"Updating preferences for user {user_id} in project: {project_id}")
    
    # First, get the current preferences
    get_query = f"""
        SELECT preferences_json 
        FROM users 
        WHERE id = {user_id}
    """
    
    current_result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": get_query},
    )
    
    current_result = ExecuteSQLResponse.model_validate(current_result)
    
    if not current_result.rows:
        return {"success": False, "error": "User not found"}
    
    current_prefs = current_result.rows[0].model_dump().get("preferences_json", {})
    
    # Deep merge preferences
    import json
    merged_prefs = deep_merge_preferences(current_prefs, preferences)
    
    # Update the user's preferences
    update_query = f"""
        UPDATE users 
        SET preferences_json = '{json.dumps(merged_prefs)}'::jsonb,
            updated_at = NOW()
        WHERE id = {user_id}
        RETURNING id, name, email, preferences_json, is_admin, is_disabled, 
                  created_at, updated_at
    """
    
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": update_query},
    )
    
    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)
    
    if result.rows:
        user_data = result.rows[0].model_dump()
        return {
            "success": True,
            "user": user_data
        }
    
    return {"success": False, "error": "Failed to update preferences"}


@function_tool
@with_error_handling
async def find_trips_by_user(
    project_id: str, user_id: int, status: Optional[str] = None
) -> Dict[str, Any]:
    """Find trips for a specific user, optionally filtered by status.
    
    Args:
        project_id: The ID of the project
        user_id: The ID of the user
        status: Optional status filter (planning, booked, completed, canceled)
        
    Returns:
        Dictionary with list of trips
        
    Raises:
        TripSageMCPError: If the request fails
    """
    logger.info(f"Finding trips for user {user_id} in project: {project_id}")
    
    # SQL query to find trips
    where_clause = f"WHERE ut.user_id = {user_id}"
    if status:
        where_clause += f" AND t.status = '{status}'"
    
    query = f"""
        SELECT t.id, t.name, t.start_date, t.end_date, t.destination, 
               t.budget, t.travelers, t.status, t.trip_type, t.flexibility,
               t.created_at, t.updated_at
        FROM trips t
        JOIN user_trips ut ON t.id = ut.trip_id
        {where_clause}
        ORDER BY t.start_date DESC
    """
    
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": query},
    )
    
    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)
    
    trips = [row.model_dump() for row in result.rows]
    
    return {
        "trips": trips,
        "count": len(trips)
    }


@function_tool
@with_error_handling
async def find_trips_by_destination(
    project_id: str, destination_pattern: str
) -> Dict[str, Any]:
    """Find trips by destination pattern.
    
    Args:
        project_id: The ID of the project
        destination_pattern: The destination pattern to search for (supports SQL LIKE)
        
    Returns:
        Dictionary with list of matching trips
        
    Raises:
        TripSageMCPError: If the request fails
    """
    logger.info(f"Finding trips by destination: {destination_pattern} in project: {project_id}")
    
    # SQL query to find trips by destination
    query = f"""
        SELECT id, name, start_date, end_date, destination, 
               budget, travelers, status, trip_type, flexibility,
               created_at, updated_at
        FROM trips
        WHERE destination ILIKE '{destination_pattern}'
        ORDER BY start_date DESC
    """
    
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": query},
    )
    
    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)
    
    trips = [row.model_dump() for row in result.rows]
    
    return {
        "trips": trips,
        "count": len(trips)
    }


@function_tool
@with_error_handling
async def find_active_trips_by_date_range(
    project_id: str, start_date: str, end_date: str
) -> Dict[str, Any]:
    """Find active trips within a date range.
    
    Args:
        project_id: The ID of the project
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        
    Returns:
        Dictionary with list of active trips in the date range
        
    Raises:
        TripSageMCPError: If the request fails
    """
    logger.info(f"Finding active trips between {start_date} and {end_date} in project: {project_id}")
    
    # SQL query to find active trips overlapping with date range
    query = f"""
        SELECT id, name, start_date, end_date, destination, 
               budget, travelers, status, trip_type, flexibility,
               created_at, updated_at
        FROM trips
        WHERE status IN ('planning', 'booked')
          AND start_date <= '{end_date}'
          AND end_date >= '{start_date}'
        ORDER BY start_date
    """
    
    result = await mcp_manager.invoke(
        mcp_name="supabase",
        method_name="execute_sql",
        params={"project_id": project_id, "query": query},
    )
    
    # Convert the result to the expected response model
    result = ExecuteSQLResponse.model_validate(result)
    
    trips = [row.model_dump() for row in result.rows]
    
    return {
        "trips": trips,
        "count": len(trips)
    }


# Helper function for deep merging preferences
def deep_merge_preferences(current: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two preference dictionaries."""
    result = current.copy()
    
    for key, value in updates.items():
        if (
            isinstance(value, dict)
            and key in result
            and isinstance(result[key], dict)
        ):
            # Merge nested dictionaries
            result[key] = deep_merge_preferences(result[key], value)
        else:
            # Override at top level
            result[key] = value
    
    return result