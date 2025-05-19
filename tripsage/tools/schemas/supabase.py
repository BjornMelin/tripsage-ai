"""
Pydantic models for Supabase MCP client.

This module defines the parameter and response models for the Supabase MCP Client,
providing proper validation and type safety.
"""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ListOrganizationsParams(BaseParams):
    """Parameters for the list_organizations method."""

    # No parameters required for this endpoint
    pass


class GetOrganizationParams(BaseParams):
    """Parameters for the get_organization method."""

    id: str = Field(..., description="The organization ID")


class ListProjectsParams(BaseParams):
    """Parameters for the list_projects method."""

    # No parameters required for this endpoint
    pass


class GetProjectParams(BaseParams):
    """Parameters for the get_project method."""

    id: str = Field(..., description="The project ID")


class GetCostParams(BaseParams):
    """Parameters for the get_cost method."""

    type: Literal["project", "branch"] = Field(
        ..., description="The type of resource to get cost for ('project' or 'branch')"
    )
    organization_id: str = Field(..., description="The organization ID")


class ConfirmCostParams(BaseParams):
    """Parameters for the confirm_cost method."""

    type: Literal["project", "branch"] = Field(
        ..., description="The type of resource ('project' or 'branch')"
    )
    recurrence: Literal["hourly", "monthly"] = Field(
        ..., description="The recurrence of the cost ('hourly' or 'monthly')"
    )
    amount: float = Field(..., description="The cost amount")


class CreateProjectParams(BaseParams):
    """Parameters for the create_project method."""

    name: str = Field(..., description="The name of the project")
    organization_id: str = Field(..., description="The organization ID")
    confirm_cost_id: str = Field(..., description="The cost confirmation ID")
    region: Optional[str] = Field(
        None, description="The region to create the project in (optional)"
    )


class PauseProjectParams(BaseParams):
    """Parameters for the pause_project method."""

    project_id: str = Field(..., description="The ID of the project to pause")


class RestoreProjectParams(BaseParams):
    """Parameters for the restore_project method."""

    project_id: str = Field(..., description="The ID of the project to restore")


class ListTablesParams(BaseParams):
    """Parameters for the list_tables method."""

    project_id: str = Field(..., description="The ID of the project")
    schemas: Optional[List[str]] = Field(
        None, description="List of schemas to include (defaults to ['public'])"
    )


class ListExtensionsParams(BaseParams):
    """Parameters for the list_extensions method."""

    project_id: str = Field(..., description="The ID of the project")


class ListMigrationsParams(BaseParams):
    """Parameters for the list_migrations method."""

    project_id: str = Field(..., description="The ID of the project")


class ApplyMigrationParams(BaseParams):
    """Parameters for the apply_migration method."""

    project_id: str = Field(..., description="The ID of the project")
    name: str = Field(..., description="The name of the migration in snake_case")
    query: str = Field(..., description="The SQL query to apply")

    @model_validator(mode="after")
    def validate_query(self) -> "ApplyMigrationParams":
        """Validate that the query is not empty."""
        if not self.query.strip():
            raise ValueError("SQL query cannot be empty")
        return self


class ExecuteSQLParams(BaseParams):
    """Parameters for the execute_sql method."""

    project_id: str = Field(..., description="The ID of the project")
    query: str = Field(..., description="The SQL query to execute")

    @model_validator(mode="after")
    def validate_query(self) -> "ExecuteSQLParams":
        """Validate that the query is not empty."""
        if not self.query.strip():
            raise ValueError("SQL query cannot be empty")
        return self


class ListEdgeFunctionsParams(BaseParams):
    """Parameters for the list_edge_functions method."""

    project_id: str = Field(..., description="The ID of the project")


class FileObject(BaseModel):
    """Represents a file with name and content."""

    name: str = Field(..., description="The name of the file")
    content: str = Field(..., description="The content of the file")


class DeployEdgeFunctionParams(BaseParams):
    """Parameters for the deploy_edge_function method."""

    project_id: str = Field(..., description="The ID of the project")
    name: str = Field(..., description="The name of the function")
    files: List[FileObject] = Field(..., description="List of file objects")
    entrypoint_path: str = Field(
        "index.ts", description="The entrypoint path (defaults to index.ts)"
    )
    import_map_path: Optional[str] = Field(None, description="Optional import map path")


class GetLogsParams(BaseParams):
    """Parameters for the get_logs method."""

    project_id: str = Field(..., description="The ID of the project")
    service: str = Field(
        ..., description="The service to fetch logs for (api, postgres, auth, etc.)"
    )


class GetProjectUrlParams(BaseParams):
    """Parameters for the get_project_url method."""

    project_id: str = Field(..., description="The ID of the project")


class GetAnonKeyParams(BaseParams):
    """Parameters for the get_anon_key method."""

    project_id: str = Field(..., description="The ID of the project")


class CreateBranchParams(BaseParams):
    """Parameters for the create_branch method."""

    project_id: str = Field(..., description="The ID of the project")
    confirm_cost_id: str = Field(..., description="The cost confirmation ID")
    name: str = Field(
        "develop", description="Name for the branch (defaults to 'develop')"
    )


class ListBranchesParams(BaseParams):
    """Parameters for the list_branches method."""

    project_id: str = Field(..., description="The ID of the project")


class DeleteBranchParams(BaseParams):
    """Parameters for the delete_branch method."""

    branch_id: str = Field(..., description="The ID of the branch to delete")


class MergeBranchParams(BaseParams):
    """Parameters for the merge_branch method."""

    branch_id: str = Field(..., description="The ID of the branch to merge")


class ResetBranchParams(BaseParams):
    """Parameters for the reset_branch method."""

    branch_id: str = Field(..., description="The ID of the branch to reset")
    migration_version: Optional[str] = Field(
        None, description="Optional migration version to reset to"
    )


class RebaseBranchParams(BaseParams):
    """Parameters for the rebase_branch method."""

    branch_id: str = Field(..., description="The ID of the branch to rebase")


class GenerateTypescriptTypesParams(BaseParams):
    """Parameters for the generate_typescript_types method."""

    project_id: str = Field(..., description="The ID of the project")


# Response Models


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class OrganizationResponse(BaseResponse):
    """Response model for organization operations."""

    id: str
    name: str
    created_at: str
    billing_email: Optional[str] = None


class ListOrganizationsResponse(BaseResponse):
    """Response model for list_organizations method."""

    organizations: List[OrganizationResponse]


class GetOrganizationResponse(BaseResponse):
    """Response model for get_organization method."""

    id: str
    name: str
    created_at: str
    billing_email: Optional[str] = None
    subscription: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseResponse):
    """Response model for project operations."""

    id: str
    name: str
    organization_id: str
    created_at: str
    status: str


class ListProjectsResponse(BaseResponse):
    """Response model for list_projects method."""

    projects: List[ProjectResponse]


class GetProjectResponse(BaseResponse):
    """Response model for get_project method."""

    id: str
    name: str
    organization_id: str
    created_at: str
    status: str
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    region: Optional[str] = None


class GetCostResponse(BaseResponse):
    """Response model for get_cost method."""

    amount: float
    recurrence: str


class ConfirmCostResponse(BaseResponse):
    """Response model for confirm_cost method."""

    id: str


class CreateProjectResponse(BaseResponse):
    """Response model for create_project method."""

    id: str
    name: str
    organization_id: str
    created_at: str
    status: str
    region: Optional[str] = None


class PauseProjectResponse(BaseResponse):
    """Response model for pause_project method."""

    id: str
    status: str


class RestoreProjectResponse(BaseResponse):
    """Response model for restore_project method."""

    id: str
    status: str


class TableResponse(BaseResponse):
    """Response model for table information."""

    name: str
    schema: str
    comment: Optional[str] = None


class ListTablesResponse(BaseResponse):
    """Response model for list_tables method."""

    tables: List[TableResponse]


class ExtensionResponse(BaseResponse):
    """Response model for extension information."""

    name: str
    schema: str
    version: str
    enabled: bool


class ListExtensionsResponse(BaseResponse):
    """Response model for list_extensions method."""

    extensions: List[ExtensionResponse]


class MigrationResponse(BaseResponse):
    """Response model for migration information."""

    id: str
    name: str
    version: str
    applied_at: str


class ListMigrationsResponse(BaseResponse):
    """Response model for list_migrations method."""

    migrations: List[MigrationResponse]


class ApplyMigrationResponse(BaseResponse):
    """Response model for apply_migration method."""

    id: str
    name: str
    version: str
    applied_at: str


class ColumnData(BaseModel):
    """Represents a column in a SQL result set."""

    name: str
    type: str


class ResultRow(BaseModel):
    """Represents a row in a SQL result set."""

    model_config = ConfigDict(extra="allow")


class ExecuteSQLResponse(BaseResponse):
    """Response model for execute_sql method."""

    columns: List[ColumnData]
    rows: List[ResultRow]


class EdgeFunctionResponse(BaseResponse):
    """Response model for edge function information."""

    id: str
    name: str
    slug: str
    status: str
    version: int
    updated_at: str


class ListEdgeFunctionsResponse(BaseResponse):
    """Response model for list_edge_functions method."""

    functions: List[EdgeFunctionResponse]


class DeployEdgeFunctionResponse(BaseResponse):
    """Response model for deploy_edge_function method."""

    id: str
    name: str
    slug: str
    status: str
    version: int
    updated_at: str


class LogEntry(BaseModel):
    """Represents a log entry."""

    timestamp: str
    message: str
    level: str


class GetLogsResponse(BaseResponse):
    """Response model for get_logs method."""

    logs: List[LogEntry]


class GetProjectUrlResponse(BaseResponse):
    """Response model for get_project_url method."""

    url: str


class GetAnonKeyResponse(BaseResponse):
    """Response model for get_anon_key method."""

    key: str


class BranchResponse(BaseResponse):
    """Response model for branch information."""

    id: str
    name: str
    project_id: str
    created_at: str
    status: str


class CreateBranchResponse(BaseResponse):
    """Response model for create_branch method."""

    id: str
    name: str
    project_id: str
    created_at: str
    status: str


class ListBranchesResponse(BaseResponse):
    """Response model for list_branches method."""

    branches: List[BranchResponse]


class DeleteBranchResponse(BaseResponse):
    """Response model for delete_branch method."""

    id: str
    status: str


class MergeBranchResponse(BaseResponse):
    """Response model for merge_branch method."""

    id: str
    status: str


class ResetBranchResponse(BaseResponse):
    """Response model for reset_branch method."""

    id: str
    status: str


class RebaseBranchResponse(BaseResponse):
    """Response model for rebase_branch method."""

    id: str
    status: str


class GenerateTypescriptTypesResponse(BaseResponse):
    """Response model for generate_typescript_types method."""

    types: str
