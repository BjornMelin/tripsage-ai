# TripSage Database MCP Strategy

This document describes the dual database strategy for TripSage, using Neon for development and Supabase for production environments.

## Overview

TripSage uses a dual database strategy to optimize the development workflow while maintaining a robust production environment:

1. **Development Environment**: [Neon PostgreSQL](https://neon.tech/)
   - Serverless postgres with branching capabilities
   - Perfect for development, allowing each branch to have its own isolated database
   - Free tier with generous limits for development work

2. **Production Environment**: [Supabase PostgreSQL](https://supabase.com/)
   - Managed PostgreSQL with robust Row-Level Security (RLS)
   - Built-in auth system and security policies
   - Excellent performance and scaling capabilities

## MCP Integration

TripSage leverages the MCP (Model Context Protocol) approach for both database providers, implementing specialized MCP clients that make it easy to switch between development and production environments.

### Key Components

1. **NeonMCPClient**: For development environments
   - Branch management capabilities
   - SQL execution and transaction support
   - Project creation and management
   - Connection string generation

2. **SupabaseMCPClient**: For production environments
   - Project management
   - SQL execution and transaction support
   - Row-Level Security management
   - Edge function deployment
   - TypeScript type generation

3. **DatabaseMCPFactory**: Factory to select the appropriate client based on the environment
   - Automatically selects the right client based on the current environment
   - Provides direct access to specific environment clients when needed

## Environment Selection Logic

```python
def get_mcp_client(environment: Optional[str] = None) -> Union[NeonMCPClient, SupabaseMCPClient]:
    """Get the appropriate database MCP client based on the environment."""
    if environment is None:
        environment = settings.environment

    if environment.lower() in ["development", "testing"]:
        return get_neon_client()
    else:
        return get_supabase_client()
```

## Configuration Settings

The database MCP configuration is part of the centralized settings system:

```python
class NeonMCPConfig(MCPConfig):
    """Neon MCP server configuration."""
    dev_only: bool = Field(default=True)
    default_project_id: Optional[str] = None


class SupabaseMCPConfig(MCPConfig):
    """Supabase MCP server configuration."""
    prod_only: bool = Field(default=True)
    default_project_id: Optional[str] = None
    default_organization_id: Optional[str] = None
```

Required environment variables:

```bash
# Neon Database MCP (Development)
NEON_MCP_ENDPOINT=http://localhost:8099
NEON_MCP_API_KEY=your_neon_api_key
NEON_MCP_DEFAULT_PROJECT_ID=your_default_project_id

# Supabase Database MCP (Production)
SUPABASE_MCP_ENDPOINT=http://localhost:8098
SUPABASE_MCP_API_KEY=your_supabase_api_key
SUPABASE_MCP_DEFAULT_PROJECT_ID=your_default_project_id
SUPABASE_MCP_DEFAULT_ORGANIZATION_ID=your_default_organization_id
```

## Common Operations

### Creating Development Branches

Each Git branch can have its own isolated database branch:

```python
from src.mcp.db_factory import db_mcp_factory

async def create_dev_branch_for_feature():
    # Get the Neon service
    neon_service = db_mcp_factory.get_development_service()
    
    # Create a branch based on the git branch name
    git_branch = get_current_git_branch()
    branch_info = await neon_service.create_development_branch(
        branch_name=f"db-{git_branch}"
    )
    
    # Store connection string in .env.local
    connection_string = branch_info["connection_string"]
    update_env_file(".env.local", "NEON_CONNECTION_STRING", connection_string)
```

### Applying Migrations

```python
from src.mcp.db_factory import db_mcp_factory

async def apply_migrations_to_production():
    # Get the Supabase service
    supabase_service = db_mcp_factory.get_production_service()
    
    # Get migration files from migrations directory
    migration_files = get_migration_files("migrations/")
    
    # Apply migrations
    result = await supabase_service.apply_migrations(
        project_id=settings.supabase_mcp.default_project_id,
        migrations=migration_files,
        migration_names=[file.name for file in migration_files]
    )
    
    print(f"Applied {result['migrations_applied']} migrations")
```

## Testing Considerations

When testing database operations, the appropriate MCP client should be selected based on the test environment:

```python
@pytest.fixture
def db_mcp_client():
    """Get the appropriate database MCP client for testing."""
    return db_mcp_factory.get_client("testing")
```

This allows tests to run against isolated Neon database branches without affecting the production environment.

## Best Practices

1. **Environment Awareness**: Always be aware of which environment you're working in
   - Development: Use Neon for isolated, disposable databases
   - Production: Use Supabase with proper RLS policies

2. **Migration Management**: Maintain migrations in SQL files and apply them systematically
   - Track migrations with version numbers and descriptions
   - Test migrations on development branches before applying to production

3. **Connection Pooling**: Use appropriate connection pooling settings for each environment
   - Development: Lower pool sizes for local work
   - Production: Higher pool sizes for concurrent operations

4. **Security**: Apply appropriate security measures in each environment
   - Development: Basic security is sufficient
   - Production: Strict RLS policies and secret management

5. **Branch Management**: Clean up unused Neon branches
   - Remove branches when feature development is complete
   - Avoid accumulating unused branches to stay within free tier limits