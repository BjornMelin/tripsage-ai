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

## Current Status & Priorities

**Completed Components:**

- ✅ Backend architecture consolidation (FastAPI with unified routers)
- ✅ Database schema with PostgreSQL + pgvector (Supabase)
- ✅ Authentication system (JWT-based with BYOK API keys)
- ✅ Memory system integration (Mem0 with pgvector embeddings)
- ✅ LangGraph orchestration (Phase 3 complete)
- ✅ Direct SDK integrations (Duffel, Google Maps, Crawl4AI)
- ✅ DragonflyDB caching layer (fully configured with 25x performance improvement)
- ✅ Backend testing infrastructure (2154 tests, 90%+ coverage achieved)

**In Progress:**

- 🔄 Frontend authentication integration (UI built, needs connection)
- 🔄 SDK migration completion (only Airbnb MCP remains)
- 🔄 WebSocket real-time features

**Next Priority Tasks:**

1. Complete frontend-backend authentication integration
2. Migrate remaining Airbnb MCP to direct SDK
3. Implement WebSocket functionality for real-time updates
4. Deploy production environment

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

## Important Implementation Notes

1. **MCP-First Development:** ALWAYS search before implementing:
   - Unknown API → Search with `exa` + `firecrawl`
   - Framework feature → Check `context7` documentation
   - Error/Issue → Search with `tavily` (recent) + `exa` (solutions)

2. **Parallel MCP Execution:** Batch all related searches:
   ```python
   # GOOD: Parallel execution
   results = await asyncio.gather(
       mcp__context7__get_library_docs("fastapi", "authentication"),
       mcp__exa__github_search("FastAPI JWT implementation"),
       mcp__firecrawl__firecrawl_deep_research("FastAPI security 2024")
   )
   ```

3. **Tool Chain Patterns:**
   - **Research**: `firecrawl` (deep) → `clear-thought` (analyze) → implement
   - **Debug**: `tavily` (error) → `debuggingapproach` → `context7` (docs)
   - **Optimize**: `stochasticalgorithm` → `exa` (benchmarks) → apply

4. **TripSage Specifics:**
   - **MCP Manager**: Only for Airbnb operations (`MCPManager.invoke()`)
   - **Storage**: Single Supabase PostgreSQL with pgvector
   - **Error Handling**: `@with_error_handling` decorator + error search
   - **Caching**: DragonflyDB (Redis-compatible) with content-aware TTLs
   - **Validation**: Pydantic v2 models + schema validation

## Quick Reference Paths

- **TODO Files:** `/TODO.md`, `/tasks/TODO-*.md`
- **Documentation:** `/docs/`
- **API:** `/tripsage/api/`
- **Core Services:** `/tripsage_core/services/`
- **Agents/Orchestration:** `/tripsage/orchestration/`
- **MCP Abstraction:** `/tripsage_core/mcp_abstraction/`
- **Tests:** `/tests/`

## Common Commands

```bash
# Development
uv run python -m tripsage.api.main  # Start API server
uv run pytest                        # Run tests
ruff check . --fix && ruff format .  # Lint and format

# Database
uv run python scripts/database/run_migrations.py  # Run migrations

# DragonflyDB
docker run -d --name tripsage-dragonfly -p 6379:6379 \
  docker.dragonflydb.io/dragonflydb/dragonfly:latest \
  --logtostderr --cache_mode --requirepass tripsage_secure_password
uv run python scripts/verification/verify_dragonfly.py  # Verify cache connection
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

_End of TripSage project instructions._
