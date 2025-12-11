# Testing

Authoritative testing reference for TripSage frontend.

## Principles and Coverage

- Test behavior, not implementation; keep runs deterministic.
- Choose the lightest test that proves behavior: unit → component → API → integration → E2E.
- Coverage: ≥85% overall (branches 85%, functions 90%, lines 90%, statements 90%); critical paths 100%.
- Layout: co-locate tests in `__tests__/`; use `*.test.ts(x)` (unit), `*.spec.ts(x)` (integration), `*.integration.test.ts(x)` (cross-module), `*.e2e.*` (Playwright).

## Vitest Projects and Environments

- Projects in `vitest.config.ts`: `schemas`, `integration`, `api`, `component`, `unit`.
- Environment directive (mandatory first line):
  - `/** @vitest-environment jsdom */` — React, DOM, browser hooks
  - `/** @vitest-environment node */` — API routes, server utilities
- Commands: `pnpm test:run`, `test:run --project=<name>`, `test:coverage`.

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

`src/test-setup.ts` provides:

- Polyfills: Web Streams, ResizeObserver
- DOM mocks: location, storage, matchMedia
- Next.js mocks: navigation, image, headers, toast
- MSW server lifecycle (`onUnhandledRequest: "warn"`)
- Automatic cleanup: RTL, React Query cache, MSW handlers

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

it("validates all fields", async () => {
  const { result } = renderHook(() => useZodForm({ schema, defaultValues: { title: "" } }));
  let validation: Awaited<ReturnType<typeof result.current.validateAllFields>>;
  await act(async () => { validation = await result.current.validateAllFields(); });
  expect(validation!.success).toBe(false);
});
```

### Submission testing

- Use `handleSubmitSafe` and `vi.fn()` to assert submits occur once for valid data and are skipped for invalid data.
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

- With `enableWizard` or `useZodFormWizard`, assert step gating and navigation helpers.

```tsx
it("prevents advancing when step invalid", async () => {
  const { result } = renderHook(() =>
    useZodForm({
      schema: fullSchema,
      enableWizard: true,
      wizardSteps: ["basics", "dates"],
      stepValidationSchemas: [basicsSchema, datesSchema],
      defaultValues: { title: "", startDate: "" },
    })
  );

  await act(async () => result.current.wizardActions.goToNext());
  expect(result.current.wizardState.currentStep).toBe(0);

  await act(async () => result.current.setValue("title", "My Trip"));
  await act(async () => result.current.wizardActions.validateAndGoToNext());
  expect(result.current.wizardState.currentStep).toBe(1);
});
```

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
pnpm test:run                           # all tests
pnpm test:unit                          # unit tests only
pnpm test:components                    # component tests only
pnpm test:api                           # API route tests only
pnpm test:integration                   # integration tests
pnpm test:run --project=api             # single project
pnpm test:run src/path/to/file.test.ts  # single file
pnpm test -- -t "pattern"               # by name pattern
pnpm test:coverage                      # with coverage
pnpm test:changed                       # only changed files
```

## CI / Quality Gates

- Pre-commit: `pnpm biome:check`, `pnpm type-check`, targeted `test:run`
- CI: `pnpm test:ci`, `pnpm test:coverage`, `test:coverage:shard`

## Playwright (E2E)

- Config: `playwright.config.ts`; specs in `e2e/`
- Commands: `pnpm test:e2e`, `--project=chromium`, `--headed`
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
