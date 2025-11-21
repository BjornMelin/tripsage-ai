# Testing Guide

Testing strategies and patterns for TripSage frontend development.

## Core Principles

- **Test behavior, not implementation:** Focus on user-observable outcomes and avoid coupling to internal details.
- **Deterministic runs:** No random data/timing; use consistent fixtures and clean up shared state.
- **Right level of coverage:** Mix unit, integration, and E2E tests; reserve E2E for critical flows.

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
- Automatic cleanup: timers, React Testing Library, React Query cache reset.

Timer lifecycle enforced for every test:

```ts
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.runOnlyPendingTimers();
  vi.clearAllTimers();
  vi.useRealTimers();
  cleanup();
  resetTestQueryClient();
  vi.restoreAllMocks();
});
```

## Patterns by Area

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
- Factories: `@/test/factories` for consistent mock data.
- React Query: `mockReactQuery` from `@/test/mocks/react-query`.
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
