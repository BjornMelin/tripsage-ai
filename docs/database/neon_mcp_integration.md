# Neon DB MCP Integration

This document describes the implementation of Neon DB MCP integration within TripSage,
focusing on its role in the development workflow.

## Overview

TripSage uses a dual database architecture:

1. **Development Environment**: [Neon DB](https://neon.tech) via MCP integration
2. **Production Environment**: Supabase PostgreSQL 

The Neon DB MCP server provides a serverless PostgreSQL database with excellent development
features like database branching, query analysis, and connection pooling.

## External MCP Server Integration

TripSage integrates with the official `mcp-server-neon` package as an external dependency
rather than implementing a custom Neon MCP server. This approach offers several advantages:

1. **Standardization**: Ensures compliance with MCP protocol specifications
2. **Maintenance**: Reduces codebase complexity by delegating to maintained packages
3. **Updates**: Automatically benefits from updates to the official implementation
4. **Functionality**: Provides full access to Neon's serverless PostgreSQL capabilities

## Key Components

The integration consists of these primary components:

### 1. Configuration (settings.py)

```python
class NeonMCPConfig(MCPConfig):
    """Neon MCP server configuration."""

    # Whether to use this MCP in development environment only
    dev_only: bool = Field(default=True)
    # Default project ID for operations (optional)
    default_project_id: Optional[str] = None
```

The configuration is defined in `src/utils/settings.py` and loaded through environment variables.

### 2. Client Implementation (client.py)

The `NeonMCPClient` class provides a comprehensive interface to the Neon DB MCP Server:

```python
class NeonMCPClient(FastMCPClient, Generic[P, R]):
    """Client for the Neon MCP Server focused on development environments."""
    
    # Client methods include:
    # - Project operations (list_projects, create_project, etc.)
    # - SQL operations (run_sql, run_sql_transaction)
    # - Branch operations (create_branch, delete_branch, etc.)
    # - Schema operations (get_database_tables, describe_table_schema)
```

### 3. Service Layer (service.py)

The `NeonService` class offers higher-level functionality built on top of the client:

```python
class NeonService:
    """High-level service for Neon database operations in TripSage."""
    
    # Service methods include:
    # - create_development_branch
    # - apply_migrations
    # - get_default_project
    # - get_database_schema
```

### 4. Factory Integration (db_factory.py)

The `DatabaseMCPFactory` automatically selects the appropriate database client based on
the environment:

```python
def get_mcp_client(environment: Optional[str] = None) -> Union[NeonMCPClient, SupabaseMCPClient]:
    """Get the appropriate database MCP client based on the environment."""
    if environment is None:
        environment = settings.environment

    if environment.lower() in [Environment.DEVELOPMENT, Environment.TESTING]:
        return get_neon_client()
    else:
        return get_supabase_client()
```

## Usage in Development Workflows

The Neon DB MCP integration is specifically designed for development workflows, providing:

1. **Isolated Development Environments**: Each developer can work with their own database branch
2. **Testing with Database Branches**: Unit and integration tests use dedicated branches
3. **Migration Testing**: Test database migrations safely before applying to production
4. **Schema Exploration**: View and analyze database schema during development

## Example: Creating a Development Branch

```python
from src.mcp.db_factory import DatabaseMCPFactory

# Get the Neon service
neon_service = DatabaseMCPFactory.get_development_service()

# Create a development branch
branch_info = await neon_service.create_development_branch(
    branch_name="feature-123"
)

# Get connection string
connection_string = branch_info["connection_string"]

# Use the connection string with any PostgreSQL client
# ...

# Apply migrations to the branch
await neon_service.apply_migrations(
    project_id=branch_info["project_id"],
    branch_id=branch_info["branch"]["id"],
    migrations=["CREATE TABLE test (id SERIAL PRIMARY KEY);"]
)
```

## Environment Configuration

To enable Neon DB MCP in your development environment, add these settings to your `.env` file:

```
# Neon MCP Configuration
NEON_MCP_ENDPOINT=http://localhost:8099
NEON_MCP_API_KEY=your_api_key_here
NEON_MCP_DEV_ONLY=true
NEON_MCP_DEFAULT_PROJECT_ID=optional_default_project_id
```

## Integration Tests

The test suite includes verification of the Neon DB MCP integration:

1. **Client Tests**: Verify client functionality with mock responses
2. **Service Tests**: Test higher-level service operations
3. **Factory Tests**: Confirm proper client selection based on environment
4. **External Connection Tests**: Validate connection to the external MCP server