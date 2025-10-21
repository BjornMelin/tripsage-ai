# 🌍 TripSage Environment Configuration

> **Centralized Environment Variable Reference**
> All configuration settings organized by service and environment

## 📋 Table of Contents

- [Environment Variable Reference](#environment-variable-reference)
- [Configuration by Service](#configuration-by-service)
- [Development vs Production](#development-vs-production)
- [Validation and Testing](#validation-and-testing)

---

## Environment Variable Reference

```bash
# Environment
ENVIRONMENT=development  # Options: development, staging, production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false  # Set to true only for development

# Security
SECRET_KEY=your-secret-key-here  # Use strong random key for production
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

```

## Database Configuration

### Supabase + pgvector (Primary Database)

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # For admin operations

# Connection Settings
SUPABASE_TIMEOUT=30
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30

# pgvector Extension (enabled by default in Supabase)
VECTOR_DIMENSION=1536  # OpenAI embedding dimension
```

### DragonflyDB (High-Performance Cache)

```bash
# DragonflyDB Configuration (25x faster than Redis)
DRAGONFLY_URL=redis://localhost:6379/0

# For production with authentication
DRAGONFLY_URL=redis://username:password@host:port/database

# For SSL/TLS (recommended for production)
DRAGONFLY_URL=rediss://username:password@host:port/database

# Connection Pool Settings
DRAGONFLY_POOL_SIZE=20
DRAGONFLY_TIMEOUT=5
```

## Memory System (Mem0)

```bash
# Mem0 Configuration
MEM0_API_KEY=your-mem0-api-key
MEM0_BASE_URL=https://api.mem0.ai
MEM0_TIMEOUT=30

# Memory Configuration
MEMORY_EMBEDDING_MODEL=text-embedding-3-small
MEMORY_VECTOR_STORE=supabase  # Uses pgvector in Supabase
MEMORY_GRAPH_STORE=supabase   # Unified storage approach
```

## BYOK (Bring Your Own Key) System

The BYOK system allows users to provide their own API keys for external services. These are stored securely in the database per user.

### User-Provided API Keys (Stored in Database)

```bash
# These are NOT environment variables - they're user-provided keys stored in api_keys table
# Listed here for reference only:

# Flight APIs
# - DUFFEL_ACCESS_TOKEN (user-provided, if you implement per-user Duffel access)

# Map/Location APIs  
# - GOOGLE_MAPS_API_KEY (user-provided)
# - GOOGLE_CALENDAR_API_KEY (user-provided)

# Weather APIs
# - OPENWEATHERMAP_API_KEY (user-provided)
# - VISUAL_CROSSING_API_KEY (user-provided)

# Web Crawling
# - CRAWL4AI_API_KEY (user-provided, optional - has free tier)

# Accommodation APIs
# - Airbnb uses MCP server (no API key needed)
```

## External Service SDKs

### Flight Service (Duffel API v2)

```bash
# Provider configuration (used by the built-in DuffelProvider)
DUFFEL_ACCESS_TOKEN=your_duffel_access_token
# Optional legacy alias also supported by the DI factory:
# DUFFEL_API_TOKEN=your_duffel_access_token
# Base URL and timeouts are sensible defaults; override only if needed.
# DUFFEL_BASE_URL=https://api.duffel.com
# DUFFEL_TIMEOUT=30
```

### Google Services SDK

```bash
# Google Maps/Calendar SDK Configuration
GOOGLE_API_BASE_URL=https://maps.googleapis.com
GOOGLE_CALENDAR_BASE_URL=https://www.googleapis.com/calendar
GOOGLE_TIMEOUT=15
GOOGLE_RATE_LIMIT=2000  # requests per day default
```

### Weather Services SDK

```bash
# OpenWeatherMap SDK Configuration
OPENWEATHERMAP_BASE_URL=https://api.openweathermap.org
OPENWEATHERMAP_TIMEOUT=10

# Visual Crossing SDK Configuration
VISUAL_CROSSING_BASE_URL=https://weather.visualcrossing.com
VISUAL_CROSSING_TIMEOUT=10
```

### Web Crawling (Crawl4AI SDK)

```bash
# Crawl4AI Configuration
CRAWL4AI_BASE_URL=https://api.crawl4ai.com
CRAWL4AI_TIMEOUT=60
CRAWL4AI_MAX_PAGES=100  # per crawl session
CRAWL4AI_RATE_LIMIT=50  # requests per minute
```

## MCP Integration (Airbnb Only)

```bash
# Airbnb MCP Server (only remaining MCP integration)
AIRBNB_MCP_SERVER_PATH=/path/to/airbnb-mcp-server
AIRBNB_MCP_TIMEOUT=30
AIRBNB_MCP_RETRY_ATTEMPTS=3
```

## Frontend Configuration (Next.js 15)

```bash
# Next.js Environment Variables
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API URL
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws  # WebSocket URL
NEXT_PUBLIC_ENVIRONMENT=development

# Authentication
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-nextauth-secret

# Supabase Frontend Client
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## Production Environment

### Security Configuration

```bash
# Production Security Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-production-secret-key  # Strong random key
CORS_ORIGINS=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com

# SSL/TLS
SSL_REDIRECT=true
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
```

### Production Database

```bash
# Production Supabase
SUPABASE_URL=https://your-prod-project.supabase.co
SUPABASE_ANON_KEY=your-prod-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-prod-service-role-key

# Production DragonflyDB with SSL
DRAGONFLY_URL=rediss://username:password@your-dragonfly-host:6380/0
```

### Production Monitoring

```bash
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=your-sentry-dsn  # Error tracking

# Metrics
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Health Checks
HEALTH_CHECK_TIMEOUT=5
```

## Testing Environment

### Test Configuration

```bash
# Test Environment (.env.test)
ENVIRONMENT=test
DEBUG=true

# Test Database (separate from development)
SUPABASE_URL=https://your-test-project.supabase.co
SUPABASE_ANON_KEY=your-test-anon-key

# Test Cache (in-memory)
DRAGONFLY_URL=redis://localhost:6379/1  # Different database

# Mock API Keys for Testing
TEST_DUFFEL_ACCESS_TOKEN=test_access_token_123
TEST_GOOGLE_MAPS_API_KEY=test_key_456
TEST_OPENWEATHERMAP_API_KEY=test_key_789
```

### Test Data

```bash
# Test User Configuration
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=testpassword123

# Mock External APIs
MOCK_EXTERNAL_APIS=true  # Use mocks instead of real APIs
```

## Performance Configuration

### Connection Pooling

```bash
# Database Connection Pool
SUPABASE_POOL_SIZE=20
SUPABASE_MAX_OVERFLOW=30
SUPABASE_POOL_TIMEOUT=30

# Cache Connection Pool
DRAGONFLY_POOL_SIZE=20
DRAGONFLY_POOL_TIMEOUT=5
```

### Rate Limiting

```bash
# API Rate Limits
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100  # per minute per user
RATE_LIMIT_BURST=20      # burst allowance

# External API Rate Limits
EXTERNAL_API_RATE_LIMIT=50  # requests per minute
EXTERNAL_API_RETRY_DELAY=1  # seconds
```

## Security Best Practices

### Secret Management

```bash
# Development: Use .env files
# Production: Use secure secret management
# - AWS Secrets Manager
# - Azure Key Vault  
# - Google Secret Manager
# - Kubernetes Secrets
```

### Database Security

```bash
# Supabase Security
# - Enable Row Level Security (RLS)
# - Use service role key only for admin operations
# - Rotate keys quarterly
# - Monitor usage with Supabase Analytics

# API Key Security
# - Store user API keys encrypted in database
# - Use AES-256 encryption
# - Never log API keys
# - Implement key rotation reminders
```

### Network Security

```bash
# Production Network Security
# - Use SSL/TLS for all connections
# - Restrict database access to application servers
# - Use VPC/private networks where possible
# - Implement IP whitelisting for admin access
```

## Validation and Health Checks

### Startup Validation

The system validates all configuration at startup:

1. **Database Connection**: Tests Supabase connectivity
2. **Cache Connection**: Tests DragonflyDB connectivity  
3. **Memory System**: Validates Mem0 API access
4. **External APIs**: Tests connectivity to required services
5. **Environment**: Validates all required variables are set

### Health Check Endpoints

```bash
# Health check URLs
GET /health              # Basic health check
GET /health/detailed     # Detailed component status
GET /health/database     # Database connectivity
GET /health/cache        # Cache connectivity
GET /health/external     # External API status
```

## Troubleshooting

### Common Issues

**Database Connection Failed:**

```bash
# Check Supabase URL format
SUPABASE_URL=https://your-project.supabase.co  # Must be HTTPS

# Verify API keys
SUPABASE_ANON_KEY=eyJ...  # Should be JWT format, >100 characters
```

**Cache Connection Failed:**

```bash
# Check DragonflyDB URL format
DRAGONFLY_URL=redis://localhost:6379/0

# For authentication
DRAGONFLY_URL=redis://username:password@host:port/database
```

**BYOK API Key Issues:**

```bash
# User API keys are stored in database, not environment
# Check api_keys table for user-specific keys
# Verify key encryption/decryption is working
```

### Debug Commands

**Check System Health:**

```bash
curl http://localhost:8000/health/detailed
```

**Test Database Connection:**

```python
from tripsage_core.services.infrastructure.database_service import DatabaseService
db = DatabaseService()
await db.health_check()
```

**Test Cache Connection:**

```python
from tripsage_core.services.infrastructure.cache_service import CacheService
cache = CacheService()
await cache.health_check()
```

## Migration from Legacy

This unified architecture represents the complete migration from the previous MCP-heavy architecture. All feature flags have been removed, and the system now uses:

- **7 Direct SDKs**: Duffel, Google Maps/Calendar, OpenWeatherMap, Visual Crossing, Crawl4AI, Mem0
- **1 MCP Integration**: Airbnb (unofficial API, remains MCP)
- **Unified Storage**: Supabase + pgvector for both relational and vector data
- **High-Performance Cache**: DragonflyDB (25x faster than Redis)
- **BYOK Security**: User-provided API keys stored encrypted in database

The migration is complete and production-ready.

## Configuration by Service

### Database Services

- **Supabase**: Primary database with pgvector extensions
- **DragonflyDB**: High-performance caching layer

### External APIs

- **Duffel**: Flight booking and search
- **Google Maps/Calendar**: Location and calendar services
- **OpenWeatherMap/Visual Crossing**: Weather data
- **Crawl4AI**: Web scraping capabilities
- **Mem0**: Memory and embedding services

### MCP Integrations

- **Airbnb**: Accommodation search (unofficial API)

## Development vs Production

### Development Environment

- Use `.env.development` for local development
- Enable DEBUG mode for detailed logging
- Use test API keys where possible
- Local DragonflyDB instance via Docker

### Production Environment (Vercel)

- Use `.env.production` with real credentials
- Disable DEBUG mode
- Use production Supabase instance
- Enable all security features

## Validation and Testing

### Environment Validation

```bash
# Validate all required environment variables are set
uv run python -c "from tripsage.core.settings import get_settings; print('✅ All env vars validated')"
```

### Connection Testing

```bash
# Test database connection
uv run python scripts/verification/verify_supabase_connection.py

# Test cache connection  
uv run python scripts/verification/verify_dragonfly.py
```
