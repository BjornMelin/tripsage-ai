# Calendar API Route Tests

## Overview

Integration tests for calendar API routes using Vitest with optimized shared mocks and helpers.

## Test Structure

- **Unit Tests**: Schema validation (`src/schemas/__tests__/calendar.test.ts`)
- **Integration Tests**: API route handlers (`src/app/api/calendar/__tests__/`)
- **E2E Tests**: Full UI flows (`e2e/calendar-integration.spec.ts`)

## Shared Test Utilities

### `test-helpers.ts`

Provides reusable mocks and helpers:

- `setupCalendarMocks()` - Configures all mocks for calendar routes
- `buildMockRequest()` - Creates mock NextRequest objects
- `CALENDAR_MOCKS` - Hoisted mocks for shared use
- `MOCK_RATE_LIMIT_SUCCESS/FAILED` - Rate limit result constants

### Usage Example

```typescript
import { setupCalendarMocks, buildMockRequest } from "./test-helpers";

describe("My Route", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("handles request", async () => {
    setupCalendarMocks({ authenticated: true });
    const mod = await import("../route");
    const req = buildMockRequest("http://localhost/api/calendar/status");
    const res = await mod.GET(req);
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
pnpm test:run src/app/api/calendar/__tests__

# Run with coverage
pnpm test:coverage src/app/api/calendar/__tests__

# Run specific test file
pnpm test:run src/app/api/calendar/__tests__/events.test.ts
```

## Best Practices

1. **Always reset modules** in `beforeEach` for test isolation
2. **Use shared helpers** instead of duplicating mock setup
3. **Test edge cases**: unauthorized, rate limits, API errors, empty arrays
4. **Keep tests fast**: Use parallel execution, avoid real network calls
5. **Mock at boundaries**: Mock external APIs (Google, Upstash) not internal code
