# Route Handler Testing

Standardized test patterns for Next.js route handlers.

## Template

```typescript
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: {
      getUser: async () => ({
        data: { user: { id: "user-1" } },
      }),
    },
  })),
}));

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

// Mock route helpers
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("/api/your-route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("handles request correctly", async () => {
    const mod = await import("../route");
    const req = createMockNextRequest({
      body: { /* your test data */ },
      method: "POST",
      url: "http://localhost/api/your-route",
    });
    const res = await mod.POST(req);
    expect(res.status).toBe(200);
  });
});
```

## Requirements

Test files must follow these patterns:

1. Mock `next/headers` cookies() at the top level before any imports that use it
2. Use `createMockNextRequest` instead of `new Request(...) as NextRequest`
3. Mock `@/lib/supabase/server` to avoid real cookie calls
4. Use `vi.clearAllMocks()` in `beforeEach`, not `vi.resetModules()`
5. Mock route helpers to avoid telemetry and span creation
6. Use `describe("/api/route-name")` for consistent naming
