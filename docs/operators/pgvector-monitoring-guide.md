# 📊 PGVector Production Monitoring Guide

> **Production Monitoring | Performance Metrics | Alert Configuration**  
> Comprehensive guide for monitoring pgvector performance in production environments  
> *Last updated: June 17, 2025*

## 📋 Table of Contents

- [Key Metrics to Monitor](#key-metrics-to-monitor)
- [Automated Monitoring Setup](#automated-monitoring-setup)
- [Monitoring Checklist](#monitoring-checklist)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Best Practices](#best-practices)

## Overview

This guide provides comprehensive instructions for monitoring pgvector performance in production environments. Based on the simplified architecture from BJO-212, it focuses on actionable metrics that indicate real performance issues.

## Key Metrics to Monitor

### 1. Query Performance Metrics

#### Latency Percentiles
```sql
-- Monitor vector search query latency
SELECT 
    percentile_cont(0.50) WITHIN GROUP (ORDER BY total_exec_time) as p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY total_exec_time) as p95_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY total_exec_time) as p99_ms,
    COUNT(*) as query_count
FROM pg_stat_statements
WHERE query LIKE '%vector%<->%'
    AND query NOT LIKE '%pg_stat%'
    AND calls > 10;
```

**Alert Thresholds:**
- p50 > 10ms: Warning
- p95 > 50ms: Warning  
- p99 > 100ms: Critical

#### Query Throughput
```sql
-- Queries per second over last 5 minutes
SELECT 
    COUNT(*) / 300.0 as qps,
    SUM(total_exec_time) / 300.0 as avg_load_ms_per_sec
FROM pg_stat_statements
WHERE query LIKE '%vector%<->%'
    AND query NOT LIKE '%pg_stat%'
    AND last_call > NOW() - INTERVAL '5 minutes';
```

### 2. Index Health Metrics

#### Index Usage Statistics
```python
# Python monitoring script using PGVectorService
async def monitor_index_usage():
    """Check if vector indexes are being used effectively."""
    
    vector_tables = await pgvector_service.list_vector_tables()
    
    for table_info in vector_tables:
        if table_info['index_status'] == 'indexed':
            stats = await pgvector_service.get_index_stats(
                table_info['table_name'],
                table_info['column_name']
            )
            
            if stats and stats.index_usage_count == 0:
                logger.warning(
                    f"Unused index on {table_info['table_name']}.{table_info['column_name']}"
                )
            
            # Check index efficiency
            if stats and stats.row_count > 0:
                bytes_per_row = stats.index_size_bytes / stats.row_count
                if bytes_per_row > 1000:  # More than 1KB per row
                    logger.warning(
                        f"Large index size on {table_info['table_name']}: "
                        f"{stats.index_size_human} for {stats.row_count} rows"
                    )
```

#### Index Bloat Detection
```sql
-- Check for index bloat
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_tup_read = 0 THEN 'EMPTY_SCANS'
        ELSE 'ACTIVE'
    END as status
FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%hnsw%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### 3. Memory Service Performance

#### Cache Hit Rates
```python
# Monitor memory service cache effectiveness
async def monitor_memory_cache():
    """Track cache hit rates for memory searches."""
    
    # Implement cache hit rate tracking
    cache_stats = {
        'hits': 0,
        'misses': 0,
        'hit_rate': 0.0
    }
    
    # Log cache performance every 5 minutes
    if cache_stats['hits'] + cache_stats['misses'] > 0:
        cache_stats['hit_rate'] = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses'])
        
        if cache_stats['hit_rate'] < 0.70:  # Less than 70% hit rate
            logger.warning(f"Low cache hit rate: {cache_stats['hit_rate']:.2%}")
```

#### Memory Table Optimization Status
```python
async def check_memory_optimization():
    """Verify memory tables are optimized."""
    
    optimization_result = await pgvector_service.optimize_memory_tables()
    
    if optimization_result.get('errors'):
        logger.error(
            f"Memory table optimization errors: {optimization_result['errors']}"
        )
    
    # Check optimization coverage
    optimized = len(optimization_result.get('memory_optimization', []))
    if optimized == 0:
        logger.warning("No memory tables found or optimized")
```

### 4. Connection Pool Monitoring

#### Supavisor Pool Statistics
```sql
-- Monitor connection pool usage
SELECT 
    usename,
    application_name,
    COUNT(*) as connection_count,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
    MAX(EXTRACT(EPOCH FROM (NOW() - state_change))) as max_idle_seconds
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY usename, application_name
ORDER BY connection_count DESC;
```

**Alert Thresholds:**
- Connection count > 80% of max_connections: Warning
- Idle in transaction > 5 minutes: Warning
- Active connections spike > 2x normal: Alert

### 5. DragonflyDB Cache Monitoring

#### Cache Performance
```bash
# Monitor DragonflyDB performance
redis-cli -h localhost -p 6379 --raw info stats | grep -E 'ops_per_sec|used_memory|hit_rate'
```

#### Python Monitoring Script
```python
async def monitor_dragonfly_cache():
    """Monitor DragonflyDB cache performance."""
    
    cache_service = get_cache_service()
    
    # Get cache statistics
    info = await cache_service.redis.info()
    
    metrics = {
        'ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
        'memory_used_mb': info.get('used_memory', 0) / (1024 * 1024),
        'hit_rate': info.get('keyspace_hit_rate', 0),
        'connected_clients': info.get('connected_clients', 0)
    }
    
    # Alert on performance degradation
    if metrics['ops_per_sec'] < 100000:  # Less than 100k ops/sec
        logger.warning(f"Low cache throughput: {metrics['ops_per_sec']} ops/sec")
    
    if metrics['hit_rate'] < 0.80:  # Less than 80% hit rate
        logger.warning(f"Low cache hit rate: {metrics['hit_rate']:.2%}")
```

## Automated Monitoring Setup

### 1. Prometheus Metrics Export

```python
# prometheus_metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
vector_query_duration = Histogram(
    'pgvector_query_duration_seconds',
    'pgvector query duration',
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

vector_query_total = Counter(
    'pgvector_queries_total',
    'Total pgvector queries'
)

index_health_gauge = Gauge(
    'pgvector_index_health',
    'pgvector index health status',
    ['table_name', 'column_name']
)

cache_hit_rate = Gauge(
    'memory_cache_hit_rate',
    'Memory service cache hit rate'
)

# Monitoring decorator
def monitor_vector_query(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            vector_query_total.inc()
            return result
        finally:
            vector_query_duration.observe(time.time() - start_time)
    return wrapper
```

### 2. Grafana Dashboard Configuration

```json
{
  "dashboard": {
    "title": "PGVector Performance Monitoring",
    "panels": [
      {
        "title": "Query Latency Percentiles",
        "targets": [
          {
            "expr": "histogram_quantile(0.5, pgvector_query_duration_seconds_bucket)",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, pgvector_query_duration_seconds_bucket)",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, pgvector_query_duration_seconds_bucket)",
            "legendFormat": "p99"
          }
        ]
      },
      {
        "title": "Query Throughput",
        "targets": [
          {
            "expr": "rate(pgvector_queries_total[5m])",
            "legendFormat": "QPS"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "targets": [
          {
            "expr": "memory_cache_hit_rate",
            "legendFormat": "Hit Rate %"
          }
        ]
      }
    ]
  }
}
```

### 3. Alert Rules

```yaml
# prometheus_alerts.yml
groups:
  - name: pgvector_alerts
    rules:
      - alert: HighVectorQueryLatency
        expr: histogram_quantile(0.95, pgvector_query_duration_seconds_bucket) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High pgvector query latency detected"
          description: "95th percentile query latency is {{ $value }}s"
      
      - alert: UnusedVectorIndex
        expr: pgvector_index_health == 0
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "Unused vector index detected"
          description: "Index on {{ $labels.table_name }}.{{ $labels.column_name }} has no usage"
      
      - alert: LowCacheHitRate
        expr: memory_cache_hit_rate < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low memory cache hit rate"
          description: "Cache hit rate is {{ $value }}"
```

## Monitoring Checklist

### Daily Checks
- [ ] Query latency percentiles within thresholds
- [ ] All vector indexes being used (no unused indexes)
- [ ] Cache hit rates above 80%
- [ ] No long-running idle transactions

### Weekly Checks
- [ ] Index size growth is proportional to data growth
- [ ] Memory optimization status for all tables
- [ ] Connection pool utilization patterns
- [ ] Query plan analysis for top vector queries

### Monthly Checks
- [ ] Full index health assessment
- [ ] Performance trend analysis
- [ ] Capacity planning review
- [ ] Cost optimization opportunities

## Troubleshooting Guide

### High Query Latency

1. **Check current ef_search setting:**
```sql
SHOW hnsw.ef_search;
```

2. **Adjust query quality if needed:**
```python
# For better accuracy at cost of speed
await pgvector_service.set_query_quality(ef_search=200)
```

3. **Verify index exists and is used:**
```sql
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM memories 
ORDER BY embedding <-> '[...]'::vector 
LIMIT 10;
```

### Low Cache Hit Rate

1. **Analyze cache patterns:**
```python
# Log cache misses with query patterns
logger.info(f"Cache miss for query: {search_request.query[:50]}...")
```

2. **Adjust cache TTL if needed:**
```python
# Increase cache TTL for stable data
memory_service = MemoryService(cache_ttl=600)  # 10 minutes
```

### Index Bloat

1. **Rebuild index if severely bloated:**
```sql
-- Create new index concurrently
CREATE INDEX CONCURRENTLY idx_memories_embedding_new 
ON memories USING hnsw (embedding vector_cosine_ops);

-- Drop old index
DROP INDEX idx_memories_embedding_old;

-- Rename new index
ALTER INDEX idx_memories_embedding_new 
RENAME TO idx_memories_embedding;
```

## Best Practices

1. **Use Read Replicas for Monitoring Queries**
   - Run monitoring queries on read replicas to avoid impacting production
   - Use Supabase read replica endpoints when available

2. **Implement Circuit Breakers**
   - Prevent cascading failures during high latency periods
   - Automatically fallback to simpler queries if needed

3. **Monitor Trending Metrics**
   - Track week-over-week changes in query patterns
   - Identify gradual performance degradation early

4. **Automate Optimization**
   - Schedule regular optimization runs during low-traffic periods
   - Use the PGVectorService optimization methods

---

## Related Documentation

- [Database Architecture Diagrams](/docs/architecture/database-architecture-diagrams.md) - Visual architecture overview
- [Database Optimization Lessons](/docs/developers/database-optimization-lessons.md) - Lessons learned from optimization
- [Deployment Guide](/docs/operators/deployment-guide.md) - Production deployment best practices
- [Security Guide](/docs/operators/security-guide.md) - Security monitoring and best practices

---

*Monitoring guide created: June 17, 2025*  
*Based on simplified architecture from BJO-212*