# TripSage AI Development Environment

Docker Compose configuration for local development and testing.

## Current Architectur

Current TripSage architecture:

- **Database**: Supabase PostgreSQL with pgvector extension (unified storage)
- **Caching**: Upstash Redis (HTTP, managed)
- **Memory**: Mem0 with pgvector backend
- **Web Crawling**: Crawl4AI direct SDK
- **Browser Automation**: Playwright direct SDK
- **External APIs**: Direct SDK integrations (Duffel, Google Maps, Weather)
- **MCP Services**: Only 1 remaining (Airbnb - no official SDK available)

### Architecture Changes

- **Caching**: Upstash Redis (serverless, no local container)
- **Vector Search**: pgvector + pgvectorscale for embeddings
- **Memory**: Mem0 with pgvector backend
- **Infrastructure**: Managed services reduce local complexity

## Services Overview

| Service | Type | Purpose | Notes |
|---------|------|---------|--------|
| `supabase` | Database | PostgreSQL + pgvector for unified storage | Vector embeddings |
| `upstash` | Cache | Serverless Redis over HTTP | Managed service |
| `tripsage-api` | Backend | FastAPI with direct SDK integrations | API server |
| `tripsage-frontend` | Frontend | Next.js 15 with App Router | React application |
| `airbnb-mcp` | Integration | Airbnb integration (no official SDK) | MCP service |
| `jaeger` | Monitoring | Distributed tracing | Observability |
| `otel-collector` | Telemetry | Receives OTLP traces/metrics/logs | Local export |

## Quick Start

### Basic Development Environment

```bash
# Start core services (Supabase + API + Frontend)
docker compose -f docker/docker-compose.mcp.yml up supabase tripsage-api tripsage-frontend

# Access services
# - API: http://localhost:8080
# - Frontend: http://localhost:3000
# - Supabase Studio: http://localhost:8000
# - Upstash Redis: configure UPSTASH_REDIS_REST_URL/TOKEN
```

### Full Environment with Monitoring

```bash
# Start complete development environment
docker compose -f docker/docker-compose.mcp.yml up -d

# Access monitoring
# - Jaeger: http://localhost:16686 (traces)
# - OTEL Collector: receives OTLP on 4317/4318; metrics exported to logging/OTLP
```

### Service Management

```bash
# Monitor all services
docker compose -f docker/docker-compose.mcp.yml ps
docker stats

# View logs
docker compose -f docker/docker-compose.mcp.yml logs tripsage-api
docker compose -f docker/docker-compose.mcp.yml logs tripsage-frontend

# Stop services
docker compose -f docker/docker-compose.mcp.yml down

# Clean volumes (reset data)
docker compose -f docker/docker-compose.mcp.yml down -v
```

## Environment Variables

### Required Configuration

```bash
# Database (Supabase local development)
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=tripsage_dev
POSTGRES_USER=postgres
SUPABASE_JWT_SECRET=your-super-secret-jwt-token
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Cache (Upstash Redis)
UPSTASH_REDIS_REST_URL=your-url
UPSTASH_REDIS_REST_TOKEN=your-token

# External APIs (Direct SDK integrations)
DUFFEL_ACCESS_TOKEN=your_duffel_access_token
GOOGLE_MAPS_API_KEY=your_google_maps_key
OPENWEATHERMAP_API_KEY=your_weather_key

# MCP Integration (Only Airbnb)
AIRBNB_API_KEY=your_airbnb_key

# Optional: Web Crawling
CRAWL4AI_API_KEY=optional_crawl4ai_key

# Optional: Monitoring (OTEL/Jaeger only)
```

### Development-Only Variables

```bash
# Mem0 Configuration
MEM0_CONFIG={"vector_store": {"provider": "pgvector"}}

# Development URLs
DATABASE_URL=postgresql://postgres:password@supabase:5432/tripsage_dev
# No local cache service; use Upstash env vars above.
SUPABASE_URL=http://supabase:8000
```

## Development Setup

### Service Configuration

1. **Database**: Supabase PostgreSQL with pgvector and Studio UI
2. **Caching**: Upstash Redis (managed HTTP-based cache)
3. **Memory**: Mem0 with pgvector backend
4. **External APIs**: Direct SDK integrations
5. **Monitoring**: Jaeger tracing and OTLP telemetry collection

## Troubleshooting

### Common Issues

**Service Won't Start**:

```bash
# Check service health
docker compose -f docker/docker-compose.mcp.yml ps
docker compose -f docker/docker-compose.mcp.yml logs [service-name]

# Verify environment variables
env | grep -E '(POSTGRES|DUFFEL|GOOGLE|AIRBNB)'
```

**Database Connection Issues**:

```bash
# Test PostgreSQL connection
docker exec -it tripsage-supabase-local psql -U postgres -d tripsage_dev

# Verify pgvector extension
docker exec -it tripsage-supabase-local psql -U postgres -d tripsage_dev -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Cache Performance Issues**:

```bash
# Verify Upstash Redis via SDK
uv run python scripts/verification/verify_upstash.py
```

### Performance Optimization

1. **Resource Allocation**: Adjust Docker resource limits based on your system
2. **SSD Storage**: Use SSD storage for Docker volumes for best performance
3. **Memory**: Allocate at least 8GB RAM for the full development environment
4. **Network**: Use Docker's default networking for optimal performance

### Environment Consistency

The development environment uses the same services as production:

- Database: Supabase PostgreSQL with pgvector
- Cache: Upstash Redis
- Memory: Mem0 with pgvector
- APIs: Direct SDK integrations
- Monitoring: Jaeger and OTLP collector

This minimizes differences between development and production environments.
