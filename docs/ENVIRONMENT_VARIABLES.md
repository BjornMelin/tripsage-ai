# Environment Variables Guide

This document describes all environment variables used by TripSage, including the new feature flags for MCP to SDK migration.

## Core Application Settings

### Database Configuration

```bash
# Supabase Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_AUTO_REFRESH_TOKEN=true
SUPABASE_PERSIST_SESSION=false
SUPABASE_TIMEOUT=30

# PostgreSQL Connection (if using direct connection)
DATABASE_URL=postgresql://user:password@host:port/database
```

### Redis/Cache Configuration

```bash
# Redis URL for caching
REDIS_URL=redis://localhost:6379/0

# Or for Redis with authentication
REDIS_URL=redis://username:password@host:port/database

# For Redis SSL/TLS (recommended for production)
REDIS_URL=rediss://username:password@host:port/database
```

## MCP to SDK Migration Feature Flags

The following environment variables control the gradual migration from MCP wrappers to direct SDK integration. Each service can be independently switched between `mcp` and `direct` modes.

### Week 1 Services (Redis/DragonflyDB & Supabase)

```bash
# Redis/DragonflyDB integration mode
FEATURE_REDIS_INTEGRATION=direct  # Options: mcp, direct

# Supabase database integration mode  
FEATURE_SUPABASE_INTEGRATION=direct  # Options: mcp, direct
```

### Week 2 Services (Memory & Neo4j)

```bash
# Neo4j memory/knowledge graph integration mode
FEATURE_NEO4J_INTEGRATION=mcp  # Options: mcp, direct
```

### Week 3-4 Services (External APIs)

```bash
# Weather API integration mode
FEATURE_WEATHER_INTEGRATION=mcp  # Options: mcp, direct

# Google Maps integration mode
FEATURE_MAPS_INTEGRATION=mcp  # Options: mcp, direct

# Duffel Flights integration mode
FEATURE_FLIGHTS_INTEGRATION=mcp  # Options: mcp, direct

# Google Calendar integration mode
FEATURE_CALENDAR_INTEGRATION=mcp  # Options: mcp, direct

# Time service integration mode
FEATURE_TIME_INTEGRATION=mcp  # Options: mcp, direct
```

### Web Crawling Services (Already Migrated)

```bash
# Crawl4AI web crawling integration mode (completed)
FEATURE_CRAWL4AI_INTEGRATION=direct  # Options: mcp, direct

# Playwright browser automation integration mode (completed)
FEATURE_PLAYWRIGHT_INTEGRATION=direct  # Options: mcp, direct
```

### Services Remaining on MCP

```bash
# Airbnb integration mode (stays MCP due to unofficial API)
FEATURE_AIRBNB_INTEGRATION=mcp  # Options: mcp, direct
```

## Migration Strategy

### Safe Rollout

1. **Default to MCP**: All services default to `mcp` mode for safety
2. **Gradual Migration**: Enable `direct` mode per service as migration completes
3. **Instant Rollback**: Switch back to `mcp` mode if issues arise
4. **Zero Downtime**: Changes take effect immediately without restart

### Environment Examples

**Development Environment (Week 1 Complete):**

```bash
FEATURE_REDIS_INTEGRATION=direct
FEATURE_SUPABASE_INTEGRATION=direct
FEATURE_NEO4J_INTEGRATION=mcp
FEATURE_WEATHER_INTEGRATION=mcp
FEATURE_MAPS_INTEGRATION=mcp
FEATURE_FLIGHTS_INTEGRATION=mcp
FEATURE_CALENDAR_INTEGRATION=mcp
FEATURE_TIME_INTEGRATION=mcp
FEATURE_CRAWL4AI_INTEGRATION=direct
FEATURE_PLAYWRIGHT_INTEGRATION=direct
FEATURE_AIRBNB_INTEGRATION=mcp
```

**Production Environment (Conservative):**

```bash
FEATURE_REDIS_INTEGRATION=mcp
FEATURE_SUPABASE_INTEGRATION=mcp
# ... all other services default to mcp
```

**Full Migration Complete (Target State):**

```bash
FEATURE_REDIS_INTEGRATION=direct
FEATURE_SUPABASE_INTEGRATION=direct
FEATURE_NEO4J_INTEGRATION=direct
FEATURE_WEATHER_INTEGRATION=direct
FEATURE_MAPS_INTEGRATION=direct
FEATURE_FLIGHTS_INTEGRATION=direct
FEATURE_CALENDAR_INTEGRATION=direct
FEATURE_TIME_INTEGRATION=direct
FEATURE_CRAWL4AI_INTEGRATION=direct
FEATURE_PLAYWRIGHT_INTEGRATION=direct
FEATURE_AIRBNB_INTEGRATION=mcp  # Only service remaining on MCP
```

## Performance Impact

### Expected Improvements by Service

- **Redis → Direct**: 25x performance improvement with DragonflyDB
- **Supabase → Direct**: 30-40% latency reduction, full API coverage
- **Neo4j → Direct**: 50-70% latency reduction
- **Weather/Maps/Flights → Direct**: 40-60% latency reduction
- **Crawl4AI → Direct**: 6x performance improvement (completed)
- **Playwright → Direct**: 25-40% performance improvement (completed)

### Overall Impact

- **Combined Performance**: 5-10x faster operations
- **Cost Savings**: $1,500-2,000/month through MCP elimination
- **Latency Reduction**: 50-70% across the stack
- **Architecture Simplification**: 85% code reduction vs MCP implementation

## Configuration Validation

The system validates configuration at startup:

### Redis URL Validation

- Must start with `redis://` or `rediss://` (SSL)
- Format: `redis://[username:password@]host:port[/database]`

### Supabase Validation  

- URL must start with `https://`
- API key must be at least 20 characters
- Connection tested with simple query

### Error Handling

- Invalid configurations log detailed error messages
- Services fail fast with clear error descriptions
- Validation errors prevent startup (fail-fast principle)

## Migration Monitoring

### Feature Flag Status

```python
from tripsage.config.feature_flags import feature_flags

# Get migration status report
status = feature_flags.get_migration_status()
print(f"Migration progress: {status['summary']['migration_percentage']}%")
```

### Service Mode Checking

```python
from tripsage.config.feature_flags import is_direct_integration

# Check if a service is using direct integration
if is_direct_integration('redis'):
    print("Redis is using direct SDK integration")
else:
    print("Redis is using MCP wrapper")
```

## Security Considerations

### Secrets Management

- Use `.env` files for development
- Use secure secret management (AWS Secrets Manager, etc.) for production
- Never commit API keys or passwords to version control

### Redis Security

- Use `rediss://` (SSL/TLS) for production Redis connections
- Configure Redis authentication with strong passwords
- Restrict Redis network access with firewall rules

### Supabase Security

- Use Row Level Security (RLS) policies
- Rotate API keys regularly
- Monitor API usage for anomalies

## Troubleshooting

### Common Issues

**Redis Connection Failed:**

```bash
# Check Redis URL format
REDIS_URL=redis://localhost:6379/0

# For authentication
REDIS_URL=redis://username:password@host:port/database

# For SSL
REDIS_URL=rediss://username:password@host:port/database
```

**Supabase Connection Failed:**

```bash
# Check URL format (must be HTTPS)
SUPABASE_URL=https://your-project.supabase.co

# Check API key length (must be >20 characters)
SUPABASE_ANON_KEY=your-full-anon-key-here
```

**Feature Flag Not Working:**

```bash
# Check case sensitivity (should be lowercase)
FEATURE_REDIS_INTEGRATION=direct  # ✓ Correct
FEATURE_REDIS_INTEGRATION=DIRECT  # ✗ Incorrect

# Check valid values
FEATURE_REDIS_INTEGRATION=direct  # ✓ Valid
FEATURE_REDIS_INTEGRATION=sdk     # ✗ Invalid (use 'direct')
```

### Debug Commands

**Check Feature Flag Status:**

```bash
# Python console
from tripsage.config.feature_flags import feature_flags
print(feature_flags.get_migration_status())
```

**Test Service Connection:**

```bash
# Redis connection test
from tripsage.services.redis_service import redis_service
await redis_service.connect()  # Should not raise exception

# Supabase connection test  
from tripsage.services.supabase_service import supabase_service
await supabase_service.connect()  # Should not raise exception
```
