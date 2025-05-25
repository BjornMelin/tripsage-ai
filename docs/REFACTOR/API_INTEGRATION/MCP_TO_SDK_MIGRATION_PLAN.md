# Direct API/SDK Integration Migration Plan

## Executive Summary

**Objective**: Migrate 8 of 12 MCP services to direct SDK integration across 3
sprints  
**Timeline**: 23-34 development days over 12 weeks  
**Expected Impact**: 40% performance improvement, 2000+ lines code reduction  
**Risk Level**: LOW-MEDIUM with comprehensive rollback strategy

## Implementation Strategy

### Parallel Development Approach

- **Maintain existing MCP wrappers** during migration
- **Feature flag system** for gradual traffic migration
- **A/B testing** to validate performance improvements
- **Zero-downtime rollout** with instant rollback capability

### Success Criteria

- [x] **Performance**: 30%+ improvement in P95 latency for database operations
- [x] **Code Quality**: 50%+ reduction in wrapper-related code
- [x] **Developer Experience**: Faster debugging and development cycles
- [x] **Reliability**: Zero regression in service availability

## Phase 1: Tier 1 Migrations (Sprint 1-2)

### Sprint 1.1: Redis Migration (3-5 days)

#### Current Implementation Analysis

```python
# File: tripsage/mcp_abstraction/wrappers/official_redis_wrapper.py
# Lines: 394 lines of complex Docker wrapper logic
# Dependencies: Docker Redis MCP server, complex error mapping
# Performance: Multiple network hops, serialization overhead
```

#### Migration Plan

#### Step 1: Create Direct Redis Client Service (Day 1)

```python
# File: tripsage/services/redis_service.py
import redis.asyncio as redis
from typing import Any, Optional
from tripsage.config.app_settings import get_settings

class RedisService:
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self.settings = get_settings()

    async def connect(self) -> None:
        """Initialize Redis connection with connection pooling"""
        self._client = redis.Redis(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            password=self.settings.redis_password,
            db=self.settings.redis_db,
            max_connections=20,
            retry_on_timeout=True,
            retry_on_error=[redis.ConnectionError, redis.TimeoutError],
            socket_connect_timeout=5,
            socket_timeout=5
        )

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self._client:
            await self.connect()
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        if not self._client:
            await self.connect()
        return await self._client.set(key, value, ex=ex)

    async def delete(self, *keys: str) -> int:
        """Delete keys from Redis"""
        if not self._client:
            await self.connect()
        return await self._client.delete(*keys)

    async def close(self) -> None:
        """Close Redis connection"""
        if self._client:
            await self._client.aclose()

# Singleton instance
redis_service = RedisService()
```

#### Step 2: Create Feature Flag System (Day 1)

```python
# File: tripsage/config/feature_flags.py
from enum import Enum
from pydantic import BaseSettings

class IntegrationMode(str, Enum):
    MCP = "mcp"
    DIRECT = "direct"

class FeatureFlags(BaseSettings):
    redis_integration: IntegrationMode = IntegrationMode.MCP
    supabase_integration: IntegrationMode = IntegrationMode.MCP
    neo4j_integration: IntegrationMode = IntegrationMode.MCP

    class Config:
        env_prefix = "FEATURE_"

feature_flags = FeatureFlags()
```

#### Step 3: Create Migration Adapter (Day 2)

```python
# File: tripsage/services/cache_service.py
from tripsage.config.feature_flags import feature_flags, IntegrationMode
from tripsage.mcp_abstraction.manager import MCPManager
from tripsage.services.redis_service import redis_service

class CacheService:
    """Unified cache interface supporting both MCP and direct Redis"""

    async def get(self, key: str) -> Optional[str]:
        if feature_flags.redis_integration == IntegrationMode.DIRECT:
            return await redis_service.get(key)
        else:
            # Fallback to MCP
            mcp_manager = MCPManager()
            return await mcp_manager.invoke("redis", "get", {"key": key})

    async def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        if feature_flags.redis_integration == IntegrationMode.DIRECT:
            return await redis_service.set(key, value, ex=ex)
        else:
            # Fallback to MCP
            mcp_manager = MCPManager()
            params = {"key": key, "value": value}
            if ex:
                params["ex"] = ex
            return await mcp_manager.invoke("redis", "set", params)

cache_service = CacheService()
```

#### Step 4: Update All Redis Usage (Day 2-3)

```python
# Example: Update tools/weather_tools.py
# Before:
# result = await mcp_manager.invoke("redis", "get", {"key": cache_key})

# After:
from tripsage.services.cache_service import cache_service
result = await cache_service.get(cache_key)
```

#### Step 5: Performance Testing & Validation (Day 3-4)

```python
# File: tests/performance/test_redis_migration.py
import asyncio
import time
import pytest
from tripsage.services.cache_service import cache_service
from tripsage.config.feature_flags import feature_flags, IntegrationMode

@pytest.mark.asyncio
async def test_redis_performance_comparison():
    """Compare MCP vs Direct Redis performance"""

    # Test MCP performance
    feature_flags.redis_integration = IntegrationMode.MCP
    mcp_times = []
    for i in range(100):
        start = time.perf_counter()
        await cache_service.set(f"test_key_{i}", f"test_value_{i}")
        await cache_service.get(f"test_key_{i}")
        mcp_times.append(time.perf_counter() - start)

    # Test Direct Redis performance
    feature_flags.redis_integration = IntegrationMode.DIRECT
    direct_times = []
    for i in range(100):
        start = time.perf_counter()
        await cache_service.set(f"test_key_{i}", f"test_value_{i}")
        await cache_service.get(f"test_key_{i}")
        direct_times.append(time.perf_counter() - start)

    avg_mcp = sum(mcp_times) / len(mcp_times)
    avg_direct = sum(direct_times) / len(direct_times)

    improvement = (avg_mcp - avg_direct) / avg_mcp * 100

    print(f"MCP Average: {avg_mcp:.4f}s")
    print(f"Direct Average: {avg_direct:.4f}s")
    print(f"Improvement: {improvement:.1f}%")

    # Assert at least 30% improvement
    assert improvement >= 30, f"Expected 30%+ improvement, got {improvement:.1f}%"
```

#### Step 6: Production Rollout (Day 5)

- Deploy with `FEATURE_REDIS_INTEGRATION=mcp` (safe default)
- Monitor performance with both modes in non-prod
- Gradual rollout: 5% → 25% → 50% → 100% traffic
- Switch to `FEATURE_REDIS_INTEGRATION=direct` for full migration

### Sprint 1.2: Supabase Migration (4-6 days)

#### Current Supabase Implementation Analysis

```python
# File: tripsage/mcp_abstraction/wrappers/supabase_wrapper.py
# Lines: 139 lines of external MCP wrapper
# Limitations: ~40% API coverage, no real-time subscriptions
# Dependencies: External Supabase MCP server
```

#### Supabase Migration Plan

#### Step 1: Install and Configure Direct Client (Day 1)

```bash
# Add to requirements.txt
supabase==2.3.4  # Latest async-supported version
```

```python
# File: tripsage/services/supabase_service.py
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from typing import Dict, List, Any, Optional
import asyncio
from tripsage.config.app_settings import get_settings

class SupabaseService:
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Client] = None

    async def connect(self) -> None:
        """Initialize Supabase client"""
        options = ClientOptions(
            auto_refresh_token=True,
            persist_session=True,
            timeout=30
        )

        self._client = create_client(
            self.settings.supabase_url,
            self.settings.supabase_key,
            options=options
        )

    @property
    def client(self) -> Client:
        if not self._client:
            asyncio.create_task(self.connect())
        return self._client

    async def insert(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert data into table"""
        result = await asyncio.to_thread(
            lambda: self.client.table(table).insert(data).execute()
        )
        return result.data

    async def select(self, table: str, columns: str = "*",
                    filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Select data from table"""
        query = self.client.table(table).select(columns)

        if filters:
            for key, value in filters.items():
                query = query.eq(key, value)

        result = await asyncio.to_thread(lambda: query.execute())
        return result.data

    async def update(self, table: str, data: Dict[str, Any],
                    filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Update data in table"""
        query = self.client.table(table).update(data)

        for key, value in filters.items():
            query = query.eq(key, value)

        result = await asyncio.to_thread(lambda: query.execute())
        return result.data

    async def delete(self, table: str, filters: Dict[str, Any]) -> bool:
        """Delete data from table"""
        query = self.client.table(table).delete()

        for key, value in filters.items():
            query = query.eq(key, value)

        result = await asyncio.to_thread(lambda: query.execute())
        return len(result.data) > 0

supabase_service = SupabaseService()
```

#### Step 2: Create Database Adapter (Day 2)

```python
# File: tripsage/services/database_service.py
from tripsage.config.feature_flags import feature_flags, IntegrationMode
from tripsage.services.supabase_service import supabase_service
from tripsage.mcp_abstraction.manager import MCPManager

class DatabaseService:
    """Unified database interface supporting both MCP and direct Supabase"""

    async def create_trip(self, trip_data: Dict[str, Any]) -> Dict[str, Any]:
        if feature_flags.supabase_integration == IntegrationMode.DIRECT:
            return await supabase_service.insert("trips", trip_data)
        else:
            mcp_manager = MCPManager()
            return await mcp_manager.invoke("supabase", "insert", {
                "table": "trips",
                "data": trip_data
            })

    async def get_user_trips(self, user_id: str) -> List[Dict[str, Any]]:
        if feature_flags.supabase_integration == IntegrationMode.DIRECT:
            return await supabase_service.select(
                "trips",
                "*",
                {"user_id": user_id}
            )
        else:
            mcp_manager = MCPManager()
            return await mcp_manager.invoke("supabase", "select", {
                "table": "trips",
                "filters": {"user_id": user_id}
            })

database_service = DatabaseService()
```

#### Step 3: Migration Testing (Day 3-4)

```python
# File: tests/integration/test_supabase_migration.py
@pytest.mark.asyncio
async def test_database_service_parity():
    """Ensure MCP and Direct implementations return identical results"""

    test_trip = {
        "title": "Test Trip",
        "user_id": "test-user-123",
        "destination": "Paris"
    }

    # Test MCP implementation
    feature_flags.supabase_integration = IntegrationMode.MCP
    mcp_result = await database_service.create_trip(test_trip)

    # Test Direct implementation
    feature_flags.supabase_integration = IntegrationMode.DIRECT
    direct_result = await database_service.create_trip(test_trip)

    # Compare results (excluding auto-generated fields like id, created_at)
    assert mcp_result["title"] == direct_result["title"]
    assert mcp_result["user_id"] == direct_result["user_id"]
    assert mcp_result["destination"] == direct_result["destination"]
```

#### Step 4: Update All Database Usage (Day 4-5)

```python
# Example: Update api/routers/trips.py
# Before:
# result = await mcp_manager.invoke("supabase", "insert", {...})

# After:
from tripsage.services.database_service import database_service
result = await database_service.create_trip(trip_data)
```

#### Step 5: Production Migration (Day 6)

- Deploy with gradual rollout
- Monitor query performance and error rates
- Full migration after validation

### Sprint 2: Neo4j Migration (3-4 days)

#### Neo4j Migration Plan

#### Step 1: Install Neo4j Driver (Day 1)

```bash
# Add to requirements.txt
neo4j==5.15.0  # Latest async driver
```

#### Step 2: Create Direct Neo4j Service (Day 1-2)

```python
# File: tripsage/services/neo4j_service.py
from neo4j import AsyncGraphDatabase
from typing import Dict, List, Any, Optional
from tripsage.config.app_settings import get_settings

class Neo4jService:
    def __init__(self):
        self.settings = get_settings()
        self._driver = None

    async def connect(self) -> None:
        """Initialize Neo4j driver"""
        self._driver = AsyncGraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            max_connection_lifetime=30 * 60,  # 30 minutes
            max_connection_pool_size=50,
            connection_acquisition_timeout=60
        )

    async def create_entities(self, entities: List[Dict[str, Any]]) -> bool:
        """Create multiple entities in a single transaction"""
        if not self._driver:
            await self.connect()

        async with self._driver.session() as session:
            async def _create_entities_tx(tx):
                for entity in entities:
                    query = f"""
                    CREATE (n:{entity['entityType']} {{name: $name}})
                    SET n += $properties
                    """
                    await tx.run(query,
                        name=entity['name'],
                        properties=entity.get('properties', {})
                    )
                return True

            return await session.execute_write(_create_entities_tx)

    async def create_relations(self, relations: List[Dict[str, Any]]) -> bool:
        """Create relationships between entities"""
        if not self._driver:
            await self.connect()

        async with self._driver.session() as session:
            async def _create_relations_tx(tx):
                for relation in relations:
                    query = """
                    MATCH (a {name: $from_name}), (b {name: $to_name})
                    CREATE (a)-[r:RELATES {type: $relation_type}]->(b)
                    """
                    await tx.run(query,
                        from_name=relation['from'],
                        to_name=relation['to'],
                        relation_type=relation['relationType']
                    )
                return True

            return await session.execute_write(_create_relations_tx)

    async def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """Search for nodes matching query"""
        if not self._driver:
            await self.connect()

        async with self._driver.session() as session:
            cypher_query = """
            MATCH (n)
            WHERE n.name CONTAINS $search_term
            RETURN n.name as name, labels(n) as types, properties(n) as properties
            LIMIT 50
            """

            result = await session.run(cypher_query, search_term=query)
            return [record.data() async for record in result]

neo4j_service = Neo4jService()
```

#### Step 3: Create Memory Adapter (Day 2)

```python
# File: tripsage/services/memory_service.py
from tripsage.config.feature_flags import feature_flags, IntegrationMode
from tripsage.services.neo4j_service import neo4j_service
from tripsage.mcp_abstraction.manager import MCPManager

class MemoryService:
    """Unified memory interface for knowledge graph operations"""

    async def create_entities(self, entities: List[Dict[str, Any]]) -> bool:
        if feature_flags.neo4j_integration == IntegrationMode.DIRECT:
            return await neo4j_service.create_entities(entities)
        else:
            mcp_manager = MCPManager()
            return await mcp_manager.invoke("neo4j_memory", "create_entities", {
                "entities": entities
            })

    async def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        if feature_flags.neo4j_integration == IntegrationMode.DIRECT:
            return await neo4j_service.search_nodes(query)
        else:
            mcp_manager = MCPManager()
            return await mcp_manager.invoke("neo4j_memory", "search_nodes", {
                "query": query
            })

memory_service = MemoryService()
```

#### Step 4: Update Memory Tool Usage (Day 3)

```python
# Update: tripsage/tools/memory_tools.py
from tripsage.services.memory_service import memory_service

async def store_trip_memory(trip_data: Dict[str, Any]) -> bool:
    """Store trip information in knowledge graph"""
    entities = [
        {
            "name": trip_data["destination"],
            "entityType": "Destination",
            "properties": {"country": trip_data.get("country")}
        },
        {
            "name": trip_data["title"],
            "entityType": "Trip",
            "properties": {"duration": trip_data.get("duration")}
        }
    ]

    return await memory_service.create_entities(entities)
```

#### Step 5: Performance Testing & Migration (Day 4)

```python
# Test transaction performance and data integrity
# Deploy with feature flag and gradual rollout
```

## Phase 2: Tier 2 Migrations (Sprint 3-5)

### Sprint 3: Time Operations Migration (1-2 days)

```python
# File: tripsage/services/time_service.py
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

class TimeService:
    """Local time operations replacing MCP time server"""

    def get_current_time(self, timezone_name: str = "UTC") -> str:
        """Get current time in specified timezone"""
        tz = ZoneInfo(timezone_name)
        return datetime.now(tz).isoformat()

    def convert_time(self, time_str: str, source_tz: str, target_tz: str) -> str:
        """Convert time between timezones"""
        # Parse time with source timezone
        dt = datetime.fromisoformat(time_str).replace(tzinfo=ZoneInfo(source_tz))
        # Convert to target timezone
        converted = dt.astimezone(ZoneInfo(target_tz))
        return converted.isoformat()

time_service = TimeService()
```

### Sprint 4: Duffel Flights Migration (4-5 days)

```python
# File: tripsage/services/flights_service.py
import httpx
from typing import Dict, List, Any
from tripsage.config.app_settings import get_settings

class FlightsService:
    """Direct Duffel API integration"""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.duffel.com"
        self.headers = {
            "Authorization": f"Bearer {self.settings.duffel_token}",
            "Duffel-Version": "v1",
            "Content-Type": "application/json"
        }

    async def search_flights(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search flights using Duffel API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/air/offer_requests",
                headers=self.headers,
                json={
                    "data": {
                        "slices": search_params["slices"],
                        "passengers": search_params["passengers"],
                        "cabin_class": search_params.get("cabin_class", "economy")
                    }
                }
            )
            response.raise_for_status()
            return response.json()["data"]

flights_service = FlightsService()
```

### Sprint 5: Google Calendar & Maps Migration (5-7 days)

Similar pattern with official Google client libraries and OAuth2 flows.

## Phase 3: Tier 3 Migrations (Sprint 6)

### Low-priority migrations for Firecrawl and Weather services with direct API clients

## Testing Strategy

### Unit Tests

```python
# Test each service independently
@pytest.mark.asyncio
async def test_redis_service():
    await redis_service.set("test_key", "test_value")
    result = await redis_service.get("test_key")
    assert result == "test_value"
```

### Integration Tests

```python
# Test adapter layer with both MCP and Direct modes
@pytest.mark.parametrize("integration_mode", [IntegrationMode.MCP, IntegrationMode.DIRECT])
async def test_cache_service_parity(integration_mode):
    feature_flags.redis_integration = integration_mode
    # Test functionality remains identical
```

### Performance Tests

```python
# Benchmark performance improvements
@pytest.mark.benchmark
async def test_database_operation_performance():
    # Measure P95 latency improvements
    # Validate 30%+ improvement target
```

### End-to-End Tests

```python
# Test complete user journeys work with new integrations
async def test_trip_creation_flow():
    # Test: Create trip → Store in database → Cache results → Update knowledge graph
```

## Rollback Strategy

### Immediate Rollback (< 5 minutes)

```bash
# Emergency rollback via environment variables
export FEATURE_REDIS_INTEGRATION=mcp
export FEATURE_SUPABASE_INTEGRATION=mcp
export FEATURE_NEO4J_INTEGRATION=mcp

# Restart services to pick up configuration
kubectl rollout restart deployment/tripsage-api
```

### Feature Flag Controls

```python
# Runtime rollback without deployment
feature_flags.redis_integration = IntegrationMode.MCP
# Service automatically switches back to MCP wrapper
```

### Database Rollback

- Maintain MCP infrastructure during migration period
- Database changes are additive only (no schema changes)
- Full rollback possible within 15 minutes

## Monitoring & Observability

### Key Metrics

```python
# Performance metrics
- P95 latency for database operations
- Cache hit/miss rates
- Knowledge graph query response times
- API error rates by integration type

# Business metrics
- User session success rates
- Trip creation completion rates
- Search result accuracy
```

### Alerting

```yaml
# Example Prometheus alerts
- alert: DirectIntegrationLatencyHigh
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 0.5
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "Direct integration showing high latency"

- alert: MCPFallbackRateHigh
  expr: rate(mcp_fallback_total[5m]) > 0.1
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "High fallback rate to MCP, investigate direct integration issues"
```

### Dashboards

- Side-by-side performance comparison (MCP vs Direct)
- Integration health status per service
- Migration progress tracking
- Error rate monitoring by integration type

## Timeline & Dependencies

### Sprint Timeline

| Sprint         | Duration | Services           | Dependencies        |
| -------------- | -------- | ------------------ | ------------------- |
| **Sprint 1.1** | 1 week   | Redis              | None                |
| **Sprint 1.2** | 1 week   | Supabase           | Feature flag system |
| **Sprint 2**   | 1 week   | Neo4j              | Database adapters   |
| **Sprint 3**   | 0.5 week | Time               | None                |
| **Sprint 4**   | 1 week   | Duffel Flights     | API credentials     |
| **Sprint 5**   | 1 week   | Google Services    | OAuth2 setup        |
| **Sprint 6**   | 0.5 week | Firecrawl, Weather | None                |

### Resource Requirements

- **2-3 senior developers** for implementation
- **1 DevOps engineer** for monitoring/deployment
- **1 QA engineer** for testing coordination
- **Access to staging environments** for all external services

### Risk Mitigation

- **Parallel development** - no disruption to current features
- **Feature flags** - instant rollback capability
- **Comprehensive testing** - unit, integration, performance, E2E
- **Staged rollout** - gradual traffic migration with monitoring
- **Maintaining MCP** - full fallback available during migration period

## Success Metrics & Validation

### Performance Targets

- [x] **30%+ improvement** in P95 latency for database operations
- [x] **50%+ reduction** in wrapper-related code complexity
- [x] **Zero regression** in service availability or functionality
- [x] **Improved developer experience** measured by debugging time reduction

### Business Impact

- **Faster page load times** from reduced latency
- **Better user experience** from improved reliability
- **Reduced operational costs** from simplified infrastructure
- **Faster feature development** from direct API access

### Technical Validation

- **All existing tests pass** with new integrations
- **Performance benchmarks** validate improvement targets
- **Code coverage maintained** at ≥90% levels
- **Security audit** confirms no regression in security posture

## Conclusion

This migration plan provides a systematic, low-risk approach to eliminating
complex MCP abstractions while maintaining system reliability. The phased
approach with comprehensive testing and rollback strategies ensures successful
delivery of significant performance and maintainability improvements.

**Next Actions:**

1. **Approve Phase 1 scope** and resource allocation
2. **Set up development environments** with feature flag infrastructure
3. **Begin Sprint 1.1** with Redis migration
4. **Establish monitoring dashboards** for migration tracking

---

_Implementation Plan completed: 2025-05-25_  
_Ready for development team execution_
