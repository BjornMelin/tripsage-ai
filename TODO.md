# TripSage Refactoring TODO List

This TODO list outlines refactoring opportunities to simplify the TripSage AI codebase following KISS/DRY/YAGNI/SIMPLE principles. The goal is to eliminate redundancy, improve maintainability, and ensure adherence to project standards.

## Coding Standards Reference

- **Python 3.12** with PEP-8 (88-char lines max)
- Type hints are mandatory
- Run `ruff check --select I --fix .` for import sorting
- Run `ruff check . --fix` and `ruff format .` on touched files
- Files should be ≤350 LoC (hard cap: 500)
- Test coverage target: ≥90%

## High Priority

- [x] **Error Handling Decorator Enhancement**

  - **Target:** `/src/utils/decorators.py`
  - **Goal:** Support both sync and async functions in `with_error_handling`
  - **Tasks:**
    - ✓ Add synchronous function support
    - ✓ Improve type hints using TypeVar
    - ✓ Add comprehensive docstrings and examples
    - ✓ Ensure proper error message formatting
  - **PR:** Completed in #85

- [x] **Apply Error Handling Decorator to Flight Search Tools**

  - **Target:** `/src/agents/flight_search.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - ✓ Refactor `search_flights` to use the decorator
    - ✓ Refactor `_add_price_history` to use the decorator
    - ✓ Refactor `_get_price_history` to use the decorator
    - ✓ Refactor `search_flexible_dates` to use the decorator

- [x] **Apply Error Handling Decorator to Accommodations Tools**

  - **Target:** `/src/agents/accommodations.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - ✓ Refactor `search_accommodations` to use the decorator
    - ✓ Refactor `get_accommodation_details` to use the decorator
    - ✓ Create standalone tests to verify error handling

- [x] **Standardize MCP Client Pattern**

  - **Target:** `/src/mcp/base_mcp_client.py` and implementations
  - **Goal:** Create consistent patterns for all MCP clients
  - **Tasks:**
    - ✓ Define standard client factory interfaces
    - ✓ Centralize configuration validation logic
    - ✓ Implement consistent initialization patterns
    - ✓ Standardize error handling approach
  - **Follow-up Tasks:**
    - ✓ Fix circular import between base_mcp_client.py and memory_client.py
    - ✓ Apply factory pattern to all other MCP clients (weather, calendar, etc.)
    - ✓ Improve unit test infrastructure for MCP client testing

- [x] **Consolidate Dual Storage Pattern**

  - **Target:** `/src/utils/dual_storage.py`
  - **Goal:** Extract common persistence logic to avoid duplication
  - **Tasks:**
    - ✓ Create a `DualStorageService` base class
    - ✓ Implement standard persistence operations
    - ✓ Refactor existing services to use the base class
    - ✓ Add proper interface for both Supabase and Memory backends
    - ✓ Create comprehensive test suite with mocked dependencies
    - ✓ Implement isolated tests for generic class behavior
  - **PR:** Completed in #91
  - **Added:** Created comprehensive documentation in dual_storage_refactoring.md

- [ ] **Complete Codebase Restructuring (Issue #31)**

  - **Target:** Throughout codebase
  - **Goal:** Consolidate application logic into the `tripsage/` directory
  - **Tasks:**
    - [x] Update tool imports:
      - ✓ Update `tripsage/tools/time_tools.py` to use `from agents import function_tool`
      - ✓ Update `tripsage/tools/memory_tools.py` to use `from agents import function_tool`
      - ✓ Update `tripsage/tools/webcrawl_tools.py` to use `from agents import function_tool`
    - [x] Migrate remaining agent files:
      - ✓ Migrate `src/agents/budget_agent.py` → `tripsage/agents/budget.py`
      - ✓ Migrate `src/agents/itinerary_agent.py` → `tripsage/agents/itinerary.py`
    - [x] Migrate remaining tool files:
      - ✓ Migrate `src/agents/planning_tools.py` → `tripsage/tools/planning_tools.py`
    - [x] Migrate additional agent files:
      - ✓ Migrate `src/agents/travel_insights.py` → `tripsage/agents/travel_insights.py`
      - ✓ Migrate `src/agents/flight_booking.py` → `tripsage/tools/flight_booking.py`
      - ✓ Migrate `src/agents/flight_search.py` → `tripsage/tools/flight_search.py`
    - [x] Migrate browser tools:
      - ✓ Migrate `src/agents/tools/browser/` → `tripsage/tools/browser/`
      - ✓ Update imports in `tripsage/tools/browser/tools.py` to use `from agents import function_tool`
      - ✓ Update imports in `tripsage/tools/browser_tools.py` to use `from agents import function_tool`
    - [ ] Update remaining imports:
      - Update all `from src.*` imports to `from tripsage.*`
      - Ensure consistent use of the `agents` module instead of `openai_agents_sdk`
    - [ ] Update tests to match new structure:
      - Update imports in test files to use tripsage module
      - Create new test files for migrated tools and agents
      - Ensure all tests pass with new structure
    - [ ] Clean up duplicated files:
      - Remove unnecessary files from src/ after migration
      - Ensure no duplicate functionality exists
    - [ ] Documentation updates:
      - Update README.md to reflect new structure
      - Add directory structure documentation
      - Create migration guide for developers

- [ ] **Integrate External MCP Servers**

  - **Target:** MCP server architecture and implementation
  - **Goal:** Adopt a hybrid approach favoring external MCPs when possible
  - **Strategy:**
    - Prioritize existing external MCPs when available
    - Only build custom MCPs for core business logic, direct database integration, or when privacy/security requirements can't be met externally
  - **Tasks:**

    - [ ] Supabase MCP Integration: (Short-Term Phase)
      - **Success Metrics:**
        - 99.9% uptime for database operations
        - <100ms average query response time
        - 100% schema validation coverage
        - 95%+ test coverage with integration tests
      - Set up Supabase MCP server configuration
      - Create wrapper functions in `tripsage/tools/supabase_tools.py`
      - Implement database operation tools with proper validation
      - Add comprehensive tests for Supabase tool integration
    - [ ] Neo4j Memory MCP Integration: (Immediate Phase)
      - **Success Metrics:**
        - 95%+ successful graph operations
        - <200ms average query response time
        - Complete coverage of entity/relationship models
        - 90%+ test coverage for graph operations
      - Configure Neo4j Memory MCP server
      - Create memory graph tools in `tripsage/tools/memory_tools.py`
      - Implement entity/relationship management functions
      - Add tests for knowledge graph operations
    - [ ] Duffel Flights MCP Integration: (Short-Term Phase)
      - **Success Metrics:**
        - 95%+ successful flight searches
        - <3 second average response time
        - Complete coverage of major global airlines
        - 90%+ test coverage with realistic flight scenarios
      - Set up Duffel Flights MCP configuration
      - Create flight search tools in `tripsage/tools/flight_tools.py`
      - Implement offer and search functionality
      - Add tests for flight search operations
    - [ ] Airbnb MCP Integration: (Short-Term Phase)
      - **Success Metrics:**
        - 90%+ successful accommodation searches
        - <5 second average response time
        - Accurate pricing and availability data
        - 90%+ test coverage for accommodation operations
      - Configure Airbnb MCP server
      - Create accommodation tools in `tripsage/tools/accommodation_tools.py`
      - Implement listing search and details functionality
      - Add tests for accommodation search operations
    - [ ] Playwright MCP Integration: (Immediate Phase)
      - **Target:** Browser automation for complex travel workflows
      - **Goal:** Provide fallback mechanism for sites that block scrapers
      - **Success Metrics:**
        - 95%+ successful completion rate for authenticated workflows
        - <5 second average response time for cached operations
        - 90%+ test coverage with integration tests
        - Successful fallback handling for at least 5 major travel sites
      - **Tasks:**
        - Configure Playwright MCP server with Python integration
        - Create browser automation toolkit in `tripsage/tools/browser/tools.py`
        - Implement session persistence for authenticated workflows
        - Develop travel-specific browser operations (booking verification, check-ins)
        - Create escalation logic from crawler to browser automation
        - Add anti-detection capabilities for travel websites
        - Implement comprehensive testing with mock travel websites
    - [ ] Hybrid Web Crawling Integration: (Immediate-to-Short-Term Phase)
      - **Target:** Implement domain-optimized web crawling strategy
      - **Goal:** Maximize extraction performance and reliability for travel sites
      - **Success Metrics:**
        - 90%+ extraction success rate across all targeted travel sites
        - <4 seconds average response time for optimized domains
        - 95% accuracy in content extraction compared to manual collection
        - <15% fallback rate to browser automation
      - **Tasks:**
        - [ ] Crawl4AI MCP Integration:
          - Configure Crawl4AI MCP server with RAG capabilities
          - Implement in `tripsage/tools/webcrawl/crawl4ai_client.py`
          - Optimize for informational sites (TripAdvisor, WikiTravel, etc.)
          - Create comprehensive tests for information extraction
        - [ ] Firecrawl MCP Integration:
          - Configure official Firecrawl MCP server from MendableAI
          - Implement in `tripsage/tools/webcrawl/firecrawl_client.py`
          - Optimize for booking sites (Airbnb, Booking.com, etc.)
          - Create comprehensive tests for structured data extraction
        - [ ] Source Selection Logic:
          - Implement domain-based routing in `tripsage/tools/webcrawl/source_selector.py`
          - Create unified abstraction layer in `tripsage/tools/webcrawl_tools.py`
          - Develop empirical performance testing framework
          - Document domain-specific optimization strategy
        - [ ] Result Normalization:
          - Create consistent output schema in `tripsage/tools/webcrawl/models.py`
          - Implement normalization logic in `tripsage/tools/webcrawl/result_normalizer.py`
          - Ensure unified interface regardless of underlying crawler
        - [ ] Production Scenario Testing Strategy:
          - Create test suite with real-world travel planning scenarios
            - Develop 10+ realistic multi-site test cases covering booking flows and research patterns
            - Implement automated performance comparison between single-crawler and hybrid approach
            - Create a/b testing framework to empirically verify domain routing effectiveness
          - Implement monitoring for crawler selection decisions
            - Add telemetry for source selection logic
            - Create dashboard for crawler performance by domain
            - Set up alerting for fallback escalation patterns
          - Establish quantitative success metrics
            - 95%+ successful extractions across tracked domains
            - <3 second average response time for cached results
            - <8 second average for uncached results
            - <5% fallback rate to Playwright for optimized domains
    - [ ] Google Maps MCP Integration: (Immediate Phase)
      - **Success Metrics:**
        - 99% geocoding success rate
        - <300ms average response time
        - Complete coverage of required location services
        - 90%+ test coverage for all implemented functions
      - Set up Google Maps MCP configuration
      - Create maps and location tools in `tripsage/tools/googlemaps_tools.py`
      - Implement geocoding, directions, and place search functionality
      - Add tests for location-based operations
    - [ ] Time MCP Integration: (Short-Term Phase)
      - **Success Metrics:**
        - 100% accuracy for timezone conversions
        - <100ms average response time
        - Support for all global timezones
        - 95%+ test coverage
      - Configure Time MCP server
      - Create time tools in `tripsage/tools/time_tools.py`
      - Implement timezone conversion and current time functionality
      - Add tests for time-related operations
    - [ ] Weather MCP Integration: (Immediate Phase)
      - **Success Metrics:**
        - 95%+ availability for global weather data
        - <1 second average response time
        - Accurate forecasting for 7+ day window
        - 90%+ test coverage for API functions
      - Configure Weather MCP server
      - Create weather tools in `tripsage/tools/weather_tools.py`
      - Implement forecast and current conditions functionality
      - Add tests for weather-related operations
    - [ ] Google Calendar MCP Integration: (Short-Term Phase)
      - **Success Metrics:**
        - 98%+ successful event creation/modification
        - <1 second average operation time
        - Complete support for all required calendar operations
        - 95%+ test coverage
      - Configure Google Calendar MCP server
      - Create calendar tools in `tripsage/tools/calendar_tools.py`
      - Implement event creation and scheduling functionality
      - Add tests for calendar-related operations
    - [ ] Redis MCP Integration: (Short-Term Phase)
      - **Success Metrics:**
        - 99.9% cache operation reliability
        - <50ms average cache operation time
        - 90%+ cache hit rate for common operations
        - Proper TTL management across content types
      - Configure Redis MCP server
      - Create caching tools in `tripsage/tools/cache_tools.py`
      - Implement distributed caching functionality
      - Add tests for cache-related operations
    - [ ] WebSearchTool Integration with Caching (Issue #37):

      - **Target:** Implement caching for OpenAI Agents SDK WebSearchTool
      - **Goal:** Optimize performance and reduce API usage for web searches
      - **Status:** Research completed - integration plan ready for implementation
      - **Research Findings:**
        - WebSearchTool already implemented in TravelPlanningAgent and DestinationResearchAgent
        - Domain configurations differ appropriately between agents
        - Redis caching infrastructure exists but needs web-specific extensions
      - **Tasks:**
        - Create WebOperationsCache class in `tripsage/utils/cache.py`:
          - Extend existing Redis caching with content-type awareness
          - Implement TTL management based on content volatility (shorter for news, longer for destinations)
          - Add metrics collection for cache performance analysis
        - Create CachedWebSearchTool wrapper in `tripsage/tools/web_tools.py`:
          - Wrap WebSearchTool with identical interface for transparent integration
          - Implement cache checking before API calls
          - Store results with appropriate TTL based on content type
        - Update agent implementations:
          - Update TravelPlanningAgent and DestinationResearchAgent to use wrapper
          - Preserve existing domain allowlists/blocklists
        - Add configuration settings:
          - Configure TTL settings in centralized configuration
          - Enable runtime TTL adjustments without code changes
        - Add comprehensive tests:
          - Create mocks for WebSearchTool testing
          - Verify cache behavior with different content types

    - [x] Implement WebOperationsCache for Web Operations (Issue #38):
      - **Target:** Advanced caching system for TripSage web operations
      - **Goal:** Create a centralized, content-aware caching system for all web operation tools
      - **Status:** Implemented core functionality, requires integration testing
      - **Tasks:**
        - [x] Implement WebOperationsCache Class in `tripsage/utils/cache.py`:
          - [x] Create `ContentType` enum with categories (REALTIME, TIME_SENSITIVE, DAILY, SEMI_STATIC, STATIC)
          - [x] Implement Redis integration using `redis.asyncio` for async compatibility
          - [x] Define configurable TTL settings for each content type
          - [x] Implement core cache methods (get, set, delete, invalidate_pattern)
          - [x] Create content-aware TTL logic that analyzes query and result patterns
          - [x] Implement `generate_cache_key` method for deterministic key generation
          - [x] Create singleton instance for application-wide use
        - [x] Implement Metrics Collection:
          - [x] Create metrics storage structure in Redis
          - [x] Add hit/miss counters with time windows (1h, 24h, 7d)
          - [x] Implement performance measurement for cache operations
          - [x] Create `get_stats` method for metrics retrieval
          - [x] Implement sampling for detailed metrics to reduce overhead
        - [x] Implement CachedWebSearchTool in `tripsage/tools/web_tools.py`:
          - [x] Create wrapper around OpenAI Agents SDK WebSearchTool
          - [x] Maintain identical interface for seamless integration
          - [x] Add caching with domain-aware cache keys
          - [x] Implement content type detection from search queries and results
        - [x] Create Web Caching Decorator:
          - [x] Implement `web_cached` decorator for other web operation functions
          - [x] Support async functions
          - [x] Add flexible content type detection
        - [x] Update Configuration Settings:
          - [x] Add TTL configuration to `app_settings.py`
          - [x] Create defaults for each content type (REALTIME: 100s, TIME_SENSITIVE: 5m, etc.)
          - [x] Make cache namespaces configurable
        - [x] Add Comprehensive Tests:
          - [x] Create unit tests for WebOperationsCache
          - [x] Add tests for CachedWebSearchTool
          - [x] Test metrics collection and retrieval
          - [x] Verify TTL logic with different content types
        - [ ] Update Agent Implementations: (Partially Complete)
          - [ ] Replace WebSearchTool with CachedWebSearchTool in TravelPlanningAgent
            - Implementation complete, pending integration testing
          - [ ] Replace WebSearchTool with CachedWebSearchTool in DestinationResearchAgent
            - Implementation complete, pending integration testing
          - [ ] Apply web_cached decorator to appropriate web operation functions
            - Add to existing webcrawl operations in both agents
            - Add performance monitoring hooks for cache hit rate analysis
      - [x] Implementation Timeline: (Completed)
        - [x] Phase 1: Core WebOperationsCache implementation
        - [x] Phase 2: Metrics and tool integration
        - [x] Phase 3: Testing and implementation
        - [ ] Phase 4: Agent integration (Pending)
      - [x] Additional Considerations: (Implemented)
        - [x] Performance impact: Implemented sampling to minimize Redis overhead
        - [x] Fallback mechanism: Added robust error handling for Redis operations
        - [x] Cache size management: Implemented cache size estimation
        - [x] Analytics: Created WebCacheStats with hit/miss ratio tracking
      - **Note:** Need to review and integrate with TravelPlanningAgent and DestinationResearchAgent

- [ ] **MCP Implementation Roadmap**

  - **Target:** Phased MCP integration
  - **Goal:** Implement MCP integration in structured phases
  - **Tasks:**
    - [ ] Immediate Actions (Next 2 Weeks):
      - [x] Set up MCP configuration management system (foundational for all MCP integrations)
        - ✓ Created hierarchical Pydantic model structure for all MCP configurations
        - ✓ Implemented environment variable loading with nested delimiter support
        - ✓ Created dedicated configuration classes for each MCP type
        - ✓ Implemented singleton pattern for global settings access
        - ✓ Added comprehensive validation with Pydantic v2
        - ✓ Created example usage and client initialization patterns
        - ✓ Implemented in `tripsage/config/mcp_settings.py`
      - Integrate Playwright MCP (see Playwright MCP Integration)
      - Integrate Google Maps MCP (see Google Maps MCP Integration)
      - Integrate Weather MCP for essential trip planning data (see Weather MCP Integration)
      - Begin hybrid web crawling implementation (see Crawl4AI & Firecrawl Integration)
      - Implement WebSearchTool caching with WebOperationsCache (Issue #37, partially completed)
      - Develop proof-of-concept for unified abstraction layer
      - Implement error handling and monitoring infrastructure
    - [ ] Short-Term Actions (Weeks 3-6):
      - Complete Neo4j Memory MCP Integration (see Neo4j Memory MCP Integration)
      - Complete hybrid Crawl4AI/Firecrawl implementation with domain routing
      - Integrate Time MCP (see Time MCP Integration)
      - Integrate Google Calendar MCP (see Google Calendar MCP Integration)
      - Develop and test the Unified Travel Search Wrapper
      - Implement Redis MCP for standardized response caching (see Redis MCP Integration)
      - Integrate Supabase MCP (see Supabase MCP Integration)
      - Integrate Duffel Flights MCP and Airbnb MCP (see respective integration sections)
      - Create domain-specific performance testing framework
      - Complete comprehensive error handling for all integrated MCPs
    - [ ] Medium-Term Actions (Weeks 7-12):
      - Develop Trip Planning Coordinator and Content Aggregator wrappers
      - Implement OpenTelemetry-based monitoring for all MCP interactions
      - Complete thorough integration testing across all MCPs
      - Optimize performance through Redis MCP caching and parallel execution
      - Complete production scenario testing for all integrations

- [ ] **MCP Client Cleanup**

  - **Target:** `/src/mcp/` directory
  - **Goal:** Replace redundant MCP client implementations with external MCP servers
  - **Strategy:** Follow hybrid approach - prioritize external MCPs, build custom only when necessary
  - **Tasks:**
    - [ ] Implement unified abstraction layer for all MCP interactions:
      - Create consistent interface patterns for all MCP clients
      - Implement standardized error handling across all MCP calls
      - Develop dependency injection pattern for MCP clients
    - [ ] Audit `src/mcp/` to identify functionality covered by external MCPs:
      - Map current clients to Supabase, Neo4j Memory, Duffel Flights, Airbnb MCPs
      - Map webcrawl functionality to hybrid Crawl4AI/Firecrawl implementation with domain-based routing
      - Map browser automation needs to Playwright MCP
      - Map Google Maps, Time, Weather, Google Calendar, and Redis MCPs
      - Document any functionality requiring custom implementations
      - Map specific correspondences:
        - `src/mcp/weather/` → Weather MCP
        - `src/mcp/calendar/` → Google Calendar MCP
        - `src/mcp/time/` → Time MCP
        - `src/mcp/webcrawl/` → Firecrawl MCP
        - `src/cache/redis_cache.py` → Redis MCP
    - [ ] Implement Redis MCP for standardized caching:
      - Configure Redis MCP server with appropriate connection parameters
      - Create cache key generation that respects parameters
      - Implement TTL management based on data type (shorter for prices, longer for destination info)
      - Add cache invalidation patterns based on travel dates and data changes
      - Develop comprehensive monitoring for cache hit/miss rates
    - [ ] Create client wrappers for external MCP servers:
      - Implement thin client interfaces for consistent access patterns
      - Ensure proper error handling and request validation
    - [ ] Implement monitoring and observability:
      - Add OpenTelemetry instrumentation for MCP interactions
      - Create performance metrics for MCP operations
      - Implement structured logging for all MCP interactions
    - [ ] Remove redundant implementations after external MCP integration
    - [ ] Ensure proper use of Pydantic V2 patterns in remaining MCP clients
    - [ ] Create proper factory patterns for all MCP clients
    - [ ] Standardize configuration across all clients
    - [ ] Migrate essential clients to tripsage/clients/ directory
    - [ ] Implement comprehensive test suite for each client

- [ ] **Ensure Proper Pydantic V2 Implementation**

  - **Target:** Throughout codebase
  - **Goal:** Ensure all models use Pydantic V2 patterns
  - **Tasks:**
    - [ ] Audit and update method usage:
      - Replace `dict()` with `model_dump()` (found in 12+ files)
      - Replace `json()` with `model_dump_json()` (found in 13+ files)
      - Replace `parse_obj()` with `model_validate()` (found in 5+ files)
      - Replace `parse_raw()` with `model_validate_json()` (found in 3+ files)
      - Replace `schema()` with `model_json_schema()` (found in 2+ files)
    - [ ] Audit and update validation patterns:
      - Replace `validator` with `field_validator` and add `@classmethod`
      - Update validator modes to use `"before"` and `"after"` parameters
      - Update any root validator usage with `model_validator`
    - [ ] Update type validation:
      - Update Union type usage for proper validation
      - Replace `typing.Optional` with field default values
      - Replace `ConstrainedInt` with `Annotated[int, Field(ge=0)]`
    - [ ] Implement advanced features:
      - Use `field_serializer` for custom serialization logic
      - Use `model_serializer` for whole-model serialization
      - Implement `TypeAdapter` for non-BaseModel validation
      - Use `discriminated_union` for polymorphic models
    - [ ] Update documentation with Pydantic V2 examples
    - [ ] Add type checking with mypy and Pydantic plugin

- [ ] **Ensure Proper OpenAI Agents SDK Implementation**

  - **Target:** Agent implementations
  - **Goal:** Ensure agents use the latest SDK patterns
  - **Tasks:**
    - [ ] Standardize agent class structure:
      - Consistent initialization with settings-based defaults
      - Proper tool registration patterns
      - Standard error handling implementation
    - [ ] Improve tool implementation:
      - Use proper parameter models with strict validation
      - Implement consistent error reporting
      - Add comprehensive docstrings with examples
    - [ ] Ensure proper handoff configuration:
      - Standardize handoff methods across agents
      - Implement context passing between agents
      - Create proper initialization in handoff list
    - [ ] Implement guardrails:
      - Add input validation on all tools
      - Implement standardized safety checks
      - Create comprehensive logging for tool usage
    - [ ] Improve conversation history management:
      - Implement proper conversation storage
      - Create efficient context retrieval methods
      - Ensure consistent memory integration

- [ ] **Implement Neo4j Knowledge Graph Integration (using Neo4j Memory MCP)**
  - **Target:** Throughout codebase
  - **Goal:** Standardize Neo4j integration using Neo4j Memory MCP server
  - **Tasks:**
    - [ ] Set up Neo4j Memory MCP server configuration
    - [ ] Define standard entity models compatible with MCP schema
    - [ ] Create reusable CRUD operations using MCP tools
    - [ ] Implement graph query patterns via MCP integration
    - [ ] Define relationship type constants in knowledge graph schema
    - [ ] Create standard validation for MCP-based graph operations
    - [ ] Implement caching for Neo4j Memory MCP operations
    - [ ] Add comprehensive test suite for Neo4j MCP integration

## Medium Priority

- [x] **Fix MCP Import Circularity**

  - **Target:** `/src/mcp/base_mcp_client.py` and `/src/utils/decorators.py`
  - **Goal:** Resolve circular imports between modules
  - **Tasks:**
    - ✓ Refactor decorators.py to remove dependency on memory_client
    - ✓ Extract error handling logic to prevent circular dependencies
    - ✓ Implement proper module initialization order
    - ✓ Add clear documentation about module dependencies
  - **PR:** Completed

- [x] **Improve MCP Client Testing**

  - **Target:** `/tests/mcp/` directory
  - **Goal:** Create robust testing infrastructure for MCP clients
  - **Tasks:**
    - ✓ Create reusable mocks for settings and cache dependencies
    - ✓ Implement test fixtures for standard MCP client testing
    - ✓ Create factories for generating test data
    - ✓ Achieve 90%+ test coverage for all MCP client code
  - **PR:** Completed
  - **Added:** Created comprehensive documentation in isolated_mcp_testing.md

- [x] **Simplify Tool Registration Logic**

  - **Target:** `/src/agents/base_agent.py`
  - **Goal:** Reduce verbosity in tool registration
  - **Tasks:**
    - ✓ Implement a generic `register_tool_group` method
    - ✓ Create a more declarative approach to tool registration
    - ✓ Add automatic tool discovery in specified modules

- [x] **Centralize Parameter Validation**

  - **Target:** MCP client implementations
  - **Goal:** Use Pydantic more consistently for validation
  - **Tasks:**
    - ✓ Define standard field validators for common patterns
    - ✓ Create base model classes for common parameter groups
    - ✓ Implement consistent validation messages

- [ ] **Optimize Cache Implementation**

  - **Target:** `/src/cache/redis_cache.py`
  - **Goal:** Standardize caching across clients
  - **Tasks:**
    - [ ] Create a standard cache key generation utility
    - [ ] Implement TTL management based on data type
    - [ ] Add cache invalidation patterns
    - [ ] Add cache hit/miss statistics tracking
    - [ ] Implement cache prefetching for common queries
    - [ ] Create cache warming strategies
    - [ ] Add distributed cache locking
    - [ ] Implement typed cache interface

- [x] **Improve HTTP Client Usage**

  - **Target:** Client implementation files
  - **Goal:** Switch from `requests` to `httpx` per coding standards
  - **Tasks:**
    - [x] Identify all uses of the `requests` library (No active usage found in Python source code as of YYYY-MM-DD)
    - [N/A] Replace with async `httpx` client (Not applicable as no `requests` usage to replace)
    - [N/A] Implement proper connection pooling and timeouts (Not applicable)

- [ ] **Library Modernization**

  - **Target:** Throughout codebase
  - **Goal:** Adopt high-performance libraries
  - **Tasks:**
    - [x] Replace any pandas usage with polars (No pandas usage found in src)
    - [x] Use pyarrow for columnar data operations (No pyarrow usage found; no immediate pandas/columnar processing to optimize with it)
    - [ ] Ensure proper async patterns with anyio/asyncio (Generally good; minor sync file I/O in migrations noted - likely acceptable)
    - [ ] Add structured logging with structlog
    - [ ] Implement typed API clients for external services
    - [ ] Use proper dependency injection patterns

- [ ] **Consider Additional MCP Servers**

  - **Target:** Potential new MCP integrations
  - **Goal:** Evaluate additional MCP servers for integration
  - **Tasks:**
    - [ ] Evaluate Sequential Thinking MCP:
      - Assess benefits for complex travel planning logic
      - Create prototype integration with planning agents
      - Test effectiveness vs. traditional approaches
      - Document integration patterns if adopted
    - [ ] Evaluate LinkUp MCP:
      - Assess benefits for destination research
      - Compare results quality with Firecrawl
      - Create integration plan if beneficial
      - Document content sourcing strategy
    - [ ] Evaluate Exa MCP:
      - Compare web search capabilities with other MCPs
      - Test integration for destination research
      - Determine optimal search provider mix
      - Create integration plan if adopted

- [ ] **Custom MCP Wrapper Development**

  - **Target:** TripSage-specific MCP functionality
  - **Goal:** Create thin custom MCP wrappers only for core functionality
  - **Tasks:**
    - [ ] Unified Travel Search Wrapper:
      - Design integrated search API that leverages multiple MCPs
      - Implement result aggregation and normalization
      - Create unified schema for travel options
      - Add comprehensive tests for combined search
    - [ ] Trip Planning Coordinator:
      - Develop coordinator for complex planning operations
      - Implement orchestration across multiple underlying MCPs
      - Create optimization algorithms for itinerary planning
      - Add tests for coordinator functionality
    - [ ] Content Aggregator:
      - Implement wrapper around hybrid Crawl4AI/Firecrawl solution
      - Create content normalization for unified schema
      - Implement domain-based source selection logic
      - Develop destination content enrichment features
      - Add comprehensive caching with Redis MCP
      - Implement error handling and fallback mechanisms
      - Add tests for multi-source content aggregation
    - [ ] Development Guidelines:
      - Use FastMCP 2.0 for all custom MCP development
      - Implement Pydantic v2 models for all schemas
      - Use function tool pattern for all MCP tools
      - Implement decorator-based error handling
      - Document when to build vs. use existing MCPs
      - Create templates for custom MCP development
      - Implement standard validation patterns
      - Define testing requirements for custom MCPs

- [ ] **API and Database Migrations**
  - **Target:** `/src/api/` and `/src/db/` directories
  - **Goal:** Migrate API and database components to tripsage structure
  - **Tasks:**
    - [ ] Create tripsage/api directory with FastAPI structure:
      - Create endpoint groups by domain (users, trips, flights, etc.)
      - Implement proper dependency injection
      - Add comprehensive request/response models
    - [ ] Implement database migration:
      - Move database models to tripsage/models/db
      - Update repositories with proper typing
      - Ensure consistent error handling
      - Implement proper connection pooling
    - [ ] API Improvements:
      - Add OpenAPI documentation
      - Implement API versioning
      - Add proper rate limiting
      - Implement comprehensive logging
      - Add request validation with Pydantic
    - [ ] Neo4j Database Improvements:
      - Standardize Neo4j query patterns
      - Implement proper transaction handling
      - Add efficient indexing strategies
      - Implement proper error handling for Neo4j operations

## Low Priority

- [x] **Extract Common Service Patterns**

  - **Target:** Service modules in MCP implementations
  - **Goal:** Standardize service layer patterns
  - **Tasks:**
    - ✓ Define base service interfaces
    - ✓ Create standard patterns for service methods
    - ✓ Extract common logic to base classes

- [x] **Neo4j AuraDB API MCP Evaluation (Issue #39)**

  - **Target:** Neo4j operational management
  - **Goal:** Evaluate the need for programmatic management of Neo4j AuraDB instances
  - **Status:** Evaluated and recommended against implementation at this time
  - **Tasks:**
    - ✓ Evaluate the mcp-neo4j-cloud-aura-api server's capabilities
    - ✓ Analyze TripSage's operational needs for Neo4j management
    - ✓ Conduct security and complexity assessment
    - ✓ Provide recommendation for Issue #39
  - **Findings:**
    - TripSage uses Neo4j as a persistent knowledge graph with stable connections
    - The Neo4j Memory MCP already provides all needed application-level interactions
    - Administrative operations are better handled through Neo4j Aura's web interface
    - Dynamic instance management would add unnecessary complexity and security concerns
    - KISS/YAGNI principles suggest avoiding this integration until specific operational needs arise
  - **Recommendation:** Maintain as Post-MVP / Low Priority. Do not implement until clear operational needs emerge.

- [ ] **Refactor Function Tool Signatures**

  - **Target:** Agent tool implementation files
  - **Goal:** Simplify function signatures, reduce parameters
  - **Tasks:**
    - [ ] Create standard request/response models
    - [ ] Replace parameter lists with configuration objects
    - [ ] Use default class instantiation for common configurations
    - [ ] Implement proper typing for all parameters
    - [ ] Add comprehensive validation with helpful error messages
    - [ ] Create reusable parameter validators

- [ ] **Eliminate Duplicated Logging**

  - **Target:** All modules with custom logging
  - **Goal:** Standardize logging approach
  - **Tasks:**
    - [ ] Create context-aware logging decorator
    - [ ] Implement standard log formatters
    - [ ] Use structured logging patterns
    - [ ] Add correlation IDs for request tracing
    - [ ] Implement log level control by module
    - [ ] Add performance metrics logging

- [x] **Create Isolated Test Utilities**

  - **Target:** Test files and fixtures
  - **Goal:** Create reusable test fixtures independent of environment variables
  - **Tasks:**
    - ✓ Create portable test modules that don't depend on settings
    - ✓ Implement isolated test fixtures with proper mocking
    - ✓ Standardize mocking approach for database and MCP clients
    - ✓ Add comprehensive test coverage for abstract base classes

- [ ] **Clean Up Test Utilities**

  - **Target:** All test files and fixtures
  - **Goal:** Refactor remaining test utilities
  - **Tasks:**
    - [ ] Extract remaining common test fixtures
    - [ ] Implement factory methods for test data
    - [ ] Apply isolated testing pattern more broadly
    - [ ] Create standard patterns for mocking
    - [ ] Add comprehensive assertion helpers
    - [ ] Implement proper test teardown
    - [ ] Add performance testing utilities

- [ ] **File Size Reduction**
  - **Target:** Files exceeding 350 LoC
  - **Goal:** Split large files into smaller modules
  - **Tasks:**
    - [ ] Identify files exceeding the size limit
    - [ ] Extract logical components to separate modules
    - [ ] Ensure proper imports and exports
    - [ ] Maintain documentation for separated modules
    - [ ] Add index files for grouped exports

## Code Quality Enforcement

- [ ] **Add Pre-commit Hooks**

  - **Target:** Root repository
  - **Goal:** Automate code quality checks
  - **Tasks:**
    - [ ] Configure pre-commit for ruff checking
    - [ ] Add type checking with mypy
    - [ ] Enforce import sorting
    - [ ] Add line length enforcement
    - [ ] Implement docstring validation
    - [ ] Add security scanning with bandit
    - [ ] Enforce consistent file naming

- [ ] **Improve Test Coverage**
  - **Target:** Modules with <90% coverage
  - **Goal:** Meet 90% coverage target
  - **Tasks:**
    - [ ] Identify modules with insufficient coverage
    - [ ] Add unit tests for untested functions
    - [ ] Create integration tests for major components
    - [ ] Implement property-based testing for complex logic
    - [ ] Add mutation testing for critical components
    - [ ] Create comprehensive edge case tests
    - [ ] Implement performance regression tests

## Compliance Checklist for Each Task

For each completed task, ensure:

- [x] `ruff check --fix` & `ruff format .` pass cleanly
- [x] Imports are properly sorted
- [x] Type hints are complete and accurate
- [x] Tests cover the changes (aim for ≥90%)
- [x] No secrets are committed
- [x] File size ≤500 LoC, ideally ≤350 LoC
- [x] Code follows KISS/DRY/YAGNI/SIMPLE principles

## Detailed Implementation Plans

### Codebase Restructuring (Issue #31)

- **Target:** Core application logic
- **Goal:** Move all application logic to `tripsage/` directory with consistent patterns
- **Implementation Phases:**

1. **Phase 1: Core Components** (In Progress)

   - [x] Migrate base agent and tool implementations
   - [x] Update import patterns to use the `agents` module
   - [x] Implement consistent agent class naming (remove redundant "Agent" suffixes)
   - [x] Migrate browser tools with updated imports
   - [ ] Update the remaining imports in all migrated files
   - [ ] Create `__init__.py` files with proper exports

2. **Phase 2: Agent Implementation**

   - [ ] Create agent factory for standardized initialization
   - [ ] Implement triage pattern for agent selection
   - [ ] Create consistent handoff mechanisms
   - [ ] Update prompt templates for all agents
   - [ ] Standardize agent metadata structure

3. **Phase 3: MCP Integration**

   - [ ] Migrate MCP clients to `tripsage/clients/` directory
   - [ ] Implement consistent client factory pattern
   - [ ] Create standardized error handling for MCP operations
   - [ ] Add response validation with Pydantic V2
   - [ ] Implement proper async context management

4. **Phase 4: Database Integration**

   - [ ] Move database models to `tripsage/models/` directory
   - [ ] Update repositories with proper dependency injection
   - [ ] Create consistent error handling for database operations
   - [ ] Implement efficient connection pooling
   - [ ] Add comprehensive validation for all database operations

5. **Phase 5: Final Integration**
   - [ ] Create integration tests for the new structure
   - [ ] Update documentation with architecture diagrams
   - [ ] Create usage examples for all components
   - [ ] Implement API endpoints with the new structure
   - [ ] Create comprehensive deployment documentation

### OpenAI Agents SDK Integration (Issue #28)

- **Target:** Agent implementation
- **Goal:** Implement the latest OpenAI Agents SDK patterns
- **Implementation Tasks:**

1. **SDK Setup and Configuration**

   - [ ] Create standardized SDK configuration
   - [ ] Implement proper initialization patterns
   - [ ] Add environment variable validation
   - [ ] Create fallback mechanisms for missing settings
   - [ ] Implement centralized settings management

2. **Agent Architecture**

   - [ ] Implement hierarchical agent structure
   - [ ] Create triage agent for request routing
   - [ ] Implement specialized agents with defined responsibilities
   - [ ] Create consistent handoff mechanisms between agents
   - [ ] Implement context preservation during handoffs

3. **Function Tool Implementation**

   - [ ] Create standardized tool parameter models
   - [ ] Implement consistent error handling for all tools
   - [ ] Add comprehensive validation for tool inputs
   - [ ] Create proper documentation for all tools
   - [ ] Implement typed return values for all tools

4. **MCP Server Integration**

   - [ ] Implement `MCPServerManager` class
   - [ ] Create async context management for server connections
   - [ ] Add proper error handling for server failures
   - [ ] Implement reconnection strategies
   - [ ] Create consistent initialization pattern

5. **Advanced Features**
   - [ ] Implement structured output with JSON mode
   - [ ] Add parallel tool execution for efficiency
   - [ ] Create streaming response handlers
   - [ ] Implement memory integration with graph database
   - [ ] Add custom model integration capabilities

### Pydantic V2 Migration

- **Target:** Core models and validation
- **Goal:** Upgrade to Pydantic V2 patterns for validation and serialization
- **Implementation Tasks:**

1. **Core Models Update**

   - [ ] Replace `BaseSettings` with `ConfigDict` approach
   - [ ] Update field validators with `@field_validator`
   - [ ] Replace `validator` with `field_validator` and add `@classmethod`
   - [ ] Update model serialization methods
   - [ ] Implement model validators with `@model_validator`

2. **MCP Client Models**

   - [ ] Update request/response models
   - [ ] Implement proper field validation
   - [ ] Create standardized error messages
   - [ ] Add type adapters for non-model validation
   - [ ] Implement serializers for custom types

3. **API Models**
   - [ ] Update FastAPI request/response models
   - [ ] Implement proper field validation
   - [ ] Create standardized error responses
   - [ ] Add model examples for documentation
   - [ ] Implement comprehensive validation for all API endpoints

## Progress Tracking

| Task                            | Status | PR  | Notes                                                                   |
| ------------------------------- | ------ | --- | ----------------------------------------------------------------------- |
| Calendar Tools Refactoring      | ✅     | #87 | Applied error handling decorator pattern                                |
| Flight Search Refactoring       | ✅     | #88 | Applied error handling decorator to four methods                        |
| Error Handling Tests            | ✅     | #88 | Created standalone tests for decorator functionality                    |
| Accommodations Refactoring      | ✅     | #89 | Applied error handling decorator to two methods                         |
| MCP Client Standardization      | ✅     | #90 | Implemented client factory pattern, improved error handling             |
| MCP Factory Pattern             | ✅     | #90 | Created standard factory interface + implementations for Time & Flights |
| MCP Error Classification        | ✅     | #90 | Added error categorization system for better error handling             |
| MCP Documentation               | ✅     | #90 | Added comprehensive README for MCP architecture                         |
| Dual Storage Service            | ✅     | #91 | Created DualStorageService base class with standard CRUD operations     |
| Trip Storage Service            | ✅     | #91 | Implemented TripStorageService with Pydantic validation                 |
| Fix Circular Imports            | ✅     | #92 | Fixed circular imports in base_mcp_client.py and decorators.py          |
| Isolated Test Patterns          | ✅     | #93 | Created environment-independent test suite for dual storage services    |
| Comprehensive Test Coverage     | ✅     | #93 | Added tests for abstract interfaces and error handling                  |
| MCP Isolated Testing            | ✅     | #94 | Implemented isolated testing pattern for MCP clients                    |
| MCP Testing Documentation       | ✅     | #94 | Created documentation for isolated MCP testing pattern                  |
| Tool Registration Logic         | ✅     | #95 | Simplified tool registration with automatic discovery                   |
| Parameter Validation            | ✅     | #95 | Centralized parameter validation with Pydantic base models              |
| Service Pattern Extraction      | ✅     | #95 | Extracted common service patterns for MCP implementations               |
| Codebase Restructuring - Part 1 | ✅     | -   | Updated tool imports, migrated all agent files and tools                |
| Browser Tools Migration         | ✅     | -   | Updated browser tools with correct imports and tools registration       |
| Codebase Restructuring - Part 2 | 🔄     | -   | Remaining import updates and test updates in progress                   |
| OpenAI Agents SDK Integration   | 🔄     | -   | Research completed, implementation planning in progress                 |
| Pydantic V2 Migration           | 📅     | -   | Scheduled to start after Codebase Restructuring is complete             |
| External MCP Server Strategy    | ✅     | -   | Completed evaluation of MCP servers and established hybrid approach     |
| Supabase MCP Integration        | 📅     | -   | Scheduled to start after Codebase Restructuring is complete             |
| Neo4j Memory MCP Integration    | 📅     | -   | Prioritized for knowledge graph implementation                          |
| Travel Data MCP Integration     | 📅     | -   | Duffel Flights MCP and Airbnb MCP identified for travel data access     |
| Playwright MCP Integration      | 📅     | -   | Prioritized for browser automation and fallback scraping                |
| Crawl4AI MCP Integration        | 📅     | -   | Scheduled for destination research and content extraction               |
| Google Maps MCP Integration     | 📅     | -   | Prioritized for location-based functionality                            |
| Time MCP Integration            | 📅     | -   | Scheduled for timezone support in travel planning                       |
