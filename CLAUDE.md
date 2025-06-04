# TripSage AI Project Context

> **Inheritance**
> This repo inherits the global Simplicity Charter (`~/.claude/CLAUDE.md`),  
> which defines all coding, linting, testing, security and library choices  
> (uv, ruff, FastMCP 2.0, Pydantic v2, ≥ 90 % pytest-cov, secrets in .env, etc.).  
> TripSage-specific implementation context is maintained in two living docs:  
> • `docs/implementation/tripsage_todo_list.md` – open tasks & design notes  
> • `docs/status/implementation_status.md` – current build state & blockers  
> Always read or update those before coding.

## Project Snapshot

TripSage is an AI travel-planning platform that fuses flight, lodging and location data,
stores it in **Supabase SQL + a domain knowledge graph**, and optimises itineraries
against budget & user constraints across sessions.

## Current Status & Priorities

**Completed Components:**

- ✅ Core MCP integrations (Flights, Airbnb, Maps, Weather, Time, Web Crawling)
- ✅ API structure with FastAPI
- ✅ Authentication system with BYOK
- ✅ Redis caching layer
- ✅ Error handling framework
- ✅ Database schema design

**Next Priority Tasks:**

1. Complete frontend core setup (Next.js 15)
2. Implement missing database operations
3. Build agent guardrails and conversation history
4. Set up testing infrastructure
5. Deploy production environment

## Taskmaster Integration

**Task Management:**

- Always check `mcp__taskmaster-ai__next_task` before starting work
- Update task status with `mcp__taskmaster-ai__set_task_status` as you progress
- Mark tasks complete immediately after finishing
- Add subtasks for complex implementations

**PRD Location:** `scripts/prd.txt`

**Task Commands:**

```
# Get next task
mcp__taskmaster-ai__next_task

# Update task progress
mcp__taskmaster-ai__set_task_status --id <task_id> --status in-progress
mcp__taskmaster-ai__set_task_status --id <task_id> --status done

# Add implementation details
mcp__taskmaster-ai__update_task --id <task_id> --prompt "Implementation notes..."
```

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
1. `flights-mcp` · `airbnb-mcp` · `google-maps-mcp` ✅
2. `linkup-mcp` · `firecrawl-mcp` ✅ 
3. `supabase-mcp` · `memory-mcp` ✅
4. `playwright-mcp` ✅ _(fallback for dynamic content)_
5. `time-mcp` · `clear-thought-mcp` · `stochasticthinking-mcp` ✅
6. `context7` · `exa` · `tavily` · `aws-docs` · `repomix` · `dev-magic` ✅

_All servers built with **FastMCP 2.0**; **Pydantic v2** models; logging via `Context`._

## Development Workflow with Auto-MCP

1. **Before Starting (Research Phase):**
   - Check taskmaster for next task
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
   - Update taskmaster status

3. **After Completing (Validation Phase):**
   - **VERIFY BEST PRACTICES**: Search for similar implementations
   - Mark task done in taskmaster
   - Document MCP insights in code comments
   - Commit with conventional format

## Memory Graph Workflow

`read_graph` (boot) → `search_nodes` → plan → `create_entities`/`create_relations`
→ `update_graph` (shutdown).

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
   - **MCP Manager**: Use `MCPManager.invoke()` for domain MCPs
   - **Dual Storage**: Supabase + knowledge graph patterns
   - **Error Handling**: `@with_error_handling` + error search
   - **Caching**: Redis MCP + search result caching
   - **Validation**: Pydantic v2 + example search

## Quick Reference Paths

- **Tasks:** `/tasks/tasks.json`
- **TODO Files:** `/TODO.md`, `/tasks/TODO-*.md`
- **Documentation:** `/docs/`
- **API:** `/tripsage/api/`
- **Agents:** `/tripsage/agents/`
- **MCP Abstraction:** `/tripsage/mcp_abstraction/`
- **Tests:** `/tests/`

## Common Commands

```bash
# Development
uv run python -m tripsage.api.main  # Start API server
uv run pytest                        # Run tests
ruff check . --fix && ruff format .  # Lint and format

# Taskmaster
mcp__taskmaster-ai__get_tasks --status pending  # View pending tasks
mcp__taskmaster-ai__complexity_report           # View task complexity
mcp__taskmaster-ai__expand_task --id <id>       # Break down complex task

# Database
uv run python scripts/database/run_migrations.py  # Run migrations
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
