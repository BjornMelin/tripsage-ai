# Supabase SSR Factory & Patterns (Frontend)

This document describes the unified Supabase client factory patterns used in the Next.js 16 frontend, including server-side rendering (SSR), middleware, browser clients, and Realtime hooks.

## Overview

The frontend uses a centralized Supabase client factory located at `frontend/src/lib/supabase/index.ts` that provides a unified API surface for all Supabase operations. This barrel export eliminates direct submodule imports and ensures consistent usage patterns across the codebase.

## Unified Public API

All Supabase client creation should import from `@/lib/supabase`:

```typescript
import {
  createServerSupabase,
  createMiddlewareSupabase,
  createClient,
  getBrowserClient,
  useSupabase,
  getCurrentUser,
  createCookieAdapter,
  createAdminSupabase,
  type TypedServerSupabase,
  type TypedSupabaseClient,
  type TypedAdminSupabase,
} from "@/lib/supabase";
```

## Client Types

### Server Client (`createServerSupabase`)

**When to use:** React Server Components, Route Handlers, Server Actions, and any server-side code that needs authenticated database access.

**Features:**

- Uses `@supabase/ssr.createServerClient` with Next.js `cookies()` integration
- Zod-validated environment variables via `getServerEnv()`
- OpenTelemetry tracing enabled by default (`supabase.init` span)
- Cookie-based session management for SSR compatibility

**Example:**

```typescript
// In a Route Handler
import { createServerSupabase } from "@/lib/supabase";

export async function GET() {
  const supabase = await createServerSupabase();
  const { data } = await supabase.from("trips").select("*");
  return Response.json(data);
}
```

**Implementation:** `src/lib/supabase/server.ts` wraps the factory with Next.js `cookies()` adapter.

### Middleware Client (`createMiddlewareSupabase`)

**When to use:** Next.js middleware (`middleware.ts`) running in Edge runtime.

**Features:**

- Uses client-safe environment variables only (`getClientEnv()`)
- Default tracing disabled (can be enabled with custom span)
- Custom cookie adapter for Edge runtime compatibility

**Example:**

```typescript
// In middleware.ts
import { createMiddlewareSupabase, getCurrentUser } from "@/lib/supabase";

export async function middleware(request: NextRequest) {
  const supabase = createMiddlewareSupabase({
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookies) => {
        // Handle cookie setting in Edge runtime
      },
    },
  });
  
  // Refresh session once per request
  await getCurrentUser(supabase);
  return NextResponse.next();
}
```

**Note:** Middleware calls `getCurrentUser()` exactly once per request to refresh cookies and sync session state for React Server Components.

### Browser Client (`getBrowserClient`, `useSupabase`, `createClient`)

**When to use:** Client components, React hooks, Zustand stores, and any browser-side code.

**Features:**

- Singleton pattern via `getBrowserClient()` for shared instance
- React hook `useSupabase()` for component usage
- `createClient()` for fresh instances (rarely needed)

**Example:**

```typescript
// In a React component
import { useSupabase } from "@/lib/supabase";

export function MyComponent() {
  const supabase = useSupabase();
  const [data, setData] = useState(null);
  
  useEffect(() => {
    supabase.from("trips").select("*").then(({ data }) => setData(data));
  }, [supabase]);
  
  return <div>{/* ... */}</div>;
}
```

**Implementation:** `src/lib/supabase/client.ts` uses `@supabase/ssr.createBrowserClient`.

### Admin Client (`createAdminSupabase`)

**When to use:** Server-only Route Handlers that need to call SECURITY DEFINER RPCs (e.g., Vault key operations, BYOK endpoints).

**Features:**

- Uses service-role key (`SUPABASE_SERVICE_ROLE_KEY`)
- Bypasses Row Level Security (RLS)
- Never exposed to browser bundles (`"server-only"`)

**Example:**

```typescript
// In /api/keys/route.ts
import { createAdminSupabase } from "@/lib/supabase";
import { insertUserApiKey } from "@/lib/supabase/rpc";

export async function POST(req: Request) {
  const admin = createAdminSupabase();
  // Call SECURITY DEFINER RPC
  await insertUserApiKey(admin, userId, service, key);
}
```

**Security:** Admin client must never be used in browser contexts. Tests mock it appropriately.

## Unified Auth Helper (`getCurrentUser`)

The `getCurrentUser` helper eliminates duplicate `auth.getUser()` calls across middleware, route handlers, and server components.

**Features:**

- Single unified helper for user retrieval
- OpenTelemetry span (`supabase.auth.getUser`) with PII redaction
- User ID always redacted in telemetry (`[REDACTED]`)
- Returns `{ user: User | null, error: Error | null }`

**Example:**

```typescript
import { createServerSupabase, getCurrentUser } from "@/lib/supabase";

export default async function Page() {
  const supabase = await createServerSupabase();
  const { user } = await getCurrentUser(supabase);
  
  if (!user) {
    redirect("/login");
  }
  
  return <div>Welcome, {user.email}</div>;
}
```

**Pattern:** Middleware calls `getCurrentUser()` once per request to refresh cookies. Server components and route handlers reuse the same helper to avoid N+1 queries.

## Cookie Adapter (`createCookieAdapter`)

Utility to convert Next.js `ReadonlyRequestCookies` to `CookieMethodsServer` interface required by the factory.

**When to use:** Custom server contexts where `cookies()` is not directly available.

**Example:**

```typescript
import { createCookieAdapter, createServerSupabase } from "@/lib/supabase";
import { cookies } from "next/headers";

const cookieStore = await cookies();
const adapter = createCookieAdapter(cookieStore);
const supabase = createServerSupabase({ cookies: adapter });
```

## Realtime Hooks

The codebase provides several Realtime hooks that use the browser client:

### `useRealtimeChannel`

Subscribes to a Supabase Realtime topic with connection state management.

```typescript
import { useRealtimeChannel } from "@/hooks/use-realtime-channel";

function MyComponent({ tripId }: { tripId: string }) {
  const { isConnected, error, onBroadcast, sendBroadcast } = 
    useRealtimeChannel(`trip:${tripId}`);
  
  useEffect(() => {
    onBroadcast({ event: "update" }, (payload) => {
      console.log("Received:", payload);
    });
  }, [onBroadcast]);
  
  return <div>{isConnected ? "Connected" : "Disconnected"}</div>;
}
```

### `useWebSocketChat`

Chat-specific Realtime hook with message and typing indicators.

```typescript
import { useWebSocketChat } from "@/hooks/use-websocket-chat";

function ChatComponent({ sessionId }: { sessionId: string }) {
  const { messages, sendMessage, isConnected, typingUsers } = 
    useWebSocketChat({ sessionId, topicType: "session" });
  
  return (
    <div>
      {messages.map((msg) => <div key={msg.id}>{msg.content}</div>)}
      <input onKeyPress={(e) => {
        if (e.key === "Enter") sendMessage(e.currentTarget.value);
      }} />
    </div>
  );
}
```

### `useSupabaseRealtime`

Aggregate hook providing `useTripRealtime(tripId)` and `useChatRealtime(sessionId)` wrappers.

**Implementation:** `src/hooks/use-supabase-realtime.ts` delegates to `useRealtimeChannel` and `useWebSocketChat`.

## Realtime and AI SDK Architectural Invariants

This section documents the architectural invariants that govern how Supabase Realtime and AI SDK v6 are used together in the frontend application. See [Frontend Architecture](./frontend-architecture.md#realtime-and-ai-sdk-responsibilities) for the complete documentation.

### Key Invariants

1. **Transport Separation**: AI SDK v6 (`useChat` + `streamText`) handles all LLM token streaming. Supabase Realtime handles multi-client events (broadcasts, presence, Postgres changes).

2. **Single Low-Level Hook**: All Realtime channel creation flows through `useRealtimeChannel`. Feature code never directly calls `supabase.channel(...)`.

3. **Hooks Own Connections, Stores Own State**: Hooks manage connection lifecycles; Zustand stores hold logical state snapshots.

4. **Security**: Private channels use Realtime Authorization and RLS. Channel topics follow patterns: `user:${userId}`, `session:${sessionId}`, `trip:${tripId}`.

### Current Architecture Violations

The following files violate the "Single Low-Level Hook" invariant and should be refactored in later phases:

- `frontend/src/stores/chat/chat-messages.ts` and `chat-memory.ts`: No direct Supabase calls (uses API endpoints and orchestrator hooks)
- `frontend/src/hooks/use-agent-status-websocket.ts` (line 261): Direct `supabase.channel()` call  
- `frontend/src/hooks/use-trips.ts` (lines 415, 574): Direct `supabase.channel()` calls for Postgres changes

These violations are documented but not yet fixed to maintain Phase 0's non-destructive scope.

## Environment Variables

### Server (`getServerEnv()`)

- `NEXT_PUBLIC_SUPABASE_URL` (required)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (required)
- `SUPABASE_SERVICE_ROLE_KEY` (required for admin client)

### Client (`getClientEnv()`)

- `NEXT_PUBLIC_SUPABASE_URL` (required)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` (required)

**Validation:** Both use Zod schemas via `@/lib/env/server` and `@/lib/env/client`.

## OpenTelemetry Integration

All server clients create OpenTelemetry spans for observability:

- **Client creation:** `supabase.init` span with attributes:
  - `db.name = "tripsage"`
  - `db.system = "postgres"`
  - `db.supabase.operation = "init"`
  - `service.name = TELEMETRY_SERVICE_NAME`

- **Auth operations:** `supabase.auth.getUser` span with:
  - `user.id = "[REDACTED]"` (always redacted)
  - `user.authenticated = boolean`

**Tracing:** Enabled by default for server clients; can be disabled with `enableTracing: false`.

## BYOK / Secure Patterns

### Admin Client Usage

The admin client (`createAdminSupabase`) is server-only and used exclusively for:

- Vault RPCs (`insertUserApiKey`, `getUserApiKey`, `deleteUserApiKey`)
- Gateway configuration RPCs (`upsertUserGatewayBaseUrl`, `deleteUserGatewayBaseUrl`)
- Any SECURITY DEFINER functions that require elevated privileges

**Never use in:**

- Browser components
- Client-side hooks
- Public API routes without authentication checks

### RPC Wrappers

Typed RPC wrappers live in `src/lib/supabase/rpc.ts` and always use the admin client:

```typescript
import { createAdminSupabase } from "@/lib/supabase";
import { insertUserApiKey } from "@/lib/supabase/rpc";

export async function POST(req: Request) {
  const admin = createAdminSupabase();
  const { userId, service, key } = await req.json();
  await insertUserApiKey(admin, userId, service, key);
}
```

## Testing Patterns

### Mocking Server Client

Tests mock the barrel export (`@/lib/supabase`) rather than submodules:

```typescript
import { vi } from "vitest";

vi.mock("@/lib/supabase", () => ({
  createServerSupabase: vi.fn(async () => ({
    auth: { getUser: vi.fn(async () => ({ data: { user: { id: "test" } } })) },
    from: vi.fn(() => ({ select: vi.fn().mockResolvedValue({ data: [], error: null }) })),
  })),
}));
```

### Mocking Browser Client

Browser client mocks use the barrel export:

```typescript
vi.mock("@/lib/supabase", () => ({
  getBrowserClient: vi.fn(() => ({
    channel: vi.fn(() => ({
      subscribe: vi.fn(),
      on: vi.fn(),
      send: vi.fn(),
    })),
  })),
}));
```

## Migration Notes

All imports have been unified to use `@/lib/supabase` barrel export:

- ✅ `@/lib/supabase/server` → `@/lib/supabase`
- ✅ `@/lib/supabase/client` → `@/lib/supabase` (for hooks/components)
- ✅ Test mocks updated to reference barrel export

**Exceptions:** Test files may still import from `@/lib/supabase/client` when mocking implementation details, but this is rare and documented inline.

## Related Documentation

- [Supabase Auth Inventory](../architecture/supabase-auth-inventory.md) - Auth touchpoints across monorepo
- [Frontend Architecture](../architecture/frontend-architecture.md) - Overall frontend structure
- [Supabase Canonical Schema](../architecture/supabase-canonical-schema.md) - Database schema reference

## References

- [Supabase SSR Docs](https://supabase.com/docs/guides/auth/server-side/creating-a-client)
- [Next.js Caching Guide](https://nextjs.org/docs/app/building-your-application/caching)
- [OpenTelemetry JS Docs](https://opentelemetry.io/docs/languages/js/)
