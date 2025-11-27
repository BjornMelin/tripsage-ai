# ADR-0047: Runtime Policy for AI SDK Routes (Edge vs Node)

**Version**: 1.0.0  
**Status**: Proposed  
**Date**: 2025-11-20  
**Category**: Architecture / Runtime  
**Domain**: Deployment Targets  
**Related ADRs**: ADR-0013, ADR-0023, ADR-0031, ADR-0032, ADR-0040, ADR-0044  
**Related Specs**: -

## Context

- Next.js 16 supports Edge and Node runtimes; the project uses Supabase SSR, Upstash, and AI Gateway.  
- Secrets (Supabase, Upstash, AI providers) must remain server-side; some SDKs are not Edge-safe.  
- No current ADR defines when to choose Edge vs Node for AI routes.

## Decision

- **Default**: Node runtime for AI SDK routes to retain `fetch` compat, Supabase SSR cookie handling, and OTEL exporters.  
- **Edge allowed** when ALL are true: no Supabase SSR client use; only HTTP-only Upstash clients; no BYOK keys; payload < 1MB; no Node-only deps.  
- `withApiGuards` remains mandatory; add comment `// ADR-0047: node|edge rationale` in handlers choosing Edge.  
- Use AI Gateway for Edge routes; BYOK registry is Node-only.  
- Rate limiting (ADR-0032) must be initialized per-request inside handler, not module scope; Edge-friendly Upstash clients permitted under the above constraints.  
- Do not mix runtimes within a single feature; choose per route and document.

## Consequences

### Positive

- Clear, auditable runtime choices; minimizes accidental secret exposure on Edge.  
- Aligns runtime selection with Supabase/Upstash compat and telemetry requirements.

### Negative

- Some endpoints remain on Node and miss potential Edge latency benefits.  
- Additional test matrix needed for Edge routes.

### Neutral

- No impact on API contracts; deployment targeting only.

## Alternatives Considered

### Allow per-developer discretion without policy

Rejected: high risk of secret leakage and runtime incompatibilities.

### Edge-first default with opt-out

Rejected: conflicts with Supabase SSR, BYOK, and telemetry exporters; higher risk than benefit today.

## References

- Next.js 16 runtime docs  
- Supabase SSR guidance  
- ADR-0023 (AI SDK v6), ADR-0032 (rate limiting), ADR-0046 (telemetry)
