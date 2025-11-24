# Testing Guide

Testing strategies and patterns for TripSage frontend development.

## Core Principles

- **Test behavior, not implementation:** Focus on user-observable outcomes and avoid coupling to internal details.
- **Deterministic runs:** No random data/timing; use consistent fixtures and clean up shared state.
- **Right level of coverage:** Mix unit, integration, and E2E tests; reserve E2E for critical flows.
- **Choose the lightest test that proves the behavior:** See the decision tree below.

## Vitest Configuration

TripSage uses a multi-project Vitest setup (see `frontend/vitest.config.ts`). Key traits:

- Five projects: `schemas`, `integration`, `api`, `component`, `unit`.
- `jsdom` for React-facing code; `node` for server-only code.
- Parallelized execution, project-scoped includes/excludes, and coverage thresholds per project.

**Environment directives (MANDATORY):** place at the top of the file.

```ts
/** @vitest-environment jsdom */ // React components, DOM APIs, browser-only hooks
/** @vitest-environment node */  // API routes and pure server utilities
```

## Global Test Setup

Configured in `frontend/src/test-setup.ts` and applied across projects.

- Platform polyfills: Web Streams, ResizeObserver, IntersectionObserver.
- DOM mocks: location, storage APIs, matchMedia.
- Next.js mocks: navigation, image, headers, toast helpers.
- Framework mocks: React Query, Zustand middleware, Supabase.
- MSW server lifecycle: starts once with `onUnhandledRequest: "warn"`, resets after each test.
- Timers: **opt-in** via `withFakeTimers` (`frontend/src/test/utils/with-fake-timers.ts`); global tests run on real timers by default.
- Cleanup: React Testing Library `cleanup()`, React Query cache reset, MSW handler reset.
- Query helpers: prefer `createMockQueryClient` and controllers in `frontend/src/test/query-mocks.tsx` instead of legacy mocks.
- Supabase helpers: use `frontend/src/test/mocks/supabase.ts` to avoid ad-hoc token stubs.

## Patterns by Area

### Test Type Decision Tree

1. **Unit (fastest):** Pure functions, hooks with no I/O, stores. No MSW; use factories and in-memory fakes.
2. **Component:** DOM-facing behavior; use RTL + jsdom; mock network with MSW only.
3. **API Route (node):** Use MSW to intercept external calls; prefer real handler code with mock NextRequest.
4. **Integration:** Multiple modules interacting (e.g., hook + API client); MSW + real providers; avoid mocking internals.
5. **E2E:** Playwright only when UI flow or browser APIs are required.

### MSW 2 Patterns

- Organize handlers by domain under `frontend/src/test/msw/handlers/*`; defaults registered in `handlers/index.ts`.
- Override per test with `server.use(...)`; MSW server starts once in `test-setup.ts` and resets after each test.
- Mirror real API shapes, including error responses (400/404/429/500) and auth headers; assert `FormData` contents for upload endpoints.
- For external providers (Amadeus, Google Places, Stripe, State Dept), prefer MSW over `vi.mock()` and include minimal required fields to satisfy downstream schemas.
- **Handler Composition**: Use `composeHandlers` utility when combining multiple handler sets:

```ts
import { composeHandlers } from "@/test/msw/handlers/utils";
import { googlePlacesHandlers } from "@/test/msw/handlers/google-places";
import { stripeHandlers } from "@/test/msw/handlers/stripe";

const handlerSet = composeHandlers(googlePlacesHandlers, stripeHandlers);
server.use(...handlerSet);
```

- **Single Handler Override**: For single handler overrides, use `server.use()` directly:

```ts
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";

server.use(
  http.post("https://api.stripe.com/v1/payment_intents", () =>
    HttpResponse.json({ id: "pi_test", client_secret: "cs_test" })
  )
);
```

- **Handler Reset**: Handlers are automatically reset after each test via `test-setup.ts`. Avoid redundant `server.resetHandlers()` calls in `beforeEach` unless you need to reset handlers mid-test.

### React Components

```ts
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

describe("TripCard", () => {
  it("displays trip name and allows editing", async () => {
    const mockTrip = { id: "1", name: "Paris Trip" };
    const onEdit = vi.fn();

    render(<TripCard trip={mockTrip} onEdit={onEdit} />);
    expect(screen.getByText("Paris Trip")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /edit/i }));
    expect(onEdit).toHaveBeenCalledWith("1");
  });
});
```

### Custom Hooks

```ts
import { renderHook, waitFor } from "@testing-library/react";

describe("useTrips", () => {
  it("loads trips on mount", async () => {
    const { result } = renderHook(() => useTrips());
    await waitFor(() => expect(result.current.trips).toHaveLength(2));
  });
});
```

### API Route Handlers

```ts
/** @vitest-environment node */
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw/server";
import { createMockNextRequest } from "@/test/route-helpers";

server.use(
  http.post("https://example.com/upstream", () => HttpResponse.json({ ok: true }))
);

const req = createMockNextRequest({ method: "POST", body: { name: "test" } });
const { POST } = await import("@/app/api/example/route");
await expect(POST(req)).resolves.toMatchObject({ status: 200 });
```

### AI SDK v6 (Tests)

- Use `MockLanguageModelV3` and `simulateReadableStream` from `ai/test` (see `frontend/src/test/ai-sdk/*`).
- Define tool schemas with Zod; assert tool calls in tests via `expect(model.calls[0].tools).toEqual(...)` patterns.
- For streaming routes, wrap responses with `toDataStreamResponse()`; in tests, consume with helper utilities to assert chunk ordering.
- Prefer AI SDK helpers over ad-hoc mocks; avoid legacy `useChat`/`useCompletion` patterns.
- Example tool test:

```ts
/** @vitest-environment node */
import { z } from "zod";
import { streamText } from "ai";
import { createMockModel } from "@/test/ai-sdk/mock-model";

const tools = {
  summarize: {
    parameters: z.strictObject({ text: z.string() }),
    execute: ({ text }: { text: string }) => `Summary: ${text.slice(0, 5)}`,
  },
};

const model = createMockModel();
const result = await streamText({ model, messages: [{ role: "user", content: "Hello" }], tools });
expect(model.calls[0]?.tools?.summarize?.parameters).toBeDefined();
```

```ts
/** @vitest-environment node */
```

Mock order (critical):

1. Mock `next/headers` **before** any imports:

    ```ts
    vi.mock("next/headers", () => ({
      cookies: vi.fn(() => Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))),
    }));
    ```

2. Hoisted mocks (before `vi.mock`):

    ```ts
    const LIMIT_SPY = vi.hoisted(() => vi.fn());
    const MOCK_GET_REDIS = vi.hoisted(() => vi.fn<() => Redis | undefined>(() => undefined));
    ```

3. Module mocks (`vi.mock("@/lib/...")`).
4. Dynamic import after mocks:

```ts
const { POST } = await import("@/app/api/keys/validate/route");
```

Rate limiting helpers:

```ts
stubRateLimitEnabled();
MOCK_GET_REDIS.mockReturnValue({} as Redis);

stubRateLimitDisabled();
MOCK_GET_REDIS.mockReturnValue(undefined);
```

Request creation:

```ts
import { createMockNextRequest } from "@/test/route-helpers";

const req = createMockNextRequest({
  body: { keyName: "test-key" },
  cookies: { "sb-access-token": "test-token" },
  headers: { "x-forwarded-for": "127.0.0.1" },
  method: "POST",
});

const res = await POST(req);
```

### Zustand Stores

Store reset + timeout helpers:

```ts
import { resetStore, setupTimeoutMock } from "@/test/store-helpers";

describe("AuthStore", () => {
  let timeoutSpy: { mockRestore: () => void };

  beforeEach(() => {
    resetStore(useAuthStore, { user: null, isLoading: false, error: null });
    timeoutSpy = setupTimeoutMock();
  });

  afterEach(() => {
    timeoutSpy.mockRestore();
  });
});
```

Waiting on store state:

```ts
import { waitForStoreState } from "@/test/store-helpers";

await waitForStoreState(useAuthStore, (state) => !state.isLoading, 5000);
expect(useAuthStore.getState().user).toBeDefined();
```

## Test Utilities

- Provider wrappers: `renderWithProviders` from `@/test/component-helpers`.
- Factories: `@/test/factories` for consistent, schema-valid data.
- React Query: prefer `createMockQueryClient` + controllers in `@/test/query-mocks` or real `QueryClientProvider`.
- Centralized directory: `frontend/src/test/` (helpers, mocks, factories, test-utils, route helpers).

## Running & Debugging Tests

Scripts (see `frontend/package.json` for full list): `test`, `test:run`, `test:unit`, `test:components`, `test:api`, `test:integration`, `test:e2e`, `test:coverage`.

Common commands:

```bash
# Targeted project runs
pnpm test:unit
pnpm test:components
pnpm test:api
pnpm test:integration
pnpm test:e2e

# Single file with explicit project
pnpm test:run --project=api src/app/api/keys/validate/route.test.ts

# Pattern or verbose output
pnpm test -- -t "trip"
pnpm test -- --reporter=verbose

# Coverage
pnpm test -- --coverage --collectCoverageFrom="src/components/TripCard.tsx"
pnpm test:coverage

# Changed files only
pnpm test:changed
```

## End-to-End (Playwright)

Config: `frontend/playwright.config.ts`. Example structure:

```text
e2e/
├── agents-budget-memory.spec.ts
├── calendar-integration.spec.ts
├── dashboard-functionality.spec.ts
├── error-boundaries-loading.spec.ts
```

Commands:

```bash
pnpm test:e2e
pnpm test:e2e --project=chromium
pnpm test:e2e --headed
pnpm test:e2e --reporter=html
```

## Coverage and Quality Gates

- Target: 85%+ overall; branches 85%, functions 90%, lines 90%, statements 90%; critical paths at 100%.
- Pre-commit checks: `pnpm biome:check`, `pnpm biome:fix`, `pnpm type-check`.
- CI: `pnpm test:ci` uses the threads pool; use `test:coverage` for v8 coverage; shard via `test:coverage:shard` when needed.

## Organization & Naming

Recommended layout:

```text
src/
├── components/
│   └── feature/
│       ├── Component.tsx
│       └── __tests__/
│           ├── Component.test.tsx
│           └── Component.integration.test.tsx
├── stores/
│   └── feature-store.ts
│   └── __tests__/
│       └── feature-store.test.ts
└── app/api/
    └── endpoint/
        ├── route.ts
        └── __tests__/
            └── route.test.ts
```

Naming:

- `*.test.ts(x)` – unit tests.
- `*.spec.ts(x)` – integration tests.
- `*.integration.test.ts(x)` – end-to-end integration.
- `*.e2e.*` – Playwright.

## Examples

Real implementations to reference:

- Store: `frontend/src/stores/auth/__tests__/auth-store.test.ts`.
- Component: `frontend/src/components/trip-card/__tests__/trip-card.test.tsx`.
- API route: `frontend/src/app/api/chat/__tests__/_handler.test.ts`.

## Why This Setup

- Consistent patterns and centralized mocks reduce maintenance.
- Shared helpers improve reliability and speed authoring.
- Multi-project Vitest configuration keeps tests isolated and performant while covering React, Next.js, and external API interactions.
- MSW + AI SDK helpers keep network and model behavior realistic without brittle `vi.mock` chains.

### Fake Timers (Opt-in)

- Default tests run on real timers; use `withFakeTimers` helper from `frontend/src/test/utils/with-fake-timers.ts` for timer-driven code.
- Avoid global `vi.useFakeTimers()`; ensure timers are restored in the helper.
- Example:

```ts
import { withFakeTimers } from "@/test/utils/with-fake-timers";

it("retries after delay", withFakeTimers(async () => {
  await doAsyncWork();
  vi.advanceTimersByTime(1000);
  expect(callback).toHaveBeenCalled();
}));
```

### Factories

- Use `@/test/factories` for consistent, schema-valid fixtures; reset counters when determinism is needed.
- Calendar events: `createMockCalendarEvent` for calendar/ICS tests.
- Supabase users/trips/search: prefer factories over inline objects.
- Extend factories in `frontend/src/test/factories/*` to keep types close to schemas.

### Performance & Anti-Patterns

- Keep tests under 3s/file; profile with `vitest --inspect` when slow.
- Prefer MSW over `vi.mock` for HTTP; avoid mocking `fetch`.
- No global fake timers; no shared mutable singletons between tests.
- Keep component tests small; avoid snapshot reliance for dynamic content.
- Clean up timers, intervals, and stores in `afterEach`.

### Additional References

- Pattern catalog and decision tables: `docs/developers/testing-patterns.md`.
- CI knobs: see `package.json` scripts `test:ci`, `test:coverage`, and `test:coverage:shard`.
