# TripSage API Reference (Complete)

Authoritative map of all implemented Next.js route handlers in `src/app/api/**`.

Base URLs

- Prod: `https://tripsage.ai/api`
- Dev: `http://localhost:3000/api`

Conventions

- **Auth**: Supabase SSR cookies (`sb-access-token`) unless “Anonymous” noted.
- **Rate limit**: Per-route keys (e.g., `trips:list`, `places:search`); 429 on exceed.
- **Errors**: `{ "error": "<code>", "reason": "<human text>", "issues"?: [...] }`
- **Streaming**: “SSE stream” returns Server-Sent Events (AI SDK v6 UI stream).

Quick trip examples

TypeScript

```ts
const BASE = process.env.API_URL ?? "http://localhost:3000/api";
export async function createTrip(jwt: string) {
  const res = await fetch(`${BASE}/trips`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: `sb-access-token=${jwt}` },
    body: JSON.stringify({
      title: "Summer Vacation",
      destination: "Paris",
      startDate: "2025-07-01",
      endDate: "2025-07-15",
      travelers: 2,
      budget: 3000,
      currency: "USD",
    }),
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
resp = requests.get(f"{BASE}/trips/1", cookies=cookies)
resp.raise_for_status()
trip = resp.json()
```

cURL

```bash
curl -X GET "http://localhost:3000/api/trips/1" --cookie "sb-access-token=<jwt>"
```

---

## Endpoint catalog

### Auth

- `POST /auth/login` (Auth: Anonymous) — Email/password login; sets Supabase cookies.

### Trips

- `GET /trips` (Auth) — List trips; query: `destination`, `status`, `startDate`, `endDate`.
- `POST /trips` (Auth) — Create trip. Body: `title`, `destination`, `startDate`, `endDate`; optional `budget`, `currency`, `status` (default `planning`), `travelers`, `tripType`, `visibility`, `tags`, `description`, `preferences`.
- `GET /trips/{id}` (Auth) — Get trip.
- `PUT /trips/{id}` (Auth) — Partial update (same fields as create).
- `DELETE /trips/{id}` (Auth) — Delete trip.
- `GET /trips/suggestions` (Auth) — AI suggestions. Query: `limit`, `budget_max`, `category`. Returns `TripSuggestion[]`.

**Examples**
TS (create)

```ts
await fetch(`${BASE}/trips`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Cookie: `sb-access-token=${jwt}` },
  body: JSON.stringify({
    title: "Summer Vacation",
    destination: "Paris",
    startDate: "2025-07-01",
    endDate: "2025-07-15",
    travelers: 2,
    budget: 3000,
    currency: "USD",
  }),
});
```

cURL (get)

```bash
curl -X GET "$BASE/trips/1" --cookie "sb-access-token=$JWT"
```

Python (update)

```python
requests.put(f"{BASE}/trips/1",
             cookies={"sb-access-token": jwt},
             json={"destination": "Rome", "title": "Updated Trip"})
```

Sample responses

- List: `200` → `UiTrip[]`
- Detail: `200` → `UiTrip`; `404` if not found
- Suggestions: `200` → `TripSuggestion[]`; `401` if unauthenticated

### Itineraries (items)

- `GET /itineraries` (Auth) — List itinerary items; optional `tripId` filter.
- `POST /itineraries` (Auth) — Create itinerary item. Body per `itineraryItemCreateSchema` (`tripId`, `title`, `itemType`, optional times, price/currency, description, metadata, location, bookingStatus).

Examples

- cURL create:

  ```bash
  curl -X POST "$BASE/itineraries" \
    --cookie "sb-access-token=$JWT" \
    -H "Content-Type: application/json" \
    -d '{"tripId":1,"title":"Louvre","itemType":"activity","startTime":"2025-07-02T10:00:00Z"}'
  ```

- Response: `201` → itinerary row; `403` if trip not owned.

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
- `POST /agents/memory` — Conversational memory agent.
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

- `POST /embeddings` (Auth) — Generate embeddings.

### Routes

- `POST /routes` (Auth) — Multimodal route planner.

### Flights utility

- `GET /flights/popular-destinations` (Auth) — Popular destination list.

### User settings

- `GET /user-settings` (Auth) — Get settings.
- `POST /user-settings` (Auth) — Update settings.

### Telemetry demo

- `POST /telemetry/ai-demo` (Auth) — Demo/observability endpoint.

### AI stream (generic)

- `POST /ai/stream` (Auth) — Generic AI stream route used in demos/tests.

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
