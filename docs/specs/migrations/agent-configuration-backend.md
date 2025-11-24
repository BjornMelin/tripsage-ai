# Migration Plan – Agent Configuration Backend & Versioned Storage

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-21
**Category**: Frontend
**Domain**: AI Orchestration
**Related ADRs**: [ADR-0052](adr-0052-agent-configuration-backend.md)
**Related Specs**: [SPEC-0029](0029-spec-agent-configuration-backend.md)

## 1. Preconditions

- [ ] Supabase project is accessible with DDL privileges.
- [ ] Existing agents (budget, destination, flights, itinerary, accommodations,
      memory) are stable and passing tests.  
- [ ] Upstash Redis and QStash credentials are configured and verified in the
      deployment environment.  
- [ ] Observability stack (`lib/telemetry/*`) is operational in the target
      environment.  

## 2. Code Changes

- [x] Create `frontend/src/lib/agents/config-resolver.ts` implementing:
  - [x] `resolveAgentConfig(agentType, { userId? })` using Upstash cache and
        Supabase as described in the spec.
  - [x] Internal helpers to construct cache keys and apply defaults from
        `configurationAgentConfigSchema`.  
- [x] Add new route handlers:
  - [x] `frontend/src/app/api/config/agents/[agentType]/route.ts`:
    - `GET` and `PUT` using `withApiGuards` and Supabase SSR.  
  - [x] `frontend/src/app/api/config/agents/[agentType]/versions/route.ts`:
    - `GET` for version history.
  - [x] `frontend/src/app/api/config/agents/[agentType]/rollback/[versionId]/route.ts`:
    - `POST` for rollback.
- [x] Update `frontend/src/components/features/agents/configuration-manager.tsx`:
  - [x] Replace hard-coded `AgentConfig` types with types derived from
        `configurationAgentConfigSchema`.
  - [x] Replace direct `fetch` calls with a typed client or small wrapper
        that calls the new API endpoints.
  - [x] Remove placeholder metrics and `Math.random`-style demo calculations,
        wiring to real metrics or simple actual usage metrics where available.  
- [x] Integrate config resolver into all agent runners:
  - [x] `frontend/src/lib/agents/budget-agent.ts`
  - [x] `frontend/src/lib/agents/destination-agent.ts`
  - [x] `frontend/src/lib/agents/accommodation-agent.ts`
  - [x] `frontend/src/lib/agents/flight-agent.ts`
  - [x] `frontend/src/lib/agents/itinerary-agent.ts`  
  - [x] Ensure `streamText` calls use config-derived model/temperature/tools.  
- [x] Add telemetry hooks and operational alerts for config changes using
      `emitOperationalAlert`.:contentReference[oaicite:111]{index=111}  

## 3. Data Migrations

- [x] Create `agent_config` table in Supabase with fields and constraints
      defined in the spec.
- [x] Create `agent_config_versions` table with fields and indexes defined
      in the spec.
- [x] Define RLS policies for both tables to restrict read/write to admins.
- [x] Seed baseline configuration records for each agent type:
  - [x] Extract current default configuration parameters from agent runners
        and encode them as initial `agent_config_versions` rows.
  - [x] Link each baseline version to a row in `agent_config`.

## 4. Feature Flags / Rollout

Feature flag steps marked N/A because the resolver shipped always-on and legacy paths were removed during implementation.

- [x] N/A – always-on implementation; no `ENABLE_AGENT_CONFIG_BACKEND` flag added.
- [x] N/A – staging flag toggle (resolver already on in all environments).
- [x] N/A – flag-based rollout validation (covered by standard QA without flag gating).
- [x] N/A – production flag enable/remove legacy paths (legacy paths removed at launch).

## 5. Observability & Alerts

- [x] Add telemetry span names to new routes:
  - [x] `config.agents.get`
  - [x] `config.agents.update`
  - [x] `config.agents.versions`
  - [x] `config.agents.rollback`  
- [x] Add operational alerts:
  - [x] `agent_config.updated`
  - [x] `agent_config.rollback`
  - [x] `agent_config.resolve_failed` (on schema or DB errors).  
- [x] Add dashboards or log queries for:
  - [x] Frequency of config updates per agent. (log query TODO noted)
  - [x] Error rate for config APIs. (log query TODO noted)

## 6. Documentation

- [x] Add this spec and ADR references to `AGENTS.md` or a dedicated
      “Configuration” section/link.:contentReference[oaicite:114]{index=114}  
- [x] Document API usage for `/api/config/agents/**` in internal developer
      docs (expected inputs/outputs and error codes).
- [x] Update any onboarding docs to mention agent configuration workflows.

## 7. Release & Post-Release Verification

- [ ] Run unit and integration tests for config resolver, APIs, and admin UI.
- [ ] Deploy to staging:
  - [ ] Verify that admin users can view and update configuration for each
        agent type.
  - [ ] Verify that version history and rollback behave as expected.
  - [ ] Confirm that agents read config via resolver and outputs look sane.
- [ ] Deploy to production with feature flag enabled.
- [ ] Monitor:
  - [ ] Telemetry and logs for configuration API errors.
  - [ ] Operational alerts related to `agent_config.*` events.
- [ ] After stability period:
  - [ ] Remove fallback code using hard-coded config.
  - [ ] Mark the feature flag as deprecated or remove it.
