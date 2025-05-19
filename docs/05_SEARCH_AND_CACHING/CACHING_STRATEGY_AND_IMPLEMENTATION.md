# TripSage Caching Strategy and Implementation Guide

This document provides a comprehensive guide to TripSage's caching strategy and its implementation, primarily leveraging Redis. Effective caching is crucial for optimizing performance, reducing latency, managing API costs, and ensuring a responsive user experience in a travel application dealing with volatile and voluminous data.

## 1. Overview of Caching Strategy

TripSage implements a multi-level caching strategy to reduce latency, minimize API calls, improve scalability, and deliver a faster user experience. Redis serves as the primary cache store.

## 2. Caching Architecture

1. **CDN Cache** (Edge for static assets).
2. **Application-Level Cache** (Redis) – Focus of this doc.
3. **Database Query Cache** (PostgreSQL).
4. **Client-Side Cache** (Browser-based).

## 3. Redis Setup and Client Implementation

- **Installation**: Docker or managed service.
- **`redis_cache.py`**: A wrapper for Redis operations (get, set, delete, TTL).
- **Namespaced Keys**: `f"{namespace}:{key}"`.

## 4. Cache Key Design and TTL Management

- **Key Structure**: `[namespace]:[entity_type]:[operation_type]:[params_hash]`.
- **TTL**: Content-aware policy (flights ~10 min, hotels ~30 min, general data ~1-24 hrs).
- **Dynamically Adjusted**: E.g., closer to travel date → shorter TTL for flight data.

## 5. Caching in Specific Components

- **WebSearchTool**: Specialized cache for search queries.
- **MCP Clients**: Cache results from external APIs (flights, weather, etc.) using generated keys.

## 6. Stale-While-Revalidate Pattern

- **Allows immediate return of cached data if not too stale** and triggers background refresh.

## 7. API Rate Limiting using Redis

- **RateLimiter**: Redis-based approach to throttle calls to external APIs.

## 8. Cache Invalidation Strategies

- **Time-Based Expiration (TTL)**: Primary method.
- **Manual Invalidation**: Admin endpoints or scripts.
- **Event-Based**: Future improvement for real-time triggers.

## 9. Monitoring and Management

- **Metrics**: Hit/miss rates, keys, TTL usage, tracked via Prometheus or logs.
- **Cache Management**: Admin endpoints to clear namespaces, reset cache.

## 10. Testing Caching

- **Unit Tests**: Mock Redis calls to ensure code attempts to get/set properly.
- **Integration Tests**: Against a live Redis instance.
- **Performance Tests**: Measure improvements with caching enabled/disabled.

## 11. Conclusion

TripSage’s Redis-based caching strategy underpins its performance by reducing unnecessary calls, intelligently managing TTL, and supporting patterns like stale-while-revalidate and rate limiting. This strategy is essential for a scalable and efficient travel planning system.
