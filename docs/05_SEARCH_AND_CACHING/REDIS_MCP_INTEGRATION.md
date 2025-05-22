# Redis MCP Integration for TripSage

This document describes the Redis MCP integration in TripSage, which provides a standardized interface for caching operations using the Model Context Protocol (MCP) architecture.

## 1. Overview

The Redis MCP implementation provides a comprehensive caching solution that integrates with TripSage's MCP architecture using the **official @modelcontextprotocol/server-redis package**. It offers advanced features such as distributed locking, batch operations, and content-aware TTL management built on top of the official Redis MCP server.

## 2. Core Components

1. **OfficialRedisMCPWrapper** (`tripsage/mcp_abstraction/wrappers/official_redis_wrapper.py`):
   - Implements the `BaseMCPWrapper` interface
   - Wraps the official Redis MCP server for TripSage integration
   - Maps user-friendly method names to official Redis MCP tools (set, get, delete, list)
   - Provides enhanced features like distributed locking and batch operations

2. **OfficialRedisMCPClient** (`tripsage/mcp_abstraction/wrappers/official_redis_wrapper.py`):
   - Handles communication with the official Redis MCP server via Docker
   - Implements core Redis operations through MCP tools
   - Provides JSON serialization/deserialization for complex data types
   - Includes performance statistics and monitoring

3. **Enhanced Cache Tools** (`tripsage/utils/cache_tools.py`):
   - Provides high-level caching utilities using Redis MCP
   - Implements caching decorators for different content types
   - Offers batch operations and cache prefetching
   - Includes distributed locking context managers

4. **Configuration** (`tripsage/config/mcp_settings.py`):
   - `RedisMCPConfig` for official Redis MCP server setup
   - Docker-based deployment configuration
   - Redis connection URL management

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

### Official Redis MCP Server Integration

The implementation uses the official Redis MCP server as an external process:
- **Docker Deployment**: Runs via `docker run -i --rm mcp/redis <redis_url>`
- **Stdio Transport**: Communicates through standard MCP protocol
- **Simple Operations**: Leverages official set, get, delete, list tools
- **Reliability**: Built on proven, maintained infrastructure

### Enhanced Features Layer

TripSage adds high-level features on top of the basic Redis operations:
- **Distributed Locking**: Implemented using Redis SET with TTL and token verification
- **Batch Operations**: Sequential execution with error handling (fallback for no pipelining)
- **Content-Aware TTL**: Automatic TTL assignment based on content volatility
- **JSON Serialization**: Automatic handling of complex data types

### Cache Key Generation

Redis MCP uses a deterministic key generation algorithm that considers:
- Function name and module
- Query parameters
- Additional context (user location, search parameters)
- SHA256 hashing for consistent key generation

### Error Handling

Comprehensive error handling ensures cache failures don't affect application stability:
- Graceful degradation on cache misses
- Logging of cache-related errors
- Fallback mechanisms for critical operations
- Exception chaining for better debugging

### Performance Monitoring

Built-in statistics collection for monitoring cache performance:
- Hit/miss rates per operation type
- Cache size estimation
- Operation counts (gets, sets, deletes)
- Content type breakdown statistics
- Average access times and cache efficiency metrics

## 5. Integration with WebSearchTool

The `CachedWebSearchTool` implementation demonstrates integration with OpenAI's Agents SDK:
- Content-aware caching based on query characteristics
- Thundering herd prevention with distributed locks
- Prefetching of related queries for improved hit rate
- Batch operations for multiple searches

## 6. Testing

Comprehensive test suite included:
- **Official Redis Wrapper Tests**: Full coverage of core operations and enhanced features
- **Enhanced Functionality Tests**: Distributed locking, batch operations, prefetching
- **Cache Utilities Tests**: Decorators, content type detection, error handling
- **Integration Tests**: End-to-end testing with official Redis MCP server
- **Performance Tests**: Load testing and cache efficiency validation

Test files:
- `tests/mcp_abstraction/wrappers/test_official_redis_wrapper.py`
- `tests/mcp_abstraction/wrappers/test_official_redis_simple.py`
- `tests/mcp_abstraction/wrappers/test_enhanced_redis_wrapper.py`

## 7. Usage Examples

### Basic Caching Operations
```python
from tripsage.utils.cache_tools import set_cache, get_cache, cache_lock
from tripsage.mcp_abstraction.wrappers.redis_wrapper import ContentType

# Set cache with content-aware TTL
await set_cache("flight:LAX-NYC", flight_data, content_type=ContentType.DAILY)

# Get cached data
cached_flight = await get_cache("flight:LAX-NYC")

# Use distributed locking
async with cache_lock("critical-flight-search"):
    # Protected operation
    results = await expensive_flight_search()
```

### Decorator-Based Caching
```python
from tripsage.utils.cache_tools import cached_daily, cached_realtime

@cached_daily
async def get_flight_prices(origin: str, destination: str, date: str):
    # Function will be cached for 1 hour (daily content type)
    return await flight_api.search(origin, destination, date)

@cached_realtime(ttl=60)  # Override TTL to 60 seconds
async def get_current_weather(city: str):
    # Function will be cached for 60 seconds
    return await weather_api.current(city)
```

### Batch Operations
```python
from tripsage.utils.cache_tools import batch_cache_set, batch_cache_get

# Batch set multiple values
items = [
    {"key": "hotel:1", "value": hotel_data_1, "content_type": ContentType.SEMI_STATIC},
    {"key": "hotel:2", "value": hotel_data_2, "content_type": ContentType.SEMI_STATIC},
]
results = await batch_cache_set(items)

# Batch get multiple values
values = await batch_cache_get(["hotel:1", "hotel:2", "hotel:3"])
```

## 8. Deployment

### Docker Setup
The Redis MCP server is automatically deployed via Docker:
```yaml
# Configuration in mcp_settings.py
redis:
  command: "docker"
  args: ["run", "-i", "--rm", "mcp/redis"]
  redis_url: "redis://localhost:6379"
```

### Redis Server Requirements
- Redis server running on specified URL (default: localhost:6379)
- Docker available for MCP server deployment
- Network access between TripSage and Redis instance

## 9. Monitoring and Management

### Cache Statistics
```python
from tripsage.utils.cache_tools import get_cache_stats

# Get comprehensive cache statistics
stats = await get_cache_stats()
print(f"Cache efficiency: {stats.cache_efficiency}%")
print(f"Total operations: {stats.operations}")
```

### Cache Management
```python
from tripsage.utils.cache_tools import clear_cache_by_pattern, clear_cache_by_content_type

# Clear specific patterns
await clear_cache_by_pattern("flight:*")

# Clear by content type
await clear_cache_by_content_type(ContentType.REALTIME)
```

## 10. Architecture Benefits

### Why Official Redis MCP Server?
- **Maintenance**: Leverages officially maintained, stable implementation
- **Compatibility**: Ensures compatibility with MCP ecosystem standards
- **Simplicity**: Four core operations (set/get/delete/list) following KISS principles
- **Reliability**: Battle-tested by the Model Context Protocol community
- **Future-Proof**: Automatic updates and improvements from official maintainers

### External First Strategy
This implementation exemplifies TripSage's "External First" MCP strategy:
1. **Use official MCPs** when available and suitable
2. **Add thin wrapper layers** for TripSage-specific features
3. **Build custom MCPs** only when external solutions don't meet requirements
4. **Maintain consistency** through standardized wrapper interfaces