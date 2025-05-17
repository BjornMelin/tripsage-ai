# TripSage Centralized Settings System

This document provides an overview of the centralized configuration system for the TripSage application.

## Overview

TripSage now uses a centralized settings system based on Pydantic Settings. All configuration is managed through a single `AppSettings` class that loads settings from environment variables or a `.env` file. This replaces the previous approach of having multiple separate configuration files and direct environment variable access scattered throughout the codebase.

## Key Benefits

- **Single Source of Truth**: All configuration is defined in one place
- **Type Safety**: Settings are typed and validated using Pydantic
- **Environment Variables**: All settings can be configured through environment variables
- **Default Values**: Sensible defaults are provided where appropriate
- **Validation**: Configuration values are validated at startup
- **Secrets Handling**: Sensitive values are handled securely
- **Documentation**: Each setting is documented with a clear description

## Usage

### Accessing Settings

To access application settings in your code, import the `settings` instance from the settings module:

```python
from src.utils.settings import settings

# Access a top-level setting
debug_mode = settings.debug

# Access a nested setting
supabase_url = settings.database.supabase_url

# Access a secret value (returns the actual value, not the SecretStr wrapper)
api_key = settings.openai_api_key.get_secret_value()
```

### Application Startup

The application should initialize the settings at startup:

```python
from src.utils.settings_init import init_settings

def startup():
    # Initialize and validate settings
    settings = init_settings()
    
    # Continue with application initialization
    # ...
```

### Configuration Structure

The settings system is organized hierarchically:

- **Top-level settings**: Basic application settings like `debug`, `environment`, `port`
- **Nested settings**: Grouped by functionality (database, MCP servers, etc.)
  - `database`: Database configuration (Supabase, Neon)
  - `neo4j`: Neo4j database configuration
  - `redis`: Redis cache configuration
  - `agent`: Agent configuration
  - MCP servers: Configuration for each MCP server (`weather_mcp`, `webcrawl_mcp`, etc.)

## Environment Variables

All settings can be configured through environment variables. The `.env.example` file at the root of the project lists all available settings with their default values and descriptions.

To configure the application:

1. Copy `.env.example` to `.env`
2. Edit `.env` to set your configuration values
3. The application will load these values at startup

### Example Environment Variables

```
# Application settings
DEBUG=false
ENVIRONMENT=development
PORT=8000

# API Keys
OPENAI_API_KEY=your_openai_api_key_here

# Database - Supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

## Extending Settings

To add new settings:

1. Update the `AppSettings` class in `src/utils/settings.py`
2. Add the new settings with appropriate types and documentation
3. Update the `.env.example` file with the new settings
4. If necessary, update the `init_settings` function in `src/utils/settings_init.py` to validate the new settings

Example of adding a new setting:

```python
class AppSettings(BaseSettings):
    # Existing settings...
    
    # New setting
    new_feature_enabled: bool = Field(default=False, description="Enable the new feature")
```

## Best Practices

- Always use the centralized settings system instead of direct environment variable access
- For sensitive data, use `SecretStr` and access values with `.get_secret_value()`
- Validate critical settings at application startup
- Document all settings in the class definitions and in `.env.example`
- Use sensible default values where appropriate
- Group related settings into nested models for better organization
