# TripSage API Reference (Complete)

Authoritative map of all implemented Next.js route handlers in `src/app/api/**`.

Base URLs

- Prod: `https://tripsage.ai/api`
- Dev: `http://localhost:3000/api`

Conventions

- **Auth**: Supabase SSR cookies (`sb-access-token`) unless “Anonymous” noted.
- **Internal key**: Some privileged endpoints require `x-internal-key` and are disabled unless explicitly enabled via env.
- **Rate limit**: Per-route keys (e.g., `trips:list`, `places:search`); 429 on exceed.
- **Errors**: `{ "error": "<code>", "reason": "<human text>", "issues"?: [...] }`
- **Streaming**: “SSE stream” returns Server-Sent Events (AI SDK v6 UI stream).

Quick trip examples

TypeScript

```ts
const BASE = process.env.API_URL ?? "http://localhost:3000/api";
export async function getTripSuggestions(jwt: string) {
  const res = await fetch(`${BASE}/trips/suggestions?limit=5`, {
    headers: { Cookie: `sb-access-token=${jwt}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

Python

```python
import requests
BASE = "http://localhost:3000/api"
cookies = {"sb-access-token": "<jwt>"}
resp = requests.get(f"{BASE}/trips/suggestions?limit=5", cookies=cookies)
resp.raise_for_status()
suggestions = resp.json()
```

cURL

```bash
curl -X GET "http://localhost:3000/api/trips/suggestions?limit=5" --cookie "sb-access-token=<jwt>"
```

---

## Endpoint catalog

### Auth

- `POST /auth/login` (Auth: Anonymous) — Email/password login; sets Supabase cookies.

### Trips

- `GET /trips/suggestions` (Auth) — AI suggestions. Query: `limit`, `budget_max`, `category`. Returns `TripSuggestion[]`.

Note: Trip CRUD, collaboration, and itinerary mutations are implemented as Next.js Server Actions (`src/lib/trips/actions.ts`) and are not exposed as internal REST routes.

Sample responses

- Suggestions: `200` → `TripSuggestion[]`; `401` if unauthenticated

### Activities (Google Places)

- `POST /activities/search` (Anonymous) — Places Text Search. Body per `placesSearchRequestSchema` (textQuery, maxResultCount, optional locationBias).
- `GET /activities/{id}` (Anonymous) — Activity/place details by Place ID.

Example (search)

```bash
curl -X POST "$BASE/activities/search" \
  -H "Content-Type: application/json" \
  -d '{"textQuery":"museum near Paris","maxResultCount":5}'
```

Response: `200` → Places results (id, displayName, formattedAddress, location, rating, photos).

### Places

- `POST /places/search` (Anonymous) — Places Text Search.
- `GET /places/photo` (Anonymous) — Photo proxy; query params match route.
- `GET /places/details/{id}` (Anonymous) — Place details (field mask minimal).

Example (details)

```bash
curl "$BASE/places/details/ChIJN1t_tDeuEmsRUsoyG83frY4"
```

### Agents (AI SDK v6, SSE stream, Auth)

- `POST /agents/flights` — Streaming flight search.
- `POST /agents/accommodations` — Streaming accommodation search.
- `POST /agents/destinations` — Destination research.
- `POST /agents/itineraries` — Itinerary agent.
- `POST /agents/budget` — Budget planning agent.
- `POST /agents/memory` — Memory update agent.
- `POST /agents/router` — Intent router.

Streaming example (TS)

```ts
const res = await fetch(`${base}/agents/flights`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Cookie: `sb-access-token=${jwt}` },
  body: JSON.stringify({
    origin: "JFK",
    destination: "CDG",
    departureDate: "2025-07-01",
    returnDate: "2025-07-15",
    passengers: 2,
    cabinClass: "economy",
  }),
});
// res.body is a ReadableStream (SSE UI message stream)
```

Python (SSE) tip: use `sseclient-py` with `requests` streaming.

### Chat

- `POST /chat` — Non-stream chat completion.
- `POST /chat/stream` — Streaming chat (SSE).
- `POST /chat/send` — Send message to session.
- `GET /chat/sessions` — List sessions.
- `POST /chat/sessions` — Create session.
- `POST /chat/attachments` — Multipart upload; auth bound to Supabase session cookie (caller Authorization headers ignored); validates size/count and total payload.

Example (stream)

```bash
curl -N -X POST "$BASE/chat/stream" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}'
```

### Files & Attachments

- `GET /attachments/files` (Auth) — List user files; cached; query passthrough.

### Calendar

- `GET /calendar/status` (Auth) — Sync status.
- `POST /calendar/freebusy` (Auth) — Free/busy lookup.
- `GET /calendar/events` (Auth) — List events.
- `POST /calendar/events` (Auth) — Create event.

### Keys (BYOK)

- `GET /keys` (Auth) — List stored provider keys.
- `POST /keys` (Auth) — Upsert provider key.
- `DELETE /keys/{service}` (Auth) — Delete key for `openai|openrouter|anthropic|xai|gateway`.
- `POST /keys/validate` (Auth) — Validate a key.

Example (POST)

```bash
curl -X POST "$BASE/keys" \
  --cookie "sb-access-token=$JWT" \
  -H "Content-Type: application/json" \
  -d '{"service":"openai","apiKey":"sk-..."}'
```

Response: `204` on success.

### Security

- `GET /security/sessions` (Auth) — Active sessions for user.
- `GET /security/metrics` (Auth) — Security metrics.
- `GET /security/events` (Auth) — Security events.

### Dashboard

- `GET /dashboard` (Auth) — Aggregated metrics. Query: `window` in `24h|7d|30d|all`.

### Time & Geo

- `POST /geocode` (Auth) — Geocode address.
- `POST /timezone` (Auth) — Timezone lookup.
- `POST /route-matrix` (Auth) — Distance/duration matrix.

### Embeddings

- `POST /embeddings` (Internal key) — Generate embeddings (disabled unless configured).

### Routes

- `POST /routes` (Auth) — Multimodal route planner.

### Flights utility

- `GET /flights/popular-destinations` (Auth) — Popular destination list.

### User settings

- `GET /user-settings` (Auth) — Get settings.
- `POST /user-settings` (Auth) — Update settings.

### Telemetry demo

- `POST /telemetry/ai-demo` (Internal key + gate) — Emit AI demo operational alert (disabled by default).

### AI stream (generic)

- `POST /ai/stream` (Auth + gate) — Generic AI stream route used in demos/tests (disabled by default).

### Keys helper endpoints

- `POST /keys/validate` (Auth) — Validate BYOK key. (Listed above for completeness.)

### Memory

- `POST /memory/conversations` (Auth) — Add conversation memory.
- `POST /memory/search` (Auth) — Search memories.

### Hooks / jobs / internal (do not expose to end-users)

- `POST /hooks/cache` — Cache invalidation hook.
- `POST /hooks/trips` — Trip collaborators webhook.
- `POST /hooks/files` — File webhook.
- `POST /jobs/notify-collaborators` — QStash job.
- `POST /jobs/memory-sync` — Memory sync job.

---

## Schema references (source of truth)

- Trips: `@schemas/trips` (`tripCreateSchema`, `tripUpdateSchema`, `tripSuggestionSchema`, `itineraryItemCreateSchema`)
- Places/Activities: `@schemas/api` (`placesSearchRequestSchema`)
- Supabase table shapes: `@schemas/supabase`

---

## Streaming notes

Endpoints under `/agents/*` and `/chat/stream` return SSE UI message streams. Use `ReadableStream`/`EventSource` on JS; Python clients should use an SSE-capable library (e.g., `sseclient-py`).

---

## Error & rate-limit notes

- Validation errors: 400 with Zod `issues`.
- Auth errors: 401; ownership checks may return 403.
- Rate limits: 429 with `Retry-After`.

---

## Maintenance

This reference mirrors the current handlers in `src/app/api/**`. Update alongside route or schema changes; reuse the trip TS/Python/cURL snippets as patterns for other JSON POST/GET routes. Streaming endpoints follow the same auth and error conventions but return SSE instead of JSON bodies.
