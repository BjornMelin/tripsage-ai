# Calendar API Route Tests

## Overview

Integration tests for calendar API routes using Vitest with optimized shared mocks and helpers.

## Test Structure

- **Unit Tests**: Schema validation (`src/schemas/__tests__/calendar.test.ts`)
- **Integration Tests**: API route handlers (`src/app/api/calendar/__tests__/`)
- **E2E Tests**: Full UI flows (`e2e/calendar-integration.spec.ts`)

## Shared Test Utilities

These tests use the shared helpers in `src/test/helpers/`:

- `@/test/helpers/api-route` for rate-limit + auth guards
- `@/test/helpers/route` for building `NextRequest` and route contexts

### Usage Example (current style)

```typescript
import {
  resetApiRouteMocks,
  enableApiRouteRateLimit,
  mockApiRouteRateLimitOnce,
} from "@/test/helpers/api-route";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";

describe("My Route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    resetApiRouteMocks();
  });

  it("handles request", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      method: "GET",
      url: "http://localhost/api/calendar/status",
    });
    const res = await mod.GET(req, createRouteParamsContext());
    expect(res.status).toBe(200);
  });
});
```

## Performance Optimizations

1. **Hoisted Mocks**: Uses `vi.hoisted()` for shared mocks across tests
2. **Parallel Execution**: Tests run in parallel by default (Vitest threads pool)
3. **Shared Setup**: Common mocks reused via `setupCalendarMocks()`
4. **Fast Timeouts**: 5s test timeout, 8s hook timeout

## Coverage Targets

- Lines: 90%
- Statements: 90%
- Functions: 90%
- Branches: 85%

## Running Tests

```bash
# Run all calendar tests
pnpm test --project=api src/app/api/calendar/__tests__

# Run with coverage
pnpm test:coverage --project=api src/app/api/calendar/__tests__

# Run specific test file (IMPORTANT: use --project=api to limit scope)
pnpm test --project=api src/app/api/calendar/__tests__/events.test.ts
```

**Note**: When running a specific test file, always include `--project=api` to limit execution to the API project only. Without this flag, Vitest will run all matching projects (api, component, unit, etc.), causing the entire test suite to execute.

## Best Practices

1. **Always reset modules** in `beforeEach` for test isolation
2. **Use shared helpers** instead of duplicating mock setup
3. **Test edge cases**: unauthorized, rate limits, API errors, empty arrays
4. **Keep tests fast**: Use parallel execution, avoid real network calls
5. **Mock at boundaries**: Mock external APIs (Google, Upstash) not internal code
