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

## Tool-Integration Order

1. `flights-mcp` · `airbnb-mcp` · `google-maps-mcp` ✅
2. `linkup-mcp` · `firecrawl-mcp` ✅
3. `supabase-mcp` · `memory-mcp` ✅
4. `playwright-mcp` ✅ _(fallback only)_
5. `time-mcp` · `sequentialthinking-mcp` ⚠️ (time done, sequential pending)

_Build every server with **FastMCP 2.0**; use **Pydantic v2** models and
`Field`/`Annotated` validation; log via `Context`._

## Development Workflow

1. **Before Starting:**
   - Check taskmaster for next task
   - Review TODO.md for context
   - Check related documentation in docs/

2. **During Development:**
   - Follow test-driven development
   - Maintain ≥90% test coverage
   - Run linting after changes: `ruff check . --fix && ruff format .`
   - Update task status in taskmaster

3. **After Completing:**
   - Mark task as done in taskmaster
   - Update TODO.md if needed
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

## Agent Pattern Guide

| Pattern              | When to use                               |
| -------------------- | ----------------------------------------- |
| **Single LLM Call**  | Simple, deterministic tasks               |
| **Workflow**         | Predictable multi-step jobs               |
| **Autonomous Agent** | Complex, dynamic planning _(last resort)_ |

Design mantra: **Start simple → add complexity only when required**.

## Security Reminder

Real keys live in `.env`; commit only `.env.example` placeholders.

## Important Implementation Notes

1. **MCP Manager Usage:** Always use `MCPManager.invoke()` for MCP operations
2. **Dual Storage:** Use service pattern for Supabase + Neo4j operations
3. **Error Handling:** Use `@with_error_handling` decorator consistently
4. **Caching:** Leverage Redis MCP for all cacheable operations
5. **Validation:** Pydantic v2 with field_validator for all models

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

_End of TripSage project instructions._
