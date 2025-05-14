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

## Tool-Integration Order

1. `flights-mcp` · `airbnb-mcp` · `google-maps-mcp`
2. `linkup-mcp` · `firecrawl-mcp`
3. `supabase-mcp` · `memory-mcp`
4. `playwright-mcp` _(fallback only)_
5. `time-mcp` · `sequentialthinking-mcp`

_Build every server with **FastMCP 2.0**; use **Pydantic v2** models and
`Field`/`Annotated` validation; log via `Context`._

## Memory Graph Workflow

`read_graph` (boot) → `search_nodes` → plan → `create_entities`/`create_relations`
→ `update_graph` (shutdown).

## Playwright Rule (rare)

Only when MCP tools can’t fetch data:  
1 Navigate → 2 Input criteria → 3 Extract → 4 Persist (Supabase + KG).

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

_End of TripSage project instructions._
