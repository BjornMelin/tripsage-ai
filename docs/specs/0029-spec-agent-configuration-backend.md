# SPEC-0029: Agent Configuration Backend & Versioned Storage – Functional & Technical Spec

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-21
**Category**: Frontend
**Domain**: AI Orchestration
**Related ADRs**: [ADR-0052](adr-0052-agent-configuration-backend.md)
**Related Specs**:

## 1. Summary

This spec defines a Supabase-backed backend for managing configuration of all
TripSage AI agents (budget, destination, flights, itineraries, accommodations,
memory). It introduces typed Supabase tables, authenticated Next.js API routes,
Upstash-backed caching, and integration hooks for agent runners, as well as
wiring for the existing admin UI.

The goal is to replace ad‑hoc, code-level configuration and mock admin flows
with a single, auditable, versioned configuration control plane.

## 2. Goals

- Provide a **single source of truth** for agent configuration (model,
  provider, temperature, tools, feature toggles).
- Support **version history** and **rollback** of configurations via
  `agent_config_versions`.
- Expose authenticated, rate‑limited, and observable APIs to manage configs.
- Integrate configuration resolution into **all agent runners**.
- Replace mock configuration & metrics in `AgentConfigurationManager` with real
  data from APIs and Supabase.

## 3. Non-Goals

- Implement a full feature‑flag framework or per‑user experimentation system
  beyond the initial `(agent_type, scope)` configuration.
- Change the core behavior of AI agents beyond reading their runtime settings
  from the new backend.
- Implement a complex policy engine or roles/permissions system beyond
  standard Supabase auth + basic admin checks.
- Replace existing observability stack; we will only **integrate** with
  existing telemetry helpers.

## 4. User Stories

- As an **internal admin**, I want to view and edit configuration for each
  agent (e.g., budget agent temperature, model, enabled tools) from a single
  admin page so I can tweak behavior without redeploying code.
- As an **internal admin**, I want to see **recent configuration versions** and
  roll back to a previous version if a change degrades behavior.
- As an **engineer**, I want agent runners to read configuration through a
  single typed resolver instead of scattering constants across files.
- As an **engineer**, I want configuration changes to be **traceable** in logs
  and metrics (who changed what and when).

## 5. User Flows

### 5.1 Admin updates agent configuration

1. Admin navigates to the Agent Configuration page.
2. Admin selects an agent (e.g., “Budget Planning Agent”) from the dropdown.
3. The UI calls `GET /api/config/agents/:agentType` to fetch the current config.
4. Admin modifies fields (model, temperature, enabled tools, etc.).
5. UI calls `PUT /api/config/agents/:agentType` with the new config.
6. Backend validates input with `agentConfigRequestSchema`.
7. Backend writes a new row into `agent_config_versions`, updates
   `agent_config`, invalidates cache, and returns the updated config.
8. UI updates display and shows a success toast.

### 5.2 Admin inspects version history

1. Admin opens the version history panel for a given agent.
2. UI calls `GET /api/config/agents/:agentType/versions`.
3. Backend returns a paginated list of versions (id, created_at, created_by,
   summary).
4. Admin can click into a version for more detail (full JSON config).

### 5.3 Admin rolls back to a previous version

1. From version history, admin chooses “Roll back” on a version.
2. UI sends `POST /api/config/agents/:agentType/rollback/:versionId`.
3. Backend:
   - Loads the version.
   - Writes a **new** version row with the same payload but new metadata.
   - Updates `agent_config` active record.
   - Invalidates cache tags.
4. UI reloads config via `GET` and shows confirmation.

### 5.4 Agent runner resolves configuration

1. Agent route handler receives a validated agent request (e.g., budget plan).
2. Handler calls `resolveAgentConfig(agentType, { userId })`.
3. Resolver:
   - Attempts to load config from Upstash JSON cache.
   - On cache miss, queries Supabase `agent_config`, validates JSON via
     `configurationAgentConfigSchema`, caches it with TTL, and returns it.
4. Agent runner uses resolved values (modelId, temperature, tools toggles) when
   building `streamText` call options.  

## 6. Data Model & Schemas

### 6.1 Zod Schemas (existing)

Source: `frontend/src/domain/schemas/configuration.ts`.:contentReference[oaicite:99]{index=99}

Key structures:

- `agentTypeSchema` – enumeration of supported agents (budget, destination,
  flights, itinerary, accommodations, memory, etc.).
- `configurationAgentConfigSchema` – canonical agent configuration record,
  including:
  - `agentType`
  - `model` (provider + id)
  - `temperature`, `maxTokens`, `topP`, `frequencyPenalty`, etc.
  - `enabledTools`, `safetyLevel`, and other knobs.
- `agentConfigRequestSchema` – request shape for configuration updates, mapping
  UI form inputs to `configurationAgentConfig`.

### 6.2 Database Tables (Supabase)

**Table: `agent_config`**

- `id` (uuid, PK, default `gen_random_uuid()`).
- `agent_type` (text, indexed) – must match `agentTypeSchema` values.
- `scope` (text, default `'global'`) – future extension: `environment`,
  `tenant`, `user`.
- `config` (jsonb) – validated against `configurationAgentConfigSchema`.
- `version_id` (uuid) – reference to `agent_config_versions.id`.
- `created_at` (timestamptz, default `now()`).
- `updated_at` (timestamptz, default `now()`).
- Unique constraint on `(agent_type, scope)`.

**Table: `agent_config_versions`**

- `id` (uuid, PK).
- `agent_type` (text, indexed).
- `scope` (text).
- `config` (jsonb).
- `created_at` (timestamptz, default `now()`).
- `created_by` (uuid, nullable) – Supabase auth user id (if a user performed
  the change).
- `summary` (text, nullable) – optional description entered by admin.

**RLS (high-level):**

- `agent_config` & `agent_config_versions`:
  - Allow `SELECT`, `INSERT`, `UPDATE` only for users with an `is_admin` flag
    (or equivalent) in a suitable profile table or Supabase auth metadata.
- Implementation detail for `is_admin` is deferred to migration and DB config.

## 7. API Design & Integration Points

All routes live under `frontend/src/app/api/config/agents`:

### 7.1 `GET /api/config/agents/:agentType`

- **Auth:** `withApiGuards({ auth: true, telemetry: "config.agents.get" })`.  
- **Input:**
  - Path param `:agentType` (string), validated with `agentTypeSchema`.
  - Query param `scope` (optional, default `global`).
- **Output (200):**
  - JSON: `{ config: ConfigurationAgentConfig; versionId: string }`, shaped by
    `configurationAgentConfigSchema`.
- **Behavior:**
  - Lookup cached config via Upstash.
  - On cache miss, query `agent_config` for `(agent_type, scope)`.
  - If not found, return 404 or default config (specifying behavior explicitly
    in implementation).
  - Cache the result with TTL (e.g., 15 minutes) using `setCachedJson`.

### 7.2 `PUT /api/config/agents/:agentType`

- **Auth:** `withApiGuards({ auth: true, telemetry: "config.agents.update", rateLimit: "config:agents:update" })`.  
- **Input:**
  - Path param `:agentType` validated with `agentTypeSchema`.
  - JSON body validated with `agentConfigRequestSchema`.  
- **Output (200):**
  - JSON: `{ config: ConfigurationAgentConfig; versionId: string }`.
- **Behavior:**
  - Validate body.
  - Start a transaction:
    - Insert into `agent_config_versions`.
    - Upsert `agent_config` row for `(agent_type, scope)`.
  - Invalidate cache via `bumpTag("configuration")` and optionally delete
    specific Upstash keys.
  - Return updated config.

### 7.3 `GET /api/config/agents/:agentType/versions`

- **Auth:** `withApiGuards({ auth: true, telemetry: "config.agents.versions" })`.  
- **Input:**
  - Path param `:agentType`.
  - Query params `scope`, `limit`, `cursor` for simple pagination.
- **Output (200):**
  - JSON: `{ versions: Array<{ id, createdAt, createdBy, summary }>, nextCursor?: string }`.
- **Behavior:**
  - Query `agent_config_versions` filtered by agent type and scope.
  - Order by `created_at DESC`, limit by `limit`.
  - Provide stable pagination token if needed.

### 7.4 `POST /api/config/agents/:agentType/rollback/:versionId`

- **Auth:** `withApiGuards({ auth: true, telemetry: "config.agents.rollback" })`.  
- **Input:**
  - Path params `:agentType` and `:versionId`.
- **Output (200):**
  - JSON: `{ config: ConfigurationAgentConfig; versionId: string }`.
- **Behavior:**
  - Read the specified version.
  - Create a new `agent_config_versions` row cloning the config payload.
  - Update `agent_config.config` and `agent_config.version_id`.
  - Invalidate cache tags.
  - Return new active config.

## 8. UI / UX States

Focusing on `AgentConfigurationManager`:

- **Loading:**
  - When the selected agent changes, show skeleton/loader for config and
    metrics while fetching.
- **Success:**
  - Display form with current values (model, temperature, tools).
  - Metrics panel shows live metrics from real sources or simplified aggregated
    metrics; placeholder metrics must be removed.
- **Validation error:**
  - Client-side validation uses the same Zod schema as the backend (`agentConfigRequestSchema`), mapping issues into inline form messages.
  - Server-side validation errors (Zod or DB) show a non-intrusive toast and
    highlight invalid fields if possible.
- **Network error:**
  - Show a banner or toast; keep last known config; allow retry.
- **Unauthorized:**
  - If API responds 401/403, redirect to access-denied or show a clear admin-
    only message.
- **Version history:**
  - Collapse/expand panel with list of versions.
  - Selecting a version opens details; clicking roll-back triggers confirmation
    dialog.

## 9. Observability & Telemetry

- All configuration API routes use `withApiGuards` with telemetry names:
  - `config.agents.get`
  - `config.agents.update`
  - `config.agents.versions`
  - `config.agents.rollback`  
- When a config update or rollback occurs, emit an operational alert via
  `emitOperationalAlert`, including:
  - `event`: `agent_config.updated` or `agent_config.rollback`.
  - Attributes: `agentType`, `scope`, `versionId`, `userId`.
- Consider using OpenTelemetry spans around:
  - Supabase read/write operations related to configuration.
  - Cache lookups and misses.

## 10. Testing Strategy

- **Unit tests (Vitest):**
  - `lib/agents/config-resolver`:
    - Cache hit / miss behavior.
    - Validation errors when stored JSON fails schema checks.
  - Route handlers:
    - Successful GET/PUT/versions/rollback flows.
    - Error paths: invalid input, unauthorized, missing versionId.
    - Rate limit feature toggles (using Upstash mocks).

- **Integration tests (Vitest + MSW):**
  - ConfigurationManager:
    - Loads config on initial agent selection.
    - Handles update success/failure.
    - Displays version history correctly.
    - Invokes rollback and reflects new config.

- **Security tests:**
  - Ensure non-admin users cannot modify configs (RLS simulation / DB-level
    tests or dedicated environment).

- **Regression tests:**
  - After integrating with agents, add tests to verify that agent runners call
    `resolveAgentConfig` and apply config parameters correctly.

## 11. Risks & Open Questions

- **Admin identification:** How do we reliably determine “admin” vs non-admin?
  - Option: use Supabase auth metadata or a `user_profiles` table with an
    `is_admin` flag.
- **Scope model:** Initial implementation will likely only support `global`
  scope. How will we extend to per-environment/per-tenant/per-user?
- **Config migration:** When schemas evolve (e.g., new fields), how do we
  migrate older configs? We may need schema versioning inside the config JSON.
- **Metrics source:** The spec assumes a future or existing metrics backend for
  configuration impact; initial implementation may show simplified statistics
  (e.g., count of calls using an agent) and evolve later.
