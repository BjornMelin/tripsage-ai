# TripSage API Documentation

Next.js 16 server route handlers (TypeScript) powering the TripSage travel planning platform. All APIs live in `frontend/src/app/api/**`.

## Quick Start

### Development Environment

```bash
# Start the development server
cd frontend
pnpm dev

# API available at:
# - Base URL: http://localhost:3000/api
```

### First API Call

```bash
# Health check via dashboard endpoint
curl http://localhost:3000/api/dashboard

# Response includes trip stats, recent trips, and system health
```

## Architecture Overview

### Tech Stack

| Layer                   | Technology                                       | Purpose                                                 |
| ----------------------- | ------------------------------------------------ | ------------------------------------------------------- |
| **Framework**           | Next.js 16                                       | Server route handlers, React Server Components          |
| **AI**                  | AI SDK v6 (`ai@6.0.0-beta.105`)                  | `streamText`, `generateObject`, tool calling, streaming |
| **Database**            | Supabase (`@supabase/ssr@0.7.0`)                 | PostgreSQL, Row Level Security, SSR cookie handling     |
| **Cache/Rate Limiting** | Upstash (`@upstash/redis`, `@upstash/ratelimit`) | Redis caching, sliding window rate limits               |
| **State Management**    | TanStack Query (`@tanstack/react-query@5.x`)     | Client-side data fetching, caching, mutations           |
| **Validation**          | Zod v4 (`zod@4.x`)                               | Request/response schema validation                      |
| **Observability**       | OpenTelemetry (`@opentelemetry/api@1.9.0`)       | Distributed tracing, metrics                            |

### Route Handler Pattern

All route handlers use the `withApiGuards` factory for consistent authentication, rate limiting, and telemetry:

```typescript
import { withApiGuards } from "@/lib/api/factory";

export const POST = withApiGuards({
  auth: true, // Require Supabase SSR authentication
  rateLimit: "trips:create", // Upstash rate limit key
  telemetry: "trips.create", // OpenTelemetry span name
})(async (req, { supabase, user }) => {
  // Handler implementation
});
```

### AI Agent Architecture

AI agents use Vercel AI SDK v6 with BYOK (Bring Your Own Key) provider resolution:

```typescript
import { resolveProvider } from "@ai/models/registry";
import { streamText } from "ai";

// Resolve user's preferred AI provider (OpenAI, Anthropic, xAI, etc.)
const { model } = await resolveProvider(userId, modelHint);

// Stream AI response with tool calling
return streamText({
  model,
  tools: agentTools,
  messages,
}).toUIMessageStreamResponse();
```

## API Reference

### Complete API Reference

**[API Reference](api-reference.md)** - Complete endpoint documentation with request/response examples

### Supporting Documentation

| Document                              | Description                        |
| ------------------------------------- | ---------------------------------- |
| **[Realtime Guide](realtime-api.md)** | Supabase Realtime private channels |
| **[Error Codes](error-codes.md)**     | Error handling and troubleshooting |

## API Categories

### AI Agents (`/api/agents/*`)

Streaming AI agents with tool calling for travel planning:

| Endpoint                     | Method | Description                                  |
| ---------------------------- | ------ | -------------------------------------------- |
| `/api/agents/flights`        | POST   | Flight search agent with Amadeus integration |
| `/api/agents/accommodations` | POST   | Accommodation search agent                   |
| `/api/agents/destinations`   | POST   | Destination research agent                   |
| `/api/agents/itineraries`    | POST   | Itinerary planning agent                     |
| `/api/agents/budget`         | POST   | Budget planning agent                        |
| `/api/agents/memory`         | POST   | Memory/context agent                         |
| `/api/agents/router`         | POST   | Intent classification router                 |

### Chat (`/api/chat/*`)

Conversational AI with session management:

| Endpoint                | Method   | Description                   |
| ----------------------- | -------- | ----------------------------- |
| `/api/chat`             | POST     | Non-streaming chat completion |
| `/api/chat/stream`      | POST     | Streaming chat with SSE       |
| `/api/chat/sessions`    | GET/POST | Session management            |
| `/api/chat/send`        | POST     | Send message to session       |
| `/api/chat/attachments` | POST     | File attachments              |

### Trips (`/api/trips/*`)

Trip CRUD with Redis caching:

| Endpoint                 | Method | Description                 |
| ------------------------ | ------ | --------------------------- |
| `/api/trips`             | GET    | List trips with filters     |
| `/api/trips`             | POST   | Create new trip             |
| `/api/trips/suggestions` | GET    | AI-powered trip suggestions |

### Authentication (`/api/auth/*`)

Supabase SSR authentication:

| Endpoint          | Method | Description          |
| ----------------- | ------ | -------------------- |
| `/api/auth/login` | POST   | Email/password login |

### Memory (`/api/memory/*`)

User context and preference storage via Mem0:

| Endpoint                           | Method | Description               |
| ---------------------------------- | ------ | ------------------------- |
| `/api/memory/conversations`        | POST   | Store conversation memory |
| `/api/memory/search`               | POST   | Search memories           |
| `/api/memory/context/[userId]`     | GET    | Get user context          |
| `/api/memory/preferences/[userId]` | POST   | Update preferences        |
| `/api/memory/stats/[userId]`       | GET    | Memory statistics         |
| `/api/memory/insights/[userId]`    | GET    | AI-generated insights     |

### Calendar (`/api/calendar/*`)

Calendar integration with ICS support:

| Endpoint                   | Method                | Description          |
| -------------------------- | --------------------- | -------------------- |
| `/api/calendar/events`     | GET/POST/PATCH/DELETE | Event CRUD           |
| `/api/calendar/freebusy`   | POST                  | Free/busy lookup     |
| `/api/calendar/status`     | GET                   | Calendar sync status |
| `/api/calendar/ics/import` | POST                  | Import ICS file      |
| `/api/calendar/ics/export` | POST                  | Export to ICS        |

### Places & Geocoding (`/api/places/*`, `/api/geocode`)

Google Places API integration:

| Endpoint                   | Method | Description     |
| -------------------------- | ------ | --------------- |
| `/api/places/search`       | POST   | Search places   |
| `/api/places/photo`        | GET    | Place photos    |
| `/api/places/details/[id]` | GET    | Place details   |
| `/api/geocode`             | POST   | Geocoding       |
| `/api/timezone`            | POST   | Timezone lookup |

### Activities (`/api/activities/*`)

Activity search (anonymous access allowed):

| Endpoint                 | Method | Description       |
| ------------------------ | ------ | ----------------- |
| `/api/activities/search` | POST   | Search activities |
| `/api/activities/[id]`   | GET    | Activity details  |

### Configuration (`/api/config/*`)

Agent configuration management:

| Endpoint                                              | Method  | Description            |
| ----------------------------------------------------- | ------- | ---------------------- |
| `/api/config/agents/[agentType]`                      | GET/PUT | Agent config CRUD      |
| `/api/config/agents/[agentType]/versions`             | GET     | Config version history |
| `/api/config/agents/[agentType]/rollback/[versionId]` | POST    | Rollback to version    |

### Security (`/api/security/*`)

Session and security management:

| Endpoint                             | Method | Description          |
| ------------------------------------ | ------ | -------------------- |
| `/api/security/sessions`             | GET    | List active sessions |
| `/api/security/sessions/[sessionId]` | DELETE | Revoke session       |
| `/api/security/metrics`              | GET    | Security metrics     |
| `/api/security/events`               | GET    | Security events      |

### API Keys (`/api/keys/*`)

BYOK API key management:

| Endpoint             | Method   | Description         |
| -------------------- | -------- | ------------------- |
| `/api/keys`          | GET/POST | List/store API keys |
| `/api/keys/validate` | POST     | Validate API key    |

### Utilities

| Endpoint             | Method   | Description              |
| -------------------- | -------- | ------------------------ |
| `/api/dashboard`     | GET      | Dashboard metrics        |
| `/api/embeddings`    | POST     | Generate embeddings      |
| `/api/routes`        | POST     | Route planning           |
| `/api/route-matrix`  | POST     | Distance/duration matrix |
| `/api/itineraries`   | GET/POST | Itinerary management     |
| `/api/user-settings` | GET/POST | User preferences         |

## Development

### Testing

```bash
# Run all tests
pnpm -C frontend test:run

# Run API route tests
pnpm -C frontend test:api

# Run with coverage
pnpm -C frontend test:coverage
```

### Type Checking

```bash
pnpm -C frontend type-check
```

### Linting

```bash
pnpm -C frontend biome:check
pnpm -C frontend biome:fix
```

## Key Dependencies

| Package                 | Version        | Usage                                                     |
| ----------------------- | -------------- | --------------------------------------------------------- |
| `ai`                    | 6.0.0-beta.105 | AI SDK core: `streamText`, `generateObject`, tool calling |
| `@ai-sdk/react`         | 3.0.0-beta.105 | React hooks: `useChat`, `useCompletion`                   |
| `@ai-sdk/openai`        | 3.0.0-beta.63  | OpenAI provider                                           |
| `@ai-sdk/anthropic`     | 3.0.0-beta.54  | Anthropic provider                                        |
| `@ai-sdk/xai`           | 3.0.0-beta.39  | xAI provider                                              |
| `@supabase/ssr`         | 0.7.0          | Supabase SSR cookie handling                              |
| `@supabase/supabase-js` | 2.84.0         | Supabase client                                           |
| `@upstash/redis`        | 1.35.6         | Redis client                                              |
| `@upstash/ratelimit`    | 2.0.7          | Rate limiting                                             |
| `@tanstack/react-query` | 5.90.10        | Data fetching/caching                                     |
| `zod`                   | 4.1.12         | Schema validation                                         |
| `@opentelemetry/api`    | 1.9.0          | Observability                                             |
| `amadeus`               | 11.0.0         | Flight/hotel search                                       |
| `mem0ai`                | 2.1.38         | Memory/context storage                                    |
