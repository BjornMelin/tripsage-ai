# API Factory Migration

Migration guide for adopting the withApiGuards factory pattern.

## Overview

The `withApiGuards` factory centralizes authentication, rate limiting,
error handling, and telemetry for API routes. This migration removes
duplicate code and keeps security patterns consistent.

## Migration Process

### Before (Inline Pattern)

```typescript
import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

export async function GET(req: NextRequest) {
  // Authentication
  const supabase = await createServerSupabase();
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error || !user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // Rate limiting
  const redis = Redis.fromEnv();
  const limiter = new Ratelimit({ /* config */ });
  const { success } = await limiter.limit(`user:${user.id}`);
  if (!success) {
    return NextResponse.json({ error: "Rate limited" }, { status: 429 });
  }

  // Handler logic
  const data = await getData(user.id);
  return NextResponse.json(data);
}
```

### After (Factory Pattern)

```typescript
import { withApiGuards } from "@/lib/api/factory";
import { NextResponse } from "next/server";

export const GET = withApiGuards({
  auth: true,
  rateLimit: "myroute:read",
  telemetry: "myroute.get"
})(async (req, { supabase, user }) => {
  const data = await getData(user!.id);
  return NextResponse.json(data);
});
```

## Migration Steps

### 1. Update Imports

```typescript
// Remove these imports
- import { createServerSupabase } from "@/lib/supabase/server";
- import { Ratelimit } from "@upstash/ratelimit";
- import { Redis } from "@upstash/redis";

// Add this import
+ import { withApiGuards } from "@/lib/api/factory";
```

### 2. Configure Rate Limiting

Add your route to `src/lib/ratelimit/routes.ts`:

```typescript
export const ROUTE_RATE_LIMITS = {
  // ... existing routes
  "myroute:read": { limit: 60, window: "1 m" },
  "myroute:write": { limit: 10, window: "1 m" },
} as const;
```

### 3. Update Handler Function

```typescript
// Before
export async function GET(req: NextRequest) {
  // auth, rate limiting, error handling code...
  const data = await handlerLogic();
  return NextResponse.json(data);
}

// After
export const GET = withApiGuards({
  auth: true,                    // Require authentication
  rateLimit: "myroute:read",     // Rate limit key
  telemetry: "myroute.get"       // Span name
})(async (req, { supabase, user }) => {
  const data = await handlerLogic(user!.id);
  return NextResponse.json(data);
});
```

### 4. Update Tests

```typescript
// Before
import { createMockRequest } from "@/test/route-helpers";

describe("GET /api/myroute", () => {
  it("returns data", async () => {
    const req = createMockRequest({ method: "GET" });
    // Manual auth/rate limit mocking...
  });
});

// After
import { setupApiTestMocks, createMockRequest } from "@/test/api-helpers";

describe("GET /api/myroute", () => {
  let cleanup: () => void;

  beforeEach(() => {
    cleanup = setupApiTestMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("returns data", async () => {
    const req = createMockRequest({ method: "GET" });
    const res = await GET(req);
    expect(res.status).toBe(200);
  });
});
```

## Factory Configuration

### Authentication Options

- `auth: true` - Require authenticated user
- `auth: false` - No authentication required

### Rate Limiting Options

- `rateLimit: "key"` - Use predefined rate limit from ROUTE_RATE_LIMITS
- `rateLimit: undefined` - No rate limiting

### Telemetry Options

- `telemetry: "span.name"` - Custom span name for observability
- `telemetry: undefined` - No telemetry

## Error Handling

### Automatic Error Responses

- **401 Unauthorized**: When auth required but user not authenticated
- **429 Rate Limited**: When rate limit exceeded with Retry-After header
- **500 Internal Error**: When handler throws, logged with telemetry

### Custom Errors

Throw or return NextResponse for custom error responses:

```typescript
export const POST = withApiGuards({ auth: true })(
  async (req, { supabase, user }) => {
    const body = await req.json();
    if (!body.name) {
      return NextResponse.json(
        { error: "Name required" },
        { status: 400 }
      );
    }
    // ... handler logic
  }
);
```

## Migration Checklist

> **Note**: This is a reusable migration template. Copy and complete for each route migration.

### Pre-Migration

- [ ] Review factory documentation
- [ ] Add rate limit config to `routes.ts`
- [ ] Update test imports to use centralized helpers
- [ ] Backup current route implementation

### During Migration

- [ ] Replace imports
- [ ] Wrap handler with withApiGuards
- [ ] Remove inline auth/rate limiting code
- [ ] Update error handling if needed

### Post-Migration

- [ ] Run tests to verify functionality
- [ ] Check telemetry spans are working
- [ ] Verify rate limiting behavior
- [ ] Remove any unused imports

## Exception Cases

### When Not to Use Factory

Routes may skip the factory if they require custom handling that the
factory cannot support:

1. **Webhook Receivers** (`/api/hooks/*`): Need signature verification before processing
2. **Background Jobs** (`/api/jobs/*`): Custom authentication, QStash signature verification
3. **Complex Requirements**: When factory cannot support the specific pattern

Document exceptions in `docs/architecture/route-exceptions.md` with
justification.

## Rollback Plan

If issues arise after migration:

1. Revert to previous implementation
2. Document what broke in the factory
3. Either fix the factory or document the exception
4. Re-attempt migration or keep as exception

## Benefits

- Reduces inline authentication and rate limiting code
- Ensures consistent error handling and telemetry
- Centralizes security patterns across routes
- Simplifies testing through shared mocks and helpers
