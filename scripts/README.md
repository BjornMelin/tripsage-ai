# Scripts Directory Structure

This directory contains various scripts used for managing and operating the TripSage system. The scripts are organized into subdirectories based on their functionality.

## Directory Organization

### `/mcp/`

MCP server management scripts for launching and controlling Model Context Protocol servers.

- `mcp_launcher.py` - Main unified launcher for all MCP servers
- `mcp_launcher_simple.py` - Simplified launcher for testing and development

### `/database/`

Database initialization and migration scripts.

- `init_database.py` - Database initialization script
- `run_migrations.py` - Database migration runner
- `setup_neo4j.sh` - Neo4j setup script

### `/startup/`

Server startup and shutdown scripts for individual MCP servers.

- `start_*.sh` - Scripts to start specific MCP servers
- `stop_*.sh` - Scripts to stop specific MCP servers

### `/verification/`

Connection verification scripts for testing database and service connectivity.

- `verify_connection.js` - JavaScript connection verification
- `verify_connection.py` - Python connection verification

### `/templates/`

Template files used by various scripts.

## Usage Examples

### Starting MCP Servers

```bash
# Using the unified launcher
python scripts/mcp/mcp_launcher.py start supabase

# Using individual startup scripts
./scripts/startup/start_time_mcp.sh
```

### Database Operations

```bash
# Initialize the database
python scripts/database/init_database.py

# Run migrations
python scripts/database/run_migrations.py
```

### Verification

```bash
# Verify database connection
node scripts/verification/verify_connection.js
```

## Testing

Integration tests for these scripts are located in `/tests/integration/`, organized by functionality:

- `/tests/integration/mcp/` - MCP-related tests
- `/tests/integration/api/` - API integration tests
- `/tests/integration/database/` - Database connection tests
