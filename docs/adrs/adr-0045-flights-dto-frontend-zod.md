# ADR-0045: Flights DTOs in Frontend (Next.js 16 + Zod v4)

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2025-11-20  
**Category**: Data / Frontend  
**Domain**: Flights DTO (Zod v4)  
**Supersedes**: ADR-0012  
**Related ADRs**: ADR-0013, ADR-0023, ADR-0031, ADR-0032, ADR-0034, ADR-0038, ADR-0039, ADR-0044, ADR-0047  
**Related Specs**: -

## Context

- Zod v4 schemas are centralized under `frontend/src/domain/schemas/*`; flights currently lack a dedicated domain schema and rely on agent-specific schemas in `@schemas/agents` plus Supabase row schemas in `domain/schemas/supabase.ts`.  
- AI flight tooling lives in `frontend/src/ai/tools/server/flights.ts` (Duffel offer search) and generic planning schemas (`frontend/src/ai/tools/schemas/planning.ts`), but there is no shared flight domain model or provider mapper.  
- ADR-0012 defined Python/FastAPI DTOs; the stack is now frontend-only with Next.js 16 + AI SDK v6. We need a single TS/Zod source of truth that fits existing domain/schema conventions and tool schema locations (`frontend/src/ai/tools/schemas/*`).

## Decision

1) **Create flight domain module aligned with existing pattern**  
   - Add `frontend/src/domain/schemas/flights.ts` with sections:  
     - `// ===== CORE SCHEMAS =====` for canonical flight entities (`FlightLocation`, `FlightSlice`, `Passenger`, `FlightOffer`, `Pricing`, `Itinerary`, `CarrierInfo`).  
     - `// ===== TOOL INPUT/OUTPUT SCHEMAS =====` for search inputs/normalized results consumed by tools and UI.  
   - Keep Supabase table shapes in `domain/schemas/supabase.ts`; reference them from this module when needed (e.g., persistence mappers), but do not duplicate.

2) **Add flight domain logic folder**  
   - Create `frontend/src/domain/flights/` with:  
     - `mappers.ts`: provider → domain normalizers (Duffel now, Expedia Rapid later). Use pure functions returning `FlightOffer`.  
     - `service.ts`: thin orchestration for flight search that calls provider clients (Duffel, future providers) and returns domain DTOs.  
     - `providers/duffel.ts`: provider-specific call + error mapping to `TOOL_ERROR_CODES`, emitting structured errors and redacted telemetry attributes.  
   - Do not introduce a new top-level schema location; all validation stays in `domain/schemas/flights.ts`.

3) **Tool schema alignment**  
   - Tools should import flight schemas directly from `@schemas/flights`; no separate tool-schema wrapper is needed.  
   - Update `frontend/src/ai/tools/server/flights.ts` to use these schemas and `domain/flights/mappers` for normalization instead of returning raw Duffel payloads. Keep guardrails (`cache`, `rateLimit`, `telemetry`) but move error mapping into the provider helper.

4) **Telemetry, caching, and runtime policy**  
   - Telemetry: route all spans through `withTelemetrySpan` (ADR-0046); include attributes `provider`, `workflow=flightSearch`, `hasReturn`, `passengers`, and hashed origin/destination.  
   - Caching: standardize cache key via `canonicalizeParamsForCache` (already used) and keep TTL at 30 minutes.  
   - Runtime: default Node; Edge only if request path avoids Supabase SSR and BYOK (per ADR-0047).

5) **Testing**  
   - Add Vitest suites under `frontend/src/domain/flights/__tests__/` covering mappers (Duffel happy/edge cases) and schema guards.  
   - Extend existing tool tests (`frontend/src/ai/tools/server/__tests__/flights*.test.ts`) to assert normalized `FlightOffer` structure and error mapping.

6) **Cleanup**  
   - Remove flight-specific literals from `@schemas/agents` once callers migrate to `@schemas/flights`.  
   - Delete lingering references to ADR-0012 / Python DTOs in docs or comments.

## Consequences

### Positive

- Single Zod v4 source for flight entities and tool IO, consistent with existing domain schema architecture.  
- Provider integrations plug into mappers, enabling multi-provider expansion without touching UI or tools.  
- AI tools return normalized, validated DTOs, improving resilience and UI compatibility.  
- Clear telemetry/runtime policy alignment improves observability and security.

### Negative

- Refactors needed in tooling/tests and any legacy callers of `@schemas/agents` flight shapes.  
- Additional mapper layer adds a small amount of code surface.

### Neutral

- Supabase table schemas remain separate; persistence logic unaffected.

## Alternatives Considered

### Keep legacy ADR-0012 (Python DTOs)

Rejected: misaligned with frontend-only stack; perpetuates drift and dual maintenance.

### Duplicate tool-specific schemas (status quo)

Rejected: increases divergence risk and maintenance overhead; breaks DRY/KISS goals.

## References

- Zod v4 migration guide (strictObject/extend recommendations)  
- docs/developers/zod-schema-guide.md  
- ADR-0013 (Next.js 16), ADR-0023 (AI SDK v6), ADR-0032 (rate limiting), ADR-0046 (telemetry), ADR-0047 (runtime policy)
