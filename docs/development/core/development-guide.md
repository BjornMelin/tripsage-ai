# Development Guide

TripSage development patterns and architecture overview. This document provides architectural context and links to specialized documentation for each topic.

**Import Paths**: All TypeScript imports must follow the [Import Path Standards](../standards/standards.md#import-paths). Use semantic aliases (`@schemas/*`, `@domain/*`, `@ai/*`) for architectural boundaries and `@/*` for generic src-root imports.

## Architecture Overview

### Technology Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| **Framework** | Next.js 16 | Server route handlers, React Server Components |
| **React** | React 19 | UI with concurrent features |
| **Language** | TypeScript 6 | Strict mode, full type safety |
| **AI** | AI SDK v7 (`ai` package version from `package.json`) | Provider V4, `streamText`, `generateText` + `Output.object`, tool calling |
| **Database** | Supabase PostgreSQL | RLS, pgvector, Realtime |
| **Cache** | Upstash Redis | HTTP REST API, rate limiting |
| **Auth** | Supabase SSR | Cookie-based sessions |
| **Validation** | Zod v4 | Request/response schemas |
| **State** | Zustand + TanStack Query | Client state + server state |
| **Styling** | Tailwind CSS v4 | CSS-first configuration |
| **Observability** | OpenTelemetry | Distributed tracing, metrics |

### Project Structure

```text
src/
├── app/                    # Next.js App Router
│   ├── (auth)/            # Auth route group
│   ├── (dashboard)/       # Protected route group
│   ├── api/               # Route handlers
│   └── ...                # Pages
├── ai/                     # AI SDK tooling
│   ├── lib/               # Tool factory, utilities
│   ├── models/            # Provider registry
│   └── tools/             # AI tools (server/client)
├── components/            # Reusable UI components
├── domain/                # Domain logic
│   ├── accommodations/   # Accommodation domain
│   ├── activities/       # Activity domain
│   ├── amadeus/          # Amadeus integration
│   ├── flights/          # Flight domain
│   └── schemas/          # Zod validation schemas
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities and configurations
├── prompts/               # AI prompt templates
├── stores/                # Zustand state management
├── styles/                # Global styles
├── test/                  # Test utilities and mocks
└── test-utils/            # Shared test utilities
```

## Specialized Documentation

### Getting Started

| Guide | Purpose |
| ------- | --------- |
| [Quick Start](quick-start.md) | Project setup, environment, first run |
| [Environment Setup](env-setup.md) | Provider credential checklist |

### Code & Architecture

| Guide | Purpose |
| ------- | --------- |
| [Standards](../standards/standards.md) | TypeScript, import paths, Zod schemas, Zustand stores, security |
| [Zod Schema Guide](../standards/zod-schema-guide.md) | Zod v4 patterns, validation, AI SDK tool schemas |
| [Database Architecture](../../architecture/database.md) | Schema design, RLS, Supabase integration |

### AI & Tools

| Guide | Purpose |
| ------- | --------- |
| [AI Integration](../ai/ai-integration.md) | Vercel AI Gateway, BYOK provider configuration |
| [AI Tools](../ai/ai-tools.md) | `createAiTool` factory, guardrails, tool patterns |
| [Activities](../frontend/activities.md) | Activity search service, tools, and API usage |

### Infrastructure

| Guide | Purpose |
| ------- | --------- |
| [Observability](../backend/observability.md) | Telemetry spans, logging, operational alerts |
| [Cache Versioned Keys](../backend/cache-versioned-keys.md) | Tag-based cache invalidation patterns |

### Utilities

| Utility | Location | Purpose |
| --------- | ---------- | --------- |
| Geo/Distance | `@/lib/geo` | Haversine distance calculation for hotel/activity proximity sorting |
| Security/Random | `@/lib/security/random` | Secure UUIDs and IDs (`secureUuid`, `secureId`, `nowIso`) |

### Quality & Testing

| Guide | Purpose |
| ------- | --------- |
| [Testing](../testing/testing.md) | Strategy, patterns, templates, MSW handlers |
| [Troubleshooting](troubleshooting.md) | Debugging, CI/CD, workflow guidance |

## Key Patterns

### Route Handlers

All standard API routes use the `withApiGuards` factory for consistent authentication, rate limiting, error handling, and telemetry:

```typescript
import { withApiGuards } from "@/lib/api/factory";
import { NextResponse } from "next/server";

export const GET = withApiGuards({
  auth: true,                    // Require authentication
  rateLimit: "myroute:read",     // Rate limit key from ROUTE_RATE_LIMITS
  telemetry: "myroute.get",      // Telemetry span name
})(async (req, { supabase, user }) => {
  const data = await fetchData(user!.id);
  return NextResponse.json(data);
});
```

Rate limits are configured in `src/lib/ratelimit/routes.ts`. See [Standards](../standards/standards.md#security--validation) for security patterns.

### AI Agents

Frontend-only AI agents use Vercel AI SDK v7 through the shared route factory:

```typescript
import "server-only";

import { createFlightAgent } from "@ai/agents/flight-agent";
import { flightSearchRequestSchema } from "@schemas/flights";
import { createAgentRoute } from "@/lib/api/factory";

export const POST = createAgentRoute({
  agentFactory: createFlightAgent,
  agentType: "flightAgent",
  rateLimit: "agents:flight",
  schema: flightSearchRequestSchema,
  telemetry: "agent.flightSearch",
});
```

`createAgentRoute()` resolves the Provider V4 model and returns the agent stream
with AI SDK v7's native `createAgentUIStreamResponse()` helper.

See [AI Integration](../ai/ai-integration.md) for provider configuration and [AI Tools](../ai/ai-tools.md) for tool creation.

### Input Validation

**Recommended: Use `withApiGuards` with `schema` option** (automatic parsing + validation):

```typescript
import { withApiGuards } from "@/lib/api/factory";
import { tripCreateSchema } from "@schemas/trips";
import { NextResponse } from "next/server";

export const POST = withApiGuards({
  auth: true,
  rateLimit: "trips:create",
  schema: tripCreateSchema,  // Automatic JSON parsing + Zod validation
})(async (_req, { user }, tripData) => {
  // tripData is typed as z.infer<typeof tripCreateSchema>
  const trip = await createTrip(tripData, user!.id);
  return NextResponse.json(trip, { status: 201 });
});
```

**Alternative: Manual validation** (for complex flows):

```typescript
import { parseJsonBody, validateSchema } from "@/lib/api/route-helpers";
import { tripCreateSchema } from "@schemas/trips";

// Parse JSON body (handles malformed JSON)
const parsed = await parseJsonBody(req);
if (!parsed.ok) return parsed.error;

// Validate against schema (returns typed data or error response)
const validation = validateSchema(tripCreateSchema, parsed.data);
if (!validation.ok) return validation.error;

const tripData = validation.data;
```

**Available route-helpers:**

| Helper | Purpose |
| -------- | --------- |
| `parseJsonBody(req)` | Parse JSON body with error handling |
| `validateSchema(schema, data)` | Zod validation with standardized error response |
| `parseNumericId(ctx)` / `parseStringId(ctx)` | Extract and validate route params |
| `requireUserId(user)` | Extract user ID with 401 fallback |
| `notFoundResponse(entity)` | Standardized 404 response |
| `unauthorizedResponse()` | Standardized 401 response |
| `forbiddenResponse(reason)` | Standardized 403 response |
| `errorResponse({...})` | Custom error responses |

**Degraded response contract:**

- Domain status payloads return `200` when the route successfully reports the requested state, such as `{ connected: false }` for a disconnected calendar or fallback insights with `success: false`.
- Partial mutation success returns `207` with explicit failed keys or records so clients can retry only the failed subset.
- Primary dependency outages return a transport error, usually `503`, when the requested operation cannot complete normally. Routes may still include deterministic fallback data in the error response body, such as accommodations personalization fallback results.
- Run `pnpm check:api-route-errors:full` before release-sensitive API/auth work to verify current route files do not return ad hoc error JSON where helpers apply.

See [Zod Schema Guide](../standards/zod-schema-guide.md) for schema patterns and [Standards](../standards/standards.md#zod-schemas-v4) for conventions.

## Development Workflow

```bash
# Install and run
pnpm install && pnpm dev

# Quality gates
pnpm biome:check && pnpm type-check && pnpm test
```

See [Quick Start](quick-start.md) for full setup and [Troubleshooting](troubleshooting.md) for common issues.
