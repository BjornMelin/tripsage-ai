# ADR-0054: Hybrid Upstash Testing (Mocks + Local Emulators + Smoke)

**Version**: 1.0.0  
**Status**: Proposed  
**Date**: 2025-11-24  
**Category**: Testing  
**Domain**: Frontend (Next.js) / Platform  
**Related ADRs**: ADR-0007, ADR-0031, ADR-0032, ADR-0048  
**Related Specs**: SPEC-0031, SPEC-0032

## Context

Recent Vitest runs (`--pool=threads`) exposed brittle, duplicated Upstash mocks (hoisted TDZ, inconsistent reset semantics) across accommodations, payment, flights, travel-advisory, and chat suites. Missing MSW handlers for `/api/chat/stream` produced warnings; Zod error changes and Amadeus fallbacks highlighted gaps in Upstash contract coverage. We need a DRY, deterministic, and higher-fidelity testing approach that aligns with Upstash guidance while remaining fast for local and CI use.

## Decision

We will adopt a three-tier Upstash testing strategy:

1. **Unit-fast tier (default):** Shared in-memory stubs for `@upstash/redis` and `@upstash/ratelimit`, plus centralized MSW handlers for REST/QStash endpoints. Every suite will import the shared helper with a single `reset()` per test to avoid hoist issues.
2. **Local integration tier (optional):** Deterministic emulators (`upstash-redis-local` or equivalent REST-compatible server; QStash CLI dev server) started once per Vitest worker to validate HTTP contracts (auth headers, TTL, 429s) without external network.
3. **Live contract smoke (gated):** A tiny serialized suite that hits real Upstash (Redis, Ratelimit, QStash publish/verify) only when `UPSTASH_SMOKE=1` and secrets are present. Defaults to skipped in CI/PRs.

Decision framework scoring (target ≥9/10 composite):

- Solution leverage: 9.5/10 (reuses MSW + emulator OSS; minimal custom code)
- Application value: 9.2/10 (covers Redis/ratelimit/QStash behaviors; reduces flakes)
- Maintenance/cognitive load: 9.0/10 (single shared helper; pinned emulator versions)
- Architectural adaptability: 9.0/10 (tiers are swappable; env-gated)
- Weighted composite: ≈9.2/10

## Consequences

### Positive

- Deterministic tests under `--pool=threads`; no hoisted mock ordering issues.
- DRY Upstash mocking with one reset API; fewer suite-specific fixtures.
- Higher fidelity via optional emulators and gated live smoke to detect API drift.
- Clear separation of fast/unit vs contract/integration vs live coverage.

### Negative

- Additional maintenance for shared stubs and emulator startup scripts.
- Live smoke requires secrets and serialized execution to avoid quota/rate limits.
- Emulator parity may lag new Upstash features; needs version pinning and periodic review.

### Neutral

- New docs/specs and test setup steps for contributors.
- Adds env flags to toggle tiers; default behavior unchanged for everyday dev loops.

## Alternatives Considered

### Per-suite ad-hoc mocks (status quo)

Rejected due to duplication, hoist/TDZ bugs, and missing contract coverage (e.g., 429, TTL, headers). High flake risk under threaded Vitest.

### Always hit real Upstash

Rejected for speed, cost, flake, and secret-management overhead. Not CI-friendly; hard to parallelize.

### Recorded HTTP fixtures (VCR/WireMock)

Rejected as brittle with evolving Upstash APIs; increases fixture churn and obscures contract intent. Emulators + MSW provide clearer, maintainable coverage.

## References

- Upstash Redis JavaScript SDK docs: <https://docs.upstash.com/redis/sdks/javascriptsdk>  
- Upstash Ratelimit (JS) overview: <https://docs.upstash.com/redis/tools/ratelimit>  
- Upstash QStash CLI (dev server) docs: <https://docs.upstash.com/qstash/cli>  
- Upstash Redis local emulator (community): <https://github.com/DarthBenro008/upstash-redis-local>  
- Upstash-compatible REST test server (Go): <https://github.com/mna/upstashdis>
