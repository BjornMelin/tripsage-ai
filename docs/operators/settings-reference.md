# TripSage Centralized Settings Reference

> Configuration system using Pydantic v2 BaseSettings
> Type-safe configuration with environment variable support
> SecretStr for sensitive values

This document covers TripSage's centralized configuration system using Pydantic's BaseSettings for configuration management.

## Table of Contents

- [System Overview](#system-overview)
- [Settings Architecture](#settings-architecture)
- [Configuration Models](#configuration-models)
- [Environment Variables](#environment-variables)
- [Usage Patterns](#usage-patterns)
- [Security Practices](#security-practices)
- [Development Workflow](#development-workflow)
- [Production Considerations](#production-considerations)
- [Future Considerations](#future-considerations)

## System Overview

TripSage uses Pydantic's BaseSettings for configuration management across environments, supporting Redis caching, Mem0 memory system, and BYOK management.

### Architecture Principles

- Single Source of Truth: Configurations defined in hierarchical structure
- Type Safety: Validation with Pydantic models
- Environment Flexibility: Overrides via environment variables
- Security: SecretStr for sensitive data
- Validation: At application startup

## Settings Architecture

### Core Configuration Structure

```python
# tripsage_core/config/base_app_settings.py
from typing import Optional, Dict, List
from pydantic import Field, SecretStr, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    """Main application settings with hierarchical configuration."""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=False
    )
    
    # Core application settings
    environment: str = Field(
        default="development", 
        pattern="^(development|staging|production|testing)$"
    )
    debug: bool = Field(default=False)
    app_name: str = Field(default="TripSage AI")
    api_port: int = Field(default=8000, ge=1024, le=65535)
    
    # Nested configuration models
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    mem0: Mem0Config = Field(default_factory=Mem0Config)
    external_services: ExternalServiceConfig = Field(default_factory=ExternalServiceConfig)
    airbnb_mcp: AirbnbMCPConfig = Field(default_factory=AirbnbMCPConfig)
    
    # Security settings
    jwt_secret_key: SecretStr = Field(
        default=SecretStr("dev-secret-key"),
        description="JWT signing secret - override in production"
    )
    api_key_master_secret: SecretStr = Field(
        default=SecretStr("byok-encryption-secret"),
        description="Master secret for BYOK encryption"
    )
    
    @model_validator(mode="after")
    def validate_production_settings(self) -> 'AppSettings':
        """Validate critical settings for production environment."""
        if self.environment == "production":
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")
            
            if not self.external_services.openai_api_key.get_secret_value():
                raise ValueError("OpenAI API key is required in production")
            
            # Use managed Redis (e.g., Upstash) for production caching
            if not getattr(self, "cache", None):
                raise ValueError("Cache configuration is required in production")
                
        return self
```

## Configuration Models

### 1. Database Configuration

```python
class DatabaseConfig(BaseSettings):
    """Database configuration for Supabase PostgreSQL with pgvector."""
    
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_DB_')
    
    # Supabase configuration
    supabase_url: str = Field(
        default="https://test-project.supabase.co",
        description="Supabase project URL"
    )
    supabase_anon_key: SecretStr = Field(
        default=SecretStr("test-anon-key"),
        description="Supabase anonymous key"
    )
    supabase_service_role_key: Optional[SecretStr] = Field(
        default=None,
        description="Supabase service role key"
    )
    supabase_project_id: Optional[str] = Field(
        default=None,
        description="Supabase project identifier"
    )
    supabase_timeout: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
        description="Database connection timeout in seconds"
    )
    
    # pgvector configuration
    pgvector_enabled: bool = Field(
        default=True,
        description="Enable pgvector extension for embeddings"
    )
    vector_dimensions: int = Field(
        default=1536,
        ge=512,
        le=3072,
        description="Vector embedding dimensions"
    )
```

### 2. Cache (Redis / Upstash) Configuration

```python
class CacheConfig(BaseSettings):
    """Redis/Upstash cache configuration."""

    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_CACHE_')

    # TCP Redis URL (use Upstash "Redis (TLS)" endpoint in production)
    # Example: rediss://default:password@<host>:<port>/0
    redis_url: str | None = Field(default=None, description="Redis connection URL")

    # Optional REST credentials for Upstash (used by Node/edge runtimes)
    upstash_redis_rest_url: str | None = Field(default=None)
    upstash_redis_rest_token: str | None = Field(default=None)

    # Pool and TTLs
    redis_max_connections: int = Field(default=1000, ge=1, le=50000)
    cache_hot_ttl: int = Field(default=300, description="Hot TTL (seconds)")
    cache_warm_ttl: int = Field(default=3600, description="Warm TTL (seconds)")
    cache_cold_ttl: int = Field(default=86400, description="Cold TTL (seconds)")
```

### 3. Mem0 Memory System Configuration

```python
class Mem0Config(BaseSettings):
    """Mem0 memory system configuration."""
    
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_MEM0_')
    
    vector_store_type: str = Field(
        default="pgvector",
        pattern="^(pgvector|qdrant|chroma)$",
        description="Vector store backend type"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model name"
    )
    embedding_dimensions: int = Field(
        default=1536,
        ge=512,
        le=3072,
        description="Embedding vector dimensions"
    )
    max_memories_per_user: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Maximum memories stored per user"
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.1,
        le=1.0,
        description="Similarity threshold for memory retrieval"
    )
    max_search_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results returned from memory search"
    )
```

### 4. External Services Configuration

```python
class ExternalServiceConfig(BaseSettings):
    """Configuration for external service integrations."""
    
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_EXTERNAL_')
    
    # Core LLM service
    openai_api_key: SecretStr = Field(
        default=SecretStr("test-openai-key"),
        description="OpenAI API key for LLM operations"
    )
    openai_organization: Optional[str] = Field(
        default=None,
        description="OpenAI organization ID"
    )
    
    # Direct SDK integrations
    duffel_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Duffel API key for flight services"
    )
    google_maps_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Google Maps API key for location services"
    )
    google_client_id: Optional[SecretStr] = Field(
        default=None,
        description="Google OAuth client ID for calendar integration"
    )
    google_client_secret: Optional[SecretStr] = Field(
        default=None,
        description="Google OAuth client secret"
    )
    openweathermap_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenWeatherMap API key for weather services"
    )
    visual_crossing_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Visual Crossing API key for weather data"
    )
    
    # Crawl4AI service configuration
    crawl4ai_api_url: str = Field(
        default="http://localhost:8000/api",
        description="Crawl4AI service endpoint"
    )
    crawl4ai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Crawl4AI API key for authentication"
    )
    
    # Service timeouts and retries
    default_timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Default timeout for external API calls"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests"
    )
```

### 5. MCP Server Configuration (Airbnb Only)

```python
class AirbnbMCPConfig(BaseSettings):
    """Configuration for the Airbnb MCP integration."""
    
    model_config = SettingsConfigDict(env_prefix='TRIPSAGE_AIRBNB_MCP_')
    
    endpoint: str = Field(
        default="http://localhost:3001",
        description="Airbnb MCP server endpoint"
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts"
    )
    cache_ttl: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Cache TTL for accommodation data (1 hour default)"
    )
    rate_limit_per_minute: int = Field(
        default=60,
        ge=10,
        le=1000,
        description="Rate limit for MCP requests per minute"
    )
```

## Environment Variables

### Environment Variable Mapping

The settings system maps environment variables to configuration fields using:

```text
{ENV_PREFIX}_{MODEL_PREFIX}_{FIELD_NAME}
```

### Example Environment Variables

```bash
# Core application settings
TRIPSAGE_ENVIRONMENT="production"
TRIPSAGE_DEBUG="False"
TRIPSAGE_API_PORT="8000"

# Database configuration (Supabase + pgvector)
TRIPSAGE_DB_SUPABASE_URL="https://your-project.supabase.co"
TRIPSAGE_DB_SUPABASE_ANON_KEY="your-anon-key"
TRIPSAGE_DB_SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
TRIPSAGE_DB_PGVECTOR_ENABLED="True"
TRIPSAGE_DB_VECTOR_DIMENSIONS="1536"

# Cache (Redis / Upstash)
TRIPSAGE_CACHE_REDIS_URL="rediss://default:password@your-upstash-host:port/0"
TRIPSAGE_CACHE_REDIS_MAX_CONNECTIONS="1000"
CACHE_HOT_TTL="300"
CACHE_WARM_TTL="3600"
CACHE_COLD_TTL="86400"

# Upstash REST (used by frontend/edge or Node tools)
UPSTASH_REDIS_REST_URL="https://<id>.upstash.io"
UPSTASH_REDIS_REST_TOKEN="<token>"

# External service integrations (BYOK)
TRIPSAGE_EXTERNAL_OPENAI_API_KEY="sk-your-openai-key"
TRIPSAGE_EXTERNAL_DUFFEL_ACCESS_TOKEN="duffel_live_your_access_token"
TRIPSAGE_EXTERNAL_GOOGLE_MAPS_API_KEY="AIza-your-google-maps-key"
TRIPSAGE_EXTERNAL_OPENWEATHERMAP_API_KEY="your-weather-key"

# Mem0 memory system
TRIPSAGE_MEM0_VECTOR_STORE_TYPE="pgvector"
TRIPSAGE_MEM0_EMBEDDING_MODEL="text-embedding-3-small"
TRIPSAGE_MEM0_MAX_MEMORIES_PER_USER="1000"
TRIPSAGE_MEM0_SIMILARITY_THRESHOLD="0.7"

# Single MCP server (Airbnb)
TRIPSAGE_AIRBNB_MCP_ENDPOINT="http://airbnb-mcp:3001"
TRIPSAGE_AIRBNB_MCP_TIMEOUT_SECONDS="30"

# Security settings
TRIPSAGE_JWT_SECRET_KEY="your-production-jwt-secret"
TRIPSAGE_API_KEY_MASTER_SECRET="your-byok-encryption-secret"
```

### .env File Structure

```bash
# .env file for local development
# Core Application
TRIPSAGE_ENVIRONMENT="development"
TRIPSAGE_DEBUG="True"
TRIPSAGE_API_PORT="8000"

# Database (Supabase)
TRIPSAGE_DB_SUPABASE_URL="https://test-project.supabase.co"
TRIPSAGE_DB_SUPABASE_ANON_KEY="test-anon-key"
TRIPSAGE_DB_SUPABASE_SERVICE_ROLE_KEY="test-service-role-key"

# Cache (Upstash Redis)
UPSTASH_REDIS_REST_URL="https://<id>.upstash.io"
UPSTASH_REDIS_REST_TOKEN="<token>"

# External Services (BYOK)
TRIPSAGE_EXTERNAL_OPENAI_API_KEY="sk-your-dev-key"
TRIPSAGE_EXTERNAL_DUFFEL_ACCESS_TOKEN="duffel_test_your_access_token"
TRIPSAGE_EXTERNAL_GOOGLE_MAPS_API_KEY="AIza-your-dev-maps-key"

# Memory System
TRIPSAGE_MEM0_VECTOR_STORE_TYPE="pgvector"

# Security
TRIPSAGE_JWT_SECRET_KEY="dev-jwt-secret-key"
TRIPSAGE_API_KEY_MASTER_SECRET="dev-byok-encryption-secret"
```

## Usage Patterns

### 1. Basic Configuration Access

```python
from tripsage_core.config.base_app_settings import settings

# Access top-level settings
app_environment = settings.environment
debug_mode = settings.debug
api_port = settings.api_port

# Access nested configuration
supabase_url = settings.database.supabase_url
upstash_url = settings.upstash_redis_rest_url
```

### 2. Secure API Key Access

```python
# Access secret values safely
openai_key = settings.external_services.openai_api_key.get_secret_value()
duffel_key = settings.external_services.duffel_api_key.get_secret_value() if settings.external_services.duffel_api_key else None

# Use in API clients
class OpenAIClient:
    def __init__(self):
        self.api_key = settings.external_services.openai_api_key.get_secret_value()
        self.organization = settings.external_services.openai_organization
```

### 3. Service Configuration

```python
# Configure database connection
async def create_database_pool():
    return await asyncpg.create_pool(
        settings.database.supabase_url,
        min_size=5,
        max_size=settings.database.max_connections,
        command_timeout=settings.database.supabase_timeout
    )

# Configure cache client
def create_redis_client():
    return redis.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        decode_responses=True
    )
```

### 4. Environment-Specific Behavior

```python
# Environment-based configuration
def configure_logging():
    if settings.environment == "production":
        logging.basicConfig(level=logging.WARNING)
    elif settings.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

# Feature flags based on environment
def should_use_cache() -> bool:
    return settings.environment in ["staging", "production"]
```

## Security Practices

### 1. Secret Management

```python
# Always use SecretStr for sensitive data
class APIKeyConfig(BaseSettings):
    api_key: SecretStr = Field(description="API key for external service")
    
    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json"
        }
```

### 2. Production Validation

```python
@model_validator(mode="after")
def validate_production_security(self) -> 'AppSettings':
    """Ensure production security requirements are met."""
    if self.environment == "production":
        # Validate JWT secret strength
        jwt_secret = self.jwt_secret_key.get_secret_value()
        if len(jwt_secret) < 32:
            raise ValueError("JWT secret must be at least 32 characters in production")
        
        # Validate BYOK master secret
        byok_secret = self.api_key_master_secret.get_secret_value()
        if len(byok_secret) < 32:
            raise ValueError("BYOK master secret must be at least 32 characters")
        
        # Ensure no default/test values
        if "test" in jwt_secret.lower() or "dev" in jwt_secret.lower():
            raise ValueError("Test/dev secrets not allowed in production")
    
    return self
```

### 3. Logging Safety

```python
import logging

def safe_log_config():
    """Log configuration without exposing secrets."""
    logger = logging.getLogger(__name__)
    
    # Safe to log
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Database URL: {settings.database.supabase_url}")
    
    # Never log secrets directly
    logger.info(f"OpenAI API key configured: {bool(settings.external_services.openai_api_key)}")
    logger.info(f"Duffel API key configured: {bool(settings.external_services.duffel_api_key)}")
```

## Development Workflow

### 1. Local Development Setup

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your development values
nano .env

# 3. Validate configuration
python -c "from tripsage_core.config.base_app_settings import settings; print('Config loaded successfully')"
```

### 2. Adding New Configuration

```python
# 1. Add to appropriate config model
class ExternalServiceConfig(BaseSettings):
    # Existing fields...
    
    new_service_api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for new external service"
    )
    new_service_timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Timeout for new service API calls"
    )

# 2. Update .env.example
echo "TRIPSAGE_EXTERNAL_NEW_SERVICE_API_KEY=\"your-new-service-key\"" >> .env.example
echo "TRIPSAGE_EXTERNAL_NEW_SERVICE_TIMEOUT=\"30.0\"" >> .env.example

# 3. Add validation if needed
@field_validator('new_service_timeout')
@classmethod
def validate_new_service_timeout(cls, v: float) -> float:
    if v > 60.0:
        warnings.warn("New service timeout > 60s may cause performance issues")
    return v
```

### 3. Testing Configuration

```python
# tests/test_config.py
import pytest
from pydantic import ValidationError
from tripsage_core.config.base_app_settings import AppSettings

def test_production_validation():
    """Test production environment validation."""
    with pytest.raises(ValidationError, match="Debug mode must be disabled"):
        AppSettings(
            environment="production",
            debug=True
        )

def test_secret_access():
    """Test secure secret access."""
    settings = AppSettings()
    
    # Should not expose secret in string representation
    assert "test-openai-key" not in str(settings.external_services.openai_api_key)
    
    # Should provide access via get_secret_value()
    assert settings.external_services.openai_api_key.get_secret_value() == "test-openai-key"
```

## Production Considerations

### 1. Environment Variable Management

```yaml
# Kubernetes ConfigMap for non-sensitive config
apiVersion: v1
kind: ConfigMap
metadata:
  name: tripsage-config
data:
  TRIPSAGE_ENVIRONMENT: "production"
  TRIPSAGE_DEBUG: "False"
  TRIPSAGE_API_PORT: "8000"
  CACHE_HOT_TTL: "300"
  CACHE_WARM_TTL: "3600"

---
# Kubernetes Secret for sensitive config
apiVersion: v1
kind: Secret
metadata:
  name: tripsage-secrets
type: Opaque
stringData:
  TRIPSAGE_EXTERNAL_OPENAI_API_KEY: "sk-production-key"
  TRIPSAGE_DB_SUPABASE_SERVICE_ROLE_KEY: "production-service-role-key"
  TRIPSAGE_JWT_SECRET_KEY: "production-jwt-secret"
```

### 2. Configuration Validation Service

```python
# services/config_validation.py
async def validate_production_config():
    """Production configuration validation."""
    errors = []
    
    # Check external service connectivity
    try:
        # Test OpenAI API key
        openai_client = AsyncOpenAI(api_key=settings.external_services.openai_api_key.get_secret_value())
        await openai_client.models.list()
    except Exception as e:
        errors.append(f"OpenAI API validation failed: {e}")
    
    # Test database connectivity
    try:
        async with asyncpg.connect(settings.database.supabase_url) as conn:
            await conn.fetch("SELECT 1")
    except Exception as e:
        errors.append(f"Database connectivity failed: {e}")
    
    # Test cache connectivity
    try:
        redis_client = redis.from_url(settings.cache.redis_url)
        await redis_client.ping()
    except Exception as e:
        errors.append(f"Cache connectivity failed: {e}")
    
    if errors:
        raise RuntimeError(f"Configuration validation failed: {errors}")
    
    return True
```

### 3. Configuration Monitoring

```python
# monitoring/config_health.py
class ConfigHealthCheck:
    """Monitor configuration health and changes."""
    
    async def check_config_drift(self):
        """Check for configuration drift from expected values."""
        issues = []
        
        # Check TTL values are within expected ranges
        if settings.cache.cache_hot_ttl > 600:  # 10 minutes
            issues.append("Short TTL is high")
        
        # Check timeout values
        if settings.external_services.default_timeout > 60:
            issues.append("Default timeout is high")
        
        # Check memory limits
        if settings.mem0.max_memories_per_user > 5000:
            issues.append("Memory limit per user is high")
        
        return issues
```

## Future Considerations

### Planned Enhancements

- Mobile application development
- AI agent capabilities
- Enterprise features and compliance

---

This configuration system ensures type-safe, secure, and manageable configuration across deployment environments.

### 5. Redis/Upstash Examples

```python
# Python (server): Upstash Redis via REST SDK (simple caching)
from upstash_redis import Redis

redis = Redis.from_env()  # uses UPSTASH_REDIS_REST_URL/TOKEN
redis.set("a", "b")
print(redis.get("a"))

# Or asyncio
from upstash_redis.asyncio import Redis as AsyncRedis
aredis = AsyncRedis.from_env()
await aredis.set("a", "b")
print(await aredis.get("a"))
```

```ts
// TypeScript (frontend/edge): Upstash Redis REST
import { Redis } from "@upstash/redis";

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL!,
  token: process.env.UPSTASH_REDIS_REST_TOKEN!,
});

await redis.set("key", "value", { ex: 60 });
const v = await redis.get<string>("key");
```
