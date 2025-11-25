# Supabase Integration & Authentication

> **Target Audience**: Frontend/backend developers, security engineers, integration leads

This document describes TripSage's Supabase integration patterns, authentication boundaries, and client configurations across the full stack.

## Table of Contents

- [Authentication Flow](#authentication-flow)
- [Server Integration](#server-integration)
- [BYOK (Bring Your Own Keys)](#byok-bring-your-own-keys)
- [Realtime Features](#realtime-features)
- [Security Patterns](#security-patterns)
- [Webhooks Integration](#webhooks-integration)

## Authentication Flow

### Next.js 16 + Supabase SSR

TripSage uses `@supabase/ssr` for cookie-based session management:

- **Middleware**: `middleware.ts` refreshes sessions and syncs cookies for Server Components
- **Server Clients**: `src/lib/supabase/server.ts` wraps Next.js `cookies()` for SSR compatibility
- **Browser Clients**: `src/lib/supabase/client.ts` provides singleton client with Realtime support
- **Route Handlers**: `withApiGuards` factory provides authenticated Supabase clients

**Key Pattern**: Server Components and route handlers get authenticated Supabase clients automatically; Client Components use hooks.

## Server Integration

### Route Handler Authentication

All protected routes use the `withApiGuards` factory for authentication:

```typescript
// src/app/api/trips/route.ts
import { withApiGuards } from '@/lib/api/factory';

export const GET = withApiGuards({
  auth: true,
  rateLimit: { limit: 100, window: '1m' },
})(async ({ supabase, user }) => {
  const { data } = await supabase
    .from('trips')
    .select('*')
    .eq('user_id', user.id);

  return Response.json(data);
});
```

### Server Client Factory

```typescript
// src/lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createServerSupabase() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => cookieStore.getAll(),
        setAll: (cookiesToSet) => {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );
}

## Browser Integration

### Unified Client Factory

All Supabase client creation goes through the unified factory:

```typescript
// src/lib/supabase/index.ts - Barrel export
export * from './server';
export * from './client';
export * from './admin';
export * from './middleware';
```

### Server Client (SSR)

**When to use**: Server Components, Route Handlers, API routes

```typescript
import { createServerSupabase } from '@/lib/supabase';

export async function GET() {
  const supabase = await createServerSupabase();
  const { data } = await supabase.from('trips').select('*');
  return Response.json(data);
}
```

**Features**:

- `@supabase/ssr.createServerClient` with Next.js `cookies()` integration
- Zod-validated environment variables
- OpenTelemetry tracing
- Cookie-based session management

### Browser Client

**When to use**: Client Components, hooks, Realtime subscriptions

```typescript
import { getBrowserClient, useSupabase } from '@/lib/supabase';

// Singleton pattern
const supabase = getBrowserClient();

// React hook
function MyComponent() {
  const supabase = useSupabase();
  // Component logic
}
```

**Features**:

- Singleton pattern for shared instance
- Automatic Realtime authentication
- Browser-compatible environment variables

### Middleware Client

**When to use**: Next.js middleware in Edge runtime

```typescript
// middleware.ts
import { createMiddlewareSupabase } from '@/lib/supabase';

export async function middleware(request: NextRequest) {
  const supabase = createMiddlewareSupabase({
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll: (cookies) => { /* Edge runtime cookie handling */ },
    },
  });

  // Refresh session once per request
  await getCurrentUser(supabase);
  return NextResponse.next();
}
```

## BYOK (Bring Your Own Keys)

### Storage Architecture

User API keys are encrypted in Supabase Vault:

```sql
-- supabase/migrations/20251030000000_vault_api_keys.sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    service TEXT NOT NULL,
    vault_secret_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used TIMESTAMPTZ,
    CONSTRAINT api_keys_user_service_uniq UNIQUE (user_id, service)
);
```

### Access Pattern

1. **Store**: `setUserApiKey(userId, service, key)` RPC encrypts and stores in Vault
2. **Retrieve**: `getUserApiKey(userId, service)` RPC decrypts via SECURITY DEFINER
3. **Validate**: RPCs verify JWT claims and user ownership
4. **Use**: Keys never exposed to client-side code (`"server-only"` imports)

### Provider Resolution

Three-tier resolution strategy in `src/lib/providers/registry.ts`:

1. **User Gateway Key** (highest priority)
   - User's own Vercel AI Gateway API key
   - `getUserApiKey(userId, "gateway")`
   - `createGateway({ apiKey, baseURL })`

2. **Provider BYOK Keys**
   - User-specific provider keys (OpenAI, Anthropic, xAI)
   - Stored encrypted in Vault
   - Resolved server-side only

3. **Team Gateway Fallback**
   - Environment `AI_GATEWAY_API_KEY`
   - Requires user consent (`allowGatewayFallback` setting)

## Realtime Features

### Supabase Realtime

Private channels with RLS enforcement:

```sql
-- supabase/migrations/20251027_01_realtime_policies.sql
-- Enable RLS on realtime.messages for private channels
```

### Channel Conventions

- `user:{sub}`: Only the subject user may broadcast/listen
- `session:{uuid}`: Session owner and trip collaborators
- Topic helpers: `rt_topic_prefix()`, `rt_topic_suffix()`, `rt_is_session_member()`

### Frontend Realtime

```typescript
// src/components/providers/realtime-auth-provider.tsx
useEffect(() => {
  const supabase = getBrowserClient();
  supabase.realtime.setAuth(access_token);

  const channel = supabase.channel('user:123', {
    config: { private: true }
  });

  channel.subscribe();
}, [access_token]);
```

### Hooks Integration

```typescript
// src/hooks/use-supabase-realtime.ts
export function useAgentStatusWebSocket(userId: string) {
  const supabase = useSupabase();

  useEffect(() => {
    const channel = supabase.channel(`user:${userId}`, {
      config: { private: true }
    });

    channel.on('broadcast', { event: 'agent_status' }, (payload) => {
      // Handle agent status updates
    });

    return () => channel.unsubscribe();
  }, [userId]);
}
```

## Security Patterns

### Row Level Security (RLS)

All user data tables use RLS with owner-based policies:

```sql
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
CREATE POLICY "owner_access" ON trips FOR ALL USING (auth.uid() = user_id);
```

### Security Definer RPCs

Vault operations use SECURITY DEFINER functions:

```sql
-- Only service role can access vault
CREATE OR REPLACE FUNCTION get_user_api_key(user_id UUID, service TEXT)
RETURNS TEXT
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
-- Implementation validates user ownership before vault access
$$;
```

### SSR Security

- **Server-only imports**: Sensitive operations use `"server-only"`
- **Dynamic routes**: BYOK routes export `dynamic = "force-dynamic"`
- **Cookie management**: `@supabase/ssr` handles secure cookie syncing

### API Key Security

- **Encryption at rest**: Supabase Vault encryption
- **Access control**: SECURITY DEFINER RPCs with ownership validation
- **Audit logging**: Last used timestamps and access patterns
- **Rotation support**: Keys can be updated without service disruption

## Webhooks Integration

### Database Triggers

```sql
-- supabase/migrations/20251113034500_webhooks_consolidated.sql
CREATE TRIGGER trips_webhook_trigger
  AFTER INSERT OR UPDATE OR DELETE ON trips
  FOR EACH ROW EXECUTE FUNCTION
    supabase_functions.http_request('webhook_url', 'POST', '{"event": "trip_changed"}', '{}');
```

### Vercel Route Handlers

```typescript
// src/app/api/hooks/trips/route.ts
export async function POST(request: NextRequest) {
  // Verify HMAC signature
  const signature = request.headers.get('x-webhook-signature');
  const body = await request.text();
  const isValid = verifyWebhookSignature(body, signature);

  if (!isValid) {
    return NextResponse.json({ error: 'Invalid signature' }, { status: 401 });
  }

  // Process webhook with deduplication
  const payload = JSON.parse(body);
  await processTripWebhook(payload);

  return NextResponse.json({ ok: true });
}
```

### Environment Configuration

```bash
# supabase/config.toml
[functions.webhook_handler]
verify_jwt = false  # Webhooks don't have JWTs

# Vercel environment variables
SUPABASE_WEBHOOK_SECRET=your_webhook_secret
VERCEL_WEBHOOK_URL=https://your-app.vercel.app/api/hooks
```

---

This integration provides secure, scalable authentication and data access patterns across the full TripSage stack.
