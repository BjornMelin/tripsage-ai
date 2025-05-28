# TripSage AI Development Priorities

This streamlined TODO list tracks current development priorities for TripSage AI.

## Current Status (2025-05-27)

### ✅ Recently Completed

- **Memory System MVP**: Mem0 integration with 91% faster performance (Issue #142)
- **Database Consolidation**: Migrated to Supabase-only with pgvector (Issue #146)
- **LangGraph Migration**: Phases 1-3 completed (Issues #170, #171)
- **MCP to SDK Migration**: Week 1 completed (Redis/DragonflyDB & Supabase)
- **Frontend Foundation**: Core components and error boundaries implemented
- **API Key Management**: Complete BYOK implementation

### Coding Standards

- Python 3.12, PEP-8 (88-char lines), mandatory type hints
- `ruff check . --fix && ruff format .` on all changes
- Test coverage ≥90%, pre-commit hooks enabled

## High Priority Tasks

### 1. DragonflyDB Migration (Issue #140)

- [ ] Deploy DragonflyDB container alongside Redis
- [ ] Update cache wrapper for DragonflyDB compatibility  
- [ ] Run parallel testing with 10% traffic
- [ ] Monitor performance (target: 6.43M ops/sec)
- [ ] Complete migration and decommission Redis
- **Expected Impact**: 25x performance improvement

### 2. MCP to SDK Migration Completion (Issue #159)

- [ ] **Week 2-4: Remaining Services Migration**
  - [ ] Neo4j direct driver integration
  - [ ] Google Maps Python client
  - [ ] Weather API direct integration
  - [ ] Time service (native Python datetime)
  - [ ] Duffel Flights API SDK
  - [ ] Google Calendar API
  - [ ] Firecrawl → Crawl4AI direct SDK
  - [ ] Playwright native SDK
- **Expected Impact**: 50-70% latency reduction

### 3. LangGraph Production Deployment (Issue #172)

- [ ] Set up LangSmith monitoring and observability
- [ ] Implement feature flags for gradual rollout
- [ ] Performance validation and A/B testing
- [ ] Production deployment with monitoring
- [ ] Documentation and team training
- **Status**: Phases 1-3 completed (foundation, migration, MCP integration)

### 4. Frontend Core Setup

- [ ] Complete Next.js 15 with App Router initialization
- [ ] Implement missing React Query patterns
- [ ] Build comprehensive error handling
- [ ] Add retry logic with exponential backoff
- [ ] Implement offline support

## Medium Priority Tasks

### 5. Complete Test Suite Migration (Issue #35)

- [ ] Migrate remaining agent tests to use tripsage.*
- [ ] Create comprehensive test suite for all modules
- [ ] Ensure 90%+ test coverage
- [ ] Remove obsolete tests
- **Current Status**: 35% overall coverage, targeting 90%+

### 6. Performance and Monitoring Infrastructure

- [ ] Basic monitoring setup with essential metrics
- [ ] Set up request tracing and error tracking
- [ ] Configure basic metrics and alerting
- [ ] Track API usage per service
- [ ] Implement usage quotas

### 7. Database Operations Completion

- [ ] Finalize remaining database operations via direct SDK tools
- [ ] Complete all essential CRUD operations for trips, accommodations, flights
- [ ] Implement comprehensive request/response validation
- [ ] Add proper error handling and status codes

## Low Priority Tasks

### Reference Documentation

- **Completed Work**: See `tasks/COMPLETED-TODO.md` for comprehensive implementation history
- **Frontend Tasks**: See `tasks/TODO-FRONTEND.md` for detailed frontend implementation plans
- **Integration Tasks**: See `tasks/TODO-INTEGRATION.md` for backend-frontend integration work
- **V2 Features**: See `tasks/TODO-V2.md` for post-MVP enhancement features

### 8. Frontend Development (Phase Completion)

- [ ] Complete Next.js 15 foundation setup
- [ ] Implement remaining authentication features
- [ ] Add travel planning UI components
- [ ] Complete API integration and state management

### 9. Code Quality and Testing

- [ ] Refactor function tool signatures and reduce complexity
- [ ] Standardize logging patterns across modules
- [ ] Improve test coverage to ≥90%
- [ ] Split files exceeding 350 LoC

## Implementation Strategy

### Critical Path (Weeks 1-3)

- **DragonflyDB Migration**: 25x performance improvement
- **MCP to SDK Migration**: 50-70% latency reduction
- **LangGraph Production**: Phase 4 deployment (Issue #172)

### Expected Impact

- **Performance**: 4-25x improvement across stack
- **Cost**: 60-80% reduction in infrastructure costs  
- **Architecture**: Simplified from 12 services to 8
- **Maintainability**: 70% reduction in orchestration complexity

## Migration Notes

### Deprecated Technologies (2025-05-27)

- **Neon Database** → Supabase PostgreSQL
- **Firecrawl MCP** → Crawl4AI direct SDK (6x faster)
- **Qdrant Vector DB** → pgvector + pgvectorscale (11x faster)
- **Custom MCP Servers** → External MCPs + direct SDKs only

### Architecture References

For detailed implementation plans, see:

- **Memory System**: `docs/REFACTOR/MEMORY_SEARCH/`
- **Agent Orchestration**: `docs/REFACTOR/AGENTS/`
- **API Integration**: `docs/REFACTOR/API_INTEGRATION/`
- **Web Crawling**: `docs/REFACTOR/CRAWLING/`
