# Configuration Management

TripSage uses Pydantic settings for configuration management with environment variable support.

## Basic Usage

```python
from tripsage_core.config import get_settings

# Get configuration (cached)
settings = get_settings()

# Access values
database_url = settings.database_url
environment = settings.environment
debug = settings.debug
```

## Environment Variables

### Required Variables

```bash
# Environment
ENVIRONMENT=development  # development, production, test, testing
DEBUG=false
LOG_LEVEL=INFO

# Database (Supabase)
DATABASE_URL=https://your-project.supabase.co
DATABASE_PUBLIC_KEY=your-anon-key
DATABASE_SERVICE_KEY=your-service-key
DATABASE_JWT_SECRET=your-jwt-secret

# Security
SECRET_KEY=your-application-secret-key

# AI Services
OPENAI_API_KEY=your-openai-api-key
```

### Optional Variables

```bash
# Redis/Cache
REDIS_URL=redis://localhost:6379  # For local development
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io  # For production
UPSTASH_REDIS_REST_TOKEN=your-upstash-token

# API Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

## Configuration Manager CLI

Use the config manager script for configuration validation and management:

```bash
# Validate current configuration
python scripts/config/config_manager.py validate

# Generate environment template
python scripts/config/config_manager.py template .env.template

# Generate secure secrets
python scripts/config/config_manager.py secrets --count 3

# Generate security report
python scripts/config/config_manager.py security-report

# Check if ready for production
python scripts/config/config_manager.py check-env production

# Export configuration as JSON
python scripts/config/config_manager.py export config.json --format json
```

## Environment Examples

### Development

```bash
# .env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=https://dev-project.supabase.co
DATABASE_PUBLIC_KEY=dev-anon-key
DATABASE_SERVICE_KEY=dev-service-key
DATABASE_JWT_SECRET=dev-jwt-secret
SECRET_KEY=dev-secret-key
OPENAI_API_KEY=dev-openai-key
```

### Production

```bash
# .env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=https://prod-project.supabase.co
DATABASE_PUBLIC_KEY=prod-anon-key
DATABASE_SERVICE_KEY=prod-service-key
DATABASE_JWT_SECRET=prod-jwt-secret
SECRET_KEY=prod-secret-key
OPENAI_API_KEY=prod-openai-key
UPSTASH_REDIS_REST_URL=https://prod-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=prod-redis-token
```

## Security Practices

- Store secrets securely and never commit to version control
- Use different secrets for each environment
- Validate configuration before deployment
- Use the security report command to check configuration health

## Troubleshooting

### Configuration Loading Issues

```python
# Debug configuration
from tripsage_core.config import get_settings
settings = get_settings()
print(settings.model_dump(exclude={'secret_key', 'database_service_key', 'database_jwt_secret', 'openai_api_key'}))
```

### Common Errors

- **Missing environment variables**: Check that all required variables are set
- **Invalid secrets**: Use the security report to validate secret strength
- **Database connection issues**: Verify DATABASE_URL and credentials
