# Testing

Unified testing standards for TripSage frontend. Follow this document as the single source of truth when writing or updating tests.

## Principles and Coverage

- Test behavior, not implementation; keep runs deterministic (no random data/timing without explicit seeds).
- Always choose the lightest test that proves the behavior (unit → component → API → integration → E2E).
- Coverage targets: overall ≥85% (branches 85%, functions 90%, lines 90%, statements 90%); critical paths aim for 100%.
- Naming/layout: co-locate tests under `__tests__` next to code; prefer `*.test.ts(x)` (unit), `*.spec.ts(x)` (integration), `*.integration.test.ts(x)` (cross-module), `*.e2e.*` (Playwright).

## Vitest Projects and Environments

- Projects defined in `frontend/vitest.config.ts`: `schemas`, `integration`, `api`, `component`, `unit` (mixed node/jsdom as configured).
- Environment directives (mandatory, first line):
  - `/** @vitest-environment jsdom */` for React, DOM, browser hooks.
  - `/** @vitest-environment node */` for API routes, server utilities.
- Commands: `pnpm -C frontend biome:check`, `pnpm -C frontend type-check`, `pnpm -C frontend test:run`; targeted runs `pnpm -C frontend test:run --project=<name>`.

## Decision Table (what to write)

| Scenario | Recommended test type | Key tools |
| --- | --- | --- |
| Pure functions, selectors, reducers | Unit | plain asserts; no MSW |
| Hooks with DOM/React state only | Component (jsdom) | RTL `renderHook`, factories |
| Hooks/services calling HTTP | Component or Integration | MSW handlers; `createMockQueryClient` when React Query involved |
| Next.js route handlers | API (node) | MSW for upstreams; `createMockNextRequest` |
| Multi-module flow (store + hook + API) | Integration | MSW + real providers |
| Browser-only flows | E2E (Playwright) | Keep minimal set |

## Global Test Setup

- `frontend/src/test-setup.ts` installs Web Streams/ResizeObserver polyfills; DOM mocks (location, storage, matchMedia); Next.js mocks (navigation, image, headers, toast); React Query + Zustand helpers; MSW server lifecycle (`onUnhandledRequest: "warn"`).
- MSW server starts once; handlers reset after each test. Avoid redundant `server.resetHandlers()` unless resetting mid-test.
- Timers are real by default; opt into fakes with `withFakeTimers` (`frontend/src/test/utils/with-fake-timers.ts`).
- Cleanup: RTL `cleanup()`, React Query cache reset, MSW handler reset executed automatically.
- Prefer helpers: `createMockQueryClient`, `createMockNextRequest`, Supabase mocks in `frontend/src/test/mocks/supabase.ts`, store helpers in `frontend/src/test/store-helpers.ts`, factories in `frontend/src/test/factories/*`.
- Fake timers (opt-in): wrap cases needing clock control with `withFakeTimers` and advance using `vi.advanceTimersByTime`; do not set global fake timers.

### MFA test configuration

- Backup code hashing requires a pepper secret: set `MFA_BACKUP_CODE_PEPPER` (>=16 chars) or `SUPABASE_JWT_SECRET`. `validateMfaConfig()` enforces this outside `NODE_ENV=test`; missing values will fail fast in server code.
- When mocking admin Supabase for MFA routes, mock `getAdminSupabase` (service-role client) and stub minimal `from`/`rpc` as needed.

```ts
/** @vitest-environment node */
import { beforeEach, vi } from "vitest";

beforeEach(() => {
  vi.doMock("@/lib/supabase/admin", () => {
    const from = vi.fn(() => ({
      select: vi.fn().mockReturnThis(),
      update: vi.fn().mockReturnThis(),
      insert: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      is: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn(),
    }));

    const rpc = vi.fn();

    return {
      getAdminSupabase: vi.fn(() => ({ from, rpc })),
    };
  });
});
```

```ts
import { withFakeTimers } from "@/test/utils/with-fake-timers";

it(
  "retries after delay",
  withFakeTimers(async () => {
    await action();
    vi.advanceTimersByTime(1_000);
    expect(retrySpy).toHaveBeenCalled();
  })
);
```

## Mocking Strategy (order matters)

1. **Network:** MSW 2 only; never `vi.mock("node-fetch")`/`fetch`. Handlers live in `frontend/src/test/msw/handlers/*`.
2. **AI SDK:** `MockLanguageModelV3`, `simulateReadableStream`, or `createMockModelWithTracking` from `frontend/src/test/ai-sdk/*` to assert tool calls.
3. **React Query:** `createMockQueryClient`, `createControlledQuery/Mutation` (`frontend/src/test/query-mocks.tsx`).
4. **Supabase:** `frontend/src/test/mocks/supabase.ts`; prefer MSW for REST/RPC.
5. **Timers:** opt-in `withFakeTimers`; avoid global `vi.useFakeTimers()`.
6. **Mock order:** mock `next/headers` (cookies) **before** importing modules that read headers; hoist spies with `vi.hoisted`; then module mocks; finally dynamic import of route under test.
7. **Rate-limiting helpers:** use `stubRateLimitEnabled/Disabled` and Redis getters (`MOCK_GET_REDIS`) from tests; keep in-memory fakes per test.

## MSW Patterns

- Organize handlers by domain; compose sets via `composeHandlers` when mixing domains.
- Override per test using `server.use(...)`; keep handlers minimal but shape-accurate (success + error cases 400/404/429/500, auth headers, FormData assertions).
- Example error path:

```ts
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";

server.use(
  http.get("https://api.example.com/items", () =>
    HttpResponse.json({ error: "fail" }, { status: 500 })
  )
);
```

- Single handler override:

```ts
server.use(http.post("https://api.stripe.com/v1/payment_intents", () =>
  HttpResponse.json({ id: "pi_test", client_secret: "cs_test" })
));
```

## Upstash Testing Harness

- **Unit/fast path:** `setupUpstashMocks()` from `@/test/setup/upstash`; call `__reset()` in `beforeEach`.
- **HTTP layer:** `@/test/msw/handlers/upstash.ts` mirrors Redis pipeline, ratelimit headers, QStash publish.
- **Emulator (optional):** `UPSTASH_USE_EMULATOR=1` + `UPSTASH_EMULATOR_URL` + `UPSTASH_QSTASH_DEV_URL`; helper in `@/test/upstash/emulator.ts`.
- **Smoke:** `pnpm -C frontend test:upstash:smoke` with `UPSTASH_SMOKE=1` (skips when env absent).

## AI SDK v6 Tests

- Use AI SDK test helpers (`frontend/src/test/ai-sdk/*`); assert tool calls via recorded `model.calls` or tracked call list.
- Example tool assertion:

```ts
import { z } from "zod";
import { streamText } from "ai";
import { createMockModelWithTracking } from "@/test/ai-sdk/mock-model";

const { model, calls } = createMockModelWithTracking();
const tools = {
  enrich: {
    parameters: z.strictObject({ id: z.string() }),
    execute: ({ id }: { id: string }) => `ok:${id}`,
  },
};

await streamText({ model, messages: [{ role: "user", content: "hi" }], tools });
expect(calls[0]?.toolName).toBe("enrich");
```

## Route Handlers (node)

- Always place environment directive first; mock `next/headers` before imports; avoid `vi.resetModules()`.
- Use `createMockNextRequest` and import route after mocks. Keep telemetry mocks minimal (e.g., stub `withRequestSpan`).

```ts
/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createMockNextRequest,
  getMockCookiesForTest,
} from "@/test/route-helpers";

vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(
      getMockCookiesForTest({ "sb-access-token": "test-token" })
    )
  ),
}));

describe("/api/example", () => {
  beforeEach(() => vi.clearAllMocks());

  it("handles request", async () => {
    const { POST } = await import("../route");
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/example",
      body: {},
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
  });
});
```

Request creation with headers/cookies and rate-limit stubs:

```ts
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(
      getMockCookiesForTest({ "sb-access-token": "test-token" })
    )
  ),
}));

const LIMIT_SPY = vi.hoisted(() => vi.fn());
const MOCK_GET_REDIS = vi.hoisted(() => vi.fn());

vi.mock("@/lib/rate-limit", () => ({
  stubRateLimitEnabled: () => LIMIT_SPY(true),
  getRedisClient: MOCK_GET_REDIS,
}));

const req = createMockNextRequest({
  method: "POST",
  url: "http://localhost/api/keys/validate",
  body: { keyName: "test" },
  headers: { "x-forwarded-for": "127.0.0.1" },
  cookies: { "sb-access-token": "test-token" },
});
```

Route helper/telemetry and Supabase/Redis mocks:

```ts
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
  })),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

vi.mock("@/lib/api/route-helpers", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/route-helpers")>(
      "@/lib/api/route-helpers"
    );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});
```

Route test requirements checklist:

1) Mock `next/headers` cookies **before** any import that reads it.
2) Use `createMockNextRequest` (never `new Request(...) as NextRequest`).
3) Mock Supabase server client to avoid real cookie access.
4) Use `vi.clearAllMocks()` in `beforeEach`; avoid `vi.resetModules()`.
5) Stub telemetry (`withRequestSpan`) and Redis dependencies as needed.
6) Name suites `describe("/api/<route>")` for consistency.

## Zustand Stores

- Reset with `resetStore` (`@/test/store-helpers`); use `waitForStoreState` for async changes; `setupTimeoutMock` for timer-backed stores.
- Example:

```ts
import { resetStore, waitForStoreState } from "@/test/store-helpers";

beforeEach(() =>
  resetStore(useAuthStore, { user: null, isLoading: false, error: null })
);
await waitForStoreState(useAuthStore, (s) => !s.isLoading, 5000);
```

## Factories and Data

- Use `@/test/factories` for schema-valid fixtures; reset counters when determinism is required.
- Extend factories close to schemas (e.g., calendar events, Supabase users/trips/search) instead of inline objects.

## Test Utilities

- Component/provider wrappers: `renderWithProviders` from `@/test/component-helpers`.
- Query helpers: `createMockQueryClient`, `createControlledQuery/Mutation` in `@/test/query-mocks.tsx`.
- Route helpers: `createMockNextRequest`, `getMockCookiesForTest` in `@/test/route-helpers`.
- Upstash: `setupUpstashMocks` and `@/test/msw/handlers/upstash`.

## Performance Benchmarks (Vitest)

- Command: `pnpm -C frontend test:benchmark`
  - Orchestrates `scripts/run-benchmark.mjs`, which shells to `vitest run --reporter=dot --reporter=json --outputFile=.vitest-reports/vitest-report.json` and then invokes `scripts/benchmark-tests.ts` to parse results into `benchmark-summary.json` (consumed by CI thresholds).
- Thresholds (current defaults): suite <20s wall-clock; per-file hard fail >3.5s; warn >500ms. Override without code changes via env: `BENCHMARK_SUITE_THRESHOLD_MS`, `BENCHMARK_FILE_FAIL_MS`, `BENCHMARK_FILE_WARNING_MS` (all in milliseconds).
- Artifacts: `.vitest-reports/vitest-report.json`, `benchmark-summary.json` (upload in CI).
- Telemetry noise: set `TELEMETRY_SILENT=1` for ad-hoc perf runs to silence console sinks from operational alerts; default runs should leave it unset so alert tests continue to assert console output.
- AI SDK: `MockLanguageModelV3`, `simulateReadableStream`, `createMockModelWithTracking`.
- Factories: `@/test/factories/*` for schema-valid fixtures.

## Running and Debugging

- Common commands: `pnpm -C frontend test`, `test:run`, `test:unit`, `test:components`, `test:api`, `test:integration`, `test:e2e`, `test:coverage`, `test:changed`.
- Single file/project: `pnpm -C frontend test:run --project=api src/app/api/keys/validate/route.test.ts`.
- Pattern/verbosity: `pnpm -C frontend test -- -t "trip" --reporter=verbose`.
- Coverage shard: `pnpm -C frontend test:coverage:shard` when CI sharding is needed.

## CI / Quality Gates

- Pre-commit: `pnpm -C frontend biome:check`, `pnpm -C frontend biome:fix`, `pnpm -C frontend type-check`, targeted `pnpm -C frontend test:run`.
- CI: `pnpm -C frontend test:ci` (threads pool), `pnpm -C frontend test:coverage`, shard with `test:coverage:shard` when required.

## Why This Setup

- Centralized helpers reduce duplication and keep mocks consistent across projects.
- MSW-first networking avoids brittle fetch mocks and keeps request shapes realistic.
- AI SDK helpers capture tool calls without custom streaming implementations.
- Deterministic factories and opt-in fake timers keep runs stable and debuggable.

## Playwright (E2E)

- Config in `frontend/playwright.config.ts`; specs in `e2e/`.
- Commands: `pnpm -C frontend test:e2e`, `--project=chromium`, `--headed`, `--reporter=html`.
- Keep E2E suite lean; reserve for browser-required flows.

## Performance and Anti-Patterns

- Keep tests under ~3s/file; profile with `vitest run --project=<name> --inspect` for slow cases.
- Prefer MSW over `vi.mock` for HTTP; avoid snapshot tests for dynamic UI; avoid shared mutable singletons; clean timers/intervals/stores in `afterEach`.
- Do not use global fake timers; avoid mocking `fetch`; keep handler data minimal (no large fixtures).

### Performance Optimization Patterns

Apply these patterns to slow tests (>500ms):

#### Pattern A: Hoisted Mocks (replaces `vi.resetModules`)

```ts
// Instead of vi.resetModules() + vi.doMock() in beforeEach:
const mockFn = vi.hoisted(() => vi.fn());
vi.mock("./module", () => ({ fn: mockFn }));

beforeEach(() => {
  vi.clearAllMocks();
  mockFn.mockReset();
});

// Single import after mocks
import { handler } from "./handler";
```

#### Pattern B: Fake Timers with Network Requests

When using fake timers with MSW, use `shouldAdvanceTime` to avoid
blocking network requests. For single tests, use `withFakeTimers` (it
creates and tears down timers around one test). For suite-level setups,
use `createFakeTimersContext`, which applies the same options but
exposes `setup/teardown` helpers so multiple tests can share the timer
configuration without repeating boilerplate:

```ts
import { createFakeTimersContext } from "@/test/utils/with-fake-timers";

describe("Debounced search with API calls", () => {
  // shouldAdvanceTime allows MSW requests to complete during fake timer use
  const timers = createFakeTimersContext({ shouldAdvanceTime: true });

  beforeEach(() => {
    timers.setup();
  });

  afterEach(() => {
    timers.teardown();
  });

  it("debounces input and fetches results", async () => {
    fireEvent.change(input, { target: { value: "test" } });
    await act(async () => {
      vi.advanceTimersByTime(350);
      await vi.runAllTimersAsync();
    });
    expect(mockApi).toHaveBeenCalled();
  });
});
```

#### Pattern C: Static Import with State Reset

```ts
const mockState = vi.hoisted(() => ({ value: null }));
vi.mock("@/hooks/use-data", () => ({
  useData: () => mockState.value,
}));

import { Component } from "../component"; // Single load

beforeEach(() => {
  mockState.value = null; // Reset per test
});
```

#### Pattern D: Shared QueryClient

Use `createMockQueryClient` from `@/test/query-mocks`:

```ts
import { createMockQueryClient } from "@/test/query-mocks";

const QUERY_CLIENT = createMockQueryClient();

afterEach(() => {
  QUERY_CLIENT.clear(); // Clear cache, don't recreate
});
```

#### Pattern E: Node Environment for Export Tests

Use `/** @vitest-environment node */` for tests that only verify exports
(no DOM needed):

```ts
/** @vitest-environment node */
import { describe, expect, it, vi } from "vitest";

// Mock child components to avoid DOM dependencies
vi.mock("../child-component", () => ({ ChildComponent: () => null }));

import * as moduleExports from "../index";

describe("Module exports", () => {
  it("exports expected symbols", () => {
    expect(moduleExports.handler).toBeDefined();
    expect(moduleExports.config).toBeDefined();
    expect(typeof moduleExports.handler).toBe("function");
  });
});
```

## References and Examples

- Real examples: `frontend/src/stores/auth/__tests__/auth-store.test.ts`, `frontend/src/components/trip-card/__tests__/trip-card.test.tsx`, `frontend/src/app/api/chat/__tests__/_handler.test.ts`.
- Pattern catalog incorporated from prior `testing-guide` and `testing-patterns`; treat this file as the authoritative merged source.
