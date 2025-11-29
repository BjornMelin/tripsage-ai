# SPEC-0020: Multi-Agent Frontend Migration & Provider Expansion

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-12

## Status

- P0 complete (framework hardening in frontend).
- P1 complete (flights + accommodations endpoints, tools, UI).
- P2 complete (budget + memory + destination + itinerary agents, tools, UI).
- P3 complete (router + error recovery).
- P4 complete (OpenTripMap POI + GeoSure travel advisory tools integrated).

**Migration Complete:** All Python LangGraph orchestration and agents have been completely removed. All functionality now runs in TypeScript AI SDK v6 via Next.js Route Handlers.

## Goals

- Migrate the remaining TypeScript AI SDK v6 agents (flight, accommodation, budget, memory update, router/error recovery) into Next.js Route Handlers powered by the hybrid ToolLoopAgent framework defined in [SPEC-0019](0019-spec-hybrid-destination-itinerary-agents.md).
- Adopt a framework-first wave rollout (per [ADR-0039](../../architecture/decisions/adr-0039-frontend-agent-modernization.md)) that hardens shared infrastructure before shipping workflow waves.
- Integrate additional providers that unlock richer responses: OpenTripMap POI API for attractions data and GeoSure/Travel Advisory safety scores for contextual advisories.

## Phase Breakdown

### P0 - Framework Hardening (Completed)

- **Schemas & Prompts**: Extend `frontend/src/schemas/agents.ts` with shared types for flights, accommodations, budgets, memories, and routing metadata. Update prompt builders to accept user/account context.
- **Guardrail Middleware**: Generalize middleware to support tool budgets per workflow, caching policies, and telemetry hooks.
- (Removed) Feature flags: We are performing a complete cutover; routes are always enabled. Rollback is via deployment rollback, not flags.
- **Deliverables**: Unit tests covering middleware, integration tests for caching + rate limits.

### P1 - Flight & Accommodation Agents (Completed)

- **Route Handlers**: `/api/agents/flights/route.ts`, `/api/agents/accommodations/route.ts` streaming ToolLoopAgent responses.
- **Tools**: Reuse existing TypeScript `searchFlights`, `searchAccommodations`, plus new OpenTripMap POI lookup for nearby lodging context.
- **UI**: AI Elements cards summarizing flight options (price, cabin, airline) and accommodation results.
- **Validation**: Integration tests verifying TypeScript AI SDK v6 tool success >95%; telemetry dashboard for tool execution monitoring.

### P2 - Budget & Memory Agents

- **Budget**: Add `/api/agents/budget` route that uses ToolLoopAgent to balance costs (flights, stays, activities). Integrate safety scores to adjust recommendations.
- **Memory Update**: Route that writes conversation memories via TypeScript tool, replacing Python node. Ensure Supabase writes happen server-side only.
- **UI/UX**: Provide budget visualizations (AI Elements charts) and memory confirmation prompts.

### P3 - Router & Error Recovery

- **Router**: Implement TypeScript intent router that uses AI SDK `generateObject` to classify user requests and set `currentAgent` before hitting specific route handlers.
- **Error Recovery**: Frontend ToolLoop handles fallback messaging and escalations.
- **Note**: Python LangGraph orchestration and agents have been completely removed; all functionality now runs in TypeScript AI SDK v6.

### P4 - Provider Expansion & Enhancements

- **OpenTripMap Tool**: `frontend/src/lib/tools/opentripmap.ts` calling `/places` endpoints with caching (per provider TOS allowing caching). Uses Google Maps Geocoding API for destination-based lookups with result caching.
- **GeoSure/Travel Advisory Tool**: `frontend/src/lib/tools/travel-advisory.ts` retrieving safety scores (fallback to GeoSure API or successor).
- **Integration**: Destination, itinerary, and budget agents consume these tools for improved recommendations; UI displays safety badges.

## Technical Requirements

- **ToolLoopAgent Instances**: Each route instantiates ToolLoopAgent with tailored instructions, tool maps, and `stopWhen` constraints. Reuse guardrail middleware from [SPEC-0019](0019-spec-hybrid-destination-itinerary-agents.md).
- **Caching & Rate Limits**: Upstash buckets per workflow (`ratelimit:flight`, etc.), TTL caches for provider responses.
- **Telemetry**: Structured events for tool calls (name, duration, cacheHit, validationResult) exported via existing logging pipeline.
- **Testing**: Vitest suites per agent, integration tests hitting API routes with mocked providers, Playwright e2e scenarios for each workflow wave.
- **Rollout**: Full cutover (no flags). Monitor telemetry; rollback is a deploy revert.
- **Runbook**: See `docs/operations/agent-frontend.md` for env and validation commands (full cutover; no flags).

## Non-Goals

- Rewriting existing travel data services (flight/accommodation search) beyond wiring them into ToolLoop.
- Building new backend APIs; all work stays within `frontend/` except for provider calls.

## Success Criteria

- All agent workflows execute solely via Next.js Route Handlers and TypeScript tools.
- Legacy LangGraph graph + nodes removed from production path.
- Telemetry shows ≥95% tool-call success and median latency increase ≤ +2 s after migration.
- OpenTripMap & safety data visible in UI with clear sourcing/caching metadata.

## References

- [ADR-0039](../../architecture/decisions/adr-0039-frontend-agent-modernization.md) (Framework-first modernization).  
- [ADR-0038](../../architecture/decisions/adr-0038-hybrid-frontend-agents.md) (Hybrid agent architecture).  
- OpenTripMap API docs (POI data).  
- GeoSure/Travel Advisory reference.  
- Zen consensus log on rollout strategy.
