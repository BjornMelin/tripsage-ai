# Supabase MCP Integration

This document outlines the Supabase MCP integration in TripSage, focused on production environments. Unlike the Neon MCP which is used for development and testing, Supabase MCP is designed for production deployment with enhanced reliability, security, and scalability.

## Overview

TripSage implements a dual-database architecture:
- **Development/Testing**: Uses Neon DB MCP
- **Production/Staging**: Uses Supabase MCP

The Supabase MCP integration provides PostgreSQL database management capabilities through the external `supabase-mcp` package, ensuring standardized Model Context Protocol (MCP) interface for database operations in production environments.

## Key Components

### 1. SupabaseMCPConfig

The `SupabaseMCPConfig` class in `src/utils/settings.py` defines the configuration parameters for the Supabase MCP:

```python
class SupabaseMCPConfig(MCPConfig):
    """Supabase MCP server configuration."""

    # Whether to use this MCP in production environment only
    prod_only: bool = Field(default=True)
    # Default project ID for operations (optional)
    default_project_id: Optional[str] = None
    # Default organization ID (optional)
    default_organization_id: Optional[str] = None
```

This configuration is included in the main `AppSettings` class and validated at application startup.

### 2. SupabaseMCPClient

The `SupabaseMCPClient` class in `src/mcp/supabase/client.py` implements the client for interacting with the Supabase MCP server. It extends the base `FastMCPClient` class and provides methods for:

- Project management (create, pause, restore)
- Database operations (execute SQL, apply migrations)
- Branch management (create, list, merge, rebase)
- Organization management
- Edge functions deployment

Example usage:

```python
from src.mcp.supabase.client import get_client

# Get the client
client = get_client()

# List projects
projects = await client.list_projects()

# Execute SQL query
result = await client.execute_sql(
    project_id="your-project-id",
    query="SELECT * FROM users WHERE id = :user_id",
    params={"user_id": 123}
)
```

### 3. SupabaseService

The `SupabaseService` class in `src/mcp/supabase/service.py` provides higher-level operations using the client:

- Getting or creating a default project
- Applying multiple migrations
- Creating development branches

Example usage:

```python
from src.mcp.supabase.service import get_service

# Get the service
service = get_service()

# Get or create the default project
project = await service.get_default_project()

# Apply migrations
migrations = [
    "CREATE TABLE users (id SERIAL PRIMARY KEY, name TEXT)",
    "CREATE TABLE posts (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id))"
]
migration_names = ["create_users_table", "create_posts_table"]
result = await service.apply_migrations(
    project_id=project["id"],
    migrations=migrations,
    migration_names=migration_names
)
```

### 4. Factory Pattern

The database client/service factory in `src/mcp/db_factory.py` determines which database provider to use based on the current environment:

```python
def get_mcp_client(environment: Optional[str] = None) -> Union[NeonMCPClient, SupabaseMCPClient]:
    """Get the appropriate database MCP client based on the environment."""
    if environment is None:
        environment = settings.environment
    
    if environment.lower() in [Environment.DEVELOPMENT, Environment.TESTING]:
        logger.info(f"Using NeonMCPClient for {environment} environment")
        return get_neon_client()
    else:
        logger.info(f"Using SupabaseMCPClient for {environment} environment")
        return get_supabase_client()
```

## External MCP Server Integration

TripSage integrates with the official `supabase-mcp` package as an external dependency rather than implementing a custom Supabase MCP server. This approach offers several advantages:

1. **Standardization**: Ensures compliance with MCP protocol specifications
2. **Maintenance**: Reduces codebase complexity by delegating to maintained packages
3. **Updates**: Automatically benefits from updates to the official implementation
4. **Functionality**: Provides full access to Supabase's PostgreSQL capabilities

## Deployment Considerations

When deploying to production, ensure:

1. All required environment variables are set:
   - `SUPABASE_MCP_ENDPOINT`
   - `SUPABASE_MCP_API_KEY`
   - `ENVIRONMENT=production`

2. Proper validation of database credentials during application startup
3. Health checks for database connectivity
4. Appropriate error handling and retry logic

## Testing

The Supabase MCP integration includes unit tests and integration tests:

- **Unit tests**: Test the client and service classes with mocked responses
- **Integration tests**: Test the interaction with an actual Supabase MCP server (requires configuration)

To run tests that require a live Supabase MCP server:

```bash
SUPABASE_MCP_TEST=1 python -m pytest tests/mcp/supabase/test_external_supabase_mcp.py -v
```

## Environment-Specific Behavior

The Supabase MCP is configured to only be used in production environments (`prod_only=True`). This ensures:

1. Development environments use Neon DB, which is better suited for local development
2. Production environments use Supabase, which offers managed hosting and enterprise features
3. A clear separation between development and production data

## Service Account Authentication

For production deployments, it's recommended to use a service account with the appropriate permissions rather than the anonymous key. This can be configured through the `SUPABASE_SERVICE_ROLE_KEY` environment variable.

## Related Documentation

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase MCP Reference](https://github.com/supabase-community/supabase-mcp)
- [TripSage Database Architecture](./README.md)
- [Neon MCP Integration](./neon_mcp_integration.md)