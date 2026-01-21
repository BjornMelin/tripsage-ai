# ADR-0072: Dependency upgrade batch (2026-01-19)

**Version**: 1.0.0  
**Status**: Accepted  
**Date**: 2026-01-19  
**Category**: Ops / Dependency Management  
**Domain**: Tooling / Security hygiene  
**Related ADRs**: ADR-0032, ADR-0063, ADR-0070, ADR-0071  
**Related Specs**: SPEC-0100, SPEC-0107, SPEC-0109, SPEC-0111

## Context

- TripSage is pre-production (no users) and optimizes for modern Next.js 16 + React 19 patterns.
- We pin exact dependency versions for determinism and treat upstream changes as migration drivers (types, security fixes, and runtime constraints).
- This batch upgrades a small set of dependencies that affect:
  - payments/webhooks security (Stripe, raw-body verification, idempotency)
  - rate limiting posture and Upstash feature surface
  - instrumentation correctness and runtime resolution
  - UI motion/typing correctness
  - dependency hygiene tooling (Knip)

## Decision

We upgrade and pin the following packages and implement any required migrations:

### Runtime dependencies

- `@upstash/ratelimit`: `2.0.7` → `2.0.8`
  - Adopted dynamic limits support (`dynamicLimits: true`) across all limiter construction sites (ADR-0032).
- `import-in-the-middle`: `2.0.1` → `2.0.4`
  - Kept resolvable in the server runtime; added regression test for resolution (see `src/lib/telemetry/__tests__/import-in-the-middle-resolve.test.ts`).
- `motion`: `12.26.0` → `12.27.0`
  - No breaking changes required in current usage; validated with component tests.
- `react-error-boundary`: `6.0.3` → `6.1.0`
  - Updated boundary typing (`Error` → `unknown`) and standardized normalization policy (ADR-0071).
- `stripe`: `20.1.2` → `20.2.0`
  - Centralized server-only Stripe client and added hardened Stripe webhook endpoint with signature verification and idempotency (ADR-0070, SPEC-0111).

### Dev dependencies

- `knip`: `5.80.2` → `5.82.0`
  - Updated `knip.json` to avoid false positives from string-loaded tooling and keep `pnpm deps:audit` deterministic.

## Consequences

### Positive

- Deterministic dependency graph with explicit migrations captured in ADRs/specs.
- Security posture improves for inbound webhooks and request-scoped rate limiting.
- Dependency hygiene enforcement (`pnpm deps:audit`) remains stable and actionable.

### Negative

- Requires periodic maintenance to keep pins and docs aligned.

### Neutral

- No backward compatibility constraints were preserved; this batch is treated as a “final state” baseline for the current pre-production phase.

## References

- Upstash Ratelimit JS v2.0.8: <https://github.com/upstash/ratelimit-js/releases/tag/v2.0.8>
- import-in-the-middle v2.0.4: <https://github.com/nodejs/import-in-the-middle/releases/tag/import-in-the-middle-v2.0.4>
- Motion v12.27.0: <https://github.com/motiondivision/motion/releases/tag/v12.27.0>
- react-error-boundary v6.1.0: <https://github.com/bvaughn/react-error-boundary/releases/tag/6.1.0>
- Stripe Node v20.2.0: <https://github.com/stripe/stripe-node/releases/tag/v20.2.0>
