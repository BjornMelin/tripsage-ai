# ADR-0039: Framework-First Frontend Agent Modernization

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-12  
**Category**: Architecture  
**Domain**: Frontend / AI Orchestration  
**Related ADRs**: ADR-0023, ADR-0028, ADR-0031, ADR-0038  
**Related Specs**: SPEC-0019, SPEC-0020

## Context

- After deleting the Python destination-research agent, the remaining LangGraph nodes (flight, accommodation, budget, memory-update, router/error handling) continue to run inside `tripsage/` and `tripsage_core`, blocking our goal of a Next.js-only agent stack.
- ADR-0038 committed us to a hybrid ToolLoopAgent + guardrail architecture for destination and itinerary workflows. We now need a consistent migration path for every agent while integrating richer provider data (e.g., OpenTripMap POIs and safety/advisory feeds).
- Three rollout options were evaluated via Zen consensus: (A) migrate each workflow sequentially, (B) uplift the shared frontend agent framework first and then migrate workflows in waves, (C) attempt a big-bang rewrite. Consensus scoring favored Option B (framework-first waves) for leverage, value, and manageable maintenance.

## Decision

We will adopt **Option B: framework-first waves** to retire the remaining backend agents and move all orchestration into `frontend/`:

1. **Framework Hardening (P0)** – extend the hybrid ToolLoop infrastructure (schemas, guardrails, telemetry, Upstash caches) so it can host any agent type.
2. **Wave Migrations (P1–P3)** – migrate flight & accommodation agents first, then budget + memory, and finally routing/error-handling flows. Each wave ships fully through the frontend Route Handlers and AI Elements UI before decommissioning the Python equivalent.
3. **Provider Expansion (P4)** – integrate OpenTripMap (POI data) and GeoSure/Travel Advisory safety scores as TypeScript tools inside the registry so all agents can leverage richer data for recommendations.
4. **Documentation & Telemetry** – codify the migration playbook in SPEC-0020, enforce feature flags per wave, and instrument tool-level metrics to monitor parity before flipping traffic.

## Consequences

### Positive

- Unified frontend architecture: all agents share the same ToolLoop, guardrail, and telemetry layers.
- Enables new providers (POI + safety scores) to be reused by any workflow without backend changes.
- Reduces dual-stack maintenance time; each wave can independently ship once telemetry shows parity.

### Negative

- Requires upfront investment in framework hardening (schemas, caching, guardrails) before visible user features ship.
- For a period, legacy LangGraph nodes and new frontend agents will coexist, requiring careful routing/feature-flag management.

### Neutral

- Router logic will be reimplemented in TypeScript; this creates an opportunity to revisit routing heuristics but is not inherently good or bad.

## Alternatives Considered

### Option A – Sequential workflow migration

- Pros: earliest wins per workflow and simpler mental model for small teams.
- Cons: prolonged dual-stack state, repeated integration seams, higher cumulative maintenance. Consensus score 7.5/10.

### Option C – Big-bang rewrite

- Pros: single launch moment, theoretically clean cutover.
- Cons: high delivery risk, long freeze with no user value, large stabilization cost. Consensus score 6.3/10.

## References

- Zen consensus log on rollout strategies (2025-11-12).  
- OpenTripMap API documentation (POI provider).  
- Amadeus/GeoSure Safe Place API overview (safety scoring).  
- SPEC-0020 (Multi-agent migration & provider expansion).
