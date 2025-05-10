# Search and Caching Strategy for TripSage

This document outlines the comprehensive search and caching strategy for the TripSage travel planning system. It details the approach to efficient data retrieval, storage, and management across multiple travel data sources while ensuring optimal performance and user experience.

## 1. Introduction

TripSage's search and caching strategy addresses several key challenges inherent in travel applications:

- **Data Volatility**: Flight and hotel prices change frequently
- **Large Data Volumes**: Massive amounts of travel inventory to search and filter
- **API Rate Limitations**: External travel APIs often impose strict rate limits
- **Performance Expectations**: Users expect fast search results despite complex queries
- **Distributed Architecture**: Data flows through multiple services and components

This strategy leverages multi-level caching, intelligent search optimizations, and forward-looking data analysis to deliver a high-performance travel planning experience.

## 2. Search Strategy

### 2.1 Multi-Source Search Integration

TripSage implements a federated search approach, querying multiple data sources through specialized MCP servers:

- **Flight MCP Server**: Queries flight APIs and aggregators
- **Accommodation MCP Server**: Searches hotels, vacation rentals, and other lodging options
- **Google Maps MCP Server**: Provides location and point-of-interest data
- **Memory MCP Server**: Queries the knowledge graph for contextual and historical data

### 2.2 Search Request Optimization

To minimize unnecessary API calls and improve performance:

1. **Query Preprocessing**:

   - Normalize location names and airport codes
   - Validate date ranges and traveler numbers
   - Apply business rules to filter impossible or unlikely search criteria

2. **Query Parameterization**:

   - Implement flexible date searching (±3 days when appropriate)
   - Support for geo-based radius searches
   - Price range adjustments based on market data

3. **Search Parallelization**:
   - Execute independent searches concurrently (e.g., flights and hotels)
   - Implement asynchronous processing for non-blocking operations
   - Use connection pooling for API requests

### 2.3 Forward-Looking Search Intelligence

TripSage leverages forward-looking search data to optimize results:

- **Search Pattern Analysis**: Identify trends in user search behaviors
- **Demand Forecasting**: Predict high-demand routes and destinations
- **Preemptive Loading**: Preload data for popular searches during low-traffic periods

### 2.4 Machine Learning Integration

Machine learning models enhance search capabilities:

- **Personalized Ranking**: Sort results based on user preferences and behavior
- **Price Prediction**: Estimate future price trends to guide purchase timing
- **Anomaly Detection**: Identify and filter out data outliers and errors

## 3. Caching Architecture

TripSage implements a multi-tiered caching strategy leveraging Redis as the primary caching technology:

### 3.1 Cache Levels

1. **CDN Cache (Edge)**:

   - Caches static assets and public content
   - Geographic distribution for reduced latency
   - Typical TTL: 24 hours for static content

2. **Application Cache (Redis)**:

   - Caches search results, API responses, and computed data
   - Distributed across multiple regions
   - Configurable TTL based on data volatility
   - Supports complex data structures and query patterns

3. **Database Query Cache**:

   - Caches frequent database queries
   - Uses Supabase's built-in caching capabilities
   - Automatically invalidated on data changes

4. **Client-Side Cache (Browser/App)**:
   - Caches user preferences and recent searches
   - Leverages service workers for offline capability
   - Implements stale-while-revalidate pattern for responsiveness

### 3.2 Redis Implementation

Redis serves as the core caching engine with the following configuration:

```typescript
// Redis client configuration (example)
import { createClient } from "redis";

export const redisClient = createClient({
  url: process.env.REDIS_URL,
  // Enable TLS for production
  socket: {
    tls: process.env.NODE_ENV === "production",
    rejectUnauthorized: process.env.NODE_ENV === "production",
  },
  // Default TTL 30 minutes
  defaultTTL: 1800,
});

// Connect and handle errors
redisClient.connect().catch((err) => {
  console.error("Redis connection error:", err);
});

redisClient.on("error", (err) => {
  console.error("Redis client error:", err);
});
```

#### Key Redis Use Cases

1. **Search Result Caching**:

   ```typescript
   export async function cacheSearchResults(
     searchParams: SearchParams,
     results: SearchResults
   ): Promise<void> {
     const cacheKey = generateSearchCacheKey(searchParams);
     const ttl = determineTTL(searchParams, results);

     await redisClient.set(cacheKey, JSON.stringify(results), { EX: ttl });
   }

   export async function getSearchResults(
     searchParams: SearchParams
   ): Promise<SearchResults | null> {
     const cacheKey = generateSearchCacheKey(searchParams);
     const cached = await redisClient.get(cacheKey);

     return cached ? JSON.parse(cached) : null;
   }
   ```

2. **API Rate Limiting**:

   ```typescript
   export async function checkRateLimit(
     apiKey: string,
     endpoint: string,
     limit: number = 100,
     windowSeconds: number = 3600
   ): Promise<boolean> {
     const now = Date.now();
     const windowStart = now - windowSeconds * 1000;
     const rateKey = `ratelimit:${apiKey}:${endpoint}`;

     // Use sorted set with timestamp scores
     await redisClient.zRemRangeByScore(rateKey, 0, windowStart);
     const count = await redisClient.zCard(rateKey);

     if (count >= limit) {
       return false; // Rate limit exceeded
     }

     // Add current request timestamp to sorted set
     await redisClient.zAdd(rateKey, [{ score: now, value: now.toString() }]);
     await redisClient.expire(rateKey, windowSeconds);

     return true; // Request allowed
   }
   ```

3. **Real-time Price Tracking**:

   ```typescript
   export async function trackPriceChange(
     entityType: "flight" | "hotel",
     entityId: string,
     price: number
   ): Promise<PriceChange | null> {
     const key = `price:${entityType}:${entityId}`;
     const oldPrice = await redisClient.get(key);

     // Store current price with 24-hour expiry
     await redisClient.set(key, price.toString(), { EX: 86400 });

     if (oldPrice) {
       const previous = parseFloat(oldPrice);
       const change = price - previous;
       const percentChange = (change / previous) * 100;

       return {
         previous,
         current: price,
         change,
         percentChange,
       };
     }

     return null; // No previous price to compare
   }
   ```

### 3.3 Cache Key Design

TripSage follows these principles for cache key design:

- **Hierarchical Naming**: Uses namespaces to organize keys (e.g., `flights:search:LAX-JFK:2025-06-01`)
- **Deterministic Generation**: Same search parameters always produce the same cache key
- **Normalization**: Standardizes parameters (lowercase, sorted, etc.) for consistent key generation

Example key generation:

```typescript
export function generateSearchCacheKey(params: SearchParams): string {
  // Normalize parameters
  const normalized = {
    ...params,
    origin: params.origin.toUpperCase(),
    destination: params.destination.toUpperCase(),
    travelers: params.travelers || 1,
    cabinClass: (params.cabinClass || "economy").toLowerCase(),
  };

  // Sort optional filters for deterministic key generation
  if (normalized.filters) {
    normalized.filters = Object.fromEntries(
      Object.entries(normalized.filters).sort(([a], [b]) => a.localeCompare(b))
    );
  }

  // Generate key based on search type
  switch (params.type) {
    case "flight":
      return `flights:search:${normalized.origin}-${normalized.destination}:${
        normalized.departureDate
      }${normalized.returnDate ? `:${normalized.returnDate}` : ""}:${
        normalized.travelers
      }:${normalized.cabinClass}`;

    case "hotel":
      return `hotels:search:${normalized.destination}:${normalized.checkIn}:${
        normalized.checkOut
      }:${normalized.travelers}:${JSON.stringify(normalized.filters || {})}`;

    default:
      return `search:${params.type}:${JSON.stringify(normalized)}`;
  }
}
```

### 3.4 Cache Invalidation Strategies

TripSage employs several cache invalidation strategies:

1. **Time-Based Expiration (TTL)**:

   - Flight search results: 10-15 minutes
   - Hotel search results: 30-60 minutes
   - Location and static data: 24+ hours
   - User-specific data: Session duration

2. **Event-Based Invalidation**:

   - Price change notifications trigger invalidation
   - Inventory updates (e.g., seat availability) invalidate relevant caches
   - External API notifications for data changes

3. **Soft Invalidation**:

   - Implement stale-while-revalidate pattern
   - Serve stale data while fetching fresh data in background
   - Gradually phase out stale data with exponential backoff

4. **Purge Patterns**:
   - Targeted key deletion for specific updates
   - Pattern-based deletion for related keys (e.g., all searches for a specific route)
   - Complete cache clearing for major data refreshes

## 4. API Rate Limiting

### 4.1 External API Management

TripSage manages external API usage through:

1. **Rate Limiting Enforcement**:

   - Track API calls by endpoint, user, and time window
   - Implement token bucket algorithm using Redis
   - Apply different limits for various API providers

2. **Quota Management**:

   - Monitor API quotas and adjust search behavior
   - Implement circuit breakers for failing or rate-limited APIs
   - Fallback strategies when API limits are reached

3. **Request Optimization**:
   - Batch similar requests when possible
   - Deduplicate redundant API calls
   - Implement exponential backoff for retries

Example implementation:

```typescript
export class ApiRateLimiter {
  constructor(
    private redisClient: ReturnType<typeof createClient>,
    private config: {
      defaultLimit: number;
      defaultWindow: number; // seconds
      endpointLimits?: Record<string, { limit: number; window: number }>;
    }
  ) {}

  public async checkLimit(
    apiKey: string,
    endpoint: string
  ): Promise<{ allowed: boolean; remaining: number; reset: number }> {
    const { limit, window } = this.getLimitConfig(endpoint);
    const key = `ratelimit:${apiKey}:${endpoint}`;
    const now = Math.floor(Date.now() / 1000);
    const windowStart = now - window;

    // Remove expired tokens
    await this.redisClient.zRemRangeByScore(key, 0, windowStart);

    // Count remaining tokens
    const tokenCount = await this.redisClient.zCard(key);
    const remaining = Math.max(0, limit - tokenCount);
    const allowed = remaining > 0;

    // Add current request if allowed
    if (allowed) {
      await this.redisClient.zAdd(key, [{ score: now, value: now.toString() }]);
      await this.redisClient.expire(key, window * 2); // Set expiry
    }

    // Calculate reset time
    const oldestToken =
      tokenCount > 0
        ? (await this.redisClient.zRange(key, 0, 0, { WITHSCORES: true }))[0]
            .score
        : now;
    const reset = Math.max(now, Number(oldestToken) + window);

    return { allowed, remaining: allowed ? remaining - 1 : remaining, reset };
  }

  private getLimitConfig(endpoint: string): { limit: number; window: number } {
    return (
      this.config.endpointLimits?.[endpoint] || {
        limit: this.config.defaultLimit,
        window: this.config.defaultWindow,
      }
    );
  }
}
```

### 4.2 Internal API Management

TripSage also implements rate limiting for its own API endpoints:

1. **User-Based Limits**:

   - Free tier: Lower limits with strict enforcement
   - Premium users: Higher limits with burst capabilities
   - Administrative endpoints: Independent pools with higher limits

2. **Dynamic Rate Limiting**:

   - Adjust limits based on server load
   - Implement leaky bucket algorithm for smooth traffic
   - Apply gradual degradation during traffic spikes

3. **Rate Limit Headers**:
   - Include standard rate limit headers in responses:
     - `X-RateLimit-Limit`
     - `X-RateLimit-Remaining`
     - `X-RateLimit-Reset`
   - Provide clear error responses when limits are exceeded

## 5. Data Consistency and Freshness

### 5.1 Staleness Control

TripSage implements strategies to ensure data freshness:

1. **TTL Optimization**:

   - Set cache TTLs based on data volatility
   - Shorter TTLs for rapidly changing data (prices)
   - Longer TTLs for stable data (flight schedules, hotel amenities)

2. **Re-query Validation**:

   - Verify critical data (prices, availability) before checkout
   - Re-fetch data asynchronously in the background
   - Update cache with the latest information

3. **Differential Updates**:
   - Store base data with long TTLs
   - Apply incremental updates to cached data
   - Calculate final state by combining base data with updates

### 5.2 Data Versioning

TripSage implements data versioning to manage consistency:

1. **Version Tagging**:

   - Add version identifiers to cached data
   - Include last-updated timestamps
   - Track data source and request context

2. **Progressive Updates**:
   - Update cached data in phases
   - Support multiple concurrent versions during transitions
   - Gracefully deprecate outdated versions

## 6. Metrics and Monitoring

### 6.1 Cache Performance Metrics

TripSage tracks the following cache metrics:

1. **Hit/Miss Rates**:

   - Overall cache hit/miss percentage
   - Hit rates by data type and endpoint
   - Pattern-based hit rate analysis

2. **Cache Efficiency**:

   - Memory usage and eviction rates
   - Average TTL by key pattern
   - Cache churn (replacement frequency)

3. **Latency Metrics**:
   - Cache retrieval time
   - Comparison of cached vs. uncached response times
   - End-to-end request latency

### 6.2 Monitoring and Alerting

TripSage implements comprehensive monitoring:

1. **Real-time Dashboards**:

   - Redis cache metrics
   - API rate limit status
   - Search performance by endpoint

2. **Alerting Thresholds**:

   - Cache hit rate drops below 75%
   - API rate limit utilization exceeds 80%
   - Cache memory usage above 85%
   - Unusual cache invalidation patterns

3. **Performance Tracking**:
   - Long-term trends in cache efficiency
   - Correlation of cache metrics with business KPIs
   - A/B testing of cache strategies

## 7. API-Specific Cache Strategies

### 7.1 Flight Data Caching

Specific strategies for flight data:

1. **Search Results Caching**:

   - Short TTL (10-15 minutes)
   - Group similar searches (e.g., same route, ±1 day)
   - Prioritize caching for popular routes

2. **Flight Details Caching**:

   - Medium TTL (1-2 hours)
   - Store base data separately from pricing
   - Update pricing more frequently than flight details

3. **Fare Rules and Policies**:
   - Longer TTL (24+ hours)
   - Versioned caching with infrequent updates
   - Shared across related flights

### 7.2 Hotel Data Caching

Specific strategies for hotel data:

1. **Hotel Search Results**:

   - Medium TTL (30-60 minutes)
   - Geo-based partitioning
   - Season-aware caching (longer TTL in off-peak)

2. **Hotel Details**:

   - Longer TTL for static content (24+ hours)
   - Shorter TTL for pricing and availability (1-2 hours)
   - Separate caching for images and rich content

3. **Reviews and Ratings**:
   - Long TTL (24+ hours)
   - Incremental updates
   - Batch processing for new reviews

### 7.3 Location and Map Data

Specific strategies for location data:

1. **Geographic Data**:

   - Very long TTL (7+ days)
   - Hierarchical caching (continent > country > city)
   - Efficient storage of polygons and boundaries

2. **Points of Interest**:

   - Medium-long TTL (24-48 hours)
   - Radius-based caching
   - Category-specific invalidation

3. **Travel Times and Distances**:
   - Medium TTL (6-12 hours)
   - Time-of-day variations
   - Traffic-aware refresh cycles

## 8. Scaling and Performance

### 8.1 Horizontal Scaling

TripSage's caching scales horizontally:

1. **Redis Cluster**:

   - Multiple Redis nodes with sharding
   - Consistent hashing for key distribution
   - Automatic failover with sentinel

2. **Regional Deployment**:

   - Geo-distributed cache instances
   - Local caching for region-specific data
   - Global replication for shared data

3. **Load Balancing**:
   - Distribute cache operations across nodes
   - Intelligent routing based on key patterns
   - Auto-scaling based on load metrics

### 8.2 Performance Optimizations

TripSage implements these performance optimizations:

1. **Redis Commands**:

   - Use pipelining for batch operations
   - Leverage Lua scripts for atomic operations
   - Implement scan instead of keys for large datasets

2. **Memory Management**:

   - Configure maxmemory policy (volatile-ttl)
   - Implement key eviction monitoring
   - Optimize data structures for memory efficiency

3. **Connection Pooling**:
   - Maintain persistent connections to Redis
   - Configure optimal pool sizes
   - Implement connection health checks

### 8.3 Disaster Recovery

TripSage ensures cache resilience:

1. **Backup Strategies**:

   - Regular RDB snapshots
   - AOF persistence for critical data
   - Cross-region replication

2. **Failure Handling**:

   - Graceful degradation during cache failures
   - Automatic fallback to direct API calls
   - Circuit breakers for unavailable cache services

3. **Recovery Procedures**:
   - Automated cache warming after failures
   - Prioritized data restoration
   - Progressive traffic routing during recovery

## 9. Testing and Validation

### 9.1 Cache Effectiveness Testing

TripSage validates cache effectiveness through:

1. **Load Testing**:

   - Simulate high-traffic scenarios
   - Measure cache performance under load
   - Identify bottlenecks and optimization opportunities

2. **A/B Testing**:

   - Compare different cache strategies
   - Measure impact on response times and API usage
   - Validate cache key designs and TTL settings

3. **Chaos Testing**:
   - Simulate cache failures and network issues
   - Validate graceful degradation
   - Test recovery procedures

### 9.2 Continuous Monitoring

TripSage implements continuous monitoring:

1. **Cache Health Checks**:

   - Regular ping tests to Redis
   - Memory usage and eviction monitoring
   - Connection pool health verification

2. **Performance Trending**:

   - Track cache metrics over time
   - Correlate with application performance
   - Identify gradual degradation patterns

3. **Alerting Systems**:
   - Real-time notifications for cache issues
   - Predictive alerts for capacity problems
   - Integration with on-call rotation

## 10. Implementation Roadmap

TripSage will implement this caching strategy according to the following roadmap:

### Phase 1: Foundation (Month 1)

- Set up Redis infrastructure
- Implement basic search result caching
- Develop cache key standardization
- Configure TTL strategy

### Phase 2: Advanced Features (Month 2-3)

- Implement rate limiting
- Develop cache invalidation patterns
- Set up monitoring and alerting
- Optimize for high-volume endpoints

### Phase 3: Optimization (Month 4-5)

- Implement intelligent TTL management
- Develop predictive caching
- Set up A/B testing framework
- Optimize memory usage

### Phase 4: Scaling (Month 6+)

- Implement cluster scaling
- Set up geo-distributed caching
- Develop disaster recovery procedures
- Optimize for global performance

## Conclusion

TripSage's search and caching strategy is designed to balance performance, data freshness, and resource efficiency. By implementing multi-tiered caching with Redis, optimizing search queries, and carefully managing API rate limits, TripSage can deliver fast, accurate travel search results while controlling costs and ensuring scalability.

The strategy emphasizes data consistency, graceful degradation, and continuous improvement through metrics-driven optimization. As the application evolves, this strategy will adapt to changing traffic patterns, new data sources, and emerging technologies to maintain optimal performance.

## References

1. Redis Documentation: [redis.io/documentation](https://redis.io/documentation)
2. "Boosting Your App's Performance with Cross-Platform Caching Strategies", Medium (2023)
3. "Implementing Rate Limiting with Redis: A Developer's Guide", CodeZup (2024)
4. "Query Caching for Travel Planning Systems", U.S. Patent US20040249799A1
5. "API Rate Limiting: Strategies and Implementation", API7.ai (2023)
6. "Trip.com Case Study: StarRocks Implementation", CelerData (2024)
