# TripSage Operators Reference

Complete technical reference for TripSage deployment and operations. Focus on essential setup, configuration, and operational procedures.

## Installation & Setup

### Prerequisites

**Core Runtime:**

- Python 3.13+ with uv package manager
- Node.js ≥24 with pnpm ≥9.0.0
- Git

**External Services:**

- Supabase account (database and authentication)
- Upstash Redis (caching)
- OpenAI API key

**Optional:**

- Docker (for containerized development)

### Quick Setup

```bash
# Install Python package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js package manager
npm install -g pnpm

# Clone and setup
git clone <repository-url>
cd tripsage-ai

# Install dependencies
uv sync
cd frontend && pnpm install && cd ..

# Configure environment (see Environment Configuration)
cp .env.example .env

# Start services
uv run python -m tripsage.api.main    # Backend (port 8000)
cd frontend && pnpm dev               # Frontend (port 3000)
```

### Verification

```bash
# Health check
curl http://localhost:8000/api/health

# Database connectivity
uv run python scripts/verification/verify_connection.py

# Full system verification
uv run python scripts/verification/verify_setup.py
```

## Environment Configuration

### Core Settings

```bash
# Environment
ENVIRONMENT=development  # development, production, test, testing
DEBUG=false
LOG_LEVEL=INFO

# API Configuration
API_TITLE=TripSage API
API_VERSION=1.0.0
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_CREDENTIALS=true

# Security
SECRET_KEY=your-application-secret-key
```

### Database Configuration

```bash
# Supabase (Primary)
DATABASE_URL=https://your-project.supabase.co
DATABASE_PUBLIC_KEY=your-anon-key
DATABASE_SERVICE_KEY=your-service-key
DATABASE_JWT_SECRET=your-jwt-secret

# Optional: Direct PostgreSQL connection
POSTGRES_URL=postgresql://user:password@host:port/database
```

### AI & External Services

```bash
# Required
OPENAI_API_KEY=your-openai-api-key

# Optional: Third-party APIs
DUFFEL_ACCESS_TOKEN=your-duffel-token
GOOGLE_MAPS_API_KEY=your-maps-key
OPENWEATHERMAP_API_KEY=your-weather-key
MEM0_API_KEY=your-mem0-key
```

### Caching & Performance

```bash
# Upstash Redis (Production)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-upstash-token

# Local Redis (Development)
REDIS_URL=redis://localhost:6379
```

### Observability Configuration

```bash
# OpenTelemetry
OTEL_SERVICE_NAME=tripsage-api
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-jaeger-endpoint
OTEL_EXPORTER_OTLP_HEADERS=authorization=Bearer+your-token

# Logging
LOG_FORMAT=json
LOG_LEVEL=INFO
```

## Supabase Setup

### Project Creation

1. Create Supabase project via dashboard
2. Enable required extensions:

   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS "vector";
   CREATE EXTENSION IF NOT EXISTS "pg_cron";
   CREATE EXTENSION IF NOT EXISTS "pg_net";
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
   CREATE EXTENSION IF NOT EXISTS "btree_gist";
   ```

3. Configure authentication providers (Google, GitHub)
4. Set up Row Level Security policies
5. Enable Realtime with private channels only

### Database Schema

Key tables and relationships:

- `users` - User accounts and profiles
- `trips` - Trip planning data
- `flights` - Flight bookings and search data
- `accommodations` - Hotel/accommodation data
- `itineraries` - Trip itineraries and schedules
- `conversations` - Chat and AI interactions
- `api_keys` - BYOK (Bring Your Own Key) storage

### Security Policies

All tables use Row Level Security with policies for:

- User data isolation
- Collaborative access (trip sharing)
- Admin operations
- Audit logging

## Deployment

### Docker Deployment

```bash
# Build and run
docker-compose up --build

# Production build
docker build -t tripsage-ai .
docker run -p 8000:8000 --env-file .env.production tripsage-ai
```

### Cloud Platforms

#### Railway

```bash
# Deploy to Railway
railway login
railway init
railway up
```

#### Render

```yaml
# render.yaml
services:
  - type: web
    name: tripsage-api
    env: python
    buildCommand: uv sync
    startCommand: uv run python -m tripsage.api.main
```

#### AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t tripsage .
docker tag tripsage:latest <account>.dkr.ecr.us-east-1.amazonaws.com/tripsage:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/tripsage:latest

# Deploy to ECS (via AWS CLI or console)
```

#### Google Cloud Run

```bash
# Build and deploy
gcloud builds submit --tag gcr.io/<project>/tripsage
gcloud run deploy --image gcr.io/<project>/tripsage --platform managed
```

### Environment-Specific Configuration

```bash
# Development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=<strong-random-key>
```

## Configuration Management

### Pydantic Settings

TripSage uses Pydantic BaseSettings for type-safe configuration:

```python
from tripsage_core.config import get_settings

settings = get_settings()
database_url = settings.database_url
environment = settings.environment
```

### Validation

Configuration is validated at startup. Missing required variables cause immediate failure with clear error messages.

### Security Configuration

- Sensitive values use `SecretStr` type
- Environment variables take precedence over config files
- No secrets in version control

## Monitoring & Observability

### Health Checks

```bash
# Basic health
GET /api/health

# Detailed health
GET /api/health/detailed

# Component health
GET /api/health/components
```

### Metrics

- Request/response times per endpoint
- Error rates by consumer type
- Cache hit/miss ratios
- External API latencies
- Database connection pool status

### Logging

Structured JSON logging with:

- Request correlation IDs
- Error context and stack traces
- Performance metrics
- Security events

### OpenTelemetry Integration

```python
# Automatic instrumentation for:
# - HTTP requests/responses
# - Database queries
# - External API calls
# - Cache operations
```

## Security Overview

### Authentication

- JWT tokens via Supabase Auth
- API keys for server-to-server communication
- BYOK (Bring Your Own Key) for third-party services handled by Next.js route handlers marked `"server-only"` with `dynamic = "force-dynamic"` to keep every secret fetch per-request

### Authorization

- Row Level Security (RLS) on all database tables
- Role-based access control
- Session management with automatic refresh

### Data Protection

- TLS/HTTPS encryption in transit
- Encrypted sensitive data at rest
- Secure API key storage with user-specific salts

### Rate Limiting

- Consumer-type based limits
- Distributed counters via Redis
- Graceful degradation with warnings

## Operations

### Database Management

```bash
# Run migrations
uv run python scripts/database/run_migrations.py

# Backup database
uv run python scripts/database/backup.py

# Restore from backup
uv run python scripts/database/restore.py path/to/backup.sql
```

### Cache Management

```bash
# Clear application cache
uv run python scripts/cache/clear_cache.py

# Cache statistics
uv run python scripts/cache/cache_stats.py
```

### Log Management

```bash
# View recent logs
uv run python scripts/logging/view_logs.py

# Search logs
uv run python scripts/logging/search_logs.py --query "ERROR"

# Export logs
uv run python scripts/logging/export_logs.py --days 7
```

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Database connection | `Connection refused` | Check Supabase credentials and network |
| Redis connection | Cache errors | Verify Upstash credentials and URLs |
| Authentication | `401 Unauthorized` | Check JWT token validity and Supabase config |
| Rate limited | `429 Too Many Requests` | Implement exponential backoff |
| Memory issues | Out of memory errors | Check Redis memory usage and limits |

### Performance Tuning

- Database query optimization with indexes
- Redis caching for frequently accessed data
- Connection pooling for database and external APIs
- Horizontal scaling with load balancers

### Emergency Procedures

1. **Service Outage**: Check health endpoints and restart services
2. **Data Corruption**: Restore from backup if available
3. **Security Incident**: Isolate affected systems, audit logs
4. **Performance Degradation**: Scale resources, optimize queries

## Development Workflow

### Code Quality

```bash
# Python linting and formatting
ruff check . --fix
ruff format .

# Type checking
uv run pyright

# Testing
uv run pytest --cov=tripsage --cov=tripsage_core

# Security scanning
uv run python scripts/security/security_scan.py
```

### Dependency Management

```bash
# Add Python dependency
uv add package-name

# Add development dependency
uv add --group dev package-name

# Update dependencies
uv sync

# Check for security vulnerabilities
uv run python scripts/security/check_vulnerabilities.py
```

## Backup & Recovery

### Automated Backups

- Database backups run daily via pg_cron
- Configuration backups with version history
- Log archival with compression

### Manual Backup

```bash
# Database dump
pg_dump $DATABASE_URL > backup.sql

# Configuration export
uv run python scripts/config/export_config.py > config_backup.json

# Full system backup
uv run python scripts/backup/create_backup.py
```

### Recovery Procedures

1. Stop application services
2. Restore database from backup
3. Restore configuration files
4. Restart services and verify functionality
5. Update DNS/load balancers if necessary
