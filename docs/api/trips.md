# Trips

This document covers Trips-related HTTP endpoints under `src/app/api/trips/**`.

Trip CRUD, collaboration, and itinerary mutations are implemented as Next.js Server Actions (see `src/lib/trips/actions.ts`) and are not exposed as internal REST endpoints.

## `GET /api/trips/suggestions`

Return AI-powered trip suggestions for the authenticated user.

**Authentication**: Required  
**Rate Limit Key**: `trips:suggestions`

### Query Parameters

| Parameter | Type | Default | Description |
| --------- | ---- | ------- | ----------- |
| `limit` | number | `4` | Maximum number of suggestions to return |
| `budget_max` | number | — | Maximum budget constraint |
| `category` | string | — | Category filter (implementation-defined) |

### Response

`200 OK` → `TripSuggestion[]` (see `@schemas/trips` `tripSuggestionSchema`).

### Errors

- `400` - Validation failed (check `issues` array)
- `401` - Not authenticated
- `429` - Rate limit exceeded

### Examples

cURL

```bash
curl -X GET "http://localhost:3000/api/trips/suggestions?limit=5&category=culture" \
  --cookie "sb-access-token=<jwt_token>"
```

TypeScript

```ts
const response = await fetch("http://localhost:3000/api/trips/suggestions?limit=5", {
  headers: {
    Cookie: `sb-access-token=${jwtToken}`,
  },
});

if (!response.ok) {
  throw new Error(await response.text());
}

const suggestions = await response.json();
```
