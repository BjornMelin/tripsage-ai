# TripSage AI Project Context

> **Inheritance**
> This repo inherits the global Simplicity Charter (`~/.claude/CLAUDE.md`),  
> which defines all coding, linting, testing, security and library choices  
> (uv, ruff, Pydantic v2, ≥ 90 % pytest-cov, secrets in .env, etc.).  
> TripSage-specific tasks and progress are tracked in:  
> • `/TODO.md` – main task list  
> • `/tasks/TODO-*.md` – categorized tasks (FRONTEND, INTEGRATION, V2)  
> Always review these files before starting work.

## Project Snapshot

TripSage is an AI travel-planning platform that integrates flight, accommodation and location data,
stores it in **Supabase PostgreSQL with pgvector embeddings** (Mem0 memory system),
and optimizes itineraries against budget & user constraints across sessions.

## Current Status & Priorities (Updated June 6, 2025)

**Completed Components:**

- ✅ Backend architecture consolidation (FastAPI with unified routers)
- ✅ Database schema with PostgreSQL + pgvector (Supabase)
- ✅ Authentication system (JWT-based with BYOK API keys)
- ✅ Memory system integration (Mem0 with pgvector embeddings)
- ✅ LangGraph orchestration (Phase 3 complete)
- ✅ Direct SDK integrations (Duffel, Google Maps, Crawl4AI)
- ✅ DragonflyDB caching layer (fully configured with 25x performance improvement)
- ✅ Backend testing infrastructure (2154 tests, 90%+ coverage achieved)
- ✅ **Frontend Grade A Implementation** - 60-70% complete with modern React 19 + Next.js 15
- ✅ **WebSocket Infrastructure** - Complete client (804 lines) and backend infrastructure ready
- ✅ **Authentication UI** - Complete JWT-based frontend authentication system
- ✅ **Agent Monitoring Dashboard** - Revolutionary real-time interface ready for connection

**Critical Security Issues Identified:**

- 🚨 **Hardcoded JWT Secret**: Production middleware.ts contains fallback secret (IMMEDIATE FIX REQUIRED)
- 🚨 **Authentication Disconnect**: Frontend JWT system not connected to backend
- 🚨 **Missing Backend Routers**: activities.py and search.py endpoints missing

**Immediate Priorities (Week 1):**

1. **CRITICAL**: Remove hardcoded JWT fallback secret from production code
2. **HIGH**: Connect frontend authentication to backend JWT service  
3. **HIGH**: Add missing backend routers (activities.py, search.py)
4. **HIGH**: Fix 527 failing tests due to Pydantic v1→v2 migration
5. **MEDIUM**: Connect WebSocket real-time features (infrastructure ready)

**Production Readiness Status**: 75% complete, blocked by authentication integration and security fixes

## MCP Tool Integration & Auto-Invocation

### 🎯 TripSage-Specific Tool Patterns

**Travel Domain Auto-Invocations:**
```
Query Analysis for Travel Context:
├── "flight", "airline", "airport" → mcp__exa__github_search("flight API integration")
├── "hotel", "accommodation", "Airbnb" → mcp__firecrawl__firecrawl_deep_research("accommodation API best practices")
├── "location", "places", "maps" → mcp__context7__get-library-docs("google-maps")
├── "weather", "forecast" → mcp__tavily__tavily-search("weather API " + location)
├── "itinerary", "trip planning" → mcp__clear-thought__sequentialthinking("trip optimization algorithm")
└── "budget", "cost optimization" → mcp__stochasticthinking__stochasticalgorithm("bandit", budget_constraints)
```

**MCP Integration Status:**
- **Currently Active**: Only `airbnb-mcp` remains (via MCP wrapper)
- **Migrated to SDKs**: Duffel (flights), Google Maps, OpenWeatherMap, Google Calendar, Crawl4AI, Playwright
- **Available for Development**: All standard MCP tools (context7, exa, tavily, firecrawl, etc.)

_Note: Most domain-specific MCPs have been migrated to direct SDK integrations for better performance and maintainability._

## Development Workflow with Auto-MCP

1. **Before Starting (Research Phase):**
   - Check your todo list or our `/TODO.md`, `/tasks/TODO-*.md` files for the next task
   - **AUTO-SEARCH**: Based on task keywords, invoke relevant MCP tools:
     - API Integration → `mcp__exa__github_search` + `mcp__context7__get-library-docs`
     - New Feature → `mcp__firecrawl__firecrawl_deep_research` + `mcp__clear-thought__sequentialthinking`
     - Bug Fix → `mcp__tavily__tavily-search` (error) + `mcp__clear-thought__debuggingapproach`
   - Review TODO.md and docs/ with context from searches

2. **During Development (Implementation Phase):**
   - **CODE WITH INTELLIGENCE**: Use search results and examples
   - **AUTO-DEBUG**: On any error, parallel invoke:
     - `mcp__tavily__tavily-search(error_message, time_range="month")`
     - `mcp__context7__get-library-docs(framework, topic="errors")`
     - `mcp__clear-thought__debuggingapproach("binary_search", issue)`
   - **AUTO-OPTIMIZE**: For performance issues:
     - `mcp__stochasticthinking__stochasticalgorithm("bayesian", metrics)`
     - `mcp__firecrawl__firecrawl_deep_research("optimization " + specific_area)`
   - Maintain ≥90% test coverage with patterns from search
   - Run linting: `ruff check . --fix && ruff format .`

3. **After Completing (Validation Phase):**
   - **VERIFY BEST PRACTICES**: Search for similar implementations
   - Document MCP insights in code comments
   - Commit with conventional format

## Memory System (Mem0)

The memory system uses Mem0 with pgvector embeddings in PostgreSQL (no separate graph database).
Memory operations are handled through the `MemoryService` class with automatic vectorization.

## Testing Requirements

- **Unit Tests:** Use pytest with ≥90% coverage
- **Integration Tests:** Test MCP integrations with mocks
- **E2E Tests:** Use Playwright for frontend testing
- **Environment Variables:** Always use `.env.test` for testing - contains mock values for all configurations
- **Always run:** `uv run pytest --cov=tripsage`

## Git Workflow

_Branches_ `main` (protected) · `feature/*` · `fix/*`  
_Commits_ Conventional format — `feat` · `fix` · `docs` · `style` · `refactor`
· `perf` · `test` · `build` · `ci`.

## Agent Pattern Guide with MCP Integration

| Pattern              | When to use                               | Auto-MCP Tool Chain                           |
| -------------------- | ----------------------------------------- | --------------------------------------------- |
| **Single LLM Call**  | Simple, deterministic tasks               | `context7` (docs) → implement                 |
| **Workflow**         | Predictable multi-step jobs               | `sequentialthinking` → `exa` (examples) → code |
| **Autonomous Agent** | Complex, dynamic planning _(last resort)_ | `firecrawl` (research) → `mcts` → `sequentialthinking` |
| **Debug Session**    | MCP integration issues                    | `tavily` (error) → `debuggingapproach` → `context7` |
| **Architecture**     | Agent/service design                      | `mentalmodel` → `exa` (patterns) → `sequentialthinking` |
| **Optimization**     | Cache/performance tuning                  | `stochasticalgorithm` → `aws-docs` → implement |

**Design mantra**: Start simple → add complexity only when required.  
**MCP mantra**: Search comprehensively → think systematically → implement thoughtfully.  
**Parallel mantra**: Always batch related MCP calls for maximum efficiency.

## Security Reminder

Real keys live in `.env`; commit only `.env.example` placeholders.

## Critical Implementation Notes (Updated June 6, 2025)

### 🚨 Security Priority Actions

1. **Immediate Security Fix Required:**
   ```typescript
   // REMOVE this from middleware.ts and server-actions.ts:
   const JWT_SECRET = new TextEncoder().encode(
     process.env.JWT_SECRET || "fallback-secret-for-development-only" // ← SECURITY RISK
   );
   
   // REPLACE with proper environment validation:
   if (!process.env.JWT_SECRET) {
     throw new Error("JWT_SECRET environment variable is required");
   }
   ```

2. **Frontend-Backend Authentication Integration:**
   - Replace mock authentication in `server-actions.ts` with real backend calls
   - Connect frontend JWT middleware to backend authentication service
   - Implement secure token refresh mechanism

### Implementation Workflow Updates

1. **MCP-First Development:** ALWAYS search before implementing:
   - Unknown API → Search with `exa` + `firecrawl`
   - Framework feature → Check `context7` documentation
   - Error/Issue → Search with `tavily` (recent) + `exa` (solutions)

2. **Frontend Development Priorities:**
   - **Quality**: Maintain Grade A implementation standard (currently 60-70% complete)
   - **Integration**: Connect existing UI to backend APIs
   - **Real-time**: Activate WebSocket features (infrastructure ready)
   - **Performance**: Enable React 19 Compiler optimizations

3. **TripSage Current State:**
   - **Frontend**: Grade A React 19 + Next.js 15 implementation ready for production
   - **Backend**: 92% complete, missing 2 routers (activities.py, search.py)
   - **WebSocket**: Complete infrastructure ready for activation
   - **Testing**: 527 failing tests requiring Pydantic v1→v2 migration
   - **Security**: Critical JWT secret vulnerability requires immediate fix

## Quick Reference Paths

- **TODO Files:** `/TODO.md`, `/tasks/TODO-*.md`
- **Documentation:** `/docs/`
- **Implementation Roadmap:** `/docs/research/reviews/implementation-roadmap-2025.md`
- **Frontend Architecture Review:** `/docs/research/reviews/frontend-architecture-review-2025.md`
- **API:** `/tripsage/api/`
- **Frontend:** `/frontend/` (React 19 + Next.js 15, Grade A implementation)
- **Core Services:** `/tripsage_core/services/`
- **Agents/Orchestration:** `/tripsage/orchestration/`
- **MCP Abstraction:** `/tripsage_core/mcp_abstraction/`
- **Tests:** `/tests/` (backend), `/frontend/src/__tests__/` (frontend)

## Common Commands

```bash
# Development
uv run python -m tripsage.api.main  # Start API server
uv run pytest                        # Run tests (527 currently failing - Pydantic v1→v2)
ruff check . --fix && ruff format .  # Lint and format

# Frontend Development
cd frontend
pnpm dev                            # Start Next.js development server
pnpm test                           # Run Vitest tests (85-90% coverage)
pnpm test:e2e                      # Run Playwright E2E tests
npx biome lint --apply .            # Format TypeScript

# Database
uv run python scripts/database/run_migrations.py  # Run migrations

# DragonflyDB
docker run -d --name tripsage-dragonfly -p 6379:6379 \
  docker.dragonflydb.io/dragonflydb/dragonfly:latest \
  --logtostderr --cache_mode --requirepass tripsage_secure_password
uv run python scripts/verification/verify_dragonfly.py  # Verify cache connection

# Security Testing
# IMPORTANT: Verify no hardcoded secrets before commit
git grep -i "fallback-secret\|development-only" .  # Should return empty
```

## TripSage-Specific Cognitive Patterns

### MCP Integration Debugging
When MCP tools fail or behave unexpectedly:
```
→ AUTO-INVOKE: debuggingapproach(reverse_engineering)
→ Analyze MCP protocol traces
→ Isolate integration issues
```

### Agent Orchestration Design
When designing multi-agent workflows:
```
→ AUTO-INVOKE: mentalmodel(first_principles)
→ AUTO-INVOKE: stochasticalgorithm(mcts) for decision trees
→ Document agent handoff patterns
```

### Performance Optimization
For caching strategies or query optimization:
```
→ AUTO-INVOKE: stochasticalgorithm(bandit) for A/B testing
→ AUTO-INVOKE: mentalmodel(pareto_principle) for 80/20 analysis
```

## Current Critical Path Summary

**Week 1 Priorities:**
1. 🚨 **Security Fix**: Remove hardcoded JWT secrets (CRITICAL)
2. 🔗 **Authentication**: Connect frontend to backend JWT service
3. 📡 **Backend APIs**: Add activities.py and search.py routers
4. 🧪 **Testing**: Fix 527 failing tests (Pydantic v1→v2)
5. ⚡ **WebSocket**: Activate real-time features (infrastructure ready)

**Success Metrics:**
- Zero critical security vulnerabilities
- Complete end-to-end authentication flow
- 90%+ test coverage maintained
- Real-time agent monitoring functional
- Grade A frontend quality preserved

_End of TripSage project instructions._
