# TripSage AI Docker Configuration

This directory contains optimized Docker configurations for TripSage AI local development environment.

## Files

- `docker-compose.mcp.yml` - **Enhanced** MCP (Model Context Protocol) services configuration
- `otel-collector-config.yaml` - **Secured** OpenTelemetry collector configuration  
- `prometheus.yml` - **Enhanced** Prometheus metrics scraping configuration
- `dev_services/` - **New** Dedicated Dockerfiles for development services (Option A)
- `docker-compose-neo4j.yml` - **DEPRECATED** - Historical Neo4j configuration (system migrated to Mem0)

## Recent Enhancements (Docker Optimization)

### ✅ Completed Optimizations

1. **Version Pinning**: All MCP services now use pinned versions (e.g., `@1.0.0`) for consistent behavior
2. **Resource Limits**: Added CPU and memory limits/reservations for all services to prevent resource exhaustion
3. **Security Hardening**: 
   - OTLP exporter now defaults to `insecure: false` for secure TLS
   - Added security comments and best practices
4. **Enhanced Documentation**: Comprehensive comments explaining service purposes and configuration options
5. **Dedicated Dockerfiles**: Created optimized Dockerfiles in `dev_services/` directory for faster builds
6. **Service Classification**: Clear distinction between mock/stub services and actual external integrations

### 🔧 Configuration Options

**Option A (Recommended)**: Use dedicated Dockerfiles in `dev_services/` for:
- Faster container startup (pre-built images)
- Better dependency caching
- Improved security with non-root users
- Health checks for better reliability

**Option B (Fallback)**: Current version-pinned `npx` commands in `docker-compose.mcp.yml`

## Current Architecture

TripSage now uses a unified storage architecture:

- **Database**: Supabase PostgreSQL with pgvector extensions (replaces Neo4j + separate vector database)
- **Memory**: Mem0 direct SDK integration (replaces Neo4j memory MCP)
- **Caching**: DragonflyDB service (Redis-compatible, 25x performance improvement)

## Usage

### Quick Start (Local Development)

From the project root:

```bash
# Start all MCP services with enhanced configuration
docker compose -f docker/docker-compose.mcp.yml up -d

# Check service status and resource usage
docker compose -f docker/docker-compose.mcp.yml ps
docker stats

# View logs for specific service
docker compose -f docker/docker-compose.mcp.yml logs <service-name>

# Stop all services
docker compose -f docker/docker-compose.mcp.yml down
```

### Environment Variables

Required environment variables (set in `.env` file):
```bash
# Database Services
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
NEO4J_URI=your_neo4j_uri  # For legacy compatibility
NEO4J_USERNAME=your_username
NEO4J_PASSWORD=your_password

# Travel APIs
DUFFEL_API_KEY=your_duffel_key
AIRBNB_API_KEY=your_airbnb_key  # ONLY service using real API

# Location & Utility
GOOGLE_MAPS_API_KEY=your_maps_key
OPENWEATHERMAP_API_KEY=your_weather_key
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# Cache
REDIS_URL=your_redis_url

# Observability (Optional)
OTLP_ENDPOINT=your_otlp_endpoint
OTLP_INSECURE=false  # IMPORTANT: Use false for production
OTLP_API_KEY=your_api_key
```

### Service Overview

| Service | Type | Purpose | Resource Limits |
|---------|------|---------|----------------|
| `supabase-mcp` | Mock | Database operations simulation | 0.5 CPU, 256MB |
| `airbnb-mcp` | **Live** | Real Airbnb platform integration | 0.5 CPU, 256MB |
| `duffel-flights-mcp` | Mock | Flight search simulation | 0.5 CPU, 256MB |
| `google-maps-mcp` | Mock | Maps/location simulation | 0.5 CPU, 256MB |
| `playwright-mcp` | Tool | Browser automation | 1.0 CPU, 1GB |
| `firecrawl-mcp` | Tool | Web scraping service | 0.5 CPU, 256MB |
| `time-mcp` | Utility | Time operations | 0.25 CPU, 128MB |
| `weather-mcp` | Mock | Weather data simulation | 0.5 CPU, 256MB |

### Monitoring & Observability

```bash
# Start with observability stack
docker compose -f docker/docker-compose.mcp.yml --profile monitoring up -d

# Access monitoring endpoints
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000
# - OTEL Collector: http://localhost:8888/metrics
```

## Architecture Notes

### Current Storage Architecture
- **Database**: Supabase PostgreSQL with pgvector extensions (replaces Neo4j + separate vector database)
- **Memory**: Mem0 direct SDK integration (replaces Neo4j memory MCP)
- **Caching**: DragonflyDB service (Redis-compatible, 25x performance improvement)

### Migration Notes
- **Neo4j → Mem0**: Knowledge graph functionality migrated to Mem0 with pgvector backend
- **Vector Search**: Now handled by pgvector extensions in Supabase (11x performance improvement)
- **Development**: No local Neo4j instance needed - unified Supabase for all environments

### Service Types
1. **Mock/Stub Services**: Simulate external API behavior for local development (most services)
2. **Live Integration**: Only `airbnb-mcp` connects to actual external platform
3. **Development Tools**: Playwright, Firecrawl for automation and scraping
4. **Utilities**: Time operations, caching services

## Troubleshooting

### Common Issues

**Resource Exhaustion**:
```bash
# Check resource usage
docker stats

# Adjust limits in docker-compose.mcp.yml if needed
```

**Service Not Starting**:
```bash
# Check service logs
docker compose -f docker/docker-compose.mcp.yml logs <service-name>

# Verify environment variables
env | grep -E '(SUPABASE|DUFFEL|AIRBNB|GOOGLE)'
```

**Network Issues**:
```bash
# Inspect network
docker network inspect tripsage-mcp-network

# Test service connectivity
docker compose -f docker/docker-compose.mcp.yml exec <service> ping <other-service>
```

### Performance Optimization

1. **Use SSD storage** for Docker volumes
2. **Allocate sufficient Docker resources** (4GB+ RAM recommended)
3. **Enable BuildKit** for faster builds: `export DOCKER_BUILDKIT=1`
4. **Use dedicated Dockerfiles** in `dev_services/` for faster startup

### Security Considerations

- All services run with non-root users where possible
- TLS is enforced by default (`OTLP_INSECURE=false`)
- Resource limits prevent DoS via resource exhaustion
- Network isolation via dedicated Docker network
- Environment variables for sensitive configuration
