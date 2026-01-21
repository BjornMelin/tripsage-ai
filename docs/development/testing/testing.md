# Testing

Authoritative testing reference for TripSage frontend.

## Principles and Coverage

- Test behavior, not implementation; keep runs deterministic.
- Choose the lightest test that proves behavior: unit → component → API → integration → E2E.
- Coverage is enforced via:
  - Global baseline thresholds in `vitest.config.ts`
  - Critical-surface thresholds in `scripts/check-coverage-critical.mjs` (run by `pnpm test:coverage`)
- **Incremental targets:** See [Coverage Milestones](./coverage-milestones.md) for current baseline, enforced thresholds, and raise plans.
- Layout: co-locate tests in `__tests__/`; use `*.test.ts(x)` (unit), `*.spec.ts(x)` (integration), `*.integration.test.ts(x)` (cross-module), `*.e2e.*` (Playwright).

## Vitest Projects and Environments

- Projects in `vitest.config.ts`: `schemas`, `integration`, `api`, `component`, `unit`.
- Environment directive (mandatory first line):
  - `/** @vitest-environment jsdom */` — React, DOM, browser hooks
  - `/** @vitest-environment node */` — API routes, server utilities
- Commands: `pnpm test`, `pnpm test:affected`, `pnpm test -- --project=<name>`, `pnpm test:coverage`.
  - `test:affected` runs tests related to changed files (e.g., `pnpm test:affected -- --base=main` for post-commit verification).

## Decision Table

| Scenario | Test type | Tools |
| --- | --- | --- |
| Pure functions, selectors, reducers | Unit | plain asserts |
| Hooks with DOM/React state | Component (jsdom) | RTL `renderHook`, factories |
| Hooks/services calling HTTP | Component/Integration | MSW, `createMockQueryClient` |
| Next.js route handlers | API (node) | MSW, `createMockNextRequest` |
| Multi-module flows | Integration | MSW + real providers |
| Browser-only flows | E2E (Playwright) | minimal set |

## Global Test Setup

Vitest uses split setup files for Node and DOM projects:

- `src/test/setup-node.ts` (all projects):
  - MSW server lifecycle (unhandled requests: `warn` locally, `error` in CI)
  - Web Streams polyfills
  - Safe default env vars for client components in tests
  - Fake timer cleanup (opt-in via `withFakeTimers`)
- `src/test/setup-jsdom.ts` (component project only):
  - `@testing-library/jest-dom` matchers
  - Next.js shims (`next/navigation`, `next/image`, toast)
  - DOM mocks (storage, matchMedia, Resize/IntersectionObserver, CSS.supports)
  - RTL cleanup + React Query cache reset

MSW server starts once; handlers reset after each test. Avoid redundant `server.resetHandlers()` unless resetting mid-test.

### Fake Timers

Real timers are default. Use helpers for clock control:

```ts
/** @vitest-environment node */
import { withFakeTimers, createFakeTimersContext } from "@/test/utils/with-fake-timers";

// Per-test wrapper:
it("retries after delay", withFakeTimers(async () => {
  await action();
  vi.advanceTimersByTime(1_000);
  expect(retrySpy).toHaveBeenCalled();
}));

// Per-suite (with MSW compatibility):
const timers = createFakeTimersContext({ shouldAdvanceTime: true });
beforeEach(timers.setup);
afterEach(timers.teardown);
```

Never use global `vi.useFakeTimers()` in `beforeEach`/`afterEach`.

### MFA Tests

Set `MFA_BACKUP_CODE_PEPPER` (≥16 chars) or `SUPABASE_JWT_SECRET`. `validateMfaConfig()` enforces this outside `NODE_ENV=test`; missing values fail fast in server code.

Mock admin client:

```ts
/** @vitest-environment node */
beforeEach(() => {
  vi.doMock("@/lib/supabase/admin", () => ({
    getAdminSupabase: vi.fn(() => ({
      from: vi.fn(() => ({
        select: vi.fn().mockReturnThis(),
        update: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        maybeSingle: vi.fn(),
      })),
      rpc: vi.fn(),
    })),
  }));
});
```

## Mocking Strategy

Order matters:

1. **Network:** MSW only; never mock `fetch` directly. Handlers in `src/test/msw/handlers/*`.
2. **AI SDK:** `MockLanguageModelV3`, `simulateReadableStream`, `createMockModelWithTracking` from `src/test/ai-sdk/*`.
3. **React Query:** `createMockQueryClient`, `createControlledQuery/Mutation` from `@/test/helpers/query`.
4. **Supabase:** `@/test/mocks/supabase`; prefer MSW for REST/RPC.
5. **Timers:** `withFakeTimers` or `createFakeTimersContext`; never global.
6. **Mock order:** mock `next/headers` **before** importing modules that read cookies; use `vi.hoisted()` for spies.
7. **Rate-limiting:** `stubRateLimitEnabled/Disabled` and `MOCK_GET_REDIS` per test.

## MSW Patterns

```ts
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";

// Override per test
server.use(
  http.get("https://api.example.com/items", () =>
    HttpResponse.json({ error: "fail" }, { status: 500 })
  )
);
```

Organize handlers by domain; compose with `composeHandlers`. Cover success + error cases (400/404/429/500).

## Upstash Testing

- **Unit:** `setupUpstashMocks()` from `@/test/upstash/redis-mock`; call `redis.__reset()` and `ratelimit.__reset()` in `beforeEach`.
- **HTTP:** `@/test/msw/handlers/upstash.ts` for pipeline/ratelimit/QStash.
- **Emulator:** `UPSTASH_USE_EMULATOR=1` + `UPSTASH_EMULATOR_URL` + `UPSTASH_QSTASH_DEV_URL`; helper in `@/test/upstash/emulator.ts`.
- **Smoke:** `pnpm test:upstash:smoke` with `UPSTASH_SMOKE=1`.

## AI SDK v6 Tests

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

Complete pattern with all required mocks. Avoid `vi.resetModules()`.

```ts
/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/helpers/route";

// 1. Mock cookies BEFORE imports that read them
vi.mock("next/headers", () => ({
  cookies: vi.fn(() => Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))),
}));

// 2. Hoisted spies for rate-limiting
const LIMIT_SPY = vi.hoisted(() => vi.fn());
vi.mock("@/lib/rate-limit", () => ({
  stubRateLimitEnabled: () => LIMIT_SPY(true),
}));

// 3. Supabase/telemetry mocks
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
  })),
}));

vi.mock("@/lib/api/route-helpers", async () => ({
  ...(await vi.importActual("@/lib/api/route-helpers")),
  withRequestSpan: vi.fn((_n, _a, fn) => fn()),
}));

describe("/api/example", () => {
  beforeEach(() => vi.clearAllMocks());

  it("handles POST", async () => {
    const { POST } = await import("../route");
    const req = createMockNextRequest({
      method: "POST",
      url: "http://localhost/api/example",
      body: { key: "value" },
      headers: { "x-forwarded-for": "127.0.0.1" },
    });
    const res = await POST(req);
    expect(res.status).toBe(200);
  });
});
```

## Zustand Stores

```ts
import { resetStore, waitForStoreState } from "@/test/helpers/store";

beforeEach(() => resetStore(useAuthStore, { user: null, isLoading: false, error: null }));
await waitForStoreState(useAuthStore, (s) => !s.isLoading, 5000);
```

Use `setupTimeoutMock` for timer-backed stores.

## Forms

Trigger validation via blur events, then wait for error messages:

```tsx
/** @vitest-environment jsdom */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

it("shows validation error", async () => {
  const user = userEvent.setup();
  render(<TripForm />);
  await user.type(screen.getByLabelText(/title/i), "ab");
  fireEvent.blur(screen.getByLabelText(/title/i));
  await waitFor(() => expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument());
});
```

Hook testing with `renderHook`:

```tsx
import { renderHook, act } from "@testing-library/react";
import { useZodForm } from "@/hooks/use-zod-form";

it("validates all fields with trigger()", async () => {
  const { result } = renderHook(() =>
    useZodForm({ schema, defaultValues: { title: "" }, mode: "onChange" })
  );
  let isValid: boolean;
  await act(async () => {
    isValid = await result.current.trigger();
  });
  expect(isValid!).toBe(false);
});
```

## Supabase local (when needed)

Most unit/component/API tests do **not** require a running database because Supabase calls are mocked or handled via MSW.

Use Supabase local for:

- Playwright E2E flows that sign in and mutate real data
- Any integration tests that intentionally hit PostgREST/RPC endpoints

Standard workflow:

- `pnpm supabase:bootstrap` (or `pnpm supabase:start` + `pnpm supabase:db:reset`)
- For deterministic data that covers more routes and UI surfaces:
  - `pnpm supabase:reset:dev` (for local UI dev)
- Copy values from `pnpm supabase:status` into `.env.local` (see `docs/runbooks/supabase.md`)
- For local sign-up confirmation, use Inbucket/Mailpit at `http://localhost:54324`

> Note: the default `pnpm test:e2e:*` Playwright config uses `scripts/e2e-webserver.mjs`, which starts a mock Supabase Auth server on `http://127.0.0.1:54329` and does not require local Supabase. Use local Supabase when you want to validate real DB/RLS/RAG/attachments behavior end-to-end.

### Submission testing

- Use `handleSubmitSafe` and `vi.fn()` to assert submits occur once for valid data and are skipped for invalid data.
- `validationState` is a submit-time summary updated by `handleSubmitSafe`; for on-change/on-blur validation, assert via `formState` or `await trigger()`.
- Example:

```tsx
it("submits with telemetry span", async () => {
  const submit = vi.fn();
  const { result } = renderHook(() => useZodForm({ schema, defaultValues: { title: "Trip" } }));
  // imports: useZodForm, withClientTelemetrySpan

  await act(async () => {
    await result.current.handleSubmitSafe(async (data) => {
      await withClientTelemetrySpan("trip.create", {}, async () => submit(data));
    })();
  });

  expect(submit).toHaveBeenCalledWith({ title: "Trip" });
});
```

### Wizard navigation testing

- For multi-step forms, drive step state in the component and gate progress with
  `await form.trigger([...fieldNames])` (or `trigger()` for the full form).

## Server Actions

```ts
/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ redirect: vi.fn(), revalidatePath: vi.fn() }));
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { getUser: async () => ({ data: { user: { id: "user-1" } } }) },
    from: vi.fn(() => ({
      insert: vi.fn().mockReturnThis(),
      select: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ data: { id: "trip-1" }, error: null }),
    })),
  })),
}));

import { createTripAction } from "../actions";

describe("createTripAction", () => {
  beforeEach(() => vi.clearAllMocks());

  it("throws on invalid input", async () => {
    await expect(createTripAction({ title: "" })).rejects.toThrow(/validation/i);
  });

  it("creates trip", async () => {
    const result = await createTripAction({ title: "Paris Trip", destination: "Paris" });
    expect(result).toMatchObject({ id: "trip-1" });
  });
});
```

## Factories and Data

Use `@/test/factories/*` for schema-valid fixtures. Reset counters when determinism required.

## Performance Benchmarks

- Command: `pnpm test:benchmark`
- Thresholds: suite <20s; per-file fail >3.5s, warn >500ms
- Override via env: `BENCHMARK_SUITE_THRESHOLD_MS`, `BENCHMARK_FILE_FAIL_MS`, `BENCHMARK_FILE_WARNING_MS`
- Artifacts: `.vitest-reports/vitest-report.json`, `benchmark-summary.json`
- Silence telemetry: `TELEMETRY_SILENT=1`

## Running and Debugging

```bash
pnpm test                               # all tests (single run)
pnpm exec vitest                        # watch mode (local)
pnpm test:unit                          # unit tests only
pnpm test:components                    # component tests only
pnpm test:api                           # API route tests only
pnpm test:integration                   # integration tests
pnpm test --project=api                 # single project
pnpm test src/path/to/file.test.ts      # single file
pnpm test -- -t "pattern"               # by name pattern
pnpm test:coverage                      # with coverage
pnpm test:changed                       # only changed files
```

## CI / Quality Gates

- Pre-commit: `pnpm biome:check`, `pnpm type-check`, `pnpm test:affected`
- CI: `pnpm test:ci`, `pnpm test:coverage`, `test:coverage:shard`

> **Tip:** Run `pnpm biome:fix` locally to auto-fix lint issues before committing.

## Playwright (E2E)

- Config: `playwright.config.ts`; specs in `e2e/`
- Commands:
  - `pnpm test:e2e:chromium` (recommended local default)
  - `pnpm test:e2e` (all configured browsers)
  - `pnpm exec playwright test --project=chromium --headed` (use `pnpm exec` for Playwright CLI flags; avoid `pnpm test:* -- <flags>`)
- Fresh machine setup: `pnpm exec playwright install chromium` (Linux deps: `pnpm exec playwright install-deps chromium`)
- Reserve for flows requiring real browser execution.

## Performance and Anti-Patterns

Keep tests under ~3s/file; profile slow cases with `vitest run --project=<name> --inspect`.

| Pattern | When | Technique |
| --- | --- | --- |
| Hoisted mocks | Avoid `vi.resetModules()` | `vi.hoisted(() => vi.fn())` + static import |
| Fake timers + MSW | Network + debounce | `createFakeTimersContext({ shouldAdvanceTime: true })` |
| State reset | Per-test isolation | `vi.hoisted(() => ({ value: null }))` + reset in `beforeEach` |
| Shared QueryClient | Reduce instantiation | `createMockQueryClient()` + `clear()` in `afterEach` |
| Node for exports | No DOM needed | `/** @vitest-environment node */` |

| Avoid | Use instead |
| --- | --- |
| Global `vi.useFakeTimers()` | `withFakeTimers` or `createFakeTimersContext` |
| `new QueryClient()` | `createMockQueryClient()` |
| Barrel imports `@/test/*` | Specific paths (see table below) |
| Inline query result objects | `createMockUseQueryResult()` |
| Mocking `fetch` directly | MSW handlers |
| Snapshot tests for dynamic UI | Explicit assertions |
| Shared mutable singletons | Reset in `afterEach` |

## Canonical Import Paths

| Category | Path | Helpers |
| --- | --- | --- |
| Component rendering | `@/test/test-utils` | `renderWithProviders` |
| QueryClient | `@/test/helpers/query` | `createMockQueryClient` |
| Query/Mutation mocks | `@/test/helpers/query` | `createControlledQuery`, `createControlledMutation` |
| Route request mocks | `@/test/helpers/route` | `createMockNextRequest`, `getMockCookiesForTest` |
| API route auth | `@/test/helpers/api-route` | `mockApiRouteAuthUser`, `resetApiRouteMocks` |
| Supabase mocks | `@/test/mocks/supabase` | `createMockSupabaseClient` |
| Upstash mocks | `@/test/upstash/redis-mock` | `setupUpstashMocks` |
| Fake timers | `@/test/utils/with-fake-timers` | `withFakeTimers`, `createFakeTimersContext` |
| Store helpers | `@/test/helpers/store` | `resetStore`, `waitForStoreState` |
| Schema assertions | `@/test/helpers/schema` | `expectValid`, `expectParseError` |
| Factories | `@/test/factories/*` | `createTrip`, `createAuthUser`, etc. |

## References

- Auth store: `src/stores/auth/__tests__/auth-store.test.ts`
- Trip card: `src/components/trip-card/__tests__/trip-card.test.tsx`
- Chat handler: `src/app/api/chat/__tests__/_handler.test.ts`
- Search page: `src/app/(dashboard)/search/__tests__/page.test.tsx`
- Server actions: `src/app/(dashboard)/search/activities/actions.test.ts`
