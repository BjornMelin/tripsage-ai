# API Documentation

The TripSage AI API is implemented as Next.js 16 server route handlers. All API endpoints live in `frontend/src/app/api/**`.

## API Explorer

For local development, the API is available at:

- **Base URL**: `http://localhost:3000/api`
- **API Reference**: See [API Reference](api/api-reference.md)

!!! note "API Base URL"
All endpoints are relative to the base URL: `https://tripsage.ai/api` (production) or `http://localhost:3000/api` (development)

!!! tip "Authentication Required"
Most endpoints require authentication via Supabase SSR. See the [API Reference](api/api-reference.md#authentication) for details.

## API Structure

Endpoints are organized by domain:

| Category      | Path                | Description                                         |
| ------------- | ------------------- | --------------------------------------------------- |
| AI Agents     | `/api/agents/*`     | Streaming AI agents (flights, accommodations, etc.) |
| Chat          | `/api/chat/*`       | Conversational AI with sessions                     |
| Trips         | `/api/trips/*`      | Trip CRUD operations                                |
| Memory        | `/api/memory/*`     | User context and preferences                        |
| Calendar      | `/api/calendar/*`   | Calendar integration                                |
| Places        | `/api/places/*`     | Google Places API integration                       |
| Activities    | `/api/activities/*` | Activity search                                     |
| Configuration | `/api/config/*`     | Agent configuration                                 |
| Security      | `/api/security/*`   | Session management                                  |
| Keys          | `/api/keys/*`       | BYOK API key management                             |

## Route Handler Pattern

All route handlers use the `withApiGuards` factory for consistent authentication, rate limiting, and telemetry:

```typescript
import { withApiGuards } from "@/lib/api/factory";

export const POST = withApiGuards({
  auth: true, // Require Supabase SSR authentication
  rateLimit: "trips:create", // Upstash rate limit key
  telemetry: "trips.create", // OpenTelemetry span name
})(async (req, { supabase, user }) => {
  // Handler implementation with validated user
});
```

## Schema Validation

The API uses Zod v4 for request/response validation. Schemas are defined in `frontend/src/domain/schemas/*` and imported via the `@schemas/*` path alias.

```typescript
import { tripCreateSchema } from "@schemas/trips";

// Validate request body
const body = tripCreateSchema.parse(await req.json());
```

## Versioning

This documentation reflects the current API implementation. Breaking changes are documented in the [CHANGELOG](../CHANGELOG.md).
