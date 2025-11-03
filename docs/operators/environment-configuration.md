# Environment Configuration

> **TripSage Environment Variables Reference**
> Configuration settings for all services and environments

## Table of Contents

- [Core Configuration](#core-configuration)
- [Database Configuration](#database-configuration)
- [AI Services](#ai-services)
- [Rate Limiting](#rate-limiting)
- [Monitoring](#monitoring)
- [Google Maps](#google-maps)
- [Environment Examples](#environment-examples)
- [Validation](#validation)

---

## Core Configuration

```bash
# Environment & Core
ENVIRONMENT=development  # Options: development, production, test, testing
DEBUG=false  # Set to true only for development
LOG_LEVEL=INFO  # Logging level

# API Configuration
API_TITLE=TripSage API
API_VERSION=1.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_CREDENTIALS=true

# Security
SECRET_KEY=your-application-secret-key  # Strong random key for production
```

## Database Configuration

### Supabase (Primary Database)

```bash
# Supabase Configuration
DATABASE_URL=https://your-project.supabase.co  # Supabase project URL
DATABASE_PUBLIC_KEY=your-anon-key  # Supabase public anon key
DATABASE_SERVICE_KEY=your-service-role-key  # Service role key for admin operations
DATABASE_JWT_SECRET=your-jwt-secret  # JWT secret for token validation

# Optional PostgreSQL direct connection (overrides DATABASE_URL if provided)
POSTGRES_URL=postgresql://user:password@host:port/database
```

### Redis/Cache Configuration

```bash
# Redis Connection (optional, for direct Redis connections)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password
REDIS_MAX_CONNECTIONS=50

# Upstash Redis (HTTP) - Preferred for serverless deployments
UPSTASH_REDIS_REST_URL=https://<id>.upstash.io  # Upstash REST URL
UPSTASH_REDIS_REST_TOKEN=<token>  # Upstash REST token
```

## AI Services

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key  # OpenAI API key
OPENAI_MODEL=gpt-5  # Default OpenAI model
MODEL_TEMPERATURE=0.7  # Default temperature for AI responses

# LangGraph Features (comma-separated)
LANGGRAPH_FEATURES=conversation_memory,advanced_routing,memory_updates,error_recovery

# OpenRouter Attribution (optional)
OPENROUTER_REFERER=your-referer-url
OPENROUTER_TITLE=your-app-title
```

## Rate Limiting

```bash
# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true  # Enable rate limiting middleware
RATE_LIMIT_REQUESTS_PER_MINUTE=60  # Default requests per minute
RATE_LIMIT_REQUESTS_PER_HOUR=1000  # Default requests per hour
RATE_LIMIT_REQUESTS_PER_DAY=10000  # Default requests per day
RATE_LIMIT_BURST_SIZE=10  # Burst size for token bucket

# Rate Limiting Strategy (comma-separated)
RATE_LIMIT_STRATEGY=sliding_window,token_bucket,burst_protection

# Rate Limiting Monitoring
RATE_LIMIT_ENABLE_MONITORING=true  # Enable rate limit monitoring

# Outbound HTTP Limits
OUTBOUND_DEFAULT_QPM=60.0  # Default queries per minute for outbound HTTP
```

## Monitoring

```bash
# Database Monitoring
ENABLE_DATABASE_MONITORING=true  # Enable database connection monitoring
ENABLE_SECURITY_MONITORING=true  # Enable security event monitoring
ENABLE_AUTO_RECOVERY=true  # Enable automatic database recovery

# Database Health Checks
DB_HEALTH_CHECK_INTERVAL=30.0  # Health check interval in seconds
DB_SECURITY_CHECK_INTERVAL=60.0  # Security check interval in seconds
DB_MAX_RECOVERY_ATTEMPTS=3  # Maximum recovery attempts
DB_RECOVERY_DELAY=5.0  # Delay between recovery attempts

# OpenTelemetry Instrumentation (comma-separated)
OTEL_INSTRUMENTATION=  # fastapi,asgi,httpx,redis

# API Key Caching
ENABLE_API_KEY_CACHING=false  # Enable caching for API key validations
```

## Google Maps

```bash
# Google Maps Platform API Key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# Google Maps Configuration
GOOGLE_MAPS_TIMEOUT=10.0  # Combined connect+read timeout in seconds
GOOGLE_MAPS_RETRY_TIMEOUT=60  # Total retry timeout across requests
GOOGLE_MAPS_QUERIES_PER_SECOND=10  # Client-side QPS throttle
```

## Frontend Configuration (Next.js 16)

```bash
# Next.js Environment Variables (set via deployment platform)
NEXT_PUBLIC_ENVIRONMENT=development
```

## Environment Examples

### Production Configuration

```bash
# Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Production Database
DATABASE_URL=https://your-prod-project.supabase.co
DATABASE_PUBLIC_KEY=your-prod-anon-key
DATABASE_SERVICE_KEY=your-prod-service-role-key
DATABASE_JWT_SECRET=your-prod-jwt-secret

# Production Redis
UPSTASH_REDIS_REST_URL=https://<id>.upstash.io
UPSTASH_REDIS_REST_TOKEN=<token>

# Production AI Services
OPENAI_API_KEY=sk-your-production-openai-key

# Production Google Maps (if used)
GOOGLE_MAPS_API_KEY=your-production-google-maps-key
```

### Development Configuration

```bash
# Development Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Development Database (use test values or local Supabase)
DATABASE_URL=https://test.supabase.com
DATABASE_PUBLIC_KEY=test-public-key
DATABASE_SERVICE_KEY=test-service-key
DATABASE_JWT_SECRET=test-jwt-secret

# Development AI Services (use test keys)
OPENAI_API_KEY=sk-test-1234567890

# Optional Redis for development
UPSTASH_REDIS_REST_URL=https://<dev-id>.upstash.io
UPSTASH_REDIS_REST_TOKEN=<dev-token>
```

### Test Configuration

```bash
# Test Environment
ENVIRONMENT=test
DEBUG=true

# Test Database (separate from development)
DATABASE_URL=https://test-project.supabase.co
DATABASE_PUBLIC_KEY=test-anon-key
DATABASE_SERVICE_KEY=test-service-key
DATABASE_JWT_SECRET=test-jwt-secret
```

## Validation

### Environment Validation

```bash
# Validate configuration at startup
uv run python -c "from tripsage_core.config import get_settings; settings = get_settings(); print('✅ Configuration loaded successfully')"
```

### Health Checks

```bash
# Health check endpoints
GET /health              # Basic health check
GET /health/detailed     # Detailed component status
```

## Configuration by Service

### Core Services

- **Database**: Supabase PostgreSQL with pgvector
- **Cache**: Upstash Redis (HTTP client)
- **AI**: OpenAI API integration
- **Maps**: Google Maps Platform

### Environment-Specific Setup

- **Development**: Use test credentials and local debugging
- **Production**: Use production credentials and monitoring
- **Testing**: Use isolated test environments

## Security Notes

- Store secrets as environment variables, never in code
- Use different credentials for each environment
- Rotate API keys regularly
- Enable monitoring and logging in production
