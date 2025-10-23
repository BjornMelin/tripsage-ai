# TripSage Configuration Management

## Overview

TripSage uses a modern, type-safe configuration system built with Pydantic V2 and pydantic-settings following 2025 best practices. The configuration provides:

- **Type Safety**: All configuration values are validated with Python type hints
- **Security Hardening**: Automatic detection of fallback/test secrets in production
- **Environment Flexibility**: Support for development, testing, and production environments
- **Docker Support**: Built-in Docker secrets and environment variable support
- **Validation**: Validation with clear error messages

## Configuration Architecture

### Core Components

```python
from tripsage_core.config import get_settings, Settings

# Get validated configuration
settings = get_settings()

# Access configuration values
database_url = settings.database_url
is_production = settings.is_production
```

### Security Features

The configuration system includes several security features:

1. **Fallback Secret Detection**: Automatically detects test/fallback secrets in production
2. **Secret Validation**: Validates secret strength and entropy
3. **Production Hardening**: Enforces security requirements in production environments
4. **Docker Secrets**: Supports Docker secret mounting at `/run/secrets`

## Environment Variables

### Core Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | string | `development` | Application environment (development, production, test, testing) |
| `DEBUG` | boolean | `false` | Enable debug mode |
| `LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |

### Database Configuration

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `DATABASE_URL` | URL | Yes | Supabase database URL |
| `DATABASE_PUBLIC_KEY` | Secret | Yes | Supabase public anon key |
| `DATABASE_SERVICE_KEY` | Secret | Yes | Supabase service role key |
| `DATABASE_JWT_SECRET` | Secret | Yes | Supabase JWT secret |
| `POSTGRES_URL` | URL | No | Direct PostgreSQL URL (overrides DATABASE_URL) |

### API Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `API_TITLE` | string | `TripSage API` | API title |
| `API_VERSION` | string | `1.0.0` | API version |
| `CORS_ORIGINS` | list | `localhost:3000,localhost:3001` | CORS allowed origins |
| `CORS_CREDENTIALS` | boolean | `true` | CORS allow credentials |

### Security

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `SECRET_KEY` | Secret | Yes | Application secret key for encryption |

### Redis/Cache

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_URL` | URL | None | Redis/DragonflyDB connection URL |
| `REDIS_PASSWORD` | Secret | None | Redis authentication password |
| `REDIS_MAX_CONNECTIONS` | int | `50` | Maximum Redis connections (1-10000) |

### AI Services

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `OPENAI_API_KEY` | Secret | Yes | OpenAI API key |
| `OPENAI_MODEL` | string | `gpt-4o` | Default OpenAI model |

## Usage Examples

### Basic Configuration Loading

```python
from tripsage_core.config import get_settings

# Load configuration (cached)
settings = get_settings()

# Use configuration
print(f"Running in {settings.environment} mode")
print(f"Database: {settings.database_url}")
```

### Security Validation

```python
from tripsage_core.config import get_settings

settings = get_settings()

# Get security report
security_report = settings.get_security_report()
print(f"Production ready: {security_report['production_ready']}")

# Check individual secrets
secret_status = settings.validate_secrets_security()
for field, is_secure in secret_status.items():
    print(f"{field}: {'✓' if is_secure else '✗'}")
```

### Environment Template Generation

```python
from tripsage_core.config import get_settings

settings = get_settings()

# Generate environment template (without actual secrets)
template = settings.export_env_template(include_secrets=False)
print(template)

# Save to file
with open('.env.template', 'w') as f:
    f.write(template)
```

### Configuration Validation

```python
from tripsage_core.config import validate_configuration

# Validate configuration without loading
is_valid = validate_configuration()
if not is_valid:
    print("Configuration validation failed")
    exit(1)
```

## Environment-Specific Configuration

### Development Environment

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=https://dev-project.supabase.co
SECRET_KEY=dev-secret-key-not-for-production
```

### Production Environment

```bash
# .env.production  
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=https://prod-project.supabase.co
SECRET_KEY=<secure-production-secret>
DATABASE_SERVICE_KEY=<secure-service-key>
DATABASE_JWT_SECRET=<secure-jwt-secret>
OPENAI_API_KEY=<production-openai-key>
```

### Testing Environment

```bash
# .env.test
ENVIRONMENT=test
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_URL=https://test-project.supabase.co
SECRET_KEY=test-secret-key-for-testing-only
```

## Docker Configuration

### Environment Variables (Dockerfile)

```dockerfile
# Dockerfile
FROM python:3.13-slim

# Set environment variables
ENV ENVIRONMENT=production
ENV DEBUG=false

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -e .

# Run application
CMD ["uvicorn", "tripsage.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Secrets (docker-compose.yml)

```yaml
# docker-compose.yml
version: '3.8'
services:
  tripsage:
    build: .
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    secrets:
      - database_service_key
      - openai_api_key
      - secret_key
    volumes:
      - /run/secrets:/run/secrets:ro

secrets:
  database_service_key:
    file: ./secrets/database_service_key.txt
  openai_api_key:
    file: ./secrets/openai_api_key.txt
  secret_key:
    file: ./secrets/secret_key.txt
```

## Security Best Practices

### 1. Secret Management

- **Never commit secrets** to version control
- Use **strong, unique secrets** for each environment
- Rotate secrets regularly
- Use **Docker secrets** or **secret management services** in production

### 2. Environment Separation

- Use **different databases** for each environment
- Use **different API keys** for each environment
- **Validate configuration** before deployment

### 3. Production Hardening

The configuration system automatically:

- Disables debug mode in production
- Validates secret strength
- Detects fallback/test secrets
- Enforces HTTPS URLs

### 4. Monitoring

```python
# Monitor configuration security
settings = get_settings()
security_report = settings.get_security_report()

if not security_report['production_ready']:
    # Alert monitoring system
    logger.exception("Production configuration security issues detected")
```

## Troubleshooting

### Common Issues

1. **ValidationError on startup**

   ```text
   Fix: Check environment variables and ensure all required values are set
   ```

2. **Fallback secret detected in production**

   ```text
   Fix: Replace test/fallback secrets with secure production values
   ```

3. **Database connection failed**

   ```text
   Fix: Verify DATABASE_URL and credentials are correct
   ```

### Debug Configuration

```python
# Debug configuration loading
import logging
logging.basicConfig(level=logging.DEBUG)

from tripsage_core.config import get_settings
settings = get_settings()

# Print all configuration (excluding secrets)
print(settings.model_dump(exclude={'secret_key', 'database_service_key', 'database_jwt_secret', 'openai_api_key'}))
```

### Validation Commands

```bash
# Validate configuration
python -c "from tripsage_core.config import validate_configuration; print('Valid' if validate_configuration() else 'Invalid')"

# Generate security report
python -c "from tripsage_core.config import get_settings; import json; print(json.dumps(get_settings().get_security_report(), indent=2))"

# Generate environment template
python -c "from tripsage_core.config import get_settings; print(get_settings().export_env_template())"
```

## Migration from Legacy Configuration

### Breaking Changes

1. **Removed nested configuration objects** - All settings are now flat
2. **Stricter validation** - Invalid values now raise errors instead of warnings
3. **Required secrets** - Production environment requires valid secrets

### Migration Steps

1. **Update environment variables** to use new names (see table above)
2. **Remove nested configuration** from any application code
3. **Update imports** to use new configuration module
4. **Validate configuration** before deploying

```python
# Old (deprecated)
from tripsage.config import DatabaseConfig, APIConfig
db_config = DatabaseConfig()
api_config = APIConfig()

# New (current)
from tripsage_core.config import get_settings
settings = get_settings()
database_url = settings.database_url
api_title = settings.api_title
```

## Usage Notes

### Custom Configuration Sources

```python
# Custom settings with additional validation
from tripsage_core.config import Settings
from pydantic_settings import SettingsConfigDict

class CustomSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=".env.custom",
        secrets_dir="/custom/secrets",
    )
    
    custom_field: str = "default_value"
```

### Runtime Configuration Updates

```python
# Note: Settings are cached by default
# To reload configuration, clear the cache

from tripsage_core.config import get_settings
get_settings.cache_clear()
new_settings = get_settings()
```

### Integration with FastAPI

```python
from fastapi import FastAPI, Depends
from tripsage_core.config import Settings, get_settings

app = FastAPI()

@app.get("/health")
def health_check(settings: Settings = Depends(get_settings)):
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug
    }
```
