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

- [ ] Create `frontend/src/lib/agents/config-resolver.ts` implementing:
  - [ ] `resolveAgentConfig(agentType, { userId? })` using Upstash cache and
        Supabase as described in the spec.
  - [ ] Internal helpers to construct cache keys and apply defaults from
        `configurationAgentConfigSchema`.  
- [ ] Add new route handlers:
  - [ ] `frontend/src/app/api/config/agents/[agentType]/route.ts`:
    - `GET` and `PUT` using `withApiGuards` and Supabase SSR.  
  - [ ] `frontend/src/app/api/config/agents/[agentType]/versions/route.ts`:
    - `GET` for version history.
  - [ ] `frontend/src/app/api/config/agents/[agentType]/rollback/[versionId]/route.ts`:
    - `POST` for rollback.
- [ ] Update `frontend/src/components/features/agents/configuration-manager.tsx`:
  - [ ] Replace hard-coded `AgentConfig` types with types derived from
        `configurationAgentConfigSchema`.
  - [ ] Replace direct `fetch` calls with a typed client or small wrapper
        that calls the new API endpoints.
  - [ ] Remove placeholder metrics and `Math.random`-style demo calculations,
        wiring to real metrics or simple actual usage metrics where available.  
- [ ] Integrate config resolver into all agent runners:
  - [ ] `frontend/src/lib/agents/budget-agent.ts`
  - [ ] `frontend/src/lib/agents/destination-agent.ts`
  - [ ] `frontend/src/lib/agents/accommodation-agent.ts`
  - [ ] `frontend/src/lib/agents/flight-agent.ts`
  - [ ] `frontend/src/lib/agents/itinerary-agent.ts`  
  - [ ] Ensure `streamText` calls use config-derived model/temperature/tools.  
- [ ] Add telemetry hooks and operational alerts for config changes using
      `emitOperationalAlert`.:contentReference[oaicite:111]{index=111}  

## 3. Data Migrations

- [ ] Create `agent_config` table in Supabase with fields and constraints
      defined in the spec.
- [ ] Create `agent_config_versions` table with fields and indexes defined
      in the spec.
- [ ] Define RLS policies for both tables to restrict read/write to admins.
- [ ] Seed baseline configuration records for each agent type:
  - [ ] Extract current default configuration parameters from agent runners
        and encode them as initial `agent_config_versions` rows.
  - [ ] Link each baseline version to a row in `agent_config`.

## 4. Feature Flags / Rollout

- [ ] Introduce a simple environment-driven flag (e.g.,
      `ENABLE_AGENT_CONFIG_BACKEND`) to control whether agents read from
      `resolveAgentConfig` or use existing hard-coded defaults.
- [ ] In initial rollout:
  - [ ] Enable feature flag in staging only.
  - [ ] Verify that agents produce sane outputs under the new configuration.
- [ ] After validation, enable feature flag in production and remove the old
      hard-coded configuration paths.

## 5. Observability & Alerts

- [ ] Add telemetry span names to new routes:
  - [ ] `config.agents.get`
  - [ ] `config.agents.update`
  - [ ] `config.agents.versions`
  - [ ] `config.agents.rollback`  
- [ ] Add operational alerts:
  - [ ] `agent_config.updated`
  - [ ] `agent_config.rollback`
  - [ ] `agent_config.resolve_failed` (on schema or DB errors).  
- [ ] Add dashboards or log queries for:
  - [ ] Frequency of config updates per agent.
  - [ ] Error rate for config APIs.

## 6. Documentation

- [ ] Add this spec and ADR references to `AGENTS.md` or a dedicated
      “Configuration” section/link.:contentReference[oaicite:114]{index=114}  
- [ ] Document API usage for `/api/config/agents/**` in internal developer
      docs (expected inputs/outputs and error codes).
- [ ] Update any onboarding docs to mention agent configuration workflows.

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
