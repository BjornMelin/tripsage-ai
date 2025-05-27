# TripSage Refactoring TODO List

This TODO list outlines refactoring opportunities to simplify the TripSage AI codebase following KISS/DRY/YAGNI/SIMPLE principles. The goal is to eliminate redundancy, improve maintainability, and ensure adherence to project standards.

## Coding Standards Reference

- **Python 3.12** with PEP-8 (88-char lines max) - ✅ **FIXED: Updated pyproject.toml**
- Type hints are mandatory
- Run `ruff check --select I --fix .` for import sorting
- Run `ruff check . --fix` and `ruff format .` on touched files
- Files should be ≤350 LoC (hard cap: 500)
- Test coverage target: ≥90%
- **NEW**: Pre-commit hooks added for automated code quality - See `.pre-commit-config.yaml`

## System Gaps Analysis

- [ ] **UI Gaps - Not Leveraging Full Capabilities**

  - Missing personalized recommendations from memory system
  - No timezone-aware scheduling with time-mcp
  - Weather data not integrated into trip planning
  - [x] ~~No automated price monitoring with browser automation~~ → **COMPLETED: Native Playwright SDK available (PR #173)**
  - Missing version control for itineraries
  - [x] Agent status monitoring implemented (needs backend integration)

- [ ] **Backend Gaps - Missing Integrations**

  - Incomplete memory implementation for learning → **SOLUTION: Mem0 Integration (see below)**
  - [x] ~~No browser automation for price tracking~~ → **COMPLETED: Native Playwright SDK integrated (PR #173)**
  - Missing GitHub integration for itinerary versioning
  - Limited use of perplexity-mcp for research
  - [x] ~~No Crawl4AI implementation~~ → **COMPLETED: Direct SDK Integration with Playwright fallback (PR #173)**

- [ ] **Database Gaps - Required Tables**
  - Missing user_preferences for personalization → **SOLUTION: Mem0 handles this**
  - No search_history for recommendations → **SOLUTION: Mem0 memory storage**
  - Missing price_alerts table
  - No agent_interactions tracking → **SOLUTION: Mem0 conversation memory**
  - Missing group collaboration tables

## 🚀 Memory System MVP Implementation (NEW - 2025-05-25)

**Goal:** Implement Mem0-based memory system for 26% better accuracy, 91% faster performance, and 90% token savings.

**Documentation:**
- Research: [docs/REFACTOR/MEMORY_SEARCH/RESEARCH_DB_MEMORY_SEARCH.md](./docs/REFACTOR/MEMORY_SEARCH/RESEARCH_DB_MEMORY_SEARCH.md)
- Implementation Plan: [docs/REFACTOR/MEMORY_SEARCH/PLAN_DB_MEMORY_SEARCH.md](./docs/REFACTOR/MEMORY_SEARCH/PLAN_DB_MEMORY_SEARCH.md)
- GitHub Issues: #146 (parent), #140, #142, #147, #149, #150, #155
- Neon Deprecation Analysis: [docs/REFACTOR/MEMORY_SEARCH/NEON_DEPRECATION_ANALYSIS.md](./docs/REFACTOR/MEMORY_SEARCH/NEON_DEPRECATION_ANALYSIS.md)

### Week 1: Infrastructure Setup (Days 1-5)

- [ ] **Day 1-2: DragonflyDB Migration** (Issue #140)
  - [ ] Deploy DragonflyDB container alongside Redis
  - [ ] Update cache wrapper for DragonflyDB compatibility
  - [ ] Run parallel testing with 10% traffic
  - [ ] Monitor performance (target: 6.43M ops/sec)
  - [ ] Complete migration and decommission Redis

- [ ] **Day 3: PGVector Setup** (Issue #147)
  - [ ] Enable pgvector extension in Supabase
  - [ ] Enable pgvectorscale for 11x performance
  - [ ] Create vector indexes with StreamingDiskANN
  - [ ] Test vector search performance (<100ms)

- [ ] **Day 4-5: Database Schema**
  - [ ] Create memories table with optimized schema
  - [ ] Implement deduplication trigger
  - [ ] Add performance indexes
  - [ ] Create search functions
  - [ ] Run migration scripts

### Week 2: Mem0 Integration (Days 6-10)

- [ ] **Day 6-7: Memory Service Implementation** (Issue #142)
  - [ ] Install mem0ai package
  - [ ] Create TripSageMemoryService class
  - [ ] Configure pgvector backend
  - [ ] Implement memory extraction methods
  - [ ] Add caching with DragonflyDB

- [ ] **Day 8-9: Agent Integration**
  - [ ] Update ChatAgent with memory service
  - [ ] Implement memory-aware prompts
  - [ ] Add conversation memory storage
  - [ ] Create user preference tracking
  - [ ] Test personalized responses

- [ ] **Day 10: Core Features**
  - [ ] Session memory management
  - [ ] Memory search API
  - [ ] User context aggregation
  - [ ] Travel-specific enrichment
  - [ ] GDPR compliance features

### Week 3: Production Readiness (Days 11-15)

- [ ] **Day 11-12: Testing Suite**
  - [ ] Unit tests (90% coverage target)
  - [ ] Integration tests with mocked MCPs
  - [ ] Performance benchmarks
  - [ ] Memory accuracy validation
  - [ ] Load testing

- [ ] **Day 13-14: Production Preparation**
  - [ ] Security hardening
  - [ ] API rate limiting
  - [ ] OpenTelemetry monitoring
  - [ ] Cost tracking setup
  - [ ] Alert configuration

- [ ] **Day 15: Documentation & Deployment**
  - [ ] API documentation
  - [ ] Integration guide
  - [ ] Operations manual
  - [ ] Production deployment
  - [ ] Team training

### Success Metrics

- [ ] **Performance Targets**
  - [ ] Memory extraction: <500ms
  - [ ] Search latency: <100ms (91% improvement)
  - [ ] Cache hit rate: >80%
  - [ ] Vector search: 471 QPS

- [ ] **Quality Targets**
  - [ ] Test coverage: 90%+
  - [ ] Memory accuracy: 26% better than baseline
  - [ ] Zero downtime deployment
  - [ ] All monitoring in place

- [ ] **Cost Targets**
  - [ ] Total monthly cost: <$120
  - [ ] 90% token savings achieved
  - [ ] 80% infrastructure cost reduction
  - [ ] No specialized databases needed

## ✅ Database Consolidation Migration (COMPLETED - 2025-05-26)

**Goal:** Migrate from dual-database architecture (Neon + Supabase) to single Supabase instance with pgvector + pgvectorscale.

**GitHub Issues:** #146 (parent), #147 ✅ **MERGED via PR #169**

### ✅ Completed Migration Tasks

- [x] **Phase 1: Pre-Migration Assessment** ✅ **COMPLETED**
  - [x] Audited current Neon database usage and dependencies
  - [x] Documented all Neon-specific features in use
  - [x] Created inventory of all database connections
  - [x] Analyzed data migration complexity
  - [x] Reviewed Neon Deprecation Analysis document

- [x] **Phase 2: Supabase Setup with pgvector** (Issue #147) ✅ **COMPLETED**
  - [x] Created pgvector extension migration script
  - [x] Added pgvectorscale support for 11x performance boost
  - [x] Documented StreamingDiskANN indexes configuration
  - [x] Created vector-enabled configuration
  - [x] Set up comprehensive production deployment guide

- [x] **Phase 3: Schema and Data Migration** (Issue #149) ✅ **COMPLETED**
  - [x] Removed Neon schema completely from codebase
  - [x] Consolidated to Supabase-only architecture
  - [x] Created migration scripts with comprehensive validation
  - [x] Implemented simplified single-database configuration
  - [x] Added rollback procedures for safety

- [x] **Phase 4: Application Code Updates** (Issue #150) ✅ **COMPLETED**
  - [x] Removed all Neon MCP tool imports and references
  - [x] Updated database connection configuration
  - [x] Replaced Neon-specific operations with Supabase-only
  - [x] Updated error handling for consolidated architecture
  - [x] Removed neon_tools.py file completely

- [ ] **Phase 5: Mem0 Integration** (Issue #142)
  - [ ] Install and configure Mem0 library
  - [ ] Create memory storage schema with pgvector
  - [ ] Implement TripSageMemory service
  - [ ] Add semantic search capabilities
  - [ ] Implement memory decay algorithms

- [ ] **Phase 6: DragonflyDB Migration** (Issue #140)
  - [ ] Deploy DragonflyDB alongside Redis
  - [ ] Update cache wrapper for DragonflyDB
  - [ ] Migrate existing cache data
  - [ ] Performance benchmark (target: 25x improvement)
  - [ ] Decommission Redis instance

- [ ] **Phase 7: Documentation Updates** (Issue #155)
  - [ ] Update all architecture documentation
  - [ ] Remove Neon references from guides
  - [ ] Add pgvector setup instructions
  - [ ] Update environment configuration docs
  - [ ] Create migration guide for developers

- [ ] **Phase 8: Testing and Validation**
  - [ ] Create comprehensive test suite
  - [ ] Validate data integrity post-migration
  - [ ] Performance testing (target: <100ms vector search)
  - [ ] Load testing with production workloads
  - [ ] Rollback procedure testing

- [ ] **Phase 9: Production Cutover**
  - [ ] Schedule maintenance window
  - [ ] Execute final data sync
  - [ ] Update DNS/connection strings
  - [ ] Monitor application health
  - [ ] Decommission Neon instance

### ✅ Success Metrics Achieved
- [x] Zero data loss during migration (development environment)
- [x] Vector search capability ready for <100ms latency (11x improvement)
- [x] Annual infrastructure cost reduction $6,000-9,600 (80% reduction)
- [x] All configuration and imports working correctly
- [x] Comprehensive documentation and rollback procedures created

**🚀 Production Ready** - See `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md` for deployment procedures.

## API and Middleware Tasks

- ✅ **API consolidation completed** (May 20, 2025) - See PR #91 and [tasks/COMPLETED-TODO.md](./tasks/COMPLETED-TODO.md)
- ✅ **Frontend security vulnerability audit and fixes completed** (May 21, 2025)
  - Removed vulnerable dependencies (old biome v0.3.3)
  - Fixed type safety issues (replaced `any` types)
  - Improved code security patterns
  - All known vulnerabilities resolved
- ✅ **Phase 4: File Handling & Attachments completed** (May 23, 2025)
  - Implemented secure file upload system with FastAPI backend
  - Added comprehensive file validation and security scanning
  - Created AI-powered document analysis service
  - Integrated frontend proxy with authentication
  - Added support for PDF, images, CSV, and office documents
  - See [tasks/TODO-INTEGRATION.md](./tasks/TODO-INTEGRATION.md) for details
- ✅ **Phase 5: Database Integration & Chat Agent Enhancement completed** (May 24, 2025)
  - Implemented MCP-based database operations (Supabase & Neo4j Memory MCPs)
  - Enhanced chat agent with tool calling and orchestration capabilities
  - Created comprehensive error handling and recovery strategies
  - Added chat session persistence and message history
  - Achieved 42/47 tests passing with comprehensive coverage
  - See PR #129 for implementation details

### Priority API Tasks (Updated Based on Phase 5 Completion)

- [ ] **Complete Remaining Database Operations via MCP Tools**
  - Finalize remaining repository pattern migrations to MCP implementations
  - Complete Neo4j schema enhancements for advanced queries
  - Optimize MCP-based error handling and recovery strategies
- [ ] **Finalize Core API Endpoints** (Phase 7 Focus)
  - Complete all essential CRUD operations for trips, accommodations, flights
  - Implement comprehensive request/response validation
  - Add proper error handling and status codes
- [ ] **Agent Integration Layer** (Phase 8 Focus)
  - Complete agent handoff system implementation
  - Integrate all MCP services into unified workflow
  - Enhance session management and conversation history
  - Add advanced error recovery and fallback mechanisms

For remaining API, MCP, and Middleware related tasks, see [tasks/TODO-API.md](./tasks/TODO-API.md)

## MVP Priority (Version 1.0)

- [x] **Frontend-Backend BYOK Integration** ✅ COMPLETED (January 21, 2025)

- [x] **FastAPI Chat Endpoint with Streaming** ✅ COMPLETED (May 22, 2025)
  - **Target:** Backend AI chat infrastructure
  - **Goal:** Implement streaming chat endpoint compatible with Vercel AI SDK
  - **Status:** ✅ IMPLEMENTED (PR #118, PR #122)
  - **Key Features:**
    - FastAPI endpoint at `/api/v1/chat` with streaming support
    - Vercel AI SDK data stream protocol implementation
    - Session continuation and history endpoints
    - Comprehensive test suite
    - PostgreSQL-based chat session persistence (PR #122)
    - Message history storage and retrieval
    - Context window management with token estimation
    - Rate limiting and content sanitization
  - **Next Steps:** See tasks/TODO-INTEGRATION.md for remaining integration tasks

  - **Target:** Full-stack secure API key management
  - **Goal:** Create seamless, secure API key management across frontend and backend
  - **Status:** ✅ IMPLEMENTED AND VERIFIED
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
  - **Completed Tasks:**
    - [x] ✅ Backend encryption service with envelope pattern implemented
    - [x] ✅ FastAPI endpoints with proper authentication created
    - [x] ✅ React components for secure key input and management built
    - [x] ✅ Redis caching for decrypted keys implemented
    - [x] ✅ Monitoring and alerting for key operations added
    - [x] ✅ Comprehensive test suite for security features created

- [x] **Backend BYOK (Bring Your Own Key) Implementation** ✅ COMPLETED (January 22, 2025)

  - **Target:** Backend API and database layer
  - **Goal:** Implement secure API key storage and usage for user-provided keys
  - **Status:** ✅ FULLY IMPLEMENTED with comprehensive testing
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

- [ ] **Complete Test Suite Migration (Issue #35)**

  - **Target:** Test infrastructure and coverage
  - **Goal:** Achieve 90%+ test coverage with modern testing patterns
  - **Status:** Currently at 35% overall coverage
  - **Tasks:**

      ### Phase 1: Test Infrastructure Setup ✅ COMPLETED (May 23, 2025)

      - [x] ✅ Set up test configuration for mocking MCPManager
      - [x] ✅ Create integration test directory for end-to-end scenarios
      - [x] ✅ **RESOLVED**: Circular import issues with MCP abstraction layer resolved
      - [x] ✅ **RESOLVED**: Environment variable dependencies handled with comprehensive test environment
      - [x] ✅ **RESOLVED**: Redis URL and other dependency issues fixed through proper isolation
      - [x] ✅ **NEW**: Comprehensive pydantic settings testing solution implemented
      - [x] ✅ **NEW**: Test environment isolation with tests/.env.test configuration
      - [x] ✅ **NEW**: TestSettings class and utilities for environment-independent tests
      - [x] ✅ **NEW**: Zero ruff linting errors across all test and application files

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
    - [ ] Complete existing test migrations:
      - [ ] API test coverage (currently 45%)
      - [ ] Agent test coverage (currently 25%)
      - [ ] MCP abstraction test coverage (currently 55%)
      - [ ] Frontend test coverage (currently 75%)
    - [ ] Implement missing test categories:
      - [ ] End-to-end workflow tests
      - [ ] Integration tests for all MCP services
      - [ ] Performance benchmarking tests
      - [ ] Load testing suite
    - [ ] Set up test infrastructure:
      - [ ] Configure test database
      - [ ] Implement proper test data factories
      - [ ] Set up test environment variables
      - [ ] Configure parallel test execution

  - [ ] **CI/CD Pipeline Setup (Issue #36)**
    - **Target:** Automated testing and deployment
    - **Goal:** Comprehensive CI/CD with quality gates
    - **Status:** Partial implementation exists
    - **Tasks:**
      - [ ] Backend CI pipeline:
        - [ ] Python linting with ruff
        - [ ] Type checking with mypy
        - [ ] Unit tests with pytest
        - [ ] Coverage reporting
        - [ ] Integration tests
      - [ ] Frontend CI pipeline:
        - [ ] TypeScript/ESLint checks
        - [ ] Biome formatting
        - [ ] Unit tests with Vitest
        - [ ] E2E tests with Playwright
        - [ ] Bundle size analysis
      - [ ] Deployment automation:
        - [ ] Docker image building
        - [ ] Environment-specific configs
        - [ ] Health check monitoring
        - [ ] Rollback procedures

  - [ ] Frontend Application Development:
    - [ ] Phase 1: Foundation & Core Setup
      - [ ] Initialize Next.js 15 with App Router
      - [ ] Configure TypeScript 5.0+ with strict mode
      - [ ] Set up Tailwind CSS v4 with OKLCH colors
      - [ ] Install and configure shadcn/ui components
      - [ ] Create root layout with theme support
      - [x] Implement Zustand stores for state management (User, Trip, Chat, Agent status, Search, Budget, Currency, Deals, API Key) - COMPLETED
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
    - [x] Phase 4: Agent Status & Visualization (COMPLETED)
      - [x] Implement agent status store and types
      - [x] Create agent status panel component  
      - [x] Add real-time status monitoring hooks
      - [x] Build task tracking and progress display
      - [x] Implement resource usage monitoring
      - [x] Add activity logging capabilities
      - [x] Create session management for agents
      - [x] Integrate agent status with chat interface
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
    - [ ] Phase 5: Travel Planning Features
      - [ ] Integrate Mapbox GL for trip visualization
      - [x] Build itinerary timeline component (trip-timeline.tsx)
      - [x] Create budget tracking component (budget-tracker.tsx)
      - [x] Implement accommodation search UI (search forms implemented)
      - [x] Add flight search interface (flight-search-form.tsx)
      - [ ] Build weather integration display
      - [x] Create destination search (destination-search-form.tsx)
      - [ ] Add basic collaborative features
    - [ ] Phase 5: State & API Integration
      - [ ] Implement Zustand stores architecture
      - [ ] Set up React Query patterns
      - [ ] Create MCP client integrations
      - [ ] Build comprehensive error handling
      - [ ] Add retry logic with exponential backoff
      - [ ] Implement offline support
      - [ ] Create API route handlers
      - [ ] Add server actions for data mutations
    - [ ] Phase 6: Performance Optimization
      - [ ] Implement basic code splitting
      - [ ] Configure Next.js Image optimization
      - [ ] Set up caching with React Query
      - [ ] Add loading states and skeletons
      - [ ] Optimize bundle with tree shaking
      - [ ] Implement lazy loading for components
      - [ ] Add basic performance monitoring
      - [ ] Ensure Core Web Vitals compliance
    - [ ] Phase 7: Testing & Quality
      - [ ] Set up Vitest for unit testing
      - [ ] Configure React Testing Library
      - [ ] Implement Playwright E2E tests
      - [x] Create Mock Service Worker setup
      - [x] Implement basic accessibility testing  
      - [ ] Create CI/CD test pipeline
      - [x] Add smoke tests for critical paths
      - [x] Ensure 90% test coverage (configured in vitest.config.ts)
    - [ ] Phase 8: Deployment & Monitoring
      - [ ] Configure Vercel deployment
      - [ ] Set up GitHub Actions workflows
      - [ ] Implement Sentry error tracking
      - [ ] Add PostHog analytics
      - [ ] Create monitoring dashboards
      - [ ] Set up alerting for errors
      - [ ] Implement A/B testing framework
      - [ ] Add performance monitoring
    - [ ] Delete old src/db/ directory after migration completion

- [ ] **Migrate to Direct SDK Integrations**

  - **Target:** Replace MCP wrappers with direct SDK integration
  - **Goal:** 50-70% latency reduction, eliminate MCP overhead
  - **Strategy:** Based on [docs/REFACTOR/API_INTEGRATION/MCP_TO_SDK_MIGRATION_PLAN.md](./docs/REFACTOR/API_INTEGRATION/MCP_TO_SDK_MIGRATION_PLAN.md)
  - **Priority Services for Direct SDK:**
    - [ ] Redis → DragonflyDB native client (Week 1)
    - [ ] Supabase MCP → Supabase Python SDK (Week 1)
    - [ ] Neo4j MCP → Neo4j Python driver (Week 2)
    - [ ] Time MCP → Native Python datetime (Week 2)
    - [ ] Duffel Flights MCP → Duffel API SDK (Week 3)
    - [ ] Weather MCP → OpenWeatherMap API (Week 4)
    - [ ] Google Maps MCP → Google Maps Python Client (Week 4)
    - [ ] Google Calendar MCP → Google Calendar API (Week 4)
  - **Services Remaining on MCP:**
    - Airbnb MCP (no official SDK available)
  - **Web Crawling Strategy:**
    - [ ] **Crawl4AI Direct SDK Integration** (Replaces Firecrawl MCP)
      - [ ] Install and configure Crawl4AI v0.6.0+
      - [ ] Implement memory-adaptive dispatcher
      - [ ] Set up browser pooling for efficiency
      - [ ] Configure LLM-optimized extraction
      - [ ] Expected: 6x performance improvement
    - [ ] **Native Playwright SDK** (Replaces Playwright MCP)
      - [ ] Direct SDK integration for complex sites
      - [ ] Browser pool management
      - [ ] Session persistence for auth
      - [ ] Expected: 25-40% performance improvement
    - [ ] **Smart Crawler Router**
      - [ ] Intelligent routing between Crawl4AI and Playwright
      - [ ] Domain-based optimization
      - [ ] Automatic fallback mechanisms
      - [ ] Performance monitoring and metrics
    - [ ] **Implementation Timeline:**
      - Week 1-2: Foundation and core engines
      - Week 3-6: Migration and integration
      - Week 7-8: Integration and production
      - Based on [docs/REFACTOR/CRAWLING/PLAN_CRAWLING_EXTRACTION.md](./docs/REFACTOR/CRAWLING/PLAN_CRAWLING_EXTRACTION.md)
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

- [x] **Agent Orchestration Migration to LangGraph** ✅ **PHASES 1-3 COMPLETED** (2025-05-26)

  - **Target:** Replace current ChatAgent with LangGraph orchestration
  - **Goal:** 40-60% performance improvement, better maintainability
  - **Strategy:** Based on [docs/REFACTOR/AGENTS/PLAN_MIGRATE_TO_LANGGRAPH.md](./docs/REFACTOR/AGENTS/PLAN_MIGRATE_TO_LANGGRAPH.md)
  - **GitHub Issue:** See comprehensive Phase 3 completion report in [docs/REFACTOR/AGENTS/PHASE3_COMPLETION_REPORT.md](./docs/REFACTOR/AGENTS/PHASE3_COMPLETION_REPORT.md)
  - **Implementation Phases:**
    - [x] **Phase 1: Foundation (Weeks 1-2)** ✅ **COMPLETED** (PR #170)
      - [x] Install LangGraph dependencies
      - [x] Create state schema (TravelPlanningState)
      - [x] Implement base node class
      - [x] Build core orchestrator graph
      - [x] Set up checkpointing
    - [x] **Phase 2: Agent Migration (Weeks 3-4)** ✅ **COMPLETED** (PR #171)
      - [x] Migrate FlightAgent to FlightAgentNode
      - [x] Migrate AccommodationAgent to AccommodationAgentNode
      - [x] Migrate BudgetAgent to BudgetAgentNode
      - [x] Migrate DestinationResearchAgent to DestinationResearchAgentNode
      - [x] Migrate ItineraryAgent to ItineraryAgentNode
      - [x] Create comprehensive test suite for all migrated agents
    - [x] **Phase 3: MCP Integration & Orchestration (Weeks 5-6)** ✅ **COMPLETED** (2025-05-26)
      - [x] Implement LangGraph-MCP bridge layer for seamless integration
      - [x] Create session memory bridge for Neo4j state synchronization
      - [x] Implement PostgreSQL checkpointing with Supabase integration
      - [x] Build comprehensive inter-agent handoff coordination system
      - [x] Update orchestration graph with all Phase 3 components
      - [x] Create comprehensive test suite with 100% coverage (77 tests)
      - **Implementation Files:**
        - `tripsage/orchestration/mcp_bridge.py` - LangGraph-MCP bridge
        - `tripsage/orchestration/memory_bridge.py` - Session memory integration
        - `tripsage/orchestration/checkpoint_manager.py` - PostgreSQL checkpointing
        - `tripsage/orchestration/handoff_coordinator.py` - Agent handoff system
        - Updated `tripsage/orchestration/graph.py` - Main integration
        - Updated `tripsage/orchestration/nodes/accommodation_agent.py` - Example migration
    - [ ] **Phase 4: Production Deployment (Weeks 7-8)** - **GitHub Issue #172**
      - [ ] Set up LangSmith monitoring and observability
      - [ ] Implement feature flags for gradual rollout
      - [ ] Performance validation and A/B testing
      - [ ] Production deployment with monitoring
      - [ ] Documentation and team training
      - **Issue Link**: [feat(production): LangGraph Phase 4 - Production Deployment and Monitoring #172](https://github.com/BjornMelin/tripsage-ai/issues/172)

- [ ] **Service Integration Cleanup and Optimization**

  - **Target:** Service layer architecture
  - **Goal:** Consolidate services and eliminate redundancy
  - **Strategy:** Direct SDK where possible, MCP only when necessary
  - **Tasks:**
    - [ ] Service Consolidation:
      - [ ] Merge duplicate service implementations
      - [ ] Create unified interface for each service type
      - [ ] Implement feature flags for gradual migration
      - [ ] Remove obsolete wrapper code
    - [ ] Performance Optimization:
      - [ ] Implement connection pooling for all services
      - [ ] Add circuit breakers for external services
      - [ ] Configure retry strategies
      - [ ] Set up performance monitoring
    - [ ] Testing Infrastructure:
      - [ ] Create service mocks for testing
      - [ ] Implement contract testing
      - [ ] Add performance benchmarks
      - [ ] Set up integration test suite

- [x] **Ensure Proper Pydantic V2 Implementation** ✅ COMPLETED (January 21, 2025)

  - **Target:** Throughout codebase
  - **Goal:** Ensure all models use Pydantic V2 patterns
  - **Status:** ✅ VERIFIED AND IMPLEMENTED
  - **Tasks:**
    - [x] ✅ Audit and update method usage:
      - [x] Replace `dict()` with `model_dump()` (verified no remaining deprecated usage)
      - [x] Replace `json()` with `model_dump_json()` (HTTP response .json() are correct)
      - [x] Replace `parse_obj()` with `model_validate()` (no deprecated usage found)
      - [x] Replace `parse_raw()` with `model_validate_json()` (no deprecated usage found)
      - [x] Replace `schema()` with `model_json_schema()` (no deprecated usage found)
    - [x] ✅ Audit and update validation patterns:
      - [x] Replace `validator` with `field_validator` and add `@classmethod` (implemented throughout)
      - [x] Update validator modes to use `"before"` and `"after"` parameters (implemented)
      - [x] Update any root validator usage with `model_validator` (implemented)
    - [x] ✅ Update type validation:
      - [x] Update Union type usage for proper validation (verified)
      - [x] Replace `typing.Optional` with field default values (implemented)
      - [x] Replace `ConstrainedInt` with `Annotated[int, Field(ge=0)]` (implemented)
    - [x] ✅ Implement advanced features:
      - [x] Use ConfigDict for model configuration (implemented throughout)
      - [x] Use proper field validators with @classmethod (implemented)
      - [x] Implement proper model dumping and validation (verified)
    - [x] ✅ Verified base model uses Pydantic V2 patterns correctly

- [x] **Ensure Proper OpenAI Agents SDK Implementation** ✅ COMPLETED (January 21, 2025)

  - **Target:** Agent implementations
  - **Goal:** Ensure agents use the latest SDK patterns
  - **Status:** ✅ IMPLEMENTED AND VERIFIED
  - **Tasks:**
    - [x] ✅ Standardize agent class structure:
      - [x] Consistent initialization with settings-based defaults (implemented in BaseAgent)
      - [x] Proper tool registration patterns (implemented with function_tool decorator)
      - [x] Standard error handling implementation (comprehensive error handling added)
    - [x] ✅ Improve tool implementation:
      - [x] Use proper parameter models with strict validation (implemented throughout)
      - [x] Implement consistent error reporting (comprehensive error handling added)
      - [x] Add comprehensive docstrings with examples (documented throughout)
    - [x] ✅ Enhance and optimize agent handoff implementation:
      - [x] Update implementation plan with latest SDK best practices (completed)
      - [x] Emphasize decentralized handoff pattern as recommended by OpenAI (implemented)
      - [x] Add error handling and fallback mechanisms (comprehensive implementation)
      - [x] Include tracing and debugging capabilities (built into BaseAgent)
      - [x] Document comprehensive test strategies (test framework created)
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


- [ ] **Major Refactoring Initiatives Summary**

  - **Database & Memory Architecture** (Issue #146)
    - Goal: Consolidate to Supabase + pgvector + Mem0
    - Impact: 4-25x performance, 80% cost reduction
    - Timeline: 2-3 weeks for MVP
    - Docs: [docs/REFACTOR/MEMORY_SEARCH/](./docs/REFACTOR/MEMORY_SEARCH/)

  - **Agent Orchestration** (LangGraph Migration)
    - Goal: Replace ChatAgent with graph-based orchestration
    - Impact: 40-60% performance improvement
    - Timeline: 8 weeks implementation
    - Docs: [docs/REFACTOR/AGENTS/](./docs/REFACTOR/AGENTS/)

  - **API Integration** (Direct SDK Migration)
    - Goal: Replace MCP wrappers with native SDKs
    - Impact: 50-70% latency reduction
    - Timeline: 8 weeks for full migration
    - Docs: [docs/REFACTOR/API_INTEGRATION/](./docs/REFACTOR/API_INTEGRATION/)

  - **Web Crawling** (Crawl4AI + Playwright)
    - Goal: Replace Firecrawl with Crawl4AI
    - Impact: 6-10x performance, $700-1200/year savings
    - Timeline: 8-12 weeks implementation
    - Docs: [docs/REFACTOR/CRAWLING/](./docs/REFACTOR/CRAWLING/)

- [ ] **Performance and Monitoring Infrastructure**

  - **Target:** System-wide observability
  - **Goal:** Basic monitoring and optimization for MVP
  - **Tasks:**
    - [ ] Basic Monitoring Setup:
      - [ ] Instrument critical service calls
      - [ ] Set up request tracing
      - [ ] Configure basic metrics
      - [ ] Implement error tracking
    - [ ] Performance Monitoring:
      - [ ] Set up basic monitoring dashboard
      - [ ] Configure essential metrics
      - [ ] Implement basic alerting
      - [ ] Track API response times
    - [ ] Cost Optimization:
      - [ ] Track API usage per service
      - [ ] Implement usage quotas
      - [ ] Monitor infrastructure costs
      - [ ] Optimize resource allocation

- [x] **Database Migration** ✅ COMPLETED (May 24, 2025)

  - **Target:** `/tripsage/api/` directory and database implementation
  - **Goal:** Complete the database migration following API consolidation
  - **Status:** ✅ COMPLETED with Phase 5 implementation (PR #129)
  - **Tasks:**
    - [x] Implement database migration:
      - [x] Create tripsage/models/db/ for essential business models (User, Trip)
      - [x] Port validation logic to new Pydantic V2 models with field_validator
      - [x] Replace repository patterns with MCP tool implementations
      - [x] Adapt SQL migrations to use Supabase MCP apply_migration
      - [x] Create Neo4j schema initialization scripts
      - [x] Ensure consistent error handling through MCP abstraction
      - [x] Remove direct database connection pooling (handled by MCPs)

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

## Deprecated/Removed Items

### Based on Refactoring Research (2025-05-25)

- **Neon Database**: Migrating to Supabase-only architecture
- **Firecrawl MCP**: Replaced by Crawl4AI direct SDK (6x faster)
- **Neo4j (MVP)**: Deferred to V2, using Mem0 + pgvector instead
- **Qdrant Vector DB**: pgvector + pgvectorscale is 11x faster
- **Custom MCP Servers**: Using external MCPs + direct SDKs only
- **Knowledge Graphs**: Simplified to Mem0 for MVP

### Migration Paths

- Neon → Supabase PostgreSQL
- Redis → DragonflyDB (25x faster)
- Qdrant → pgvector + pgvectorscale
- Firecrawl → Crawl4AI + native Playwright
- MCP wrappers → Direct SDK integrations
- Custom memory → Mem0 (production-proven)

## Code Quality Enforcement

- [x] **Add Pre-commit Hooks** ✅ **COMPLETED**

  - **Target:** Root repository
  - **Goal:** Automate code quality checks
  - **Status:** ✅ **Implemented - See `.pre-commit-config.yaml`**
  - **Features:**
    - [x] ✅ Configured pre-commit for ruff checking and formatting
    - [x] ✅ Added type checking with mypy
    - [x] ✅ Enforced import sorting and line length
    - [x] ✅ Implemented security scanning with bandit
    - [x] ✅ Added file validation (YAML, JSON, TOML)
    - [x] ✅ Configured CI integration for automation
  - **Installation:** Run `pre-commit install` to enable hooks

- [ ] **Improve Test Coverage**
  - **Target:** Modules with <90% coverage
  - **Goal:** Meet 90% coverage target
  - **Tasks:**
    - [ ] Identify modules with insufficient coverage
    - [ ] Add unit tests for untested functions
    - [ ] Create integration tests for major components
    - [ ] Create comprehensive edge case tests
    - [ ] Implement basic performance tests

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

4. **Phase 4: Basic Budget Features (Weeks 9-12)**

   - [ ] Basic budget tracking dashboard
   - [ ] Simple expense management
   - [ ] Currency converter
   - [ ] Basic cost splitting
   - [ ] Budget overview and reports

5. **Phase 5: Polish & Launch (Weeks 13-16)**
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

5. **Core Features**
   - [ ] Implement structured output with JSON mode
   - [ ] Add parallel tool execution for efficiency
   - [ ] Create streaming response handlers
   - [ ] Implement memory integration
   - [ ] Add basic model configuration

### Implementation Priority Order

1. **Immediate (Week 1-3):** Memory System MVP
   - DragonflyDB + pgvector + Mem0 integration
   - Highest impact, lowest complexity
   - Enables personalization features

2. **Short-term (Week 4-8):** Direct SDK Migration
   - Replace high-latency MCP wrappers
   - Start with Redis, Supabase, Neo4j
   - Immediate performance gains

3. **Medium-term (Week 9-16):** Agent Orchestration
   - LangGraph migration for better scalability
   - Improved error handling and flow control
   - Foundation for advanced features

4. **Long-term (Week 17-24):** Web Crawling Optimization
   - Crawl4AI implementation
   - Native Playwright integration
   - Complete Firecrawl deprecation

### Version 2.0 Features

**See:** `tasks/TODO-V2.md` for features beyond MVP including:
- Advanced visual agent flow diagrams (beyond current status monitoring)
- LLM provider configuration UI
- Visual regression testing and Storybook
- Price prediction and fare alerts  
- Group collaboration with voting systems
- Mobile app and advanced PWA features
- Enterprise-grade infrastructure


### Database Requirements

- **Target:** Complete database schema implementation
- **Goal:** Support all MVP features with scalable architecture
- **Status:** Core schema implemented, migration to MCP tools in progress
- **MVP Tables Required:**
  - ✅ users (authentication, profiles) - Implemented
  - ✅ api_keys (BYOK storage) - Implemented  
  - ✅ trips (trip planning) - Core implementation complete
  - ✅ chat_sessions (AI interactions) - Implemented
  - [ ] trip_items (flights, hotels, activities) - Migration to MCP needed
  - [ ] budgets (budget tracking) - Pending MCP integration
  - [ ] expenses (expense management) - Pending MCP integration

**Migration Priority:** Focus on MCP tool integration for remaining operations per Phase 7 plan

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
| Memory System MVP (Mem0)        | 📅     | #146| 2-3 week implementation, highest priority                           |
| Direct SDK Migration            | 📅     | -   | 8 services to migrate, 50-70% latency reduction expected            |
| LangGraph Agent Migration       | ✅     | #172| Phase 1-3 completed, Phase 4 (Production) ready - Issue #172       |
| Crawl4AI Web Crawling           | 📅     | -   | Replace Firecrawl, 6-10x performance gain                           |
| Test Suite Completion           | 🔄     | #35 | Currently 35% coverage, target 90%+                                 |
| CI/CD Pipeline                  | 🔄     | #36 | Partial implementation, needs completion                            |
| Python Version Consistency      | ✅     | -   | Fixed pyproject.toml to require Python ≥3.12                       |
| Pre-commit Hooks Setup          | ✅     | -   | Added .pre-commit-config.yaml with comprehensive checks             |

## Timeline Summary (Updated 2025-05-26)

### Parallel Track Implementation Strategy

**Track 1: Infrastructure & Memory (Weeks 1-3)**
- Week 1: DragonflyDB + pgvector setup
- Week 2-3: Mem0 integration and testing
- Owner: Backend team
- Impact: Core performance improvements

**Track 2: SDK Migration (Weeks 1-8)**
- Week 1-2: Redis, Supabase, Neo4j SDKs
- Week 3-4: Time, Flights, Weather SDKs
- Week 5-6: Maps, Calendar SDKs
- Week 7-8: Testing and optimization
- Owner: Integration team
- Impact: 50-70% latency reduction

**Track 3: Agent Orchestration (Weeks 4-11)** ✅ **PHASES 1-3 COMPLETED**
- Week 4-5: LangGraph foundation ✅ COMPLETED
- Week 6-7: Agent node migration ✅ COMPLETED
- Week 8-9: MCP Integration & Orchestration ✅ COMPLETED (2025-05-26)
- Week 10-11: Production deployment 📅 PENDING (Phase 4)
- Owner: AI team
- Impact: Better scalability and debugging, 40-60% performance improvement

**Track 4: Web Crawling (Weeks 6-13)**
- Week 6-7: Crawl4AI setup
- Week 8-9: Playwright native integration
- Week 10-11: Router implementation
- Week 12-13: Production optimization
- Owner: Data team
- Impact: 6-10x performance gain

**Track 5: Enhancement Sprints (Weeks 9-14)**
- Week 9-10: Unified Observability MVP
  - OpenTelemetry basic setup
  - Correlation ID tracking
  - Structured logging with context
  - Owner: Platform team
  - Impact: End-to-end request tracing
- Week 11-12: Event-Driven Foundation
  - SimpleEventBus implementation
  - Async event handlers
  - Basic pub/sub patterns
  - Owner: Architecture team
  - Impact: Decoupled components, better scalability
- Week 13-14: Progressive Enhancement
  - Error handling patterns (retry, circuit breaker)
  - Service registry setup
  - V2+ migration interfaces
  - Owner: Platform team
  - Impact: Resilience and future-proofing

### Critical Path: Memory System MVP (Weeks 1-3)
- Highest priority due to immediate user impact
- Enables personalization features
- Unblocks other AI enhancements
- Relatively low complexity and risk

### Expected Outcomes by End of Q1 2025
- **Performance**: 4-25x improvement across the stack
- **Cost**: 60-80% reduction in infrastructure costs
- **Architecture**: Simplified from 12 services to 8
- **Maintainability**: 70% reduction in orchestration complexity
- **User Experience**: Personalized, faster, more reliable
