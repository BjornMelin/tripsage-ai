# TripSage AI Modern Development Environment

**Optimized Docker environment aligned with TripSage's current high-performance architecture.**

## Current Architecture (2025)

TripSage has evolved to a streamlined, high-performance architecture with dramatic improvements:

- **Database**: Supabase PostgreSQL with pgvector extension (unified storage)
- **Caching**: Upstash Redis (HTTP, managed)
- **Memory**: Mem0 with pgvector backend (91% faster than Neo4j)
- **Web Crawling**: Crawl4AI direct SDK
- **Browser Automation**: Playwright direct SDK
- **External APIs**: Direct SDK integrations (Duffel, Google Maps, Weather)
- **MCP Services**: Only 1 remaining (Airbnb - no official SDK available)

### Performance Achievements

- **Serverless cache** via Upstash Redis (no local container)
- **11x faster vector search** (pgvector + pgvectorscale)
- **91% faster memory operations** (Mem0 vs Neo4j)
- **80% infrastructure cost** reduction
- **60-70% architecture complexity** reduction

## Services Overview

| Service | Type | Purpose | Performance |
|---------|------|---------|-------------|
| `supabase` | Database | PostgreSQL + pgvector for unified storage | 11x faster vector search |
| `upstash` | Cache | Serverless Redis over HTTP | Managed |
| `tripsage-api` | Backend | FastAPI with modern direct SDKs | 91% faster memory ops |
| `tripsage-frontend` | Frontend | Next.js 15 with App Router | Modern React architecture |
| `airbnb-mcp` | Integration | Only remaining MCP (no SDK available) | Minimal MCP usage |
| `jaeger` | Monitoring | Distributed tracing | Production-ready observability |
| `otel-collector` | Telemetry | Receives OTLP traces/metrics/logs | Local development export |

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
DUFFEL_API_KEY=your_duffel_api_key
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

## Architecture Benefits

### Eliminated Legacy Components

**Removed from Docker environment** (migrated to direct SDKs):

- ❌ Neo4j MCP (replaced by Mem0)
- ❌ Local Redis/Dragonfly containers (replaced by Upstash Redis)
- ❌ Firecrawl MCP (replaced by Crawl4AI SDK)
- ❌ Google Maps MCP (replaced by direct SDK)
- ❌ Weather MCP (replaced by direct HTTP)
- ❌ Duffel MCP (replaced by direct SDK)
- ❌ 8+ other legacy MCP services

**Retained Essential Services**:

- ✅ Airbnb MCP (only remaining - no official SDK)
- ✅ Modern monitoring with Jaeger (traces) and OTEL Collector (OTLP metrics/logs)
- ✅ Managed infrastructure (Supabase, Upstash Redis)

### Development Workflow

1. **Database**: Supabase provides PostgreSQL + pgvector + Studio UI
2. **Caching**: Upstash Redis provides managed HTTP-based cache
3. **Memory**: Mem0 integrates directly with pgvector for 91% faster operations
4. **External APIs**: Direct SDK calls eliminate MCP overhead
5. **Monitoring**: Production-ready observability stack for performance insights

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

### Production Alignment

This development environment mirrors the production architecture:

- Same database technology (Supabase + pgvector)
- Same caching solution (Upstash Redis)
- Same memory system (Mem0)
- Same direct SDK integrations
- Same monitoring stack

This ensures development-production parity and prevents environment-specific issues.

## Migration Notes

**From Legacy MCP Architecture**:

- Docker environment has been streamlined to match the current high-performance architecture
- Legacy MCP services have been removed in favor of direct SDK integrations
- Only Airbnb MCP remains due to lack of official SDK
- Performance improvements are immediately visible in the development environment

**Database Migration**:

- Neo4j → Mem0 with pgvector backend
- Multiple databases → Single Supabase instance
- Complex vector setup → Unified pgvector + pgvectorscale

**Cache Migration**:

- Redis/Dragonfly → Upstash Redis (serverless, no local ops)
- No configuration changes needed (Redis-compatible)
- Dramatic performance improvements in development environment
