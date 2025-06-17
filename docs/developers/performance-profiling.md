# ⚡ Performance Profiling Guide

> *Last updated: June 16, 2025*

This guide covers performance profiling and optimization techniques for TripSage AI, focusing on identifying bottlenecks and improving system performance.

## 📋 Table of Contents

- [🐍 Python Backend Profiling](#-python-backend-profiling)
- [🎨 Frontend Performance](#-frontend-performance)
- [🗄️ Database Optimization](#️-database-optimization)
- [🔄 Cache Performance](#-cache-performance)
- [🌐 API Performance](#-api-performance)
- [📊 Monitoring & Metrics](#-monitoring--metrics)
- [🔧 Optimization Strategies](#-optimization-strategies)
- [📈 Performance Testing](#-performance-testing)

## 🐍 Python Backend Profiling

### **CPU Profiling**

```python
import cProfile
import pstats
from functools import wraps

def profile_function(func):
    """Profile function execution."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(10)
    
    return wrapper

# Usage
@profile_function
async def search_flights(params: FlightSearchParams):
    """Profile flight search performance."""
    return await duffel_client.search_flights(params)
```

### **Memory Profiling**

```python
import tracemalloc
import psutil
import asyncio

async def profile_memory_usage():
    """Profile memory usage patterns."""
    
    # Start memory tracing
    tracemalloc.start()
    
    # Get initial memory
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform operations
    trips = await load_large_dataset()
    
    # Get memory snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    final_memory = process.memory_info().rss / 1024 / 1024
    
    print(f"Memory usage: {initial_memory:.1f}MB → {final_memory:.1f}MB")
    print("Top allocations:")
    for stat in top_stats[:5]:
        print(f"  {stat.size / 1024:.1f}KB: {stat.traceback.format()[-1]}")
    
    tracemalloc.stop()
```

### **Async Performance**

```python
import asyncio
import time

async def profile_async_operations():
    """Profile async operation performance."""
    
    # Test concurrent vs sequential
    tasks = [
        search_flights_async(params1),
        search_hotels_async(params2),
        get_weather_async(location)
    ]
    
    # Sequential execution
    start_time = time.time()
    results_sequential = []
    for task in tasks:
        result = await task
        results_sequential.append(result)
    sequential_time = time.time() - start_time
    
    # Concurrent execution
    start_time = time.time()
    results_concurrent = await asyncio.gather(*tasks)
    concurrent_time = time.time() - start_time
    
    print(f"Sequential: {sequential_time:.2f}s")
    print(f"Concurrent: {concurrent_time:.2f}s")
    print(f"Speedup: {sequential_time/concurrent_time:.1f}x")
```

## 🎨 Frontend Performance

### **React Performance**

```typescript
// Performance monitoring
import { Profiler, ProfilerOnRenderCallback } from 'react';

const onRenderCallback: ProfilerOnRenderCallback = (
  id,
  phase,
  actualDuration,
  baseDuration,
  startTime,
  commitTime
) => {
  console.log('Profiler:', {
    id,
    phase,
    actualDuration,
    baseDuration,
    startTime,
    commitTime
  });
};

export const TripPlanningApp = () => {
  return (
    <Profiler id="TripPlanning" onRender={onRenderCallback}>
      <TripPlanningComponent />
    </Profiler>
  );
};

// Optimize re-renders
import { memo, useMemo, useCallback } from 'react';

export const TripCard = memo<TripCardProps>(({ trip, onSelect }) => {
  const formattedDates = useMemo(() => {
    return formatDateRange(trip.startDate, trip.endDate);
  }, [trip.startDate, trip.endDate]);

  const handleClick = useCallback(() => {
    onSelect(trip.id);
  }, [trip.id, onSelect]);

  return (
    <div onClick={handleClick}>
      <h3>{trip.name}</h3>
      <p>{formattedDates}</p>
    </div>
  );
});
```

### **Bundle Analysis**

```bash
# Analyze bundle size
cd frontend
npx @next/bundle-analyzer

# Check for large dependencies
npx webpack-bundle-analyzer .next/static/chunks/*.js
```

### **Core Web Vitals**

```typescript
// Monitor Core Web Vitals
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals';

function sendToAnalytics(metric: any) {
  console.log('Web Vital:', metric);
  // Send to analytics service
}

// Measure all vitals
getCLS(sendToAnalytics);
getFID(sendToAnalytics);
getFCP(sendToAnalytics);
getLCP(sendToAnalytics);
getTTFB(sendToAnalytics);
```

## 🗄️ Database Optimization

### **Query Performance**

```python
# Profile database queries
import time
from sqlalchemy import text

async def profile_database_queries(db: AsyncSession):
    """Profile database query performance."""
    
    queries = [
        ("Simple select", select(TripModel).where(TripModel.user_id == user_id)),
        ("With joins", select(TripModel).options(joinedload(TripModel.destinations))),
        ("Complex aggregation", text("""
            SELECT t.*, COUNT(d.id) as dest_count
            FROM trips t LEFT JOIN destinations d ON t.id = d.trip_id
            WHERE t.user_id = :user_id GROUP BY t.id
        """))
    ]
    
    for name, query in queries:
        start_time = time.time()
        
        if isinstance(query, str):
            result = await db.execute(text(query), {"user_id": user_id})
        else:
            result = await db.execute(query)
        
        rows = result.fetchall() if hasattr(result, 'fetchall') else result.scalars().all()
        execution_time = time.time() - start_time
        
        print(f"{name}: {execution_time:.3f}s ({len(rows)} rows)")

# Index analysis
async def analyze_query_performance(db: AsyncSession):
    """Analyze query execution plans."""
    
    query = text("""
        EXPLAIN (ANALYZE, BUFFERS)
        SELECT t.*, d.name as destination_name
        FROM trips t
        JOIN destinations d ON t.id = d.trip_id
        WHERE t.user_id = :user_id
        ORDER BY t.created_at DESC
        LIMIT 10
    """)
    
    result = await db.execute(query, {"user_id": user_id})
    for row in result:
        print(row[0])
```

### **Connection Pool Monitoring**

```python
async def monitor_connection_pool():
    """Monitor database connection pool performance."""
    
    engine = get_database_engine()
    pool = engine.pool
    
    metrics = {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalidated()
    }
    
    print(f"Connection Pool Metrics: {metrics}")
    
    # Alert if pool utilization is high
    utilization = metrics["checked_out"] / metrics["pool_size"]
    if utilization > 0.8:
        print(f"⚠️  High pool utilization: {utilization:.1%}")
```

## 🔄 Cache Performance

### **Cache Hit Rates**

```python
class CacheMetrics:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.total_time = 0
    
    async def get_with_metrics(self, key: str):
        """Get cache value with performance metrics."""
        start_time = time.time()
        
        value = await cache_service.get(key)
        
        execution_time = time.time() - start_time
        self.total_time += execution_time
        
        if value is not None:
            self.hits += 1
        else:
            self.misses += 1
        
        return value
    
    def get_stats(self):
        """Get cache performance statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        avg_time = self.total_time / total_requests if total_requests > 0 else 0
        
        return {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "avg_response_time": avg_time
        }

# Usage
cache_metrics = CacheMetrics()

@cache_result(ttl=3600)
async def cached_flight_search(params):
    """Cached flight search with metrics."""
    return await duffel_client.search_flights(params)
```

## 🌐 API Performance

### **Response Time Monitoring**

```python
import time
from fastapi import Request, Response

@app.middleware("http")
async def performance_middleware(request: Request, call_next):
    """Monitor API performance."""
    
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:  # Slow request threshold
        print(f"⚠️  Slow request: {request.method} {request.url} ({process_time:.2f}s)")
    
    return response

# Rate limiting performance
class PerformantRateLimiter:
    def __init__(self):
        self.redis_client = get_redis_client()
    
    async def check_rate_limit(self, identifier: str) -> bool:
        """High-performance rate limiting using Redis."""
        
        key = f"rate_limit:{identifier}"
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 60)  # 1 minute window
        
        results = await pipe.execute()
        current_count = results[0]
        
        return current_count <= 100  # Rate limit
```

## 📊 Monitoring & Metrics

### **Application Metrics**

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_database_connections', 'Active database connections')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect application metrics."""
    
    start_time = time.time()
    
    # Increment request counter
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()
    
    response = await call_next(request)
    
    # Record request duration
    REQUEST_DURATION.observe(time.time() - start_time)
    
    return response

# Custom metrics
async def collect_custom_metrics():
    """Collect custom application metrics."""
    
    # Database connections
    engine = get_database_engine()
    ACTIVE_CONNECTIONS.set(engine.pool.checkedout())
    
    # Cache hit rate
    cache_stats = await cache_service.info()
    cache_hit_rate = cache_stats.get('keyspace_hits', 0) / max(cache_stats.get('keyspace_misses', 1), 1)
    
    print(f"Cache hit rate: {cache_hit_rate:.2%}")
```

### **Health Checks**

```python
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with performance metrics."""
    
    start_time = time.time()
    
    # Check database
    db_start = time.time()
    try:
        async with AsyncSession(engine) as session:
            await session.execute(text("SELECT 1"))
        db_status = "healthy"
        db_latency = time.time() - db_start
    except Exception as e:
        db_status = f"unhealthy: {e}"
        db_latency = None
    
    # Check cache
    cache_start = time.time()
    try:
        await cache_service.ping()
        cache_status = "healthy"
        cache_latency = time.time() - cache_start
    except Exception as e:
        cache_status = f"unhealthy: {e}"
        cache_latency = None
    
    total_time = time.time() - start_time
    
    return {
        "status": "healthy" if db_status == "healthy" and cache_status == "healthy" else "degraded",
        "checks": {
            "database": {"status": db_status, "latency_ms": db_latency * 1000 if db_latency else None},
            "cache": {"status": cache_status, "latency_ms": cache_latency * 1000 if cache_latency else None}
        },
        "total_check_time_ms": total_time * 1000
    }
```

## 🔧 Optimization Strategies

### **Caching Strategies**

```python
# Multi-level caching
class MultiLevelCache:
    def __init__(self):
        self.memory_cache = {}  # L1 cache
        self.redis_cache = get_redis_client()  # L2 cache
    
    async def get(self, key: str):
        """Get value from multi-level cache."""
        
        # Check L1 cache (memory)
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # Check L2 cache (Redis)
        value = await self.redis_cache.get(key)
        if value:
            # Populate L1 cache
            self.memory_cache[key] = value
            return value
        
        return None
    
    async def set(self, key: str, value: any, ttl: int = 3600):
        """Set value in multi-level cache."""
        
        # Set in both caches
        self.memory_cache[key] = value
        await self.redis_cache.setex(key, ttl, value)

# Cache warming
async def warm_cache():
    """Pre-populate cache with frequently accessed data."""
    
    # Popular destinations
    popular_destinations = await get_popular_destinations()
    for dest in popular_destinations:
        cache_key = f"destination:{dest.id}"
        await cache_service.set(cache_key, dest, ttl=86400)  # 24 hours
    
    print(f"Warmed cache with {len(popular_destinations)} destinations")
```

### **Database Optimization**

```python
# Connection pooling optimization
from sqlalchemy.pool import QueuePool

def create_optimized_engine():
    """Create database engine with optimized settings."""
    
    return create_async_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=20,          # Base connections
        max_overflow=30,       # Additional connections
        pool_pre_ping=True,    # Validate connections
        pool_recycle=3600,     # Recycle connections hourly
        echo=False             # Disable SQL logging in production
    )

# Batch operations
async def batch_insert_trips(trips_data: List[dict]):
    """Efficiently insert multiple trips."""
    
    async with AsyncSession(engine) as session:
        # Use bulk insert for better performance
        session.add_all([TripModel(**data) for data in trips_data])
        await session.commit()
        
        print(f"Inserted {len(trips_data)} trips in batch")
```

## 📈 Performance Testing

### **Load Testing**

```python
# Load testing with asyncio
import asyncio
import aiohttp
import time

async def load_test_endpoint(url: str, concurrent_requests: int = 100):
    """Load test an API endpoint."""
    
    async def make_request(session, request_id):
        start_time = time.time()
        try:
            async with session.get(url) as response:
                await response.text()
                return {
                    "request_id": request_id,
                    "status": response.status,
                    "duration": time.time() - start_time
                }
        except Exception as e:
            return {
                "request_id": request_id,
                "status": "error",
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    # Run concurrent requests
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session, i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks)
    
    # Analyze results
    successful = [r for r in results if r["status"] == 200]
    failed = [r for r in results if r["status"] != 200]
    
    avg_duration = sum(r["duration"] for r in successful) / len(successful) if successful else 0
    
    print(f"Load test results:")
    print(f"  Successful: {len(successful)}/{concurrent_requests}")
    print(f"  Failed: {len(failed)}")
    print(f"  Average duration: {avg_duration:.3f}s")
    print(f"  Requests/second: {len(successful) / max(avg_duration, 0.001):.1f}")

# Usage
await load_test_endpoint("http://localhost:8001/api/trips", 100)
```

### **Benchmark Comparisons**

```python
import timeit

def benchmark_operations():
    """Benchmark different implementation approaches."""
    
    # Test different serialization methods
    data = {"trip_id": "123", "destinations": ["Paris", "Rome"]}
    
    # JSON serialization
    json_time = timeit.timeit(
        lambda: json.dumps(data),
        number=10000
    )
    
    # Pickle serialization
    pickle_time = timeit.timeit(
        lambda: pickle.dumps(data),
        number=10000
    )
    
    print(f"JSON serialization: {json_time:.3f}s")
    print(f"Pickle serialization: {pickle_time:.3f}s")
    print(f"JSON is {pickle_time/json_time:.1f}x faster" if json_time < pickle_time else f"Pickle is {json_time/pickle_time:.1f}x faster")

# Database query benchmarks
async def benchmark_queries():
    """Benchmark different query approaches."""
    
    # Test eager loading vs lazy loading
    async with AsyncSession(engine) as session:
        
        # Lazy loading
        start_time = time.time()
        trips = await session.execute(select(TripModel))
        for trip in trips.scalars():
            destinations = await trip.awaitable_attrs.destinations
        lazy_time = time.time() - start_time
        
        # Eager loading
        start_time = time.time()
        trips = await session.execute(
            select(TripModel).options(joinedload(TripModel.destinations))
        )
        for trip in trips.scalars():
            destinations = trip.destinations
        eager_time = time.time() - start_time
        
        print(f"Lazy loading: {lazy_time:.3f}s")
        print(f"Eager loading: {eager_time:.3f}s")
```

---

This performance profiling guide provides essential tools and techniques for optimizing TripSage AI performance across all system components. Use these methods to identify bottlenecks and improve system efficiency.
