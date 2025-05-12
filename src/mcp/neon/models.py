"""
Pydantic models for Neon MCP client.

This module defines the parameter and response models for the Neon MCP Client,
providing proper validation and type safety.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseParams(BaseModel):
    """Base model for all parameter models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ListProjectsParams(BaseParams):
    """Parameters for the list_projects method."""

    # No parameters required for this endpoint
    pass


class CreateProjectParams(BaseParams):
    """Parameters for the create_project method."""

    name: Optional[str] = Field(None, description="Optional name for the project")


class DescribeProjectParams(BaseParams):
    """Parameters for the describe_project method."""

    project_id: str = Field(..., description="The ID of the project to describe")


class DeleteProjectParams(BaseParams):
    """Parameters for the delete_project method."""

    project_id: str = Field(..., description="The ID of the project to delete")


class RunSQLParams(BaseParams):
    """Parameters for the run_sql method."""

    project_id: str = Field(..., description="The ID of the project")
    sql: str = Field(..., description="The SQL query to execute")
    database_name: Optional[str] = Field(
        default=None,
        description="Optional database name (defaults to neondb)",
    )
    branch_id: Optional[str] = Field(
        default=None,
        description="Optional branch ID (defaults to main branch)",
    )

    @model_validator(mode="after")
    def validate_sql_query(self) -> "RunSQLParams":
        """Validate that the SQL query is not empty."""
        if not self.sql.strip():
            raise ValueError("SQL query cannot be empty")
        return self


class RunSQLTransactionParams(BaseParams):
    """Parameters for the run_sql_transaction method."""

    project_id: str = Field(..., description="The ID of the project")
    sql_statements: List[str] = Field(..., description="The SQL statements to execute")
    database_name: Optional[str] = Field(
        None, description="Optional database name (defaults to neondb)"
    )
    branch_id: Optional[str] = Field(
        None, description="Optional branch ID (defaults to main branch)"
    )

    @model_validator(mode="after")
    def validate_sql_statements(self) -> "RunSQLTransactionParams":
        """Validate that at least one SQL statement is provided and none are empty."""
        if not self.sql_statements:
            raise ValueError("At least one SQL statement is required")

        for i, stmt in enumerate(self.sql_statements):
            if not stmt.strip():
                raise ValueError(f"SQL statement at index {i} cannot be empty")

        return self


class CreateBranchParams(BaseParams):
    """Parameters for the create_branch method."""

    project_id: str = Field(..., description="The ID of the project")
    branch_name: Optional[str] = Field(None, description="Optional name for the branch")


class DescribeBranchParams(BaseParams):
    """Parameters for the describe_branch method."""

    project_id: str = Field(..., description="The ID of the project")
    branch_id: str = Field(..., description="The ID of the branch to describe")
    database_name: Optional[str] = Field(None, description="Optional database name")


class DeleteBranchParams(BaseParams):
    """Parameters for the delete_branch method."""

    project_id: str = Field(..., description="The ID of the project")
    branch_id: str = Field(..., description="The ID of the branch to delete")


class ConnectionStringParams(BaseParams):
    """Parameters for the get_connection_string method."""

    project_id: str = Field(..., description="The ID of the project")
    branch_id: Optional[str] = Field(None, description="Optional branch ID")
    database_name: Optional[str] = Field(None, description="Optional database name")
    role_name: Optional[str] = Field(None, description="Optional role name")
    compute_id: Optional[str] = Field(None, description="Optional compute ID")


class GetDatabaseTablesParams(BaseParams):
    """Parameters for the get_database_tables method."""

    project_id: str = Field(..., description="The ID of the project")
    branch_id: Optional[str] = Field(None, description="Optional branch ID")
    database_name: Optional[str] = Field(None, description="Optional database name")


class DescribeTableSchemaParams(BaseParams):
    """Parameters for the describe_table_schema method."""

    project_id: str = Field(..., description="The ID of the project")
    table_name: str = Field(..., description="The name of the table")
    branch_id: Optional[str] = Field(None, description="Optional branch ID")
    database_name: Optional[str] = Field(None, description="Optional database name")


# Response Models


class BaseResponse(BaseModel):
    """Base model for all response models."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NeonProject(BaseModel):
    """Model representing a Neon project."""

    id: str
    name: str
    region_id: str
    pg_version: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class NeonBranch(BaseModel):
    """Model representing a Neon branch."""

    id: str
    project_id: str
    name: str
    parent_id: Optional[str] = None
    parent_lsn: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ProjectResponse(BaseResponse):
    """Response model for project operations."""

    project: NeonProject


class ProjectListResponse(BaseResponse):
    """Response model for listing projects."""

    projects: List[NeonProject]


class BranchResponse(BaseResponse):
    """Response model for branch operations."""

    branch: NeonBranch


class ConnectionStringResponse(BaseResponse):
    """Response model for connection string operations."""

    connection_string: str


class SQLResult(BaseModel):
    """Model representing SQL query results."""

    rows: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    rowCount: Optional[int] = None
    command: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class SQLResponse(BaseResponse):
    """Response model for SQL operations."""

    results: List[SQLResult]


class TableResponse(BaseResponse):
    """Response model for table information."""

    name: str
    schema: str
    columns: Optional[List[Dict[str, Any]]] = None


class GetDatabaseTablesResponse(BaseResponse):
    """Response model for get_database_tables method."""

    tables: List[TableResponse]


class DescribeTableSchemaResponse(BaseResponse):
    """Response model for describe_table_schema method."""

    columns: List[Dict[str, Any]]
    constraints: Optional[List[Dict[str, Any]]] = None
    indexes: Optional[List[Dict[str, Any]]] = None
