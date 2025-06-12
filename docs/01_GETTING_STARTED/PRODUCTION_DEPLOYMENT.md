# TripSage Production Deployment Guide

**Complete Production Setup:** Unified Supabase architecture with real-time capabilities  
**Architecture:** Single database with pgvector, DragonflyDB cache, direct SDK integrations  
**Benefits:** 25x cache performance, 91% memory system improvement, 80% cost reduction

## Pre-Deployment Requirements

### Infrastructure Requirements

- [ ] **Supabase Pro/Enterprise**: Required for pgvector, real-time features, and production SLA
- [ ] **DragonflyDB Instance**: High-performance cache deployment (25x faster than Redis)
- [ ] **Domain & SSL**: Production domain with SSL certificates
- [ ] **CI/CD Pipeline**: GitHub Actions or equivalent for automated deployment
- [ ] **Monitoring Stack**: Prometheus, Grafana, and alerting systems
- [ ] **Backup Strategy**: Automated database backups and disaster recovery plan

### Supabase Project Preparation

- [ ] **Plan Verification**: Confirm Supabase plan supports all required extensions
- [ ] **Extension Checklist**: pgvector, pg_cron, pg_net, pgcrypto, uuid-ossp
- [ ] **Resource Planning**: Estimate connection limits, storage, and compute requirements
- [ ] **Security Planning**: RLS policies, authentication configuration, API key management
- [ ] **Performance Planning**: Index optimization, connection pooling, cache configuration

### Application Readiness

- [ ] **Environment Configuration**: Production environment variables configured and secured
- [ ] **Database Schema**: All migrations tested and ready for deployment
- [ ] **Security Policies**: RLS policies implemented and tested
- [ ] **Real-time Features**: WebSocket integration and real-time subscriptions configured
- [ ] **Performance Optimization**: Indexes, connection pooling, and caching optimized
- [ ] **Health Checks**: Comprehensive health endpoints implemented
- [ ] **Monitoring Integration**: Application metrics and alerting configured
- [ ] **Testing Suite**: End-to-end tests passing in staging environment

## Deployment Steps

### 1. Supabase Project Setup

```bash
# Login and connect to Supabase
supabase login
supabase projects list

# Link to your production project
supabase link --project-ref [your-project-ref]

# Verify project connection
supabase status
```

**Enable Required Extensions:**

```sql
-- Execute in Supabase SQL Editor or via CLI
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_cron";
CREATE EXTENSION IF NOT EXISTS "pg_net";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
```

### 2. Database Schema Deployment

```bash
# Deploy complete schema using consolidated migration
supabase db push

# Verify schema deployment
supabase db diff

# Check extension installation
psql -d "$DATABASE_URL" -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'pg_cron', 'pg_net');"
```

### 3. Security Configuration

```bash
# Test RLS policies
psql -d "$DATABASE_URL" -c "SELECT schemaname, tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"

# Verify authentication settings
curl -X POST "https://[project-ref].supabase.co/auth/v1/signup" \
  -H "apikey: [anon-key]" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

### 4. Application Deployment

```bash
# Deploy backend application
docker build -t tripsage-api:production .
docker run -d --name tripsage-api \
  --env-file .env.production \
  -p 8000:8000 \
  tripsage-api:production

# Deploy frontend application
cd frontend
npm run build
npm run start

# Verify deployment
curl https://api.your-domain.com/health
curl https://your-domain.com/api/health
```

**Environment Configuration:**

- [ ] **Production Variables**: All environment variables set and secured
- [ ] **API Keys**: Supabase keys configured correctly
- [ ] **Cache Configuration**: DragonflyDB connection configured
- [ ] **Memory System**: Mem0 integration configured
- [ ] **External APIs**: All service API keys configured

### 5. Performance Optimization

**Vector Search Configuration:**

```sql
-- Create optimized vector indexes
CREATE INDEX memories_embedding_hnsw_idx ON memories 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- User-specific vector index
CREATE INDEX memories_user_embedding_idx ON memories 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64)
WHERE user_id IS NOT NULL;
```

**Cache Optimization:**

```bash
# Configure DragonflyDB connection
export DRAGONFLY_URL="rediss://username:password@your-host:6380/0"
export DRAGONFLY_POOL_SIZE=20
export DRAGONFLY_TIMEOUT=5

# Test cache connectivity
python -c "import redis; r = redis.from_url('$DRAGONFLY_URL'); print(r.ping())"
```

**Connection Pool Configuration:**

```bash
# Optimize database connections
export SUPABASE_POOL_SIZE=20
export SUPABASE_MAX_OVERFLOW=30
export SUPABASE_POOL_TIMEOUT=30
```

### 6. Real-time Feature Setup

```sql
-- Create real-time publication
DROP PUBLICATION IF EXISTS supabase_realtime CASCADE;
CREATE PUBLICATION supabase_realtime;

-- Add tables to real-time
ALTER PUBLICATION supabase_realtime ADD TABLE trips;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_messages;
ALTER PUBLICATION supabase_realtime ADD TABLE chat_sessions;
ALTER PUBLICATION supabase_realtime ADD TABLE trip_collaborators;
ALTER PUBLICATION supabase_realtime ADD TABLE itinerary_items;
```

**Test Real-time Functionality:**

```javascript
// Frontend real-time test
const subscription = supabase
  .channel('trips-changes')
  .on('postgres_changes', {
    event: '*',
    schema: 'public',
    table: 'trips'
  }, (payload) => console.log('Change:', payload))
  .subscribe()
```

## Post-Deployment Validation

### Performance Testing

**Database Performance:**

```sql
-- Test vector search performance
EXPLAIN (ANALYZE, BUFFERS) 
SELECT content, embedding <=> '[0.1,0.2,...]'::vector as similarity 
FROM memories 
WHERE user_id = 'test-user-id'
ORDER BY embedding <=> '[0.1,0.2,...]'::vector 
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%hnsw%';
```

**Performance Targets:**

- [ ] **Vector Search**: <100ms p95 latency for similarity queries
- [ ] **Database QPS**: >471 queries per second capacity
- [ ] **Cache Hit Rate**: >95% for DragonflyDB
- [ ] **Memory Operations**: <50ms for Mem0 operations
- [ ] **Real-time Latency**: <200ms for WebSocket messages
- [ ] **API Response Time**: <500ms p95 for REST endpoints

### Functional Testing

**Core Features:**

```bash
# Test API endpoints
curl -H "Authorization: Bearer <token>" https://api.your-domain.com/trips
curl -H "Authorization: Bearer <token>" https://api.your-domain.com/chat/sessions
curl -H "Authorization: Bearer <token>" https://api.your-domain.com/search/destinations

# Test real-time features
wscat -c "wss://api.your-domain.com/ws?token=<token>"

# Test vector search
curl -X POST https://api.your-domain.com/memory/search \
  -H "Authorization: Bearer <token>" \
  -d '{"query": "hotels in Paris", "limit": 5}'
```

**End-to-End Testing:**

- [ ] **User Registration**: Complete signup and email verification flow
- [ ] **Trip Creation**: Create, edit, and share trip functionality
- [ ] **Real-time Collaboration**: Multi-user trip editing
- [ ] **Chat System**: AI agent conversations and tool calls
- [ ] **Search Features**: Flight, hotel, and destination search
- [ ] **Memory System**: Context retention across sessions
- [ ] **BYOK System**: User API key management
- [ ] **Error Scenarios**: Graceful error handling and recovery

### Monitoring & Alerting Setup

**Database Monitoring:**

```sql
-- Monitor active connections
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- Monitor slow queries
SELECT query, calls, total_exec_time, mean_exec_time 
FROM pg_stat_statements 
WHERE mean_exec_time > 100 
ORDER BY mean_exec_time DESC;

-- Monitor cache hit ratio
SELECT 
  sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;
```

**Application Metrics:**

- [ ] **Response Times**: P50, P95, P99 latencies tracked
- [ ] **Error Rates**: 4xx and 5xx error rates monitored
- [ ] **Throughput**: Requests per second tracking
- [ ] **Vector Search**: Query performance and accuracy metrics
- [ ] **Real-time**: WebSocket connection and message metrics
- [ ] **Memory System**: Mem0 operation performance
- [ ] **Cache Performance**: DragonflyDB hit rates and latency

**Alerting Configuration:**

```yaml
# Example Prometheus alerts
groups:
  - name: tripsage.alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected

      - alert: SlowVectorSearch
        expr: histogram_quantile(0.95, vector_search_duration_seconds) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: Vector search performance degraded

      - alert: DatabaseConnectionsHigh
        expr: pg_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High database connection count
```

## Rollback Procedure

If issues arise, follow this rollback sequence:

### Immediate Rollback (Application Level)

1. **Revert Code**: Deploy previous application version
2. **Restore Environment**: Restore previous environment variables
3. **Health Check**: Verify application stability

### Database Rollback (If Needed)

1. **Migration Rollback**: Use Supabase CLI to rollback migrations if needed

   ```bash
   supabase db reset
   # Or create a rollback migration
   supabase migration new rollback_pgvector_extensions
   ```

2. **Data Restoration**: Restore from backup if data corruption occurs

3. **Service Restoration**: Verify all services operational

## Success Criteria

### Performance Targets

**Database Performance:**
- [ ] **Vector Search**: <100ms p95, 471+ QPS capacity
- [ ] **Query Performance**: <50ms p95 for standard queries
- [ ] **Connection Pool**: <80% utilization under normal load
- [ ] **Cache Hit Rate**: >95% for DragonflyDB

**Application Performance:**
- [ ] **API Response Times**: <500ms p95 for REST endpoints
- [ ] **WebSocket Latency**: <200ms for real-time messages
- [ ] **Memory Operations**: <50ms for Mem0 queries
- [ ] **Error Rate**: <0.1% for critical endpoints

**Infrastructure Metrics:**
- [ ] **Availability**: >99.9% uptime SLA
- [ ] **Scalability**: Handle 10x current traffic load
- [ ] **Cost Optimization**: 80% reduction from previous architecture

### Operational Targets

**Architecture Consolidation:**
- [ ] **Unified Database**: Single Supabase instance for all data operations
- [ ] **Real-time Features**: Live collaboration and agent monitoring operational
- [ ] **Security Model**: RLS policies enforced across all user data
- [ ] **Cache Integration**: DragonflyDB providing 25x performance improvement
- [ ] **Memory System**: Mem0 with 91% performance improvement operational

**Development Workflow:**
- [ ] **CI/CD Pipeline**: Automated deployment and testing functional
- [ ] **Monitoring**: Comprehensive observability and alerting active
- [ ] **Documentation**: Architecture and deployment guides complete
- [ ] **Team Readiness**: Development and operations teams trained

## Post-Deployment Optimization

### Week 1: Immediate Monitoring

**Performance Validation:**
```bash
# Daily performance check script
#!/bin/bash
echo "🔍 TripSage Production Health Check - $(date)"

# API health check
curl -f https://api.your-domain.com/health/detailed

# Database performance
psql -d "$DATABASE_URL" -c "SELECT COUNT(*) as active_connections FROM pg_stat_activity WHERE state = 'active';"

# Vector search performance test
time curl -X POST https://api.your-domain.com/memory/search \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -d '{"query": "test search", "limit": 5}'

# Cache performance
redis-cli -u "$DRAGONFLY_URL" ping

echo "✅ Health check complete"
```

**Monitoring Tasks:**
- [ ] **Daily Metrics Review**: Performance, error rates, and usage patterns
- [ ] **Real-time Monitoring**: WebSocket connections and message throughput
- [ ] **Security Monitoring**: Authentication failures and suspicious activity
- [ ] **Cost Tracking**: Infrastructure costs and usage optimization
- [ ] **User Experience**: Response times and error rates from user perspective

### Week 2-4: Performance Optimization

**Database Optimization:**
```sql
-- Analyze query performance
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    rows
FROM pg_stat_statements 
WHERE calls > 100
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Optimize vector indexes based on usage
SELECT 
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_tup_read / idx_tup_fetch as selectivity
FROM pg_stat_user_indexes 
WHERE indexname LIKE '%hnsw%';

-- Update table statistics
ANALYZE memories;
ANALYZE trips;
ANALYZE chat_messages;
```

**Performance Tuning:**
- [ ] **Vector Index Optimization**: Tune HNSW parameters based on query patterns
- [ ] **Connection Pool Tuning**: Optimize pool sizes based on usage
- [ ] **Cache Configuration**: Adjust TTL strategies for optimal hit rates
- [ ] **Query Optimization**: Index creation and query plan improvements
- [ ] **Resource Scaling**: Assess need for compute or storage upgrades

### Month 1: Strategic Assessment

**Performance Analysis:**
```python
# Performance metrics collection script
import psycopg2
import redis
import time
from datetime import datetime, timedelta

def collect_performance_metrics():
    metrics = {
        'timestamp': datetime.utcnow(),
        'database': {
            'connections': get_db_connections(),
            'query_performance': get_slow_queries(),
            'vector_search_performance': get_vector_metrics(),
            'cache_hit_ratio': get_cache_hit_ratio()
        },
        'application': {
            'response_times': get_api_metrics(),
            'error_rates': get_error_rates(),
            'websocket_connections': get_ws_metrics()
        },
        'infrastructure': {
            'cpu_usage': get_cpu_metrics(),
            'memory_usage': get_memory_metrics(),
            'storage_usage': get_storage_metrics()
        }
    }
    return metrics
```

**Strategic Evaluation:**
- [ ] **Cost Analysis**: Detailed comparison with previous architecture costs
- [ ] **Performance Benchmarking**: Actual vs. projected performance metrics
- [ ] **Scalability Assessment**: Growth capacity and scaling requirements
- [ ] **Security Review**: Security posture and compliance validation
- [ ] **Operational Efficiency**: Developer productivity and maintenance overhead
- [ ] **Future Roadmap**: Next phase improvements and feature additions

## Emergency Contacts

**Database Issues:**

- Primary: Database Team Lead
- Secondary: Platform Engineering
- Escalation: CTO

**Application Issues:**

- Primary: Backend Team Lead
- Secondary: DevOps Engineer
- Escalation: Engineering Manager

## Additional Resources

- [Supabase pgvector Documentation](https://supabase.com/docs/guides/database/extensions/pgvector)
- [pgvector Performance Tuning Guide](https://github.com/pgvector/pgvector#performance)
- [Migration Summary Documentation](./MIGRATION_SUMMARY.md)
- [Supabase Migration Guide](https://supabase.com/docs/guides/cli/local-development#database-migrations)
- [Supabase CLI Reference](https://supabase.com/docs/reference/cli)

---

**Migration Lead:** _[Your Name]_  
**Date:** _[Deployment Date]_  
**Sign-off:** _[Stakeholder Approval]_
