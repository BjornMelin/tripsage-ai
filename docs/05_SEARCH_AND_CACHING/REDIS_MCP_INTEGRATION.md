# Redis MCP Integration for TripSage

This document describes the Redis MCP integration in TripSage, which provides a standardized interface for caching operations using the Model Context Protocol (MCP) architecture.

## 1. Overview

The Redis MCP implementation provides a comprehensive caching solution that integrates with TripSage's MCP architecture. It offers advanced features such as distributed locking, batch operations, and content-aware TTL management.

## 2. Core Components

1. **RedisMCPWrapper** (`tripsage/mcp_abstraction/wrappers/redis_wrapper.py`):
   - Implements the `BaseMCPWrapper` interface
   - Maps user-friendly method names to Redis operations
   - Provides a standardized interface for Redis operations

2. **RedisMCPClient** (`tripsage/mcp_abstraction/wrappers/redis_wrapper.py`):
   - Handles direct communication with Redis
   - Implements core Redis operations
   - Provides advanced features like distributed locking and pipelining

3. **Cache Tools** (`tripsage/utils/cache_tools.py`):
   - Provides high-level caching utilities using Redis MCP
   - Implements caching decorators for different content types
   - Offers batch operations and cache prefetching

4. **Web Tools** (`tripsage/tools/web_tools.py`):
   - Implements `CachedWebSearchTool` with Redis MCP-based caching
   - Provides batch web search operations with optimized caching

## 3. Key Features

### Content-Aware Caching

The Redis MCP implementation uses a content-aware TTL management system that adjusts cache expiration times based on the volatility of the content:

- **REALTIME**: 100s (weather, stock prices)
- **TIME_SENSITIVE**: 300s (news, social media)
- **DAILY**: 3600s (flight prices, events)
- **SEMI_STATIC**: 28800s (restaurant menus, business details)
- **STATIC**: 86400s (historical data, documentation)

### Distributed Locking

Supports distributed locking for coordinating operations across multiple application instances:

```python
async with cache_lock("critical-operation"):
    # This section is protected by a distributed lock
    # Only one application instance can execute it at a time
    await perform_critical_operation()
```

### Batch Operations

Optimizes performance with batch operations that reduce network round-trips:

```python
results = await batch_cache_get(["key1", "key2", "key3"])
```

### Cache Prefetching

Improves cache hit rates by prefetching predictable keys:

```python
await prefetch_cache_keys("websearch:*")
```

### Decorator-Based Caching

Simplifies caching implementation with decorators for different content types:

```python
@cached_daily
async def get_flight_prices(origin, destination, date):
    # Function will be cached with TTL appropriate for daily data
    ...
```

## 4. Implementation Details

### Cache Key Generation

Redis MCP uses a deterministic key generation algorithm that considers:
- Function name and module
- Query parameters
- Additional context (user location, search parameters)

### Error Handling

Comprehensive error handling ensures cache failures don't affect application stability:
- Graceful degradation on cache misses
- Logging of cache-related errors
- Fallback mechanisms for critical operations

### Performance Monitoring

Built-in statistics collection for monitoring cache performance:
- Hit/miss rates
- Cache size estimation
- Operation counts (gets, sets, deletes)
- Time-windowed metrics (1h, 24h, 7d)

## 5. Integration with WebSearchTool

The `CachedWebSearchTool` implementation demonstrates integration with OpenAI's Agents SDK:
- Content-aware caching based on query characteristics
- Thundering herd prevention with distributed locks
- Prefetching of related queries for improved hit rate
- Batch operations for multiple searches

## 6. Testing

Comprehensive test suite included:
- Unit tests for Redis MCP client and wrapper
- Tests for cache utilities and decorators
- Web tools caching tests
- Content type detection tests

## 7. Future Enhancements

Planned enhancements for the Redis MCP implementation:
- Integration with OpenTelemetry for advanced metrics
- Adaptive TTL based on access patterns
- Enhanced prefetching algorithms
- Integration with additional agent components