# TripSage Centralized Settings System Guide

This document provides an overview and guide to the centralized configuration system used in the TripSage application, based on Pydantic's `BaseSettings`.

## 1. Overview

TripSage employs a centralized settings system to manage all application configurations. This system leverages Pydantic's `BaseSettings` class, which allows for type-safe configuration loading from environment variables, `.env` files, or default values defined in code. This approach replaces scattered configuration files and direct environment variable access, promoting consistency, maintainability, and robustness.

## 2. Key Benefits

*   **Single Source of Truth**: All application configurations are defined and accessed from a single, hierarchical structure.
*   **Type Safety and Validation**: Pydantic automatically validates that configuration values conform to their defined types (e.g., `str`, `int`, `bool`, `SecretStr`, nested models) and constraints (e.g., min/max values, patterns). This catches configuration errors at application startup.
*   **Environment Variable Overrides**: All settings can be easily overridden by environment variables, which is standard practice for modern deployments (e.g., Docker, Kubernetes).
*   **`.env` File Support**: Pydantic `BaseSettings` can automatically load configurations from a `.env` file in the project root, simplifying local development setup.
*   **Default Values**: Sensible default values can be provided directly in the settings model definitions.
*   **Secrets Handling**: Pydantic's `SecretStr` type is used for sensitive values like API keys and passwords, preventing them from being accidentally exposed in logs or tracebacks.
*   **Clear Documentation**: Settings are self-documenting through their Pydantic model definitions (field names, types, descriptions, defaults).
*   **Hierarchical Structure**: Settings can be organized into nested Pydantic models for better clarity and management (e.g., `DatabaseSettings`, `MCPServerSettings`).

## 3. Core Settings Structure (`src/utils/config.py` or similar)

The heart of the system is typically an `AppSettings` class.

```python
# src/utils/config.py (Illustrative Structure)
from typing import Optional, Dict, List
from pydantic import Field, SecretStr, HttpUrl, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict # For Pydantic v2 pydantic-settings

# --- Individual Service Configurations ---
class DatabasePrimaryConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_DB_PRIMARY_') # Example prefix
    
    url: PostgresDsn = "postgresql://user:pass@host:port/db"
    pool_size: int = Field(default=5, ge=1)
    # ... other primary DB settings

class Neo4jGraphConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_NEO4J_')
    
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: Optional[SecretStr] = None
    database: str = "neo4j"
    # ... other Neo4j settings

class RedisCacheConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_REDIS_')
    
    url: RedisDsn = "redis://localhost:6379/0"
    default_ttl_seconds: int = Field(default=3600, ge=60)
    # ... other Redis settings

class OpenAIServiceConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_OPENAI_')
    
    api_key: Optional[SecretStr] = None
    default_model: str = "gpt-4o"
    # ... other OpenAI settings

# --- MCP Server Specific Configurations ---
class BaseMCPServiceConfig(BaseSettings):
    # Common fields for all MCP server client configs
    endpoint: HttpUrl
    api_key: Optional[SecretStr] = None # API key for the MCP server itself, if secured
    timeout_seconds: int = Field(default=30, ge=5)

class WeatherMCPConfig(BaseMCPServiceConfig):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_MCP_WEATHER_')
    # Specific settings for Weather MCP, if any, beyond BaseMCPServiceConfig
    # e.g., primary_provider_api_key: Optional[SecretStr] = None (if WeatherMCP needs its own keys)

class FlightsMCPConfig(BaseMCPServiceConfig):
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_MCP_FLIGHTS_')
    # e.g., duffel_api_key: Optional[SecretStr] = None (if FlightsMCP needs its own keys)

# ... other MCP configurations (Memory, WebCrawl, Calendar, GoogleMaps, Accommodations, etc.)

class MCPServersConfig(BaseSettings):
    # This model groups all MCP client configurations
    weather: WeatherMCPConfig = WeatherMCPConfig(endpoint="http://localhost:3003") # Default endpoint
    flights: FlightsMCPConfig = FlightsMCPConfig(endpoint="http://localhost:3002")
    # memory: MemoryMCPConfig = ...
    # webcrawl: WebCrawlMCPConfig = ...
    # ... add all other MCPs

# --- Main Application Settings ---
class AppSettings(BaseSettings):
    # Pydantic Settings configuration
    model_config = SettingsConfigDict(
        env_file='.env',              # Load from .env file
        env_file_encoding='utf-8',
        extra='ignore',               # Ignore extra fields from env/dotenv
        case_sensitive=False          # Environment variables are case-insensitive
    )

    # Top-level application settings
    environment: str = Field(default="development", pattern="^(development|staging|production|testing)$")
    debug: bool = False
    app_name: str = "TripSage AI"
    api_port: int = Field(default=8000, ge=1024, le=65535)
    
    # JWT Settings (example for backend auth)
    jwt_secret_key: SecretStr = "your-default-super-secret-key" # MUST be overridden in prod
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Nested configuration models
    primary_database: DatabasePrimaryConfig = DatabasePrimaryConfig()
    knowledge_graph_db: Neo4jGraphConfig = Neo4jGraphConfig()
    cache_db: RedisCacheConfig = RedisCacheConfig()
    openai_config: OpenAIServiceConfig = OpenAIServiceConfig()
    mcp_servers: MCPServersConfig = MCPServersConfig()

    # Example of a validator
    @model_validator(mode="after")
    def check_production_debug_off(self) -> 'AppSettings':
        if self.environment == "production" and self.debug:
            raise ValueError("DEBUG mode must be disabled in production environment.")
        return self
    
    @model_validator(mode="after")
    def ensure_openai_key_if_not_dev(self) -> 'AppSettings':
        if self.environment != "development" and (not self.openai_config.api_key or not self.openai_config.api_key.get_secret_value()):
            # In dev, might allow no key for local LLM or mocked tests
            # logger.warning("OpenAI API key is not set. AI features may be limited.")
            pass # Or raise ValueError if strictly required
        return self

# --- Global Settings Instance ---
# This instance is created once and imported throughout the application
try:
    settings = AppSettings()
except Exception as e: # Catch Pydantic's ValidationError or others during init
    # logger.critical(f"Failed to load application settings: {e}", exc_info=True)
    # sys.exit(1) # Critical failure, exit
    raise # Re-raise for handling by an init function

# --- Initialization Function (Optional, for explicit loading/validation) ---
# src/utils/settings_init.py
# def init_settings() -> AppSettings:
#     try:
#         loaded_settings = AppSettings()
#         # Perform additional cross-setting validations if needed
#         # logger.info(f"Application settings loaded for environment: {loaded_settings.environment}")
#         return loaded_settings
#     except ValidationError as e:
#         # logger.critical(f"Configuration validation error: {e.errors()}")
#         # sys.exit(1)
#         raise
```

## 4. Usage in Application Code

To access settings within any part of the TripSage application:

```python
from src.utils.config import settings # Assuming settings.py is in src/utils/

# Accessing a top-level setting
if settings.debug:
    # logger.setLevel(logging.DEBUG)
    pass

# Accessing a nested setting
primary_db_url = settings.primary_database.url
flights_mcp_endpoint = settings.mcp_servers.flights.endpoint

# Accessing a secret value (Pydantic's SecretStr handles this)
openai_api_key_value = settings.openai_config.api_key.get_secret_value() if settings.openai_config.api_key else None

# Using settings to configure a client
# class SomeApiClient:
#     def __init__(self):
#         self.base_url = settings.some_external_api.base_url
#         self.api_key = settings.some_external_api.api_key.get_secret_value()
```

## 5. Environment Variables and `.env` File

Pydantic `BaseSettings` automatically loads values from environment variables. Variable names are constructed by:
1.  Optional `env_prefix` from `model_config` (e.g., `TRIPSAGE_DB_PRIMARY_`).
2.  The setting name (e.g., `URL`).
Nested models also contribute their parent's name to the prefix. For example, `mcp_servers.weather.endpoint` would correspond to an environment variable like `TRIPSAGE_MCP_SERVERS_WEATHER_ENDPOINT` (if `TRIPSAGE_` is a global prefix and `MCP_SERVERS_` and `WEATHER_` are prefixes from nested models or field names). Pydantic typically handles the nesting by looking for `PARENTMODEL_NESTEDMODEL_FIELDNAME`.

*   **`.env` File**: Create a `.env` file in the project root for local development. This file is loaded automatically if `env_file='.env'` is set in `model_config`.
    ```plaintext
    # .env example
    TRIPSAGE_ENVIRONMENT="development"
    TRIPSAGE_DEBUG="True"
    TRIPSAGE_API_PORT="8001"

    TRIPSAGE_OPENAI_API_KEY="sk-yourkey"
    
    TRIPSAGE_PRIMARY_DATABASE_URL="postgresql://devuser:devpass@localhost:5432/tripsage_dev"
    
    TRIPSAGE_MCP_SERVERS_WEATHER_ENDPOINT="http://127.0.0.1:7001" 
    # Note: Pydantic v2 BaseSettings might form this as TRIPSAGE_MCP_SERVERS__WEATHER__ENDPOINT
    # Check pydantic-settings documentation for exact env var naming with nested models.
    # Often it's PARENT_FIELD_NAME__CHILD_FIELD_NAME (double underscore for nesting).
    ```
*   **`.env.example`**: Maintain an `.env.example` file in the repository. This file should list all possible environment variables with placeholders or default values, serving as a template for users. **Do not commit the actual `.env` file with secrets.**

## 6. Extending Settings

To add new settings:
1.  Identify the appropriate Pydantic model in `src/utils/config.py` (or create a new nested model if needed).
2.  Add the new field with its type hint, a `Field` definition (including `default` and `description`), and any validators.
3.  Update the `.env.example` file to include the new environment variable(s).
4.  If the new setting requires specific validation logic during application startup (beyond Pydantic's field/model validation), you might update an `init_settings()` function if you have one.

## 7. Best Practices

*   **Central Import**: Always import the global `settings` instance from your main config module (e.g., `from src.utils.config import settings`). Avoid re-instantiating `AppSettings` elsewhere.
*   **Secrets**: Use `SecretStr` for all sensitive data. Access the actual value using `.get_secret_value()` only when and where it's needed (e.g., when passing to an API client).
*   **Validation**: Leverage Pydantic validators (`@field_validator`, `@model_validator`) to ensure configuration integrity at startup. Fail fast if critical configurations are missing or invalid.
*   **Descriptions**: Provide clear `description` attributes for all `Field` definitions. This self-documents the configuration.
*   **Environment Specificity**: Use the `ENVIRONMENT` setting (`development`, `staging`, `production`, `testing`) to conditionally load other settings or alter application behavior if necessary, but prefer distinct configurations per environment where possible (e.g., different database URLs).
*   **Prefixes**: Use `env_prefix` in `model_config` for nested settings models to avoid naming collisions and keep environment variables organized (e.g., `TRIPSAGE_REDIS_URL`, `TRIPSAGE_NEO4J_URI`).

By adhering to this centralized settings system, TripSage ensures that its configuration is type-safe, easily manageable across different environments, and well-documented.