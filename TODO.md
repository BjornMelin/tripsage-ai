# TripSage Refactoring TODO List

This TODO list outlines refactoring opportunities to simplify the TripSage AI codebase following KISS/DRY/YAGNI/SIMPLE principles. The goal is to eliminate redundancy, improve maintainability, and ensure adherence to project standards.

## Coding Standards Reference

- **Python 3.12** with PEP-8 (88-char lines max)
- Type hints are mandatory
- Run `ruff check --select I --fix .` for import sorting
- Run `ruff check . --fix` and `ruff format .` on touched files
- Files should be ≤350 LoC (hard cap: 500)
- Test coverage target: ≥90%

## System Gaps Analysis

- [ ] **UI Gaps - Not Leveraging Full Capabilities**

  - Missing personalized recommendations from memory-mcp
  - No timezone-aware scheduling with time-mcp
  - Weather data not integrated into trip planning
  - No automated price monitoring with browser-mcp
  - Missing version control for itineraries
  - No real-time agent workflow visualization

- [ ] **Backend Gaps - Missing Integrations**

  - Incomplete memory-mcp implementation for learning
  - No browser automation for price tracking
  - Missing GitHub integration for itinerary versioning
  - Limited use of perplexity-mcp for research
  - No firecrawl deep research implementation

- [ ] **Database Gaps - Required Tables**
  - Missing user_preferences for personalization
  - No search_history for recommendations
  - Missing price_alerts table
  - No agent_interactions tracking
  - Missing group collaboration tables

## API and Middleware Tasks

- ✅ API consolidation completed (May 20, 2025) - See PR #91 and [tasks/COMPLETED-TODO.md](./tasks/COMPLETED-TODO.md)
- The database migration is in progress - See "Database Migration" section below
- For remaining API, MCP, and Middleware related tasks, see [tasks/TODO-API.md](./tasks/TODO-API.md)

## MVP Priority (Version 1.0)

- [ ] **Frontend-Backend BYOK Integration**

  - **Target:** Full-stack secure API key management
  - **Goal:** Create seamless, secure API key management across frontend and backend
  - **Status:** Architecture and specifications completed
  - **Key Documents:**
    - Backend implementation details: TODO.md (Backend BYOK section)
    - Frontend implementation details: TODO-FRONTEND.md (API Key Management section)
    - Architecture documentation: docs/frontend/ARCHITECTURE.md
  - **Integration Points:**
    - API endpoints: `/api/user/keys` (CREATE, LIST, DELETE, VALIDATE, ROTATE)
    - Envelope encryption: PBKDF2 + Fernet (AES-128 CBC + HMAC-SHA256)
    - Key validation: Service-specific patterns on frontend, comprehensive checks on backend
    - Status display: Comprehensive UI without revealing actual keys
    - Security features: Auto-clearing forms, session timeouts, CSP headers
  - **Next Steps:**
    - [ ] Implement backend encryption service with envelope pattern
    - [ ] Create FastAPI endpoints with proper authentication
    - [ ] Build React components for secure key input and management
    - [ ] Implement Redis caching for decrypted keys
    - [ ] Add monitoring and alerting for key operations
    - [ ] Create comprehensive test suite for security features

- [x] **Backend BYOK (Bring Your Own Key) Implementation**

  - **Target:** Backend API and database layer
  - **Goal:** Implement secure API key storage and usage for user-provided keys
  - **Status:** Implemented in FastAPI structure
  - **Tasks:**
    - [x] Create API key models and database schema:
      - [x] Add key rotation support with rotation schedule
      - [x] Implement secure key validation before storage
    - [x] Create key encryption service using envelope encryption:
      - [x] Add key rotation support with rotation schedule
      - [x] Implement secure key validation before storage
    - [x] Implement API endpoints:
      - [x] GET `/api/user/keys` - List available keys (without values)
      - [x] DELETE `/api/user/keys/{id}` - Remove a stored key
      - [x] POST `/api/user/keys/validate` - Validate a key with service
      - [x] POST `/api/user/keys/{id}/rotate` - Rotate an existing key
    - [x] Update MCPManager for user keys:
      - [x] Implement dynamic key injection for MCP calls
      - [x] Add fallback to default keys when user keys unavailable
      - [x] Create secure caching mechanism for decrypted keys
    - [x] Add monitoring and security:
      - [x] Implement access logging with structured logs:
      - [x] Add rate limiting for key operations (max 10 per minute)
      - [x] Create alerts for suspicious patterns:
        - Rapid key rotation attempts
        - Failed validation attempts
        - Unusual access patterns
      - [x] Implement key expiration notifications
      - [x] Add automatic key rotation reminders (90 days)
      - [x] Create key health metrics dashboard
    - [x] Security best practices:
      - [x] Use secure random for all salt generation
      - [x] Clear sensitive data from memory after use
      - [x] Implement proper session timeouts
      - [x] Add audit trail for all key operations
      - [x] Use constant-time comparison for key validation
      - [x] Implement proper error handling without information leakage
    - [ ] Frontend Integration:
      - [x] Frontend AI chat interface completed (Vercel AI SDK v4.3.16)
      - [ ] Coordinate with frontend BYOK implementation in TODO-FRONTEND.md
      - [ ] Connect chat interface to backend endpoints
      - [ ] Ensure API endpoints match frontend expectations
      - [ ] Implement CORS configuration for secure key submission
      - [ ] Add rate limiting middleware for key endpoints
      - [ ] Document API integration for frontend developers
      - **Reference**: See tasks/TODO-INTEGRATION.md for remaining steps

- [ ] **Complete Codebase Restructuring (Issue #31)**

  - **Target:** Throughout codebase
  - **Goal:** Consolidate application logic into the `tripsage/` directory
  - **Tasks:**

    - [ ] Update tests to match new structure (Issue #31):

      ### Phase 1: Test Infrastructure Setup

      - [ ] Set up test configuration for mocking MCPManager
      - [ ] Create integration test directory for end-to-end scenarios
      - [ ] **BLOCKER**: Resolve circular import issues with MCP abstraction layer
      - [ ] **BLOCKER**: Handle environment variable dependencies for tests
      - [ ] **BLOCKER**: Fix Redis URL dependency in cache initialization

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
    - [ ] Handle src/types/supabase.ts TypeScript file
      - Option 1: Delete if no frontend planned
      - Option 2: Move to docs/schemas/ for reference
    - [ ] Remove empty src/ directory once fully cleaned
    - [ ] Documentation updates:
      - Update README.md to reflect new structure
      - Add directory structure documentation
      - Create migration guide for developers

  - [ ] Frontend Application Development:
    - [ ] Phase 1: Foundation & Core Setup
      - [ ] Initialize Next.js 15 with App Router
      - [ ] Configure TypeScript 5.0+ with strict mode
      - [ ] Set up Tailwind CSS v4 with OKLCH colors
      - [ ] Install and configure shadcn/ui components
      - [ ] Create root layout with theme support
      - [x] Implement Zustand stores for state management (User, Trip, Chat, Agent status, Search, Budget, Currency, Deals, API Key)
      - [ ] Set up React Query for server state
      - [ ] Configure Vercel AI SDK v5
      - [ ] Create base UI components library
      - [ ] Set up development environment with Turbopack
    - [ ] Phase 2: Authentication & Security (BYOK)
      - [ ] Build secure API key management interface (BYOK)
      - [ ] Create key submission component with auto-clear functionality
      - [ ] Implement client-side key validation patterns
      - [ ] Create comprehensive key status display (without revealing keys)
      - [ ] Add key rotation dialogs with expiration warnings
      - [ ] Implement secure session management with shorter timeouts
      - [ ] Create CSP headers for sensitive pages
      - [ ] Build audit log visualization components
    - [x] Phase 3: AI Chat Interface (COMPLETED)
      - [x] Implement chat UI with Vercel AI SDK v4.3.16
      - [x] Add streaming responses with typing indicators
      - [x] Create rich content rendering (markdown, code)
      - [x] Build message history with search
      - [x] Add file and image upload capabilities
      - [ ] Implement voice input/output support (scheduled for integration)
      - [x] Create conversation management
      - [ ] Add chat export functionality (scheduled for integration)
      - **Status**: Frontend implementation complete
      - **Next**: Backend integration (see tasks/TODO-INTEGRATION.md)
    - [x] Phase 4: Error Boundaries & Loading States (COMPLETED)
      - [x] Implement Next.js 15 App Router error boundaries (error.tsx, global-error.tsx)
      - [x] Create production-ready error reporting with errorService
      - [x] Build comprehensive loading states using CVA (class-variance-authority)
      - [x] Develop travel-specific skeleton components (flights, hotels, trips)
      - [x] Add route-level loading states (loading.tsx files)
      - [x] Create error fallback components with recovery options
      - [x] Implement comprehensive test suite with 90%+ coverage
      - [x] Integrate enhanced testing infrastructure (Vitest UI + Coverage + Playwright)
      - **Status**: Production-ready error handling and loading states complete
      - **Architecture**: CVA-based components, errorService pattern, Next.js 15 best practices
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
    - [ ] Delete old src/db/ directory after migration completion

- [ ] **Integrate External MCP Servers**

  - **Target:** MCP server architecture and implementation
  - **Goal:** Adopt a hybrid approach favoring external MCPs when possible
  - **Strategy:**
    - Prioritize existing external MCPs when available
    - Only build custom MCPs for core business logic, direct database integration, or when privacy/security requirements can't be met externally
  - **Tasks:**
    - **Sub-tasks for further enhancements:**
      - [ ] Configure production OpenTelemetry exporter (OTLP)
      - [ ] Implement advanced error alerting based on error types
      - [ ] Integrate structlog more deeply if PoC is successful
      - [ ] Add metrics collection for MCP performance
      - [ ] Create dashboards for monitoring MCP operations
    - [ ] Playwright MCP Integration:
      - [ ] Implement session persistence for authenticated workflows
      - [ ] Develop travel-specific browser operations (booking verification, check-ins)
      - [ ] Create escalation logic from crawler to browser automation
      - [ ] Add anti-detection capabilities for travel websites
      - [ ] Implement comprehensive testing with mock travel websites
    - [ ] Hybrid Web Crawling Integration:
      - [ ] Develop empirical performance testing framework
      - [ ] Production Scenario Testing Strategy: - Create test suite with real-world travel planning scenarios - Develop 10+ realistic multi-site test cases covering booking flows and research patterns - Implement automated performance comparison between single-crawler and hybrid approach - Create a/b testing framework to empirically verify domain routing effectiveness - Implement monitoring for crawler selection decisions - Add telemetry for source selection logic - Create dashboard for crawler performance by domain - Set up alerting for fallback escalation patterns - Establish quantitative success metrics - 95%+ successful extractions across tracked domains - <3 second average response time for cached results - <8 second average for uncached results - <5% fallback rate to Playwright for optimized domains
    - [x] Redis MCP Integration: (Completed)
      - **Target:** Distributed caching for performance optimization
      - **Goal:** Improve response times and reduce API call volumes
      - **Success Metrics:**
        - 99.9% cache operation reliability
        - <50ms average cache operation time
        - 90%+ cache hit rate for common operations
        - Proper TTL management across content types
      - **Resources:**
        - **Server Repo:** <https://github.com/redis/mcp-redis>
        - **Redis Docs:** <https://redis.io/docs/>
      - ✅ Configured Redis MCP server
      - ✅ Created comprehensive caching tools in `tripsage/utils/cache_tools.py`
      - ✅ Implemented distributed caching with TTL based on content type
      - ✅ Added distributed locking for coordinated cache operations
      - ✅ Implemented batch operations for improved performance
      - ✅ Added cache warming/prefetching capabilities
      - ✅ Created comprehensive tests for cache-related operations
    - [x] Applied web_cached decorator to web operation functions
      - ✅ Added to existing webcrawl operations in CachedWebSearchTool
      - ✅ Enhanced web_tools.py with comprehensive caching
      - ✅ Implemented batch_web_search for optimized performance
      - ✅ Added performance monitoring hooks for cache hit rate analysis

- [ ] **MCP Implementation Roadmap**

  - **Target:** Phased MCP integration
  - **Goal:** Implement MCP integration in structured phases
  - **Status:** Several key MCPs already integrated, continuing with remaining components
  - **Tasks:**
    - [x] Completed Integrations:
      - ✅ Integrated Google Maps MCP for location services
      - ✅ Integrated Weather MCP for trip planning data
      - ✅ Implemented hybrid web crawling with Crawl4AI & Firecrawl
      - ✅ Integrated Time MCP for timezone and clock operations
      - ✅ Implemented WebSearchTool caching with WebOperationsCache
      - ✅ Developed unified abstraction layer via MCPManager
      - ✅ Implemented error handling and monitoring infrastructure
      - ✅ Integrated Neo4j Memory MCP
      - ✅ Integrated Duffel Flights MCP for flight search
      - ✅ Integrated Airbnb MCP for accommodation search
    - [ ] Current Focus (Next 2 Weeks):
      - Continue developing the Unified Travel Search Wrapper
      - ✅ Implement Redis MCP for standardized response caching
      - ✅ Integrate Supabase MCP for relational database operations
      - Integrate Google Calendar MCP for itinerary scheduling
      - Create domain-specific performance testing framework
      - Complete comprehensive error handling for all integrated MCPs
    - [x] MCP Server Strategy Implementation:
      - ✅ Created unified launcher (scripts/mcp_launcher.py)
      - ✅ Standardized MCP server scripts to use mcp_launcher.py
      - ✅ Implemented Docker-Compose integration for all services
      - [ ] Next steps: Remove any redundant individual start/stop scripts
    - [ ] Medium-Term Actions (Weeks 7-12):
      - Develop Trip Planning Coordinator and Content Aggregator wrappers
      - Implement OpenTelemetry-based monitoring for all MCP interactions
      - Complete thorough integration testing across all MCPs
      - Optimize performance through Redis MCP caching and parallel execution
      - Complete production scenario testing for all integrations

- [ ] **MCP Client Cleanup**

  - **Target:** `/tripsage/clients/` directory
  - **Goal:** Replace redundant MCP client implementations with external MCP servers
  - **Strategy:** Follow hybrid approach - prioritize external MCPs, build custom only when necessary
  - **Tasks:**
    - [ ] Audit `tripsage/clients/` to identify functionality covered by external MCPs:
      - Map current clients to Supabase, Neo4j Memory, Duffel Flights, Airbnb MCPs
      - Map webcrawl functionality to hybrid Crawl4AI/Firecrawl implementation with domain-based routing
      - Map browser automation needs to Playwright MCP
      - Map Google Maps, Time, Weather, Google Calendar, and Redis MCPs
      - Document any functionality requiring custom implementations
      - Map specific correspondences:
        - `tripsage/clients/weather/` → Weather MCP
        - `tripsage/clients/accommodations.py` → Airbnb MCP
        - `tripsage/clients/flights.py` → Duffel Flights MCP
        - `tripsage/clients/webcrawl/` → Hybrid Crawl4AI/Firecrawl MCP
        - `tripsage/utils/cache.py` → Redis MCP
    - [x] Implement Redis MCP for standardized caching:
      - ✅ Configured Redis MCP server with appropriate connection parameters
      - ✅ Created cache key generation that respects parameters
      - ✅ Implemented TTL management based on data type (shorter for prices, longer for destination info)
      - ✅ Added cache invalidation patterns based on travel dates and data changes
      - ✅ Developed comprehensive monitoring for cache hit/miss rates
    - [ ] Refactor all agent tools to use MCPManager.invoke:
    - [ ] Implement monitoring and observability:
      - Add OpenTelemetry instrumentation for MCP interactions
      - Create performance metrics for MCP operations
      - Implement structured logging for all MCP interactions

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
    - [x] Enhance and optimize agent handoff implementation:
      - [x] Update implementation plan with latest SDK best practices
      - [x] Emphasize decentralized handoff pattern as recommended by OpenAI
      - [x] Add error handling and fallback mechanisms
      - [x] Include tracing and debugging capabilities
      - [x] Document comprehensive test strategies
    - [ ] Implement remaining handoff configuration:
      - [ ] Standardize handoff methods across agents
      - [ ] Implement context passing between agents
      - [ ] Create proper initialization in handoff list
      - [ ] Add robust error handling with fallbacks
    - [ ] Implement guardrails:
      - Add input validation on all tools
      - Implement standardized safety checks
      - Create comprehensive logging for tool usage
    - [ ] Improve conversation history management:
      - Implement proper conversation storage
      - Create efficient context retrieval methods
      - Ensure consistent memory integration

- [x] **Implement Neo4j Knowledge Graph Integration (using Neo4j Memory MCP)**
  - **Target:** Throughout codebase
  - **Goal:** Standardize Neo4j integration using Neo4j Memory MCP server
  - **Status:** Core integration completed, enhancing with additional features
  - **Tasks:**
    - [x] Set up Neo4j Memory MCP server configuration
    - [x] Define standard entity models compatible with MCP schema
    - [x] Create reusable CRUD operations using MCP tools
    - [x] Implement graph query patterns via MCP integration
    - [x] Define relationship type constants in knowledge graph schema
    - [x] Create standard validation for MCP-based graph operations
    - [ ] Implement advanced caching for Neo4j Memory MCP operations
    - [ ] Enhance comprehensive test suite for Neo4j MCP integration
    - [ ] Create dual storage pattern with Supabase and Neo4j

## Medium Priority

- [x] **Optimize Cache Implementation via Redis MCP**

  - **Target:** Redis MCP integration
  - **Goal:** Standardize caching across clients using Redis MCP
  - **Context:** Generic caching in `tripsage/utils/cache.py` to be enhanced with:
    - WebOperationsCache for web-specific caching (already implemented)
    - Redis MCP for generic caching (now implemented)
  - **Tasks:**
    - [x] Complete Redis MCP client implementation in RedisMCPWrapper
    - [x] Create generic `cached()` decorator using Redis MCP
    - [x] Implement standard cache key generation utility via MCP
    - [x] Implement TTL management based on data type
    - [x] Add cache invalidation patterns
    - [x] Migrate cache hit/miss statistics to Redis MCP
    - [x] Implemented cache prefetching for common queries
    - [x] Created cache warming strategies
    - [x] Added distributed cache locking via Redis MCP
    - [x] Implemented typed cache interface using MCP patterns

- [ ] **Library Modernization**

  - **Target:** Throughout codebase
  - **Goal:** Adopt high-performance libraries
  - **Tasks:**
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
    - [x] Implement Redis MCP Integration:
      - ✅ Standardized caching across applications
      - ✅ Created comprehensive cache tools
      - ✅ Implemented TTL management by content type
      - ✅ Added cache invalidation patterns
      - ✅ Implemented distributed locking for cache operations
      - ✅ Added batch operations for performance optimization

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

- [ ] **Database Migration**

  - **Target:** `/tripsage/api/` directory and database implementation
  - **Goal:** Complete the database migration following API consolidation
  - **Status:** API consolidation completed on May 20, 2025 (PR #91), database migration in progress
  - **Tasks:**
    - [ ] Implement database migration:
      - [x] Create tripsage/models/db/ for essential business models (User, Trip)
      - [x] Port validation logic to new Pydantic V2 models with field_validator
      - [ ] Replace repository patterns with MCP tool implementations
      - [ ] Adapt SQL migrations to use Supabase MCP apply_migration
      - [ ] Create Neo4j schema initialization scripts
      - [ ] Ensure consistent error handling through MCP abstraction
      - [ ] Remove direct database connection pooling (handled by MCPs)

- [ ] **Frontend Application Development**
  - [ ] Phase 1: Foundation & Core Setup (see TODO-FRONTEND.md)
    - [ ] Project initialization with Next.js 15.3
    - [ ] Development environment setup
    - [ ] Core dependencies installation
    - [ ] Tailwind CSS v4 configuration
    - [ ] shadcn/ui v3 setup
  - [ ] Phase 2: Authentication & Security (see TODO-FRONTEND.md)
    - [ ] Integrate with backend BYOK implementation
    - [ ] Create secure key management components
    - [ ] Implement service-specific validation
    - [ ] Build comprehensive status displays

## Low Priority

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

## Detailed Implementation Plans

### MVP Frontend Implementation (Version 1.0)

- **Target:** Modern, AI-centric frontend implementation
- **Goal:** Build state-of-the-art frontend with Next.js 15, React 19, and Tailwind CSS v4
- **Key Technologies:**
  - Next.js 15.3.1 with App Router
  - React 19.1.0 with Server Components
  - TypeScript 5.5+ (strict mode)
  - Tailwind CSS v4.0 with OKLCH colors
  - Zustand v5.0.4 for state management
  - TanStack Query v5 for data fetching
  - Vercel AI SDK v5 for AI streaming

**Implementation Phases:**

1. **Phase 1: Foundation (Weeks 1-2)**

   - [ ] Initialize Next.js 15.3.1 project
   - [ ] Configure TypeScript and ESLint 9
   - [ ] Set up Tailwind CSS v4 with OKLCH
   - [ ] Install and configure shadcn/ui v3
   - [ ] Implement authentication with Supabase

2. **Phase 2: Component Library (Weeks 3-4)**

   - [ ] Build core UI components
   - [ ] Create feature-specific components
   - [ ] Implement loading states and skeletons
   - [ ] Design notification system
   - [ ] Build data visualization components

3. **Phase 3: Core Features (Weeks 5-8)**

   - [ ] Trip planning workflows
   - [ ] Search and discovery interface
   - [ ] AI chat with streaming (Vercel AI SDK)
   - [ ] Booking flows
   - [ ] User profile management
   - [ ] Budget tracking dashboard
   - [ ] Expense management system

4. **Phase 4: Budget Features (Weeks 9-12)**

   - [ ] Price prediction engine
   - [ ] Fare alert system
   - [ ] Group cost splitting
   - [ ] Alternative routing (hidden city, split tickets)
   - [ ] Currency converter and fee calculator
   - [ ] Deals aggregation platform
   - [ ] Community savings tips system
   - [ ] Budget templates and tracking

5. **Phase 5: Advanced Features (Weeks 13-16)**

   - [ ] Real-time updates with SSE
   - [ ] Collaborative planning features
   - [ ] Advanced data visualization
   - [ ] Performance optimizations
   - [ ] Code splitting and lazy loading

6. **Phase 6: Enhancement (Weeks 17-20)**

   - [ ] Progressive Web App features
   - [ ] Service worker implementation
   - [ ] Internationalization (i18n)
   - [ ] Advanced security (BYOK UI)
   - [ ] Comprehensive testing

7. **Phase 7: Polish & Launch (Weeks 21-24)**
   - [ ] User experience refinements
   - [ ] Analytics and monitoring
   - [ ] Performance audit
   - [ ] Production deployment
   - [ ] Documentation completion

### Codebase Restructuring (Issue #31)

- **Target:** Core application logic
- **Goal:** Move all application logic to `tripsage/` directory with consistent patterns
- **Implementation Phases:**

1. **Phase 1: Core Components** (In Progress)

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

### Next Release Features (Version 2.0)

- **Target:** Advanced features and enterprise capabilities
- **Goal:** Build comprehensive collaborative, intelligent travel platform
- **Key Enhancements:**
  - Group travel and expense splitting
  - Price prediction and monitoring
  - Advanced personalization with AI learning
  - Complete MCP server coverage
  - Mobile application support

**Implementation Phases:**

1. **Phase 1: Collaborative Features (Months 4-5)**

   - [ ] Group trip planning interface
   - [ ] Real-time expense splitting
   - [ ] Shared itinerary management
   - [ ] Voting and decision systems
   - [ ] Activity feed for group updates

2. **Phase 2: Intelligence Layer (Months 6-7)**

   - [ ] Price prediction algorithms
   - [ ] Fare alert system
   - [ ] Learning user preferences
   - [ ] AI recommendation engine
   - [ ] Alternative routing finder

3. **Phase 3: Platform Expansion (Months 8-9)**
   - [ ] Mobile app development (React Native)
   - [ ] PWA capabilities
   - [ ] Offline support
   - [ ] Advanced MCP integrations
   - [ ] Enterprise features

### Database Requirements

- **Target:** Complete database schema implementation
- **Goal:** Support all MVP features with scalable architecture
- **MVP Tables Required:**
  - users (authentication, profiles)
  - api_keys (BYOK storage)
  - trips (trip planning)
  - trip_items (flights, hotels, activities)
  - budgets (budget tracking)
  - expenses (expense management)
  - chat_sessions (AI interactions)

**Implementation Tasks:**

1. **Core Tables Creation**

   - [ ] Implement users table with OAuth support
   - [ ] Create api_keys table with encryption fields
   - [ ] Design trips table with status tracking
   - [ ] Build trip_items with flexible JSON storage
   - [ ] Implement budgets with category support

2. **Relationships and Indices**

   - [ ] Add foreign key constraints
   - [ ] Create composite indices for queries
   - [ ] Implement soft delete support
   - [ ] Add audit timestamps

3. **Next Release Tables (v2.0)**
   - [ ] user_preferences (personalization)
   - [ ] search_history (recommendations)
   - [ ] price_alerts (monitoring)
   - [ ] groups (collaboration)
   - [ ] shared_expenses (splitting)
   - [ ] agent_interactions (tracking)

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

| Task                            | Status | PR  | Notes                                                               |
| ------------------------------- | ------ | --- | ------------------------------------------------------------------- |
| Codebase Restructuring - Part 2 | 🔄     | -   | Remaining import updates and test updates in progress               |
| OpenAI Agents SDK Integration   | 🔄     | -   | Research completed, implementation planning in progress             |
| Pydantic V2 Migration           | 📅     | -   | Scheduled to start after Codebase Restructuring is complete         |
| Supabase MCP Integration        | 📅     | -   | Scheduled to start after Codebase Restructuring is complete         |
| Neo4j Memory MCP Integration    | 📅     | -   | Prioritized for knowledge graph implementation                      |
| Travel Data MCP Integration     | 📅     | -   | Duffel Flights MCP and Airbnb MCP identified for travel data access |
