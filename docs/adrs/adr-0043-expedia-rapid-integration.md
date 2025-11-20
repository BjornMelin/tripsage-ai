# ADR-0043: Expedia Rapid API Integration for Lodging Search/Booking

**Version**: 1.0.0
**Status**: Proposed
**Date**: 2025-11-19
**Category**: Architecture
**Domain**: Travel Supply Integrations
**Related ADRs**: ADR-0020, ADR-0024, ADR-0026, ADR-0031, ADR-0036, ADR-0039, ADR-0042
**Related Specs**: SPEC-001, SPEC-0010, SPEC-0015

## Context

- Current accommodation tooling relies primarily on Airbnb MCP responses, which limits coverage (no Vrbo inventory, fewer hotels) and keeps us tied to third-party MCP reliability.
- `docs/prompts/tools/accommodation-details-tool-migration.md` calls out Expedia as a desired alternative source, but no design exists.
- Expedia Group’s Rapid API exposes Content, Shopping, and Booking endpoints that cover hotels and Vrbo; Rapid also mandates explicit launch requirements, authentication controls, and telemetry for compliance.
- We already have a placeholder `ExpediaClient` plus tool scaffolding (`frontend/src/lib/tools/accommodations.ts`) and payment orchestration (`frontend/src/lib/payments/booking-payment.ts`), but they are mocks with no real auth, retry, or telemetry.
- We must align with AGENTS.md constraints (library-first, telemetry wrappers, Upstash rate limits) and ADR-0031 chat API guardrails.

## Decision

We will fully integrate Expedia Rapid (Content, Shopping, Booking) as the canonical lodging supply inside the Next.js frontend by:

1. **Implementing a production-grade Expedia client** now housed in `frontend/src/domain/expedia/client.ts` with Rapid SHA-512 signature authentication (`EAN APIKey={key},Signature={sha512},timestamp={ts}`), request signing, structured errors, and telemetry spans via `withTelemetrySpan()`. Schemas now live in the consolidated `frontend/src/domain/schemas/expedia.ts`. The client exposes Content, Shopping, Booking endpoints and uses a singleton pattern behind `getExpediaClient()`. Base URL defaults to `https://api.ean.com/v3` (production) when `EPS_BASE_URL` is unset; sandbox (`https://test.ean.com/v3`) should be set explicitly.
2. **Wiring AI tools through a service + adapter layer**: `frontend/src/ai/tools/server/accommodations.ts` now delegates to `frontend/src/domain/accommodations/service.ts`, which in turn calls the `ExpediaProviderAdapter`. Tool guardrails keep the AI SDK v6 surface but cache/rate-limit logic lives inside the service.
3. **Coordinating payment + booking via orchestrator**: `frontend/src/domain/accommodations/booking-orchestrator.ts` sequences approval → payment (Stripe) → provider booking → Supabase persistence with refund compensation. `frontend/src/lib/payments/booking-payment.ts` now only handles Stripe payment intents/refunds (no provider calls).
4. **Documenting configuration** (env schema + runbooks) and creating a research note (`docs/research/expedia-rapid.md`) plus this ADR so future engineers understand auth keys, endpoints, and compliance requirements.
5. **Removing the legacy Python `get_accommodation_details` pipeline** once Rapid-backed tools ship, keeping frontend as the single source of truth.

## Consequences

### Positive

- Access to Expedia/Vrbo inventory with official SLA-backed APIs, broadening coverage.
- Consistent telemetry/logging, making debugging easier than with MCP proxies.
- Single implementation point in TypeScript reduces duplication with Python.
- Enables future caching strategies (Content API) using Supabase tables.

### Negative

- Requires partner onboarding, credential management, and adherence to Rapid launch requirements (UI disclosures, customer support info).
- Adds maintenance overhead for auth token rotation, sandbox/prod environments, and Rapid changelog tracking.

### Neutral

- Airbnb MCP fallback stays available during rollout but will be deprecated after parity validation.

## Alternatives Considered

### Continue Relying on Airbnb MCP

Rejected because it does not provide hotel/Vrbo breadth, and MCP outages are outside our control. It also complicates compliance and telemetry.

### Build Aggregated Proxy Service

Considered a custom backend proxy (Python/FastAPI) that wraps Rapid. Rejected for now: adds latency, duplicates logic across stacks, and violates frontend-first mandate unless future constraints require backend-side caching.

## References

- Research notes: `docs/research/expedia-rapid.md`
- Expedia Rapid docs: <https://developers.expediagroup.com/rapid>
- Rapid setup: <https://developers.expediagroup.com/rapid/setup>
- Rapid Content: <https://developers.expediagroup.com/rapid/lodging/content>
- Rapid Shopping: <https://developers.expediagroup.com/rapid/lodging/shopping>
- Rapid Booking: <https://developers.expediagroup.com/rapid/lodging/booking>
- AGENTS.md, ADR-0020/0024/0026/0031/0036/0039/0042
