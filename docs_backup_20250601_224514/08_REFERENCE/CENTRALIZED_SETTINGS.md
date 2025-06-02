# TripSage Centralized Settings System Guide

This document provides an overview and guide to the centralized configuration system used in the TripSage application, based on Pydantic's `BaseSettings`. The system has been unified to support the current architecture with DragonflyDB caching, Mem0 memory, and 7 direct SDK integrations.

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
class DatabaseConfig(BaseSettings):
    """Unified database configuration for Supabase PostgreSQL with pgvector."""
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_DB_')
    
    # Supabase configuration
    supabase_url: str = Field(default="https://test-project.supabase.co")
    supabase_anon_key: SecretStr = Field(default=SecretStr("test-anon-key"))
    supabase_service_role_key: Optional[SecretStr] = Field(default=None)
    supabase_project_id: Optional[str] = Field(default=None)
    supabase_timeout: float = Field(default=60.0)
    
    # pgvector configuration
    pgvector_enabled: bool = Field(default=True)
    vector_dimensions: int = Field(default=1536)

class DragonflyConfig(BaseSettings):
    """DragonflyDB configuration (Redis-compatible with 25x performance)."""
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_DRAGONFLY_')
    
    url: str = Field(default="redis://localhost:6379/0")
    ttl_short: int = Field(default=300, description="TTL for short-lived data (5m)")
    ttl_medium: int = Field(default=3600, description="TTL for medium-lived data (1h)")
    ttl_long: int = Field(default=86400, description="TTL for long-lived data (24h)")
    max_connections: int = Field(default=10000)
    thread_count: int = Field(default=4)

class Mem0Config(BaseSettings):
    """Mem0 memory system configuration."""
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_MEM0_')
    
    vector_store_type: str = Field(default="pgvector")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536)
    max_memories_per_user: int = Field(default=1000)
    similarity_threshold: float = Field(default=0.7)
    max_search_results: int = Field(default=10)

class ExternalServiceConfig(BaseSettings):
    """Configuration for external service integrations."""
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_EXTERNAL_')
    
    # Core LLM service
    openai_api_key: SecretStr = Field(default=SecretStr("test-openai-key"))
    
    # Direct SDK integrations (7 services)
    duffel_api_key: Optional[SecretStr] = Field(default=None)
    google_maps_api_key: Optional[SecretStr] = Field(default=None)
    google_client_id: Optional[SecretStr] = Field(default=None)
    google_client_secret: Optional[SecretStr] = Field(default=None)
    openweathermap_api_key: Optional[SecretStr] = Field(default=None)
    visual_crossing_api_key: Optional[SecretStr] = Field(default=None)
    
    # Crawl4AI service
    crawl4ai_api_url: str = Field(default="http://localhost:8000/api")
    crawl4ai_api_key: Optional[SecretStr] = Field(default=None)

# --- Single MCP Configuration (Airbnb only) ---
class AirbnbMCPConfig(BaseSettings):
    """Configuration for the remaining Airbnb MCP integration."""
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_AIRBNB_MCP_')
    
    endpoint: str = Field(default="http://localhost:3001")
    timeout_seconds: int = Field(default=30, ge=5)
    max_retries: int = Field(default=3)
    cache_ttl: int = Field(default=3600)  # 1 hour for accommodation data

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

    # Unified configuration models
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    dragonfly: DragonflyConfig = Field(default_factory=DragonflyConfig)
    mem0: Mem0Config = Field(default_factory=Mem0Config)
    external_services: ExternalServiceConfig = Field(default_factory=ExternalServiceConfig)
    airbnb_mcp: AirbnbMCPConfig = Field(default_factory=AirbnbMCPConfig)
    
    # BYOK (Bring Your Own Key) configuration
    api_key_master_secret: SecretStr = Field(
        default=SecretStr("master-secret-for-byok-encryption"),
        description="Master secret for BYOK encryption"
    )

    # Example of a validator
    @model_validator(mode="after")
    def check_production_debug_off(self) -> 'AppSettings':
        if self.environment == "production" and self.debug:
            raise ValueError("DEBUG mode must be disabled in production environment.")
        return self
    
    @model_validator(mode="after")
    def validate_production_settings(self) -> 'AppSettings':
        if self.environment == "production":
            # Validate critical service configurations
            if not self.external_services.openai_api_key.get_secret_value():
                raise ValueError("OpenAI API key is required in production")
            
            if self.dragonfly.url == "redis://localhost:6379/0":
                raise ValueError("DragonflyDB must not use localhost in production")
            
            if "test-project.supabase.co" in self.database.supabase_url:
                raise ValueError("Supabase URL must be configured for production")
                
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

# Accessing unified settings
supabase_url = settings.database.supabase_url
dragonfly_url = settings.dragonfly.url
airbnb_mcp_endpoint = settings.airbnb_mcp.endpoint

# Accessing external service keys
openai_api_key = settings.external_services.openai_api_key.get_secret_value()
duffel_api_key = settings.external_services.duffel_api_key.get_secret_value() if settings.external_services.duffel_api_key else None

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
    # .env example for unified architecture
    TRIPSAGE_ENVIRONMENT="development"
    TRIPSAGE_DEBUG="True"
    TRIPSAGE_LOG_LEVEL="INFO"

    # Core LLM service
    TRIPSAGE_EXTERNAL_OPENAI_API_KEY="sk-yourkey"
    
    # Database configuration (Supabase + pgvector)
    TRIPSAGE_DB_SUPABASE_URL="https://your-project.supabase.co"
    TRIPSAGE_DB_SUPABASE_ANON_KEY="your-anon-key"
    TRIPSAGE_DB_SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
    
    # DragonflyDB cache configuration
    TRIPSAGE_DRAGONFLY_URL="redis://localhost:6379/0"
    TRIPSAGE_DRAGONFLY_TTL_SHORT="300"
    TRIPSAGE_DRAGONFLY_TTL_MEDIUM="3600"
    TRIPSAGE_DRAGONFLY_TTL_LONG="86400"
    
    # External service integrations (BYOK)
    TRIPSAGE_EXTERNAL_DUFFEL_API_KEY="duffel_live_your-key"
    TRIPSAGE_EXTERNAL_GOOGLE_MAPS_API_KEY="AIza-your-google-maps-key"
    TRIPSAGE_EXTERNAL_OPENWEATHERMAP_API_KEY="your-weather-key"
    
    # Crawl4AI configuration
    TRIPSAGE_EXTERNAL_CRAWL4AI_API_URL="http://localhost:8000/api"
    
    # Single MCP server (Airbnb)
    TRIPSAGE_AIRBNB_MCP_ENDPOINT="http://localhost:3001"
    
    # Mem0 memory system
    TRIPSAGE_MEM0_VECTOR_STORE_TYPE="pgvector"
    TRIPSAGE_MEM0_EMBEDDING_MODEL="text-embedding-3-small"
    
    # Security
    TRIPSAGE_JWT_SECRET_KEY="your-production-jwt-secret"
    TRIPSAGE_API_KEY_MASTER_SECRET="your-byok-encryption-secret"
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