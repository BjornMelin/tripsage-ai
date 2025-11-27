# TripSage API Reference

Authoritative documentation for all Next.js route handlers in `frontend/src/app/api/**`.

## Introduction

The TripSage API is organized around REST principles and uses standard HTTP response codes, authentication, and verbs. All API endpoints return JSON responses unless otherwise specified (e.g., ICS exports, streaming endpoints).

### API Design Principles

- **RESTful**: Resource-oriented URLs with standard HTTP methods
- **JSON**: Request and response bodies use JSON encoding
- **Type-safe**: Request/response schemas validated with Zod v4
- **Authenticated**: Most endpoints require Supabase SSR authentication
- **Rate-limited**: Per-route rate limiting with Upstash Redis
- **Streaming**: AI agent endpoints use Server-Sent Events (SSE) for real-time responses

### Base URLs

- **Production**: `https://tripsage.ai/api`
- **Development**: `http://localhost:3000/api`

All examples in this documentation use the development base URL.

## Authentication

Most endpoints require authentication via Supabase SSR cookies. The authentication cookie is named `sb-access-token` and contains a JWT token.

### Authentication Methods

#### Cookie-based (Recommended)

```bash
curl -X GET "http://localhost:3000/api/trips" \
  --cookie "sb-access-token=<jwt_token>"
```

#### TypeScript

```typescript
const response = await fetch("http://localhost:3000/api/trips", {
  headers: {
    Cookie: `sb-access-token=${jwtToken}`,
  },
});
```

#### Python

```python
import requests

response = requests.get(
    "http://localhost:3000/api/trips",
    cookies={"sb-access-token": jwt_token}
)
```

### Anonymous Endpoints

Endpoints marked as "Anonymous" do not require authentication:

- `POST /api/activities/search`
- `POST /api/places/search`
- `GET /api/places/details/{id}`
- `GET /api/places/photo`
- `GET /api/activities/{id}`

### Authentication Errors

- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Authenticated but insufficient permissions (e.g., admin-only endpoints)

## Rate Limiting

All endpoints are rate-limited using Upstash Redis with sliding window algorithms. Rate limit keys are per-route and scoped to authenticated users or IP addresses.

### Rate Limit Headers

When rate limits are exceeded, responses include:

- `429 Too Many Requests`
- `Retry-After`: Seconds until retry is allowed

### Rate Limit Keys

Rate limit keys follow the pattern `{resource}:{action}`. Common examples:

- `trips:list` - List trips endpoint
- `trips:create` - Create trip endpoint
- `chat:stream` - Chat streaming endpoint
- `agents:flight` - Flight agent endpoint

See individual endpoint documentation for specific rate limit keys.

### Rate Limit Thresholds

The following rate limits are applied per authenticated user/IP address:

| Endpoint Category | Rate Limit | Time Window | Notes |
|-------------------|-----------|------------|-------|
| **Read Operations** (list, get) | 100 requests | 1 minute | Standard queries, filters |
| **Write Operations** (create, update) | 50 requests | 1 minute | CREATE, PUT, PATCH operations |
| **Delete Operations** | 30 requests | 1 minute | Destructive operations |
| **Search Operations** | 60 requests | 1 minute | Text search, filtering endpoints |
| **AI Agents** (streaming) | 20 requests | 1 minute | resource-intensive agents |
| **Anonymous Endpoints** | 100 requests | 1 hour | Places/Activities search, no auth |
| **Admin Endpoints** | 50 requests | 1 hour | Configuration changes, admin-only |

**Note**: These are global defaults. Specific endpoints may have custom limits noted in their documentation. Limits are enforced using sliding window rate limiting with Upstash Redis.

## Errors

The API uses conventional HTTP response codes to indicate success or failure.

### HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| `200` | OK | Request succeeded |
| `201` | Created | Resource created successfully |
| `204` | No Content | Success with no response body |
| `400` | Bad Request | Invalid request parameters or body |
| `401` | Unauthorized | Authentication required or invalid |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource not found |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `502` | Bad Gateway | External API error |

### Error Response Format

All error responses follow this structure:

```json
{
  "error": "<error_code>",
  "reason": "<human-readable message>",
  "issues": [
    {
      "path": ["fieldName"],
      "message": "Validation error message",
      "code": "invalid_type"
    }
  ]
}
```

### Common Error Codes

- `invalid_request`: Request validation failed (includes `issues` array)
- `unauthorized`: Authentication required
- `forbidden`: Insufficient permissions
- `not_found`: Resource not found
- `internal`: Server error
- `external_api_error`: External service error

For detailed error types, troubleshooting scenarios, and code examples, see the [Error Codes Reference](error-codes.md).

### Validation Errors

Validation errors (`400 Bad Request`) include a `issues` array with Zod validation details:

```json
{
  "error": "invalid_request",
  "reason": "Request validation failed",
  "issues": [
    {
      "path": ["startDate"],
      "message": "Required",
      "code": "invalid_type"
    }
  ]
}
```

## Pagination

Most list endpoints return full results without pagination. Some endpoints support query parameters for filtering:

- `GET /api/trips` - Supports `destination`, `status`, `startDate`, `endDate` filters
- `GET /api/calendar/events` - Supports `maxResults`, `pageToken` for pagination
- `GET /api/itineraries` - Supports `tripId` filter

Pagination details are documented per endpoint where applicable.

## Resources

API resources are organized by domain:

| Resource | Description |
|----------|-------------|
| [Auth](auth.md) | Authentication and login |
| [Trips](trips.md) | Trip management and itineraries |
| [Agents](agents.md) | AI streaming agents (flights, accommodations, etc.) |
| [Chat](chat.md) | Chat sessions and messaging |
| [Calendar](calendar.md) | Calendar events and ICS import/export |
| [Places](places.md) | Activities, places, and geolocation |
| [Keys](keys.md) | BYOK API key management |
| [Memory](memory.md) | User memory and context |
| [Security](security.md) | Security sessions and dashboard |
| [Settings](settings.md) | User settings and miscellaneous |

## Internal Resources

Internal endpoints for admin and system use:

| Resource | Description |
|----------|-------------|
| [Agent Config](internal/config.md) | Agent configuration (admin-only) |
| [Webhooks](internal/webhooks.md) | Database and file webhooks |
| [Jobs](internal/jobs.md) | Background job handlers |

## Schema References

Request and response schemas are defined using Zod v4 and located in:

- **Trips**: `@schemas/trips` (`tripCreateSchema`, `tripUpdateSchema`, `tripSuggestionSchema`, `itineraryItemCreateSchema`)
- **Flights**: `@schemas/flights` (`flightSearchRequestSchema`, `flightSearchResultSchema`)
- **Calendar**: `@schemas/calendar` (`createEventRequestSchema`, `updateEventRequestSchema`, `icsExportRequestSchema`)
- **API**: `@schemas/api` (`placesSearchRequestSchema`, `postKeyBodySchema`, `loginRequestSchema`)
- **Supabase**: `@schemas/supabase` (Database table schemas)

All schemas use Zod v4 APIs exclusively. See `docs/developers/zod-schema-guide.md` for schema organization details.

## Streaming Endpoints

Endpoints under `/agents/*` and `/chat/stream` return Server-Sent Events (SSE) streams using AI SDK v6 UI message format.

### JavaScript/TypeScript

```typescript
const response = await fetch("http://localhost:3000/api/agents/flights", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Cookie: `sb-access-token=${jwtToken}`,
  },
  body: JSON.stringify({...}),
});

// res.body is a ReadableStream
const reader = response.body?.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value);
  // Process SSE messages
}
```

### Python

Use `sseclient-py` library:

```python
import requests
import sseclient

response = requests.post(
    "http://localhost:3000/api/agents/flights",
    cookies={"sb-access-token": jwt_token},
    json={...},
    stream=True
)

client = sseclient.SSEClient(response)
for event in client.events():
    print(event.data)
```

### cURL

```bash
curl -N -X POST "http://localhost:3000/api/chat/stream" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

## Related Guides

| Guide | Description |
|-------|-------------|
| [Realtime](../guides/realtime.md) | Supabase Realtime with private channels |
| [Error Codes](error-codes.md) | Detailed error reference and troubleshooting |

## Maintenance

This reference mirrors the current handlers in `frontend/src/app/api/**`. Update alongside route or schema changes. When adding new endpoints:

1. Document authentication requirements
2. Include rate limit key
3. Document request/response schemas
4. Provide examples in TypeScript, Python, and cURL
5. List all possible error responses
6. Update the appropriate resource file
