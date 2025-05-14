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

**Tasks:**

- [ ] **Implement Caching for the Existing WebSearchTool:**
  - Create `WebOperationsCache` class in `tripsage/utils/cache.py` extending existing Redis caching:
    - Implement content-aware TTL management (longer for stable content, shorter for news)
    - Add methods for cache key generation and metrics collection
  - Create `CachedWebSearchTool` wrapper in `tripsage/tools/web_tools.py`:
    - Wrap the SDK's `WebSearchTool` while maintaining the same interface
    - Add caching logic using the `WebOperationsCache`
  - Update agent implementations to use the wrapper:
    - Modify `TravelPlanningAgent._add_websearch_tool` method
    - Modify `DestinationResearchAgent._add_websearch_tool` method
    - Preserve existing domain configurations
- [ ] **Add Configuration Settings:**
  - Add cache TTL configuration to centralized settings
  - Configure content-type specific TTLs for different types of searches
- [ ] **Testing:**
  - Mock the OpenAI SDK's `WebSearchTool` execution
  - Test the caching wrapper tool with various search queries
  - Verify cache hits/misses and correct TTL application
  - Test domain allowlist/blocklist effectiveness
- [ ] **Documentation:**
  - Document the caching pattern and WebSearchTool configurations
  - Create examples showing how the caching improves performance

## Issue #38 - 24. feat(cache): Implement Advanced Redis-based Caching for TripSage Web Operations

**Description:**
Implement a centralized, advanced Redis-based caching system within TripSage for its web operations, as detailed in `integrations/mcp-servers/webcrawl/webcrawl_search_caching.md`. This cache will be used by TripSage's agent tools that call the OpenAI WebSearchTool (Issue #37), and tools calling the Crawl4AI MCP, Firecrawl, Playwright MCP, and Stagehand MCP (Issues #5, #12) to improve performance and reduce API calls.

**Relevant Original Documentation:**

- `integrations/mcp-servers/webcrawl/webcrawl_search_caching.md` (Detailed caching strategy)

**Relevant Links (for TripSage Implementation):**

- (Redis client library for Python, e.g., `redis-py`)
- Pydantic V2 (for any data models used in caching): [https://docs.pydantic.dev/latest/](https://docs.pydantic.dev/latest/)

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

**Tasks:**

- [ ] **Implement `WebOperationsCache` Class in TripSage:**
  - Develop the caching class within TripSage with methods for:
    - `_generate_cache_key` - considers tool name, query params, domains, etc.
    - `_get_ttl_for_content_type` - determines expiration based on content type
    - `get` - retrieves cached web results with type awareness
    - `set` - stores web results with appropriate TTL
    - `invalidate` - clears cached data by pattern
    - `get_stats` - retrieves metrics on cache performance
  - Ensure integration with existing Redis infrastructure
- [ ] **Implement Content-Aware TTL Logic:**
  - Define and implement rules for determining TTL based on content semantics:
    - News/current events: Short TTL (1-4 hours)
    - Destination information: Longer TTL (1-7 days)
    - Travel guidelines/regulations: Medium TTL (12-24 hours)
    - Historical information: Extended TTL (7-30 days)
  - Implement content classification logic for automatic TTL assignment
- [ ] **Create Configuration Structure:**
  - Add TTL configuration to centralized settings
  - Allow override of default TTL values without code changes
  - Implement environment variable support for Redis connection parameters
- [ ] **Implement Usage Metrics:**
  - Track and collect cache hit/miss statistics
  - Measure latency differences between cached and uncached requests
  - Create monitoring endpoints for cache performance analysis
- [ ] **Testing:**
  - Unit test the `WebOperationsCache` class
  - Test cache key generation with various web query parameters
  - Verify correct TTL application for different content types
  - Test integration with WebSearchTool and other web operation tools
- [ ] **Documentation:**
  - Document caching strategy with examples and configuration options
  - Create usage examples for tool integration
  - Document performance benefits and expected impact

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
