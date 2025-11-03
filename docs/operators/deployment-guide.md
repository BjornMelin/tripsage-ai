# TripSage Deployment Guide

## Architecture Overview

TripSage uses a modern, serverless-first architecture:

- **Backend**: FastAPI application (Python 3.13+) with async architecture
- **Database**: Supabase PostgreSQL with pgvector extension
- **Cache**: Upstash Redis (HTTP REST API)
- **Auth**: Supabase authentication with JWT tokens
- **Observability**: OpenTelemetry with Jaeger tracing
- **Deployment**: Containerized with Docker

## Prerequisites

- Docker and Docker Compose
- Python 3.13+
- Supabase project with database access
- Upstash Redis instance
- OpenAI API key

## Environment Configuration

### Required Environment Variables

```bash
# Core
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Supabase
DATABASE_URL=https://your-project.supabase.co
DATABASE_PUBLIC_KEY=your-supabase-anon-key
DATABASE_SERVICE_KEY=your-supabase-service-key
DATABASE_JWT_SECRET=your-supabase-jwt-secret

# Application Security
SECRET_KEY=your-application-secret-key

# AI Services
OPENAI_API_KEY=your-openai-api-key

# Upstash Redis (HTTP REST API)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-upstash-token
```

### Production Security Settings

- CORS origins restricted to production domains
- Supabase Realtime Authorization enabled
- Rate limiting configured for production load
- API keys rotated and secured
- Database connection strings encrypted

## Supabase Setup

### Project Configuration

1. Create Supabase project
2. Enable pgvector extension in database settings
3. Configure authentication providers
4. Set up Row Level Security (RLS) policies

### Database Migrations

```bash
# Link local project to Supabase
make supa.link PROJECT_REF=your-project-ref

# Push migrations to remote
make supa.db.push

# Deploy edge functions
make supa.functions.deploy-all PROJECT_REF=your-project-ref
```

### Secrets Management

```bash
# Set minimal required secrets
make supa.secrets-min \
  SUPABASE_URL=https://your-project.supabase.co \
  SUPABASE_ANON_KEY=your-anon-key \
  SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Set Upstash Redis secrets
make supa.secrets-upstash \
  UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io \
  UPSTASH_REDIS_REST_TOKEN=your-token
```

## Container Deployment

### Build and Run

```bash
# Build container
docker build -f docker/Dockerfile.api -t tripsage-api .

# Run locally for testing
docker run -p 8080:8080 \
  --env-file .env \
  tripsage-api

# Health check
curl http://localhost:8080/health
```

### Production Deployment Options

#### Docker Compose (Development/Staging)

```yaml
version: '3.8'
services:
  tripsage-api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8080:8080"
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Cloud Platforms

**Railway/Render**:

- Connect GitHub repository
- Set environment variables
- Deploy from main branch
- Configure health checks

**AWS ECS/Google Cloud Run**:

- Build container image
- Push to container registry
- Create service with environment variables
- Configure load balancer and health checks

## Observability Setup

### OpenTelemetry Configuration

TripSage includes OpenTelemetry instrumentation for:

- FastAPI request/response tracing
- Database query monitoring
- Redis operation tracking
- External API call tracing

### Jaeger Integration

```bash
# Run Jaeger locally for development
docker-compose up otel-collector jaeger
```

Access Jaeger UI at `http://localhost:16686`

### Metrics Collection

The application exposes:

- Health endpoint: `GET /health`
- Metrics endpoint: `GET /metrics` (if configured)
- Database status: `GET /health/database`

## Performance Optimization

### Database Optimization

- Monitor query performance with `EXPLAIN ANALYZE`
- Keep pgvector indexes optimized
- Use connection pooling efficiently
- Monitor disk I/O and memory usage

### Caching Strategy

- Upstash Redis for session storage and API response caching
- Configure appropriate TTL values
- Monitor cache hit rates

### Rate Limiting

- Configurable per-endpoint rate limits
- Redis-backed rate limiting storage
- Automatic cleanup of expired keys

## CI/CD Pipeline

### GitHub Actions

The deployment workflow supports:

- Automated testing and linting
- Container image building
- Deployment to multiple environments
- Health checks and rollback

### Environment Management

- **Development**: Feature branches with preview deployments
- **Staging**: Integration testing environment
- **Production**: Stable releases from main branch

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Test Supabase connection
python -c "
from supabase import create_client
client = create_client('https://your-project.supabase.co', 'service-key')
print('Connection successful')
"

# Check Upstash Redis
curl https://your-redis.upstash.io/ping \
  -H 'Authorization: Bearer your-token'
```

#### Container Health Check Failures

```bash
# Check container logs
docker logs tripsage-container

# Test health endpoint directly
curl -v http://localhost:8080/health
```

#### Performance Degradation

```bash
# Monitor resource usage
docker stats tripsage-container

# Check application logs
docker logs --tail 100 tripsage-container
```

### Rollback Procedure

1. Identify failed deployment
2. Revert to previous container image
3. Clear application cache if needed
4. Monitor error rates and performance
5. Update deployment status in CI/CD

### Security Validation

```bash
# Run security audit
python -c "
from tripsage_core.config import get_settings
settings = get_settings()
report = settings.get_security_report()
print('Security validation:', report)
"
```

## Maintenance Tasks

### Database Maintenance

- Regular vacuum and analyze operations
- Monitor index usage and rebuild if needed
- Backup verification and testing

### Cache Management

- Monitor Redis memory usage
- Clear stale cache entries
- Update cache TTL policies as needed

### Dependency Updates

- Regular security updates for Python packages
- Update base container images
- Test compatibility before production deployment

## Support

For deployment issues:

1. Check application logs
2. Verify environment configuration
3. Test individual service connectivity
4. Review Supabase dashboard for database issues
5. Check Upstash Redis metrics
