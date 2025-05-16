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
    - [x] Update remaining imports:
      - ✓ Update all `from src.*` imports to `from tripsage.*`
      - ✓ Ensure consistent use of the `agents` module instead of `openai_agents_sdk`
    - [ ] Update tests to match new structure (Issue #31):

      - ✓ Update imports in test files to use tripsage module

      ### Phase 1: Test Infrastructure Setup

      - [x] Create new `tests/` directory structure mirroring `tripsage/`
      - [x] Create shared `conftest.py` with common fixtures
      - [ ] Set up test configuration for mocking MCPManager
      - [ ] Create integration test directory for end-to-end scenarios
      - [ ] **BLOCKER**: Resolve circular import issues with MCP abstraction layer
      - [ ] **BLOCKER**: Handle environment variable dependencies for tests
      - [ ] **BLOCKER**: Fix Redis URL dependency in cache initialization

      ### Phase 2: Core Component Tests

      - [x] Create unit tests for MCPManager
        - [x] Test initialization and configuration
        - [x] Test invoke() method with various scenarios
        - [x] Test error handling and retries
      - [x] Create unit tests for MCPClientRegistry
        - [x] Test wrapper registration
        - [x] Test wrapper retrieval
        - [x] Test dynamic loading
      - [x] Create tests for core MCP wrappers
        - [x] Test Weather MCP wrapper
        - [x] Test Google Maps MCP wrapper
        - [x] Test Time MCP wrapper
        - [x] Test Supabase MCP wrapper
        - [x] Test method mapping
        - [x] Test parameter validation
        - [x] Test error handling
      - [x] Create tests for Base MCP Wrapper
      - [x] Create tests for exception hierarchy

      ### Phase 3: Migrate Existing Tests

      - [ ] Migrate agent tests from `src/tests/agents/`
        - [ ] Update imports to use `tripsage.*`
        - [ ] Refactor to use MCPManager mocks
      - [ ] Migrate tool tests from `src/tests/`
        - [ ] Update imports
        - [ ] Add tests for MCP integration
        - [ ] Test error handling through MCP
      - [ ] Migrate utility tests
        - [ ] Ensure compatibility with new structure
        - [ ] Add tests for new utilities

      ### Phase 4: New Component Tests

      - [ ] Create tests for WebOperationsCache
        - [ ] Test caching logic
        - [ ] Test TTL management
        - [ ] Test metrics collection
      - [ ] Create tests for webcrawl components
        - [ ] Test source selector
        - [ ] Test result normalizer
        - [ ] Test persistence
      - [ ] Create tests for monitoring
        - [ ] Test OpenTelemetry integration
        - [ ] Test span creation
        - [ ] Test metrics collection

      ### Phase 5: Integration Tests

      - [ ] Create end-to-end scenario tests
        - [ ] Test complete travel planning flow
        - [ ] Test agent handoffs
        - [ ] Test error recovery
      - [ ] Create MCP integration tests
        - [ ] Test real MCP server connections
        - [ ] Test failover scenarios
        - [ ] Test performance characteristics

      ### Phase 6: Coverage and Cleanup

      - [ ] Ensure 90%+ test coverage for all modules
      - [ ] Remove obsolete tests
      - [ ] Update test documentation
      - [ ] Create test guidelines for contributors

    - [x] Clean up duplicated files:
      - [x] Migrate key utilities from src/utils:
        - ✓ Deleted deprecated `src/utils/config.py`
        - ✓ Migrated `src/utils/decorators.py` functionality to `tripsage/utils/decorators.py`
        - ✓ Deleted `src/utils/error_decorators.py` (merged into decorators.py)
        - ✓ Deleted `src/utils/error_handling.py` (covered by new implementation)
      - [x] Complete remaining source directory cleanup
        - ✓ Deleted src/db/ (replaced by MCP approach)
        - ✓ Deleted src/mcp/ (refactored to mcp_abstraction and clients)
        - ✓ Deleted src/agents/ (migrated to tripsage)
        - ✓ Deleted src/utils/ (enhanced implementations in tripsage)
        - ✓ Deleted src/tests/ (obsolete tests)
      - [ ] Handle src/types/supabase.ts TypeScript file
        - Option 1: Delete if no frontend planned
        - Option 2: Move to docs/schemas/ for reference
      - [ ] Remove empty src/ directory once fully cleaned
      - [x] Ensure no duplicate functionality exists
    - [ ] Documentation updates:
      - Update README.md to reflect new structure
      - Add directory structure documentation
      - Create migration guide for developers

  - [ ] Frontend Application Development:
    - [x] Frontend Architecture & Planning:
      - ✓ Conducted comprehensive research on Next.js 15, React 19, and shadcn/ui
      - ✓ Researched Vercel AI SDK v5 with streaming protocol
      - ✓ Analyzed MCP SDK integration patterns for TypeScript
      - ✓ Created comprehensive frontend specifications (frontend_specifications_v2.md)
      - ✓ Implemented Zod integration strategy (zod_integration_guide.md)
      - ✓ Created detailed frontend TODO list (TODO-FRONTEND.md)
      - ✓ Validated technology stack with latest documentation
      - ✓ Defined architecture patterns for AI-native interface
    - [ ] Phase 1: Foundation & Core Setup
      - [ ] Initialize Next.js 15 with App Router
      - [ ] Configure TypeScript 5.0+ with strict mode
      - [ ] Set up Tailwind CSS v4 with OKLCH colors
      - [ ] Install and configure shadcn/ui components
      - [ ] Create root layout with theme support
      - [ ] Implement Zustand stores for state management
      - [ ] Set up React Query for server state
      - [ ] Configure Vercel AI SDK v5
      - [ ] Create base UI components library
      - [ ] Set up development environment with Turbopack
    - [ ] Phase 2: Authentication & Security
      - [ ] Build secure API key management interface
      - [ ] Implement client-side key storage with encryption
      - [ ] Create provider-specific validation
      - [ ] Add usage tracking and limits visualization
      - [ ] Implement secure key rotation support
      - [ ] Create environment-based configuration
      - [ ] Add runtime key validation
      - [ ] Build cost estimation per provider
    - [ ] Phase 3: AI Chat Interface
      - [ ] Implement chat UI with Vercel AI SDK
      - [ ] Add streaming responses with typing indicators
      - [ ] Create rich content rendering (markdown, code)
      - [ ] Build message history with search
      - [ ] Add file and image upload capabilities
      - [ ] Implement voice input/output support
      - [ ] Create conversation management
      - [ ] Add chat export functionality
    - [ ] Phase 4: Agent Visualization
      - [ ] Create real-time agent activity monitoring
      - [ ] Build agent flow diagrams with React Flow
      - [ ] Implement progress bars for operations
      - [ ] Add agent status indicators
      - [ ] Create execution timeline visualization
      - [ ] Build resource usage metrics
      - [ ] Add WebSocket connection for updates
      - [ ] Implement agent interaction animations
    - [ ] Phase 5: Travel Planning Features
      - [ ] Integrate Mapbox GL for trip visualization
      - [ ] Build itinerary timeline component
      - [ ] Create budget tracking with Recharts
      - [ ] Implement accommodation search UI
      - [ ] Add flight search and booking interface
      - [ ] Build weather integration display
      - [ ] Create destination recommendations
      - [ ] Add collaborative planning features
    - [ ] Phase 6: LLM Configuration
      - [ ] Build model selection UI with providers
      - [ ] Add cost estimation per query
      - [ ] Create custom parameter controls
      - [ ] Implement performance metrics dashboard
      - [ ] Add model comparison feature
      - [ ] Create usage analytics display
      - [ ] Build A/B testing interface
      - [ ] Add model switching capabilities
    - [ ] Phase 7: State & API Integration
      - [ ] Implement Zustand stores architecture
      - [ ] Set up React Query patterns
      - [ ] Create MCP client integrations
      - [ ] Build comprehensive error handling
      - [ ] Add retry logic with exponential backoff
      - [ ] Implement offline support
      - [ ] Create API route handlers
      - [ ] Add server actions for data mutations
    - [ ] Phase 8: Performance Optimization
      - [ ] Implement code splitting strategies
      - [ ] Configure Next.js Image optimization
      - [ ] Set up caching with React Query
      - [ ] Add loading states and skeletons
      - [ ] Optimize bundle with tree shaking
      - [ ] Implement lazy loading for components
      - [ ] Add performance monitoring
      - [ ] Create lighthouse CI integration
    - [ ] Phase 9: Testing & Quality
      - [ ] Set up Vitest for unit testing
      - [ ] Configure React Testing Library
      - [ ] Implement Playwright E2E tests
      - [ ] Add Storybook for components
      - [ ] Create Mock Service Worker setup
      - [ ] Add visual regression testing
      - [ ] Implement accessibility testing
      - [ ] Create CI/CD test pipeline
    - [ ] Phase 10: Deployment & Monitoring
      - [ ] Configure Vercel deployment
      - [ ] Set up GitHub Actions workflows
      - [ ] Implement Sentry error tracking
      - [ ] Add PostHog analytics
      - [ ] Create monitoring dashboards
      - [ ] Set up alerting for errors
      - [ ] Implement A/B testing framework
      - [ ] Add performance monitoring
    - [x] Database layer migration:
      - ✓ Created tripsage/models/db/ directory for essential business models
      - ✓ Migrated core entity models (User, Trip) with business validation
      - ✓ Implemented domain-specific Supabase tools in supabase_tools.py
      - ✓ Enhanced SupabaseMCPWrapper for database operations
      - ✓ Created tripsage/db/migrations/sql/ directory (exists as root migrations/)
      - ✓ Adapted run_migrations.py to use Supabase MCP's execute_sql
      - ✓ Created tripsage/db/migrations/neo4j/ for graph schema scripts
      - ✓ Implemented Neo4j initialization logic using Memory MCP
      - ✓ Added domain-specific tools in memory_tools.py for complex queries
      - [ ] Delete old src/db/ directory after migration completion

- [ ] **Integrate External MCP Servers**

  - **Target:** MCP server architecture and implementation
  - **Goal:** Adopt a hybrid approach favoring external MCPs when possible
  - **Strategy:**
    - Prioritize existing external MCPs when available
    - Only build custom MCPs for core business logic, direct database integration, or when privacy/security requirements can't be met externally
  - **Tasks:**

    - [x] Implement error handling and monitoring infrastructure (foundational):
      - **Target:** MCP error handling, structured logging, and OpenTelemetry tracing
      - **Goal:** Create standardized error handling and monitoring for all MCP interactions
      - **Completed Tasks:**
        - ✓ Refined custom MCP exception hierarchy with specific error types
        - ✓ Added MCPTimeoutError, MCPAuthenticationError, MCPRateLimitError, MCPNotFoundError
        - ✓ Enhanced MCPManager.invoke with structured logging
        - ✓ Implemented OpenTelemetry span creation with appropriate attributes
        - ✓ Created exception mapping logic for common error types
        - ✓ Added monitoring.py for OpenTelemetry configuration
        - ✓ Configured OpenTelemetryConfig in app_settings.py
        - ✓ Used existing FastAPI dependency injection patterns
      - **Sub-tasks for further enhancements:**
        - [ ] Configure production OpenTelemetry exporter (OTLP)
        - [ ] Implement advanced error alerting based on error types
        - [ ] Integrate structlog more deeply if PoC is successful
        - [ ] Add metrics collection for MCP performance
        - [ ] Create dashboards for monitoring MCP operations
    - [x] Supabase MCP Integration: (Short-Term Phase)
      - **Target:** Database operations for TripSage's SQL data
      - **Goal:** Provide seamless integration with Supabase database
      - **Success Metrics:**
        - 99.9% uptime for database operations
        - <100ms average query response time
        - 100% schema validation coverage
        - 95%+ test coverage with integration tests
      - **Resources:**
        - **Server Repo:** https://github.com/supabase/mcp-supabase
        - **Supabase Docs:** https://supabase.com/docs
      - **Completed Tasks:**
        - ✓ Set up Supabase MCP server configuration
        - ✓ Created SupabaseMCPWrapper with standardized method mapping
        - ✓ Refactored `tripsage/tools/supabase_tools.py` to use MCPManager
        - ✓ Implemented all database operation tools with Pydantic validation
        - ✓ Added proper error handling with TripSageMCPError
    - [x] Neo4j Memory MCP Integration: (Immediate Phase)
      - **Target:** Knowledge graph operations for trip planning and domain data
      - **Goal:** Implement persistent memory graph for travel domain knowledge
      - **Success Metrics:**
        - 95%+ successful graph operations
        - <200ms average query response time
        - Complete coverage of entity/relationship models
        - 90%+ test coverage for graph operations
      - **Resources:**
        - **Server Repo:** https://github.com/neo4j-contrib/mcp-neo4j
        - **Neo4j Docs:** https://neo4j.com/docs/
        - **Memory MCP Docs:** https://neo4j.com/labs/claude-memory-mcp/
      - **Completed Tasks:**
        - ✓ Configured Neo4j Memory MCP server
        - ✓ Created Neo4jMemoryMCPWrapper with standardized method mapping
        - ✓ Refactored `tripsage/tools/memory_tools.py` to use MCPManager
        - ✓ Implemented entity/relationship management functions
        - ✓ Added proper error handling with TripSageMCPError
        - ✓ Added model validation for all operations
    - [x] Duffel Flights MCP Integration: (Short-Term Phase)
      - **Target:** Flight search and booking for travel planning
      - **Goal:** Enable comprehensive flight options with real-time pricing
      - **Success Metrics:**
        - 95%+ successful flight searches
        - <3 second average response time
        - Complete coverage of major global airlines
        - 90%+ test coverage with realistic flight scenarios
      - **Resources:**
        - **Server Repo:** https://github.com/duffel/mcp-flights
        - **Duffel API Docs:** https://duffel.com/docs/api
      - **Completed Tasks:**
        - ✓ Set up Duffel Flights MCP configuration
        - ✓ Created DuffelFlightsMCPWrapper with standardized method mapping
        - ✓ Refactored `tripsage/tools/flight_tools.py` to use MCPManager
        - ✓ Implemented offer and search functionality
        - ✓ Added proper error handling with TripSageMCPError
        - ✓ Added model validation for all operations
    - [x] Airbnb MCP Integration: (Short-Term Phase)
      - **Target:** Accommodation search and booking capabilities
      - **Goal:** Enable comprehensive lodging options for travel planning
      - **Success Metrics:**
        - 90%+ successful accommodation searches
        - <5 second average response time
        - Accurate pricing and availability data
        - 90%+ test coverage for accommodation operations
      - **Resources:**
        - **Server Repo:** https://github.com/openbnb/mcp-airbnb
        - **API Reference:** https://github.com/openbnb/openbnb-api
      - **Completed Tasks:**
        - ✓ Configured Airbnb MCP server
        - ✓ Created AirbnbMCPWrapper with standardized method mapping
        - ✓ Refactored `tripsage/tools/accommodation_tools.py` to use MCPManager
        - ✓ Implemented listing search and details functionality
        - ✓ Added proper error handling with TripSageMCPError
        - ✓ Added model validation for all operations
    - [x] Playwright MCP Integration: (Immediate Phase)
      - **Target:** Browser automation for complex travel workflows
      - **Goal:** Provide fallback mechanism for sites that block scrapers
      - **Success Metrics:**
        - 95%+ successful completion rate for authenticated workflows
        - <5 second average response time for cached operations
        - 90%+ test coverage with integration tests
        - Successful fallback handling for at least 5 major travel sites
      - **Resources:**
        - **Server Repo:** https://github.com/executeautomation/mcp-playwright
        - **Playwright Docs:** https://playwright.dev/docs/intro
      - **Tasks:**
        - [x] Configure Playwright MCP server with Python integration
          - ✓ Created PlaywrightMCPClient class in tripsage/tools/browser/playwright_mcp_client.py
          - ✓ Implemented JSON-RPC style client using httpx for async operations
          - ✓ Added proper connection pooling and timeout management
          - ✓ Integrated with MCP configuration system for settings
        - [x] Create browser automation toolkit
          - ✓ Added core browser operations (navigate, screenshot, click, fill)
          - ✓ Implemented content extraction methods (get_visible_text, get_visible_html)
          - ✓ Created agent-callable function tools in browser_tools.py
          - ✓ Used proper async/await patterns with context managers
        - [x] Implement proper error handling
          - ✓ Used @with_error_handling decorator for standardized error reporting
          - ✓ Created PlaywrightMCPError class for clear error categorization
          - ✓ Added comprehensive logging for operations and errors
        - [ ] Implement session persistence for authenticated workflows
        - [ ] Develop travel-specific browser operations (booking verification, check-ins)
        - [ ] Create escalation logic from crawler to browser automation
        - [ ] Add anti-detection capabilities for travel websites
        - [ ] Implement comprehensive testing with mock travel websites
    - [x] Hybrid Web Crawling Integration: (Immediate-to-Short-Term Phase)
      - **Target:** Implement domain-optimized web crawling strategy
      - **Goal:** Maximize extraction performance and reliability for travel sites
      - **Success Metrics:**
        - 90%+ extraction success rate across all targeted travel sites
        - <4 seconds average response time for optimized domains
        - 95% accuracy in content extraction compared to manual collection
        - <15% fallback rate to browser automation
      - **Tasks:**
        - [x] Crawl4AI MCP Integration:
          - **Resources:**
            - **Server Repo:** https://github.com/unclecode/crawl4ai
            - **API Docs:** https://github.com/unclecode/crawl4ai/blob/main/DEPLOY.md
          - **Completed Tasks:**
            - ✓ Configured Crawl4AI MCP server with WebSocket and SSE support
            - ✓ Implemented in `tripsage/clients/webcrawl/crawl4ai_mcp_client.py`
            - ✓ Created comprehensive client methods for crawling, extraction, and Q&A
            - ✓ Implemented content-aware caching with appropriate TTLs
            - ✓ Added support for markdown, HTML, screenshots, PDFs, and JavaScript execution
            - ✓ Created comprehensive tests in `tests/clients/webcrawl/test_crawl4ai_mcp_client.py`
            - ✓ Added documentation in `docs/integrations/mcp-servers/webcrawl/crawl4ai_mcp_client.md`
            - ✓ Extended ContentType enum with JSON, MARKDOWN, HTML, BINARY types
        - [x] Firecrawl MCP Integration:
          - **Resources:**
            - **Server Repo:** https://github.com/mendableai/firecrawl-mcp-server
            - **API Docs:** https://docs.firecrawl.dev/
          - **Completed Tasks:**
            - ✓ Configured official Firecrawl MCP server from MendableAI
            - ✓ Implemented in `tripsage/clients/webcrawl/firecrawl_mcp_client.py`
            - ✓ Created comprehensive client methods for scraping, crawling, and extraction
            - ✓ Implemented content-aware caching with specialized TTLs for booking sites
            - ✓ Added structured data extraction, batch operations, and search capabilities
            - ✓ Optimized for booking sites with shorter cache TTLs (1 hour for dynamic pricing)
            - ✓ Created comprehensive tests for client functionality
            - ✓ Added proper error handling with @with_error_handling decorator
        - [x] Source Selection Logic:
          - ✓ Implemented domain-based routing in `tripsage/tools/webcrawl/source_selector.py`
            - Created WebCrawlSourceSelector class with configurable domain mappings
            - Added content-type based routing for optimal crawler selection
            - Implemented domain routing configuration in `mcp_settings.py`
            - Created example configuration documentation
          - ✓ Created unified abstraction layer in `tripsage/tools/webcrawl_tools.py`
            - Implemented `crawl_website_content` as the main unified interface
            - Added convenience functions for specific content types
            - Integrated with source selector and result normalizer
          - [ ] Develop empirical performance testing framework
          - ✓ Documented domain-specific optimization strategy
        - [x] Result Normalization:
          - ✓ Created consistent output schema in `tripsage/tools/webcrawl/models.py`
            - Defined UnifiedCrawlResult Pydantic V2 model
            - Included all common fields across both crawlers
            - Added helper methods for timestamp and source checking
          - ✓ Implemented normalization logic in `tripsage/tools/webcrawl/result_normalizer.py`
            - Created normalize_firecrawl_output method
            - Created normalize_crawl4ai_output method
            - Handled error cases and edge conditions
          - ✓ Ensured unified interface regardless of underlying crawler
        - [x] Playwright MCP Fallback Integration:
          - ✓ Extended result normalizer with `normalize_playwright_mcp_output` method
            - Created normalization for Playwright MCP output
            - Handled browser-specific metadata (browser type, screenshots)
            - Integrated with UnifiedCrawlResult schema
          - ✓ Enhanced unified web crawl tool with fallback logic
            - Added Playwright MCP as fallback when primary crawlers fail
            - Implemented intelligent failure detection (error status, empty content, JS requirements)
            - Added `enable_playwright_fallback` parameter for control
            - Integrated proper error handling for both primary and fallback attempts
          - ✓ Refined WebCrawlSourceSelector for Playwright-only domains
            - Added CrawlerType.PLAYWRIGHT enum value
            - Defined default Playwright-only domains (social media, Google services)
            - Enhanced `select_crawler` method with `force_playwright` parameter
            - Added support for direct Playwright selection as primary crawler
          - Implemented graceful degradation with proper error tracking
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
    - [x] Google Maps MCP Integration: (Immediate Phase)
      - **Target:** Location services and geographic data for trip planning
      - **Goal:** Enable high-quality geographic data for travel planning and routing
      - **Success Metrics:**
        - 99% geocoding success rate
        - <300ms average response time
        - Complete coverage of required location services
        - 90%+ test coverage for all implemented functions
      - **Resources:**
        - **Server Repo:** https://github.com/googlemaps/mcp-googlemaps
        - **API Docs:** https://developers.google.com/maps/documentation
      - **Tasks:**
        - [x] Set up Google Maps MCP configuration
          - ✓ Created GoogleMapsMCPConfig in tripsage/config/app_settings.py
          - ✓ Added proper configuration for server URL and API keys
          - ✓ Provided example configuration in example_mcp_settings.py
        - [x] Create GoogleMapsMCPClient implementation
          - ✓ Implemented in tripsage/clients/maps/google_maps_mcp_client.py
          - ✓ Created singleton client pattern with async/await support
          - ✓ Added content-aware caching with WebOperationsCache
          - ✓ Implemented comprehensive error handling with MCPError
        - [x] Created Google Maps MCP tools in tripsage/tools/googlemaps_tools.py
          - ✓ Implemented geocoding, reverse geocoding, place search
          - ✓ Added place details, directions, distance matrix
          - ✓ Created timezone and elevation tools
          - ✓ Added proper error handling with @with_error_handling decorator
        - [x] Added tests for Google Maps MCP client
          - ✓ Created comprehensive unit tests with mocked responses
          - ✓ Tested all API endpoints and caching behavior
          - ✓ Implemented error case testing
          - ✓ Created tests for singleton pattern and context management
    - [x] Time MCP Integration: (Short-Term Phase)
      - **Target:** Timezone and time operations for global travel planning
      - **Goal:** Provide accurate time services for cross-timezone itineraries
      - **Success Metrics:**
        - 100% accuracy for timezone conversions
        - <100ms average response time
        - Support for all global timezones
        - 95%+ test coverage
      - **Resources:**
        - **Server Repo:** https://github.com/anthropics/mcp-time
        - **API Docs:** https://worldtimeapi.org/api/
      - [x] Configure Time MCP server
      - [x] Create time tools in `tripsage/tools/time_tools.py`
        - ✓ Implemented MCP client wrapper for the Time MCP
        - ✓ Updated tools to use MCPManager.invoke() instead of direct client calls
        - ✓ Added proper error handling with TripSageMCPError
      - [x] Implement timezone conversion and current time functionality
      - [x] Add tests for time-related operations
    - [x] Weather MCP Integration: (Immediate Phase)
      - **Target:** Weather forecasting and historical data for trip planning
      - **Goal:** Enable weather-aware itinerary planning and recommendations
      - **Success Metrics:**
        - 95%+ availability for global weather data
        - <1 second average response time
        - Accurate forecasting for 7+ day window
        - 90%+ test coverage for API functions
      - **Resources:**
        - **Server Repo:** https://github.com/szypetike/weather-mcp-server
        - **API Docs:** https://github.com/szypetike/weather-mcp-server#usage
      - **Tasks:**
        - [x] Configure Weather MCP server
          - ✓ Created WeatherMCPConfig in tripsage/config/app_settings.py
          - ✓ Added configuration for server URL and API keys
          - ✓ Integrated with OpenWeatherMap API
        - [x] Create WeatherMCPClient implementation
          - ✓ Implemented in tripsage/clients/weather/weather_mcp_client.py
          - ✓ Created singleton client pattern with async/await support
          - ✓ Added content-aware caching with different TTLs (REALTIME, DAILY)
          - ✓ Implemented comprehensive error handling with MCPError
        - [x] Created weather tools in `tripsage/tools/weather_tools.py`
          - ✓ Updated existing weather tools to use new client
          - ✓ Implemented get_current_weather, get_forecast, get_travel_recommendation
          - ✓ Added get_destination_weather, get_trip_weather_summary tools
          - ✓ Maintained backward compatibility with existing tool interfaces
        - [x] Add tests for weather-related operations
          - ✓ Created comprehensive unit tests for WeatherMCPClient
          - ✓ Added tests for all API endpoints and caching behavior
          - ✓ Implemented isolated tests to avoid settings loading issues
          - ✓ Created tests for singleton pattern and error handling
    - [x] Google Calendar MCP Integration: (Short-Term Phase)
      - **Target:** Calendar integration for trip planning and scheduling
      - **Goal:** Enable seamless addition of travel events to user calendars
      - **Success Metrics:**
        - 98%+ successful event creation/modification
        - <1 second average operation time
        - Complete support for all required calendar operations
        - 95%+ test coverage
      - **Resources:**
        - **Server Repo:** https://github.com/googleapis/mcp-calendar
        - **API Docs:** https://developers.google.com/calendar/api/v3/reference
      - ✓ Configure Google Calendar MCP server
      - ✓ Create calendar tools in `tripsage/tools/calendar_tools.py`
        - ✓ Created GoogleCalendarMCPWrapper with standardized method mapping
        - ✓ Refactored calendar_tools.py to use MCPManager for all MCP interactions
        - ✓ Added proper error handling with TripSageMCPError
      - ✓ Implement event creation and scheduling functionality
      - ✓ Add tests for calendar-related operations
    - [ ] Redis MCP Integration: (Short-Term Phase)
      - **Target:** Distributed caching for performance optimization
      - **Goal:** Improve response times and reduce API call volumes
      - **Success Metrics:**
        - 99.9% cache operation reliability
        - <50ms average cache operation time
        - 90%+ cache hit rate for common operations
        - Proper TTL management across content types
      - **Resources:**
        - **Server Repo:** https://github.com/redis/mcp-redis
        - **Redis Docs:** https://redis.io/docs/
      - Configure Redis MCP server
      - Create caching tools in `tripsage/tools/cache_tools.py`
      - Implement distributed caching functionality
      - Add tests for cache-related operations
    - [x] WebSearchTool Integration with Caching (Issue #37):

      - **Target:** Implement caching for OpenAI Agents SDK WebSearchTool
      - **Goal:** Optimize performance and reduce API usage for web searches
      - **Status:** ✅ COMPLETED - Integration implemented and validated
      - **Resources:**
        - **OpenAI Agents SDK:** https://openai.github.io/openai-agents-python/
        - **Redis Client Docs:** https://redis-py.readthedocs.io/en/stable/
      - **Research Findings:**
        - WebSearchTool already implemented in TravelPlanningAgent and DestinationResearchAgent
        - Domain configurations differ appropriately between agents
        - Redis caching infrastructure exists but needs web-specific extensions
        - **Note:** OpenAI SDK's WebSearchTool does not support allowed_domains/blocked_domains
      - **Tasks:**
        - [x] Create WebOperationsCache class in `tripsage/utils/cache.py`:
          - ✓ Extended existing Redis caching with content-type awareness
          - ✓ Implemented TTL management based on content volatility
          - ✓ Added metrics collection for cache performance analysis
        - [x] Create CachedWebSearchTool wrapper in `tripsage/tools/web_tools.py`:
          - ✓ Wrapped WebSearchTool with identical interface for transparent integration
          - ✓ Implemented cache checking before API calls
          - ✓ Store results with appropriate TTL based on content type
        - [x] Update agent implementations:
          - ✓ Updated TravelPlanningAgent and DestinationResearchAgent to use wrapper
          - ✓ Updated TravelAgent to use CachedWebSearchTool instead of WebSearchTool
          - ✓ Removed domain configurations (not supported by OpenAI SDK)
        - [x] Add configuration settings:
          - ✓ Configured TTL settings in centralized configuration
          - ✓ Enabled runtime TTL adjustments without code changes
        - [x] Add comprehensive tests:
          - ✓ Created validation tests for code structure
          - ✓ Verified integration in both agents

    - [x] Implement WebOperationsCache for Web Operations (Issue #38):
      - **Target:** Advanced caching system for TripSage web operations
      - **Goal:** Create a centralized, content-aware caching system for all web operation tools
      - **Status:** Implemented core functionality, requires integration testing
      - **Resources:**
        - **Redis Client Docs:** https://redis-py.readthedocs.io/en/stable/
        - **OpenAI Agents SDK:** https://openai.github.io/openai-agents-python/
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
        - [x] Update Agent Implementations: (Completed)
          - [x] Replace WebSearchTool with CachedWebSearchTool in TravelPlanningAgent
            - Implementation complete using src/agents/travel_planning_agent.py
          - [x] Replace WebSearchTool with CachedWebSearchTool in DestinationResearchAgent
            - Implementation complete using src/agents/destination_research_agent.py
          - [x] Replace WebSearchTool with CachedWebSearchTool in TravelAgent
            - Updated src/agents/travel_agent.py to use cached version
          - [ ] Apply web_cached decorator to appropriate web operation functions
            - Add to existing webcrawl operations in both agents
            - Add performance monitoring hooks for cache hit rate analysis
      - [x] Implementation Timeline: (Completed)
        - [x] Phase 1: Core WebOperationsCache implementation
        - [x] Phase 2: Metrics and tool integration
        - [x] Phase 3: Testing and implementation
        - [x] Phase 4: Agent integration (Completed)
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
      - [x] Integrate Playwright MCP (see Playwright MCP Integration)
        - ✓ Implemented PlaywrightMCPClient with core browser operations
        - ✓ Created agent-callable tools in browser_tools.py
        - ✓ Added proper error handling and logging
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
    - [x] Implement unified abstraction layer for all MCP interactions:
      - ✓ Created Manager/Registry pattern with type-safe wrappers
      - ✓ Implemented standardized error handling with custom exceptions
      - ✓ Developed dependency injection support for FastAPI and similar frameworks
      - ✓ Created BaseMCPWrapper abstract class for consistent interface
      - ✓ Implemented MCPManager for centralized lifecycle management
      - ✓ Created MCPClientRegistry for dynamic wrapper registration
      - ✓ Added automatic registration of default wrappers on import
      - ✓ Provided examples for PlaywrightMCP, GoogleMapsMCP, and WeatherMCP
      - ✓ Core components reimplemented (2025-01-16):
        - ✓ BaseMCPWrapper with updated method signatures
        - ✓ MCPClientRegistry singleton implementation
        - ✓ MCPManager with configuration loading
        - ✓ Custom exception hierarchy under TripSageMCPError
      - ✓ Specific wrapper implementations (2025-01-16):
        - ✓ PlaywrightMCPWrapper with standardized method mapping
        - ✓ GoogleMapsMCPWrapper with comprehensive mapping for maps APIs
        - ✓ WeatherMCPWrapper with weather service method mapping
        - ✓ Automatic registration in registration.py
        - ✓ Example refactored tool (weather_tools_abstraction.py)
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
    - [x] Create additional MCP wrappers for remaining clients:
      - [x] SupabaseMCPWrapper for database operations
      - [x] Neo4jMemoryMCPWrapper for knowledge graph operations
      - [x] DuffelFlightsMCPWrapper for flight search and booking
      - [x] AirbnbMCPWrapper for accommodation search
      - [x] FirecrawlMCPWrapper for web crawling
      - [x] Crawl4AIMCPWrapper for AI-powered web crawling
      - [x] TimeMCPWrapper for timezone operations
      - [x] GoogleCalendarMCPWrapper for calendar integration
      - [x] RedisMCPWrapper for caching operations
      - [x] CachedWebSearchToolWrapper for web search with caching
    - [ ] Refactor all agent tools to use MCPManager.invoke:
      - [x] Update browser_tools.py to use PlaywrightMCPWrapper
      - [x] Update googlemaps_tools.py to use GoogleMapsMCPWrapper
      - [x] Update weather_tools.py to use WeatherMCPWrapper
      - [x] Update flight_tools.py to use DuffelFlightsMCPWrapper
      - [x] Update accommodation_tools.py to use AirbnbMCPWrapper
      - [x] Update webcrawl_tools.py to use Firecrawl/Crawl4AI wrappers
      - [x] Update time_tools.py to use TimeMCPWrapper
      - [x] Update calendar_tools.py to use GoogleCalendarMCPWrapper
      - [x] Update supabase_tools.py to use SupabaseMCPWrapper
      - [x] Update memory_tools.py to use Neo4jMemoryMCPWrapper
    - [ ] Implement monitoring and observability:
      - Add OpenTelemetry instrumentation for MCP interactions
      - Create performance metrics for MCP operations
      - Implement structured logging for all MCP interactions
    - [x] Remove redundant implementations after external MCP integration
      - ✓ Deleted entire src/mcp/ directory
      - ✓ All functionality migrated to new abstraction layer
    - [x] Ensure proper use of Pydantic V2 patterns in remaining MCP clients
    - [x] Create proper factory patterns for all MCP clients
    - [x] Standardize configuration across all clients
    - [x] Migrate essential clients to tripsage/clients/ directory
    - [x] Implement comprehensive test suite for each client

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

- [ ] **Optimize Cache Implementation via Redis MCP**

  - **Target:** Redis MCP integration
  - **Goal:** Standardize caching across clients using Redis MCP
  - **Context:** Old generic caching in `/src/cache/redis_cache.py` deprecated in favor of:
    - WebOperationsCache for web-specific caching (already implemented)
    - Redis MCP for generic caching (to be implemented)
  - **Tasks:**
    - [ ] Complete Redis MCP client implementation in RedisMCPWrapper
    - [ ] Create generic `cached()` decorator using Redis MCP
    - [ ] Implement standard cache key generation utility via MCP
    - [ ] Implement TTL management based on data type
    - [ ] Add cache invalidation patterns
    - [ ] Migrate cache hit/miss statistics to Redis MCP
    - [ ] Implement cache prefetching for common queries
    - [ ] Create cache warming strategies
    - [ ] Add distributed cache locking via Redis MCP
    - [ ] Implement typed cache interface using MCP patterns

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
      - Create tripsage/models/db/ for essential business models (User, Trip)
      - Port validation logic from src/db/models/ to new Pydantic models
      - Replace repository patterns with MCP tool implementations
      - Adapt SQL migrations to use Supabase MCP apply_migration
      - Create Neo4j schema initialization scripts
      - Ensure consistent error handling through MCP abstraction
      - Remove direct database connection pooling (handled by MCPs)
    - [ ] API Improvements:
      - Add OpenAPI documentation
      - Implement API versioning
      - Add proper rate limiting
      - Implement comprehensive logging
      - Add request validation with Pydantic
    - [x] Neo4j Database Improvements:
      - ✓ Standardized Neo4j query patterns through Memory MCP tools
      - ✓ Implemented proper transaction handling via MCP abstraction
      - ✓ Created Neo4j schema management system in tripsage/db/migrations/neo4j/
      - ✓ Ported constraint and index definitions from src/db/neo4j/migrations/
      - ✓ Implemented initialization logic using Memory MCP operations
      - ✓ Added domain-specific memory tools for complex entity relationships
      - ✓ Migrated domain schemas to appropriate tool schemas
      - ✓ Implemented proper error handling for Neo4j operations

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

| Task                            | Status | PR  | Notes                                                                                          |
| ------------------------------- | ------ | --- | ---------------------------------------------------------------------------------------------- |
| Calendar Tools Refactoring      | ✅     | #87 | Applied error handling decorator pattern                                                       |
| Flight Search Refactoring       | ✅     | #88 | Applied error handling decorator to four methods                                               |
| Error Handling Tests            | ✅     | #88 | Created standalone tests for decorator functionality                                           |
| Accommodations Refactoring      | ✅     | #89 | Applied error handling decorator to two methods                                                |
| MCP Client Standardization      | ✅     | #90 | Implemented client factory pattern, improved error handling                                    |
| MCP Factory Pattern             | ✅     | #90 | Created standard factory interface + implementations for Time & Flights                        |
| MCP Error Classification        | ✅     | #90 | Added error categorization system for better error handling                                    |
| MCP Documentation               | ✅     | #90 | Added comprehensive README for MCP architecture                                                |
| Dual Storage Service            | ✅     | #91 | Created DualStorageService base class with standard CRUD operations                            |
| Trip Storage Service            | ✅     | #91 | Implemented TripStorageService with Pydantic validation                                        |
| Fix Circular Imports            | ✅     | #92 | Fixed circular imports in base_mcp_client.py and decorators.py                                 |
| Isolated Test Patterns          | ✅     | #93 | Created environment-independent test suite for dual storage services                           |
| Comprehensive Test Coverage     | ✅     | #93 | Added tests for abstract interfaces and error handling                                         |
| MCP Isolated Testing            | ✅     | #94 | Implemented isolated testing pattern for MCP clients                                           |
| MCP Testing Documentation       | ✅     | #94 | Created documentation for isolated MCP testing pattern                                         |
| Tool Registration Logic         | ✅     | #95 | Simplified tool registration with automatic discovery                                          |
| Parameter Validation            | ✅     | #95 | Centralized parameter validation with Pydantic base models                                     |
| Service Pattern Extraction      | ✅     | #95 | Extracted common service patterns for MCP implementations                                      |
| Codebase Restructuring - Part 1 | ✅     | -   | Updated tool imports, migrated all agent files and tools                                       |
| Browser Tools Migration         | ✅     | -   | Updated browser tools with correct imports and tools registration                              |
| Codebase Restructuring - Part 2 | 🔄     | -   | Remaining import updates and test updates in progress                                          |
| OpenAI Agents SDK Integration   | 🔄     | -   | Research completed, implementation planning in progress                                        |
| Pydantic V2 Migration           | 📅     | -   | Scheduled to start after Codebase Restructuring is complete                                    |
| External MCP Server Strategy    | ✅     | -   | Completed evaluation of MCP servers and established hybrid approach                            |
| Supabase MCP Integration        | 📅     | -   | Scheduled to start after Codebase Restructuring is complete                                    |
| Neo4j Memory MCP Integration    | 📅     | -   | Prioritized for knowledge graph implementation                                                 |
| Travel Data MCP Integration     | 📅     | -   | Duffel Flights MCP and Airbnb MCP identified for travel data access                            |
| Playwright MCP Integration      | ✅     | -   | Implemented core client and agent-callable tools                                               |
| Crawl4AI MCP Integration        | ✅     | -   | Implemented client with WebSocket/SSE support, caching, and comprehensive tests                |
| Firecrawl MCP Integration       | ✅     | -   | Implemented client with specialized booking site optimization and caching                      |
| Hybrid Web Crawl Schema         | ✅     | -   | Created UnifiedCrawlResult model for consistent output across crawlers                         |
| Result Normalizer               | ✅     | -   | Implemented normalize methods for both Firecrawl and Crawl4AI outputs                          |
| Source Selection Logic          | ✅     | -   | Implemented domain routing and content-type based crawler selection                            |
| Unified Crawl Interface         | ✅     | -   | Created crawl_website_content with automatic crawler selection                                 |
| Playwright MCP Fallback         | ✅     | -   | Enhanced hybrid crawling with Playwright fallback and direct selection                         |
| Playwright Result Normalizer    | ✅     | -   | Added normalize_playwright_mcp_output for browser-based crawling                               |
| Playwright-only Domains         | ✅     | -   | Added support for direct Playwright selection for specific domains                             |
| Google Maps MCP Integration     | ✅     | -   | Implemented GoogleMaps MCP client wrapper and refactored googlemaps_tools.py to use MCPManager |
| Time MCP Integration            | ✅     | -   | Implemented Time MCP client wrapper and refactored time_tools.py to use MCPManager             |
| WebSearchTool Caching           | ✅     | -   | Implemented CachedWebSearchTool wrapper with content-aware caching                             |
| MCP Abstraction Layer           | ✅     | -   | Implemented Manager/Registry pattern with type-safe wrappers                                   |
| Specific MCP Wrappers           | ✅     | -   | Implemented Supabase, Neo4j Memory, Duffel Flights, and Airbnb wrappers                        |
