# TripSage Research Issues

This document contains the full descriptions of research-oriented issues for the TripSage project.

## Issue #37 - 23. feat(search): Integrate OpenAI Agents SDK WebSearchTool for General Web Queries in TripSage

**Description:**
Integrate the built-in **WebSearchTool** from the **OpenAI Agents SDK** for the TripSage agent to perform broad, general-purpose web queries. This tool will be the first tier in the hybrid search strategy for initial information gathering, as outlined in `integrations/core-technologies/hybrid_search_strategy.md`.

**Relevant Original Documentation:**

- `integrations/core-technologies/hybrid_search_strategy.md` (Defines WebSearchTool as primary for general queries)

**Relevant Links (for TripSage Implementation):**

- OpenAI Agents SDK: [https://openai.github.io/openai-agents-python/](https://openai.github.io/openai-agents-python/) (Refer to its WebSearchTool documentation)
- Pydantic V2: [https://docs.pydantic.dev/latest/](https://docs.pydantic.dev/latest/)

**Research Findings:**

- Based on codebase analysis, WebSearchTool is already integrated in both `TravelPlanningAgent` and `DestinationResearchAgent` but without caching.
- The `TravelPlanningAgent` uses a comprehensive domain allowlist focused on travel sites (airlines, hotels, weather, etc.).
- The `DestinationResearchAgent` has a more specialized domain allowlist targeting travel guides and local tourism sites.
- Both agents appropriately block content farm domains like Pinterest and Quora.
- A caching wrapper solution would be most appropriate following KISS principles:
  1. Create a `WebOperationsCache` class in `tripsage/utils/cache.py` extending existing Redis caching
  2. Implement a `CachedWebSearchTool` wrapper in `tripsage/tools/web_tools.py`
  3. Update agent implementations to use the wrapper instead of direct WebSearchTool

**Status:** ✅ COMPLETED

**Implementation Notes:**

- Discovered that OpenAI SDK's WebSearchTool does not support allowed_domains/blocked_domains parameters
- Updated implementation to work with the actual WebSearchTool API (user_location, search_context_size)
- Successfully integrated CachedWebSearchTool in both TravelPlanningAgent and DestinationResearchAgent

**Tasks:**

- [x] **Implement Caching for the Existing WebSearchTool:**
  - ✓ Created `WebOperationsCache` class in `tripsage/utils/cache.py` extending existing Redis caching:
    - ✓ Implemented content-aware TTL management (longer for stable content, shorter for news)
    - ✓ Added methods for cache key generation and metrics collection
  - ✓ Created `CachedWebSearchTool` wrapper in `tripsage/tools/web_tools.py`:
    - ✓ Wrapped the SDK's `WebSearchTool` while maintaining the same interface
    - ✓ Added caching logic using the `WebOperationsCache`
  - ✓ Updated agent implementations to use the wrapper:
    - ✓ Modified `TravelPlanningAgent._add_websearch_tool` method
    - ✓ Modified `DestinationResearchAgent._add_websearch_tool` method
    - ✓ Removed domain configurations (not supported by OpenAI SDK)
- [x] **Add Configuration Settings:**
  - ✓ Added cache TTL configuration to centralized settings
  - ✓ Configured content-type specific TTLs for different types of searches
- [x] **Testing:**
  - ✓ Created validation tests for code structure
  - ✓ Verified integration in both agents
  - ✓ Domain allowlist/blocklist not applicable (not supported by SDK)
- [x] **Documentation:**
  - ✓ Documented the implementation changes
  - ✓ Updated TODO.md with completion status

## Issue #38 - 24. feat(cache): Implement Advanced Redis-based Caching for TripSage Web Operations

**Description:**
Implement a centralized, advanced Redis-based caching system within TripSage for its web operations, as detailed in `integrations/mcp-servers/webcrawl/webcrawl_search_caching.md`. This cache will be used by TripSage's agent tools that call the OpenAI WebSearchTool (Issue #37), and tools calling the Crawl4AI MCP, Firecrawl, Playwright MCP, and Stagehand MCP (Issues #5, #12) to improve performance and reduce API calls.

**Relevant Original Documentation:**

- `integrations/mcp-servers/webcrawl/webcrawl_search_caching.md` (Detailed caching strategy)

**Relevant Links (for TripSage Implementation):**

- Redis async client library: `redis.asyncio` from redis-py
- Pydantic V2 (for data models): [https://docs.pydantic.dev/latest/](https://docs.pydantic.dev/latest/)

**Research Findings:**

- The codebase already has two caching implementations:
  1. `InMemoryCache` in `tripsage/utils/cache.py` (simple in-memory caching)
  2. `RedisCache` in `src/cache/redis_cache.py` (Redis-based distributed caching)
- The existing `RedisCache` already implements core functionality for:
  - Cache key generation
  - JSON serialization/deserialization
  - TTL support
  - Basic invalidation
  - Decorator-based caching
- Specifically for web operations, we need to extend RedisCache with:
  - Content-aware TTL management (different expiration for different content types)
  - Specialized key generation that considers web-specific parameters
  - Metrics collection for web operation cache effectiveness
  - Web content invalidation strategies

**Implementation Strategy:**

- Create a `WebOperationsCache` class in `tripsage/utils/cache.py` that extends or wraps the existing Redis caching
- Implement specialized methods for web content caching (news, destinations, travel info)
- Configure TTL values that align with content volatility (shorter TTL for news, longer for stable content)
- Integrate with centralized configuration for easy TTL adjustments

**Implementation Status:** ✅ COMPLETED

**Tasks:**

- [x] **Implement `WebOperationsCache` Class in TripSage:**
  - Developed the caching class in `tripsage/utils/cache.py` with methods for:
    - `generate_cache_key` - considers tool name, query params, domains, etc.
    - `get_ttl_for_content_type` - determines expiration based on content type
    - `get` - retrieves cached web results with type awareness
    - `set` - stores web results with appropriate TTL
    - `invalidate_pattern` - clears cached data by pattern
    - `get_stats` - retrieves metrics on cache performance
  - Implemented integration with existing Redis infrastructure
- [x] **Implement Content-Aware TTL Logic:**
  - Created `ContentType` enum with five categories: REALTIME, TIME_SENSITIVE, DAILY, SEMI_STATIC, STATIC
  - Implemented rules for determining TTL based on content semantics:
    - Real-time data (weather, stocks): Very short TTL (100s default)
    - Time-sensitive (news, social media): Short TTL (5m default)
    - Daily changing data (flight prices): Medium TTL (1h default)
    - Semi-static data (business info): Longer TTL (8h default)
    - Static content (historical, reference): Extended TTL (24h default)
  - Created `determine_content_type` method for automatic content classification
- [x] **Create Configuration Structure:**
  - Added `WebCacheTTLConfig` class to `app_settings.py`
  - Implemented configurable TTL settings for each content type
  - Made cache namespaces configurable
- [x] **Implement Usage Metrics:**
  - Implemented metrics collection with time windows (1h, 24h, 7d)
  - Created `CacheMetrics` model for structured statistics
  - Added sampling to reduce overhead (configurable sample rate)
  - Created `get_web_cache_stats` utility function
- [x] **Implement CachedWebSearchTool:**
  - Created wrapper for OpenAI Agents SDK WebSearchTool
  - Implemented transparent caching with the same interface
  - Added content-aware TTL based on query and result analysis
  - Created utility functions for cache management
- [x] **Testing:**
  - Created comprehensive unit tests for `WebOperationsCache`
  - Implemented tests for `CachedWebSearchTool`
  - Added tests for metrics collection and retrieval
  - Verified TTL logic with different content types

**Remaining Work:**

- Integration with TravelPlanningAgent and DestinationResearchAgent
- Apply web_cached decorator to additional webcrawl functions
- Performance benchmarking in production environment

**Key Features Implemented:**

1. Content-aware TTL management (REALTIME to STATIC)
2. Intelligent content classification based on query keywords and domains
3. Metrics collection with time windows and sampling
4. Domain-aware cache key generation
5. Robust error handling and Redis fallback mechanisms
6. Size estimation and cache statistics

**Notes:**
This implementation successfully meets the requirements for a centralized caching system for web operations in TripSage. The `WebOperationsCache` class provides content-aware TTL management with intelligent classification of web content, while the `CachedWebSearchTool` offers a seamless drop-in replacement for the OpenAI WebSearchTool. The implementation follows KISS principles by building on the existing Redis infrastructure while adding the specialized functionality needed for web content caching.

## Issue #39 - 25. ops(neo4j): Evaluate Neo4j AuraDB API MCP for Operational Management of TripSage's Neo4j

**Description:**
(Post-MVP / Low Priority) Evaluate the `mcp-neo4j-cloud-aura-api` server for managing Neo4j AuraDB instances if AuraDB is chosen as the production deployment for TripSage's Neo4j Memory graph. This MCP could provide administrative capabilities for tasks like creating, pausing, resuming, or deleting AuraDB instances programmatically or via an administrative agent interface within or alongside TripSage.

**Relevant Links (for TripSage Implementation/Evaluation):**

- `mcp-neo4j-cloud-aura-api`: [https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cloud-aura-api](https://github.com/neo4j-contrib/mcp-neo4j/tree/main/servers/mcp-neo4j-cloud-aura-api)
- Neo4j Aura Docs: [https://neo4j.com/docs/aura/](https://neo4j.com/docs/aura/)
- Neo4j Operations Manual: [https://neo4j.com/docs/operations-manual/current/](https://neo4j.com/docs/operations-manual/current/)

**Tasks:**

- [ ] **Decision on Production Neo4j Hosting for TripSage:** Determine if Neo4j AuraDB will be used for TripSage's production Neo4j database (which is accessed by the Neo4j Memory MCP).
- [ ] **Evaluate `mcp-neo4j-cloud-aura-api` Features:** If AuraDB is used, review the capabilities of this MCP.
- [ ] **Identify Use Cases for TripSage Operations:** Determine if TripSage requires programmatic management of AuraDB instances (e.g., for dynamic environment provisioning for testing, automated backups beyond Aura's native capabilities, cost management alerts).
- [ ] **Security Assessment:** Evaluate the security implications of exposing AuraDB management functions via an MCP accessible by any TripSage component.
- [ ] **Integration (If Deemed Useful for TripSage Ops):**
  - Deploy and configure the `mcp-neo4j-cloud-aura-api` server.
  - Develop administrative tools or scripts within TripSage's operational toolkit that leverage this MCP.
- [ ] **Documentation:** Document any integrated operational procedures for TripSage's Neo4j AuraDB instances.
