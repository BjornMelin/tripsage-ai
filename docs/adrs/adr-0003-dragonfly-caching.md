# ADR-0003: Use DragonflyDB for High-Performance Caching

**Date**: 2025-06-17

## Status

Accepted

## Context

TripSage's AI agents require a high-performance caching layer to:

- Store frequently accessed flight and hotel search results
- Cache expensive AI model responses
- Maintain session state for multi-step workflows
- Handle high-throughput read/write operations
- Support complex data structures for agent memory

Traditional Redis, while popular, has limitations in multi-core utilization and memory efficiency that impact performance at scale.

## Decision

We will use DragonflyDB as our primary caching solution.

DragonflyDB provides:
- 25x higher throughput than Redis on multi-core machines
- Full Redis API compatibility (drop-in replacement)
- Memory efficiency with built-in compression
- Native support for modern hardware (NUMA-aware)
- Simplified operations (single binary, no clustering complexity)

## Consequences

### Positive

- **Performance**: Significantly higher throughput for agent operations
- **Compatibility**: Works with existing Redis clients and tools
- **Efficiency**: Better memory utilization reduces infrastructure costs
- **Simplicity**: Single-node can handle workloads that would require Redis cluster
- **Modern Architecture**: Designed for current hardware capabilities

### Negative

- **Maturity**: Newer project compared to Redis (though production-ready)
- **Ecosystem**: Smaller community and fewer third-party tools
- **Migration Path**: Less documented migration patterns from Redis
- **Enterprise Features**: Some Redis enterprise features not available

### Neutral

- Different performance characteristics may require tuning adjustments
- Team needs to monitor DragonflyDB-specific metrics
- Backup and persistence strategies differ from Redis

## Alternatives Considered

### Redis

The industry-standard in-memory data store.

**Why not chosen**: 
- Single-threaded architecture limits multi-core utilization
- Higher memory overhead
- Would require clustering for our performance needs
- More complex operational overhead

### Memcached

Simple, high-performance distributed memory caching system.

**Why not chosen**: 
- Limited data structure support
- No persistence options
- Lacks advanced features needed for agent state management
- No built-in pub/sub for real-time features

### KeyDB

Multi-threaded fork of Redis.

**Why not chosen**: 
- Less performance improvement compared to DragonflyDB
- Smaller community and uncertain long-term support
- Still carries Redis architectural limitations

## References

- [Caching Strategy Documentation](../05_SEARCH_AND_CACHING/CACHING_STRATEGY_AND_IMPLEMENTATION.md)
- [Infrastructure Upgrade Summary](../03_ARCHITECTURE/INFRASTRUCTURE_UPGRADE_SUMMARY.md)
- [DragonflyDB Benchmarks](https://www.dragonflydb.io/blog/dragonflydb-benchmarks)
- [System Architecture Overview](../03_ARCHITECTURE/SYSTEM_OVERVIEW.md)