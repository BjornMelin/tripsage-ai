# Memory

User memory, context, preference, stats, and insight routes. All memory routes
require Supabase SSR authentication, and `{userId}` path parameters must match
the authenticated user.

## Routes

| Endpoint | Method | Rate limit key | Description |
| :--- | :--- | :--- | :--- |
| `/api/memory/conversations` | POST | `memory:conversations` | Store one conversation memory entry |
| `/api/memory/search` | POST | `memory:search` | Search memory context |
| `/api/memory/context/{userId}` | GET | `memory:context` | Fetch recent memory context |
| `/api/memory/stats/{userId}` | GET | `memory:stats` | Fetch memory counts and storage estimates |
| `/api/memory/insights/{userId}` | GET | `memory:insights` | Generate or fetch cached AI memory insights |
| `/api/memory/preferences/{userId}` | POST | `memory:preferences` | Persist preference entries as user memory |
| `/api/memory/user/{userId}` | DELETE | `memory:delete` | Delete all memories for the authenticated user |

## Add Conversation Memory

```bash
curl -X POST "http://localhost:3000/api/memory/conversations" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{"category":"conversation_context","content":"Prefers nonstop morning flights."}'
```

`200 OK`

```json
{
  "createdAt": "2026-05-11T19:00:00.000Z",
  "id": "memory-uuid"
}
```

## Search Memories

```bash
curl -X POST "http://localhost:3000/api/memory/search" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"morning flights","limit":10,"similarityThreshold":0.2}'
```

`200 OK`

```json
{
  "success": true,
  "memories": [],
  "searchMetadata": {
    "queryProcessed": "morning flights",
    "searchTimeMs": 12,
    "similarityThresholdUsed": 0.2
  },
  "totalFound": 0
}
```

## User-Scoped Reads and Writes

```bash
curl "http://localhost:3000/api/memory/context/$USER_ID" \
  --cookie "sb-access-token=$JWT"

curl -X POST "http://localhost:3000/api/memory/preferences/$USER_ID" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{"preferences":{"seat":"aisle","pace":"slow"}}'

curl -X DELETE "http://localhost:3000/api/memory/user/$USER_ID" \
  --cookie "sb-access-token=$JWT"
```

## Errors

- `400` - Invalid request or invalid authenticated user id
- `401` - Not authenticated
- `403` - `{userId}` does not match the authenticated user
- `404` - Unknown memory intent
- `405` - Method not supported for the selected memory intent
- `429` - Rate limit exceeded
- `500` - Memory tool, cache, or persistence failure
