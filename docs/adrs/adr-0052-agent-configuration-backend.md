# ADR-0052: Agent Configuration Backend with Supabase & Versioning

**Status**: Accepted  
**Date**: 2025-11-21
**Category**: Architecture
**Domain**: AI Orchestration / Frontend
**Related ADRs**: ADR-0051
**Related Specs**: SPEC-0029

## Context

TripSage uses multiple AI agents (budget, destinations, flights, itineraries,
accommodations, memory) implemented with AI SDK v6 and domain-specific tools.
Today, configuration for these agents (model selection, temperature, tool
tuning, safety toggles) is scattered in code and partially duplicated in the
UI.

We already have:

- Canonical Zod schemas for agent configuration requests and records in
  `frontend/src/domain/schemas/configuration.ts`.
- An admin UI (`AgentConfigurationManager`) that allows choosing an agent,
  editing configuration fields, and showing basic metrics.
- A robust Supabase SSR client (`createServerSupabase`) and route guards
  (`withApiGuards`) used for other authenticated APIs.
- Upstash Redis helpers for JSON caching and cache tag versioning.

However:

- There is **no backend API** for reading/writing agent configuration; the UI
  calls `/api/config/agents/...` endpoints that do not exist.
- Configuration is not a first-class persisted concept: there are no Supabase
  tables for agent configuration or its version history.
- Agent runners (e.g., `runBudgetAgent`, `runDestinationAgent`) use parameters
  embedded directly in code and do not consult a central configuration source.

We need a single, consistent configuration backend that:

- Stores per-agent configuration with versioning and auditability.
- Exposes authenticated APIs for read/update/list/rollback.
- Integrates with Upstash for caching and with our observability stack.
- Is consumed by all agent runners when building `streamText` calls.

## Decision

Implement a **Supabase-backed agent configuration service** with:

1. **Data model:**

   - `agent_config` table storing the current active configuration per
     `(agent_type, scope)` (scope: global, environment, or tenant/user).
   - `agent_config_versions` table storing an append-only version log, including
     diffable payload, created_by, created_at, and optional description.
   - Config payloads are validated with `configurationAgentConfigSchema` at
     write time and stored as JSONB.
   - Both tables must have RLS policies enforcing admin-only or
     service-role-only read/write access to ensure database-level protections
     in addition to application guards.

2. **API surface (`frontend/src/app/api/config/agents/**`):**

   - `GET /api/config/agents/:agentType` → returns the effective active config
     using hierarchical scope resolution (global → tenant → user). API accepts an
     explicit `scope` (and identifier where applicable); resolvers attempt the
     requested scope, fall back to the next broader level when not found, and
     return a clear not-found error if nothing exists. Authorization is enforced
     per scope (tenant/user isolation) before returning configs.
   - `PUT /api/config/agents/:agentType` → validates request body against
     `agentConfigRequestSchema`, writes a new version record, and updates the
     active config, wrapped in a Supabase transaction.
   - `GET /api/config/agents/:agentType/versions` → lists recent versions with
     metadata (id, created_at, created_by, summary).
   - `POST /api/config/agents/:agentType/rollback/:versionId` → clones a
     previous version as a new head version.

   All handlers:

   - Use `withApiGuards({ auth: true, telemetry: "...", rateLimit: ... })`
     for auth, rate limiting, and tracing.
   - Use `createServerSupabase` for DB access per Supabase SSR guidelines.
   - Validate and parse JSON via `parseJsonBody` and `validateSchema`.

3. **Caching & invalidation:**

   - Agent configs are cached in Upstash Redis using `getCachedJson` /
     `setCachedJson` with a key prefix such as
     `agent-config:{agentType}:{scope}`.
   - After a successful config update or rollback, we bump a cache tag
     `configuration` using `bumpTag("configuration")` to invalidate dependent
     caches.

4. **Agent runtime integration:**

   - Introduce `@/lib/agents/config-resolver` with a function  
     `resolveAgentConfig(agentType, { userId? })` that:
     - Reads from Upstash cache (with fallback to Supabase).
     - Applies defaults as defined in `configurationAgentConfigSchema`.
   - Update agent runners (budget, destination, accommodations, itinerary,
     flights) to call `resolveAgentConfig` and apply the resolved config
     when constructing `streamText` call options (model, temperature, tools,
     max tokens).

5. **Admin UI wiring:**
   - Refactor `AgentConfigurationManager` to:
     - Use a typed client calling the new APIs.
     - Use types derived from `configurationAgentConfigSchema` instead of an
       ad‑hoc `AgentConfig` interface.
     - Display version history and expose rollback via the new endpoints.

## Options Considered

- **Option A – Supabase tables + Next.js API routes + Upstash cache (chosen)**

  - **Pros:**
    - Leverages existing Supabase SSR integration, RLS, and observability.
    - Fits existing route handler + `withApiGuards` pattern.
    - Enables versioning, rollback, and future scope extensions.
    - Uses existing Upstash JSON cache and cache tag tools.
  - **Cons:**
    - Requires DB migrations and new server code; more moving parts.

- **Option B – Store configuration only in environment variables or Vercel KV**

  - **Pros:**
    - Simple for global, static configuration.
  - **Cons:**
    - No per‑environment/per‑user scope; no version history or auditability.
    - Harder to manage via UI; updates require redeploys.
    - Inconsistent with current Supabase‑centric data model.

- **Option C – Keep configuration purely in code (constants, prompts)**
  - **Pros:**
    - No new infrastructure; low initial implementation cost.
  - **Cons:**
    - No dynamic updates or experimentation; code deploys required for every change.
    - No UI integration, audit trail, or safe rollback.
    - Already causing duplication and drift between UI and agent code.

## Consequences

- **Positive:**

  - Central, type‑safe source of truth for agent configuration with clear UI.
  - Consistent behavior of agents across routes and features.
  - Easier experimentation (e.g., try new model for budget agent) with version
    history and rollback.
  - Config caching reduces repeated DB reads while still supporting invalidation
    via cache tags.

- **Negative / Risks:**
  - Incorrect RLS or auth configuration could expose or allow modification of
    agent configs to non‑admin users.
  - Misconfigured cache invalidation could lead to stale configs in agents until
    TTL expiry.
  - Cache invalidation edge cases (prescriptive handling):
    - If `bumpTag("configuration")` fails (e.g., Redis unavailable), retry up to
      3 times with a short backoff; on final failure, emit an operational alert
      and continue serving the last cached config (stale) while marking the
      response as degraded (do not fail the user‑visible request after a
      successful DB write).
    - Concurrency window: Supabase writes may be readable before the tag bump is
      observed. Mitigation: perform the tag bump in the same transaction when
      possible; otherwise include the version/etag in cached payloads and have
      readers revalidate once (short backoff) when a newer version/etag is
      detected.
    - Maximum acceptable staleness: 5 minutes. Monitor/alert on tag bump errors
      and on cache age >5 minutes so operators can intervene (e.g., manual tag
      bump or cache flush).
  - Schemas for configuration need to evolve carefully; breaking changes may
    require migration logic between versions. Mitigation: preserve backward
    compatibility or ship a compatibility layer (version/etag on payloads), and
    add migration tooling (schema version metadata, automated migration scripts,
    CI validation tests) to block breaking changes without an explicit migration
    path.

## References

- `frontend/src/domain/schemas/configuration.ts` (agent configuration schemas).
- `frontend/src/components/features/agents/configuration-manager.tsx`
  (current admin UI).
- `frontend/src/lib/supabase/server.ts`, `frontend/src/lib/supabase/factory.ts` (SSR
  Supabase client).
- `frontend/src/lib/cache/upstash.ts`, `frontend/src/lib/cache/tags.ts` (Upstash
  JSON cache + cache tags).
- `frontend/src/app/api/agents/*.ts` (agent route handlers using AI SDK v6).
- `docs/specs/migrations/agent-configuration-backend.md` (migration: agent-configuration-backend).
- `docs/specs/0029-spec-agent-configuration-backend.md` (spec: 0029 agent configuration backend).
