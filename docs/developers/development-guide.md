# Development Guide

TripSage development patterns, architecture, and implementation details.

**Import Paths**: All TypeScript imports must follow the [Import Path Standards](import-paths.md). Use semantic aliases (`@schemas/*`, `@domain/*`, `@ai/*`) for architectural boundaries and `@/*` for generic src-root imports.

## Architecture Overview

### Technology Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| **Framework** | Next.js 16 | Server route handlers, React Server Components |
| **React** | React 19 | UI with concurrent features |
| **Language** | TypeScript 5.9.x | Strict mode, full type safety |
| **AI** | AI SDK v6 (`ai@6.0.0-beta.105`) | `streamText`, `generateObject`, tool calling |
| **Database** | Supabase PostgreSQL | RLS, pgvector, Realtime |
| **Cache** | Upstash Redis | HTTP REST API, rate limiting |
| **Auth** | Supabase SSR | Cookie-based sessions |
| **Validation** | Zod v4 | Request/response schemas |
| **State** | Zustand + TanStack Query | Client state + server state |
| **Styling** | Tailwind CSS v4 | CSS-first configuration |
| **Observability** | OpenTelemetry | Distributed tracing, metrics |

### Project Structure

```text
frontend/src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Auth route group
│   ├── (dashboard)/       # Protected route group
│   ├── api/               # Route handlers
│   │   ├── agents/        # AI agent endpoints
│   │   ├── chat/          # Chat endpoints
│   │   ├── trips/         # Trip CRUD
│   │   └── ...            # Other API routes
│   ├── auth/              # Auth pages (callback, confirm, etc.)
│   ├── chat/              # Chat UI pages
│   ├── settings/          # Settings pages
│   └── ...                # Other pages
├── ai/                     # AI SDK tooling
│   ├── lib/               # Tool factory, utilities
│   ├── models/            # Provider registry
│   └── tools/             # AI tools (server/client)
├── components/            # Reusable UI components
│   ├── admin/            # Admin components
│   ├── auth/             # Auth components
│   ├── features/         # Feature-specific components
│   ├── ui/               # Base UI components
│   └── ...               # Other component categories
├── domain/                # Domain logic
│   ├── accommodations/   # Accommodation domain
│   ├── activities/       # Activity domain
│   ├── amadeus/          # Amadeus integration
│   ├── flights/          # Flight domain
│   └── schemas/          # Zod validation schemas
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities and configurations
│   ├── api/              # Route handler factory
│   ├── agents/           # Agent implementations
│   ├── cache/            # Caching utilities
│   ├── calendar/         # Calendar integration
│   ├── providers/        # AI provider types
│   ├── ratelimit/        # Rate limit configuration
│   ├── supabase/         # Supabase client factories
│   ├── telemetry/        # Observability helpers
│   └── ...               # Other utilities
├── prompts/               # AI prompt templates
├── stores/                # Zustand state management
│   ├── auth/             # Auth stores
│   ├── chat/             # Chat stores
│   └── ...               # Other stores
├── styles/                # Global styles
├── test/                  # Test utilities and mocks
│   ├── factories/        # Test data factories
│   ├── mocks/            # Mock implementations
│   ├── msw/              # MSW handlers
│   └── ...               # Other test utilities
└── test-utils/            # Shared test utilities
```

### Database Schema

Core entities with Row Level Security:

- **users**: Authentication and profile data (Supabase Auth)
- **trips**: Travel plans with destinations and dates
- **chat_sessions**: AI chat history with messages
- **memories**: User preferences and context (pgvector)
- **api_keys**: User-provided BYOK API keys (encrypted in Vault)
- **calendar_events**: Trip calendar events

## Frontend Development

### Stack Summary

- **Framework**: Next.js 16 with App Router
- **React**: React 19 with concurrent features
- **Language**: TypeScript with strict mode
- **Styling**: Tailwind CSS v4
- **State**: Zustand for client state
- **Data**: TanStack Query for server state
- **Forms**: React Hook Form with Zod validation
- **AI**: AI SDK v6 for streaming and tool calling

### Data Fetching

#### TanStack Query Integration

```typescript
// lib/hooks/use-trips.ts
import { useQuery, useMutation } from "@tanstack/react-query";

export function useTrips() {
  return useQuery({
    queryKey: ["trips"],
    queryFn: async () => {
      const response = await fetch("/api/trips");
      if (!response.ok) throw new Error("Failed to fetch trips");
      return response.json();
    },
  });
}

export function useCreateTrip() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (tripData: TripCreate) => {
      const response = await fetch("/api/trips", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(tripData),
      });
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
    },
  });
}
```

### State Management

#### Zustand Stores

```typescript
// stores/auth-store.ts
import { create } from "zustand";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isLoading: false,

  signIn: async (email, password) => {
    set({ isLoading: true });
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) throw new Error("Login failed");

      const user = await response.json();
      set({ user, isLoading: false });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  signOut: async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    set({ user: null });
  },
}));
```

### API Integration

#### Route Handlers

```typescript
// app/api/trips/route.ts
import { NextRequest, NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const supabase = await createServerSupabase();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { data: trips } = await supabase
    .from("trips")
    .select("*")
    .eq("user_id", user.id);

  return NextResponse.json(trips);
}

export async function POST(request: NextRequest) {
  const supabase = await createServerSupabase();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  const { data: trip } = await supabase
    .from("trips")
    .insert({ ...body, user_id: user.id })
    .select()
    .single();

  return NextResponse.json(trip);
}
```

#### Frontend AI Agents

Flight and accommodation operations are handled by frontend-only AI
agents using Vercel AI SDK v6:

```typescript
// app/api/agents/flights/route.ts
import "server-only";
import type { NextRequest } from "next/server";
import { runFlightAgent } from "@/lib/agents/flight-agent";
import { resolveProvider } from "@ai/models/registry";
import { createServerSupabase } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest): Promise<Response> {
  const supabase = await createServerSupabase();
  const user = (await supabase.auth.getUser()).data.user;

  const body = await req.json();
  const { model } = await resolveProvider(user?.id ?? "anon");

  const result = runFlightAgent({ identifier: user?.id, model }, body);
  return result.toUIMessageStreamResponse();
}
```

**Key features:**

- Server-only routes with `"server-only"` import
- BYOK provider resolution via `resolveProvider`
- AI SDK v6 streaming with `toUIMessageStreamResponse()`
- Tool calling for flight/accommodation search
- Upstash Redis caching and rate limiting
- AI Elements card rendering

### Component Patterns

#### Server Components

```typescript
// app/(dashboard)/trips/page.tsx
import { createServerSupabase } from "@/lib/supabase/server";

export default async function TripsPage() {
  const supabase = await createServerSupabase();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: trips } = await supabase
    .from("trips")
    .select("*")
    .eq("user_id", user.id);

  return (
    <div>
      <h1>My Trips</h1>
      {trips?.map((trip) => (
        <TripCard key={trip.id} trip={trip} />
      ))}
    </div>
  );
}
```

#### Client Components

```typescript
// components/trip-card.tsx
"use client";

import { useRouter } from "next/navigation";

interface TripCardProps {
  trip: Trip;
}

export function TripCard({ trip }: TripCardProps) {
  const router = useRouter();

  const handleEdit = () => {
    router.push(`/trips/${trip.id}/edit`);
  };

  return (
    <div className="border rounded-lg p-4">
      <h3 className="text-lg font-semibold">{trip.name}</h3>
      <p className="text-sm text-gray-600">{trip.destinations.join(", ")}</p>
      <button
        onClick={handleEdit}
        className="mt-2 px-3 py-1 bg-blue-500 text-white rounded"
      >
        Edit Trip
      </button>
    </div>
  );
}
```

## Database Design

### Supabase PostgreSQL

#### Why Supabase

- Managed PostgreSQL service
- Built-in authentication and RLS
- Real-time subscriptions
- Extension ecosystem including pgvector
- Vault for secure key storage

#### Core Tables

```sql
-- Users (managed by Supabase Auth)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Trips
CREATE TABLE trips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  name TEXT NOT NULL,
  destination TEXT NOT NULL,
  start_date DATE,
  end_date DATE,
  budget DECIMAL,
  currency TEXT DEFAULT 'USD',
  status TEXT DEFAULT 'planning',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat Sessions
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  title TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Memories with embeddings
CREATE TABLE memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  embedding VECTOR(1536), -- OpenAI ada-002 dimensions
  created_at TIMESTAMP DEFAULT NOW()
);

-- API Keys (encrypted in Vault)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  provider TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  is_valid BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Vector Search

#### pgvector Setup

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create vector index for similarity search
CREATE INDEX ON memories USING ivfflat (embedding vector_cosine_ops);
```

#### TypeScript Vector Search

```typescript
// lib/memory/search.ts
export async function searchSimilarMemories(
  supabase: TypedServerSupabase,
  embedding: number[],
  limit = 5
) {
  const { data } = await supabase.rpc("search_memories", {
    query_embedding: embedding,
    match_count: limit,
  });
  return data;
}
```

## API Route Handlers

TripSage uses Next.js API routes with a centralized factory pattern for
consistent authentication, rate limiting, error handling, and telemetry.

### Factory Pattern

All standard API routes use the `withApiGuards` factory:

```typescript
import { withApiGuards } from "@/lib/api/factory";
import { NextResponse } from "next/server";

export const GET = withApiGuards({
  auth: true, // Require authentication
  rateLimit: "myroute:read", // Rate limit key from ROUTE_RATE_LIMITS
  telemetry: "myroute.get", // Telemetry span name
})(async (req, { supabase, user }) => {
  // Handler logic only - auth/errors handled by factory
  const data = await fetchData(user!.id);
  return NextResponse.json(data);
});
```

### Configuration Options

- **auth**: `true` for required authentication, `false` for public routes
- **rateLimit**: Key from `ROUTE_RATE_LIMITS` registry for rate limiting
- **telemetry**: Span name for observability and tracing

### Rate Limiting Setup

Add route configurations to `src/lib/ratelimit/routes.ts`:

```typescript
export const ROUTE_RATE_LIMITS = {
  // ... existing routes
  "myroute:read": { limit: 60, window: "1 m" },
  "myroute:write": { limit: 10, window: "1 m" },
} as const;
```

### Factory Error Handling

The factory automatically handles:

- **401 Unauthorized**: Authentication required but user not found
- **429 Rate Limited**: Rate limit exceeded with `Retry-After` header
- **500 Internal Error**: Handler exceptions with telemetry logging

For custom errors, throw or return `NextResponse`:

```typescript
export const POST = withApiGuards({ auth: true })(
  async (req, { supabase, user }) => {
    const body = await req.json();
    if (!body.requiredField) {
      return NextResponse.json(
        { error: "Required field missing" },
        { status: 400 }
      );
    }
    // ... handler logic
  }
);
```

### Route Exceptions

Some routes cannot use the factory due to special requirements:

- **Webhooks** (`/api/hooks/*`): Require signature verification before
  processing
- **Background jobs** (`/api/jobs/*`): Custom authentication patterns
- **Complex requirements**: When the factory cannot support the pattern

See `docs/architecture/route-exceptions.md` for details.

### Testing API Routes

Use centralized test helpers:

```typescript
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

### Benefits

- Reduces inline authentication and rate limiting code
- Keeps security patterns consistent across routes
- Centralizes error handling and telemetry
- Simplifies testing with standardized mocks
- Applies rate limiting and authentication by configuration

## Observability

### Telemetry Helpers

The project uses OpenTelemetry for distributed tracing. Helpers are in `frontend/src/lib/telemetry`.

#### Server-Side Telemetry

```typescript
import { withTelemetrySpan, recordTelemetryEvent } from "@/lib/telemetry/span";
import { createServerLogger } from "@/lib/telemetry/logger";

// Wrap async operations with telemetry spans
const result = await withTelemetrySpan(
  "myOperation",
  { userId: user.id },
  async (span) => {
    // Operation logic
    return await doSomething();
  }
);

// Record events
recordTelemetryEvent("trip.created", { tripId: trip.id });

// Structured logging
const logger = createServerLogger("trips");
logger.info("Trip created", { tripId: trip.id });
```

#### Route Handler Telemetry

The `withApiGuards` factory automatically adds telemetry:

```typescript
export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:create",
  telemetry: "trips.create", // Span name
})(async (req, { supabase, user }) => {
  // Handler logic - telemetry span wraps this
});
```

#### Client-Side Telemetry

```typescript
import { initClientTelemetry } from "@/lib/telemetry/client";

// Initialize in app layout
initClientTelemetry();
```

### Logging Guidelines

- **Server code**: Use `createServerLogger()` - never `console.*`
- **Tests**: `console.*` is allowed
- **Client components**: Use `@/lib/telemetry/client`

## Performance Optimization

### Caching Strategy

Upstash Redis for serverless caching:

```typescript
import { getCachedJson, setCachedJson } from "@/lib/cache/upstash";

// Check cache first
const cached = await getCachedJson<Trip[]>(cacheKey);
if (cached) return cached;

// Fetch and cache
const data = await fetchData();
await setCachedJson(cacheKey, data, 300); // 5 min TTL
return data;
```

### Cache Tag Versioning

For bulk cache invalidation:

```typescript
import { bumpTag, versionedKey } from "@/lib/cache/tags";

// Build versioned key
const key = await versionedKey("trips", `trips:list:${userId}`);

// Invalidate all keys with tag
await bumpTag("trips");
```

### Database Best Practices

- Use RLS policies for security at the database layer
- Select only needed columns
- Use proper indexes on frequently queried columns
- Leverage Supabase's built-in connection pooling

## Security Considerations

### Input Validation

All inputs validated with Zod v4:

```typescript
import { tripCreateSchema } from "@schemas/trips";

const parsed = tripCreateSchema.safeParse(body);
if (!parsed.success) {
  return errorResponse({
    error: "invalid_request",
    issues: parsed.error.issues,
    status: 400,
  });
}
```

### Rate Limiting

Rate limiting via Upstash Ratelimit with sliding window:

```typescript
// lib/ratelimit/routes.ts
export const ROUTE_RATE_LIMITS = {
  "trips:list": { limit: 60, window: "1 m" },
  "trips:create": { limit: 10, window: "1 m" },
  "agents:flights": { limit: 20, window: "1 m" },
  // ...
} as const;
```

The `withApiGuards` factory applies rate limiting automatically:

```typescript
export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:create", // Uses ROUTE_RATE_LIMITS config
})(async (req, { user }) => {
  // Handler is rate-limited per user
});
```

### Row Level Security

```sql
-- Enable RLS on trips table
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own trips
CREATE POLICY "Users can view own trips" ON trips
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can only modify their own trips
CREATE POLICY "Users can modify own trips" ON trips
    FOR ALL USING (auth.uid() = user_id);
```

### BYOK Security

API keys stored securely in Supabase Vault:

```typescript
// Keys resolved server-side only
import "server-only";
import { resolveProvider } from "@ai/models/registry";

// Provider resolution happens server-side
const { model } = await resolveProvider(userId, modelHint);
```

- BYOK routes must import `"server-only"`
- Keys never exposed to client
- Key validation before storage
