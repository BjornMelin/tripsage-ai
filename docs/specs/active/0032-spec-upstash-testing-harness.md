# SPEC-0032: Upstash Testing Harness (Mocks, Emulators, Smoke)

**Version**: 1.0.0  
**Status**: Proposed  
**Date**: 2025-11-24

## Objective

Define a DRY, deterministic testing harness for all Upstash integrations (Redis, Ratelimit, QStash) in the frontend repo, combining shared in-memory stubs, optional local emulators, and gated live smoke checks while remaining compatible with Vitest `--pool=threads` and existing MSW setup.

## Scope

- Next.js 16 code and tests that depend on `@upstash/redis`, `@upstash/ratelimit`, or QStash HTTP calls.
- Vitest unit/integration suites, MSW handlers, and test setup files.

## Non-Goals

- Changing production Upstash configuration or runtime providers.
- Introducing new caching/rate-limiting features; this spec only covers testing.
- Backend (non-frontend) services.

## Current State / Problems

- Per-suite, hoisted mocks cause TDZ/order bugs under `--pool=threads`.
- Duplicate Upstash mock code across accommodations, payment, flights, travel-advisory, chat.
- Missing MSW coverage for some endpoints (e.g., `/api/chat/stream`), producing warnings.
- No consistent way to exercise HTTP contract behavior (auth headers, TTL, 429) without hitting real Upstash.

## Requirements

### Must

- Provide a shared in-memory stub for `@upstash/redis` supporting commands we use: `get`, `set`, `mset`, `del`, `incr`, `expire`, `ttl`, and pipelined `multi/exec` equivalents.
- Provide a shared stub for `@upstash/ratelimit` (sliding window) returning realistic `{ success, limit, remaining, retryAfter, reset }` and allowing forced 429 responses.
- Centralize MSW handlers in `src/test/msw/handlers/upstash.ts` covering Redis REST, ratelimit, and QStash publish/verify endpoints; silence on-unhandled warnings for Upstash paths only.
- Expose a single `reset()` API for stubs/handlers to ensure per-test isolation and thread safety.
- Allow switching to local emulators via env (`UPSTASH_EMULATOR_URL`, `UPSTASH_QSTASH_DEV_URL`, `UPSTASH_USE_EMULATOR=1`) without code changes.
- Add a gated live smoke suite that runs only when `UPSTASH_SMOKE=1` and secrets are present; serialize execution and keep total live calls minimal.
- Document usage in `docs/development/testing.md` (Upstash section).

### Should

- Provide helper factories under `src/test/upstash/` (TypeScript, strict) with typed return values and optional time mocking to simulate TTL expiry.
- Supply a Vitest setup helper to register/reset stubs and MSW handlers (`src/test/setup/upstash.ts`).
- Add npm scripts: `pnpm test:upstash:unit`, `test:upstash:int` (emulator), `test:upstash:smoke` (gated).
- Pin emulator container/tag versions and fail fast with clear error when emulators unavailable.

## Design

### Shared Stubs (Unit/Fast Tier)

- File: `src/test/upstash/redis-mock.ts`
  - Implements minimal in-memory store with TTL tracking via `Date.now()`; pipelines return array results.
  - Export factory `createRedisMock()` returning `{ module, reset }`; `module` matches `@upstash/redis` surface used in app.
- File: `src/test/upstash/ratelimit-mock.ts`
  - Simulates `slidingWindow` responses; supports injected outcomes to test 429 paths.
- Reset pattern: each suite imports the factory, calls `vi.mock('@upstash/redis', () => redisMock.module)` and `beforeEach(redisMock.reset)`.

### MSW Handlers (HTTP Layer)

- Extend `src/test/msw/handlers/upstash.ts` to cover:
  - Redis REST endpoints (`/pipeline`, `/set`, `/get`, `/del`, etc.) delegating to the same in-memory store.
  - Ratelimit endpoints returning structured headers for 429 cases.
  - QStash publish/verify endpoints with configurable responses.
- Provide `registerUpstashHandlers({ store })` and `resetUpstashHandlers()`.

### Local Emulator Tier (Optional)

- Use `upstash-redis-local` (or `upstashdis`) container to emulate REST-compatible Redis.
- Use QStash CLI dev server container for publish/verify.
- Add helper `src/test/upstash/emulator.ts` to start/stop containers (testcontainers or docker CLI) once per worker; seed deterministic keys/rate buckets.
- Config via env: `UPSTASH_USE_EMULATOR=1`, `UPSTASH_EMULATOR_URL=http://127.0.0.1:8079`, `UPSTASH_QSTASH_DEV_URL=http://127.0.0.1:8081`.

### Live Smoke Tier (Gated)

- File: `src/__tests__/contracts/upstash.smoke.test.ts` (skipped unless `UPSTASH_SMOKE=1`).
- Validates: Redis set/get with TTL, ratelimit 429 path, QStash publish + signature verify.
- Serialized execution; low call count; surface clear skip reason when env missing.

### Tooling & Scripts

- `package.json` scripts:
  - `test:upstash:unit` → Vitest with stubs only.
  - `test:upstash:int` → starts emulators, runs integration-tagged tests.
  - `test:upstash:smoke` → gated live suite.
- Vitest config: tag integration and smoke suites; ensure `threads` pool works with shared reset helpers.

## Acceptance Criteria

- All existing Upstash-dependent suites migrate to shared stubs/handlers (no per-suite hoisted mocks).
- `pnpm test:upstash:unit` passes without network/docker; no MSW unhandled warnings.
- Emulator tier starts and passes on a fresh machine with Docker available; fails fast with actionable error when missing.
- Smoke suite cleanly skips without env; passes when creds provided; total live calls remain <20.
- Docs updated; [ADR-0054](../../architecture/decisions/adr-0054-upstash-testing-harness.md) referenced from testing guide and spec README.

## Rollout Plan

1. Land shared stubs + MSW extensions and migrate current failing suites.
2. Add emulator harness and integration tag; wire `test:upstash:int` in CI (optional job).
3. Add smoke suite and gated CI job (nightly or pre-release).
4. Update docs and CHANGELOG; remove duplicated mocks.

## Progress

- [x] Shared in-memory stubs for `@upstash/redis` and `@upstash/ratelimit` with reset helpers.
- [x] Centralized MSW handlers for Upstash REST backed by the shared store (coverage for Redis pipeline, ratelimit headers, and QStash publish stubs).
- [x] DRY cache mocks applied to repeated suites (flights, travel-advisory, service-payment, trips, attachments).
- [x] Emulator harness and integration-tier script (`test:upstash:int`).
- [x] Gated live smoke suite (`test:upstash:smoke`).
- [x] Documentation/CHANGELOG for emulator + smoke, and CI wiring.

> Note: For Vitest `--pool=threads`, use `vi.doMock` (not `vi.mock`) when registering shared Upstash mocks to avoid hoist/TDZ issues.

## Risks & Mitigations

- **Emulator drift vs Upstash:** Pin emulator versions; add periodic smoke tests to detect drift.
- **Thread safety:** Central reset helper must be called in `beforeEach`; document pattern and enforce via lint rule if feasible.
- **Docker availability:** Emulator tier optional; unit tier remains default.

## References

- [ADR-0054](../../architecture/decisions/adr-0054-upstash-testing-harness.md): Hybrid Upstash Testing (Mocks + Local Emulators + Smoke)
- Upstash Redis JS SDK: <https://docs.upstash.com/redis/sdks/javascriptsdk>  
- Upstash Ratelimit: <https://docs.upstash.com/redis/tools/ratelimit>  
- Upstash QStash CLI (dev server): <https://docs.upstash.com/qstash/cli>  
- Upstash Redis local emulator: <https://github.com/DarthBenro008/upstash-redis-local>
