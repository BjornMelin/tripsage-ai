# Frontend Agent Operations (Full Cutover)

This runbook covers operating the frontend-only agents implemented with Vercel AI SDK v6. This deployment performs a full cutover (no feature flags/waves).

## Endpoints

- `POST /api/agents/flights` – Flight search (streaming)
- `POST /api/agents/accommodations` – Accommodation search (streaming)
- `POST /api/agents/budget` – Budget planning (streaming)
- `POST /api/agents/memory` – Memory updates (streaming)
- `POST /api/agents/destinations` – Destination research (streaming)
- `POST /api/agents/itineraries` – Itinerary planning (streaming)
- `POST /api/agents/router` – Router classification (JSON)

All streaming endpoints return UI-compatible responses via `toUIMessageStreamResponse()`.

## Required Environment

- Upstash Redis for caching and rate limiting:
  - `UPSTASH_REDIS_REST_URL`
  - `UPSTASH_REDIS_REST_TOKEN`
- Supabase SSR:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- QStash webhooks: `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`
- Model providers: BYOK or gateway keys (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `AI_GATEWAY_API_KEY`, `AI_GATEWAY_URL`)
- Flights provider (Duffel): prefer `DUFFEL_ACCESS_TOKEN` (fallback `DUFFEL_API_KEY`)
- Google Maps: server key `GOOGLE_MAPS_SERVER_API_KEY`; browser key `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY`
- Weather (optional): `OPENWEATHERMAP_API_KEY`

Temperatures are hard-coded per agent (default 0.3). Adjust via code near each agent orchestrator.

## Guardrails (Always On)

- Per-tool Redis caching with TTLs and SHA-256 input hashing.
- Upstash sliding-window rate limits configured in `frontend/src/lib/ratelimit/config.ts`:
  - Flights: 8/minute
  - Accommodations: 10/minute
  - Budget: 6/minute
  - Memory: 20/minute
  - Destinations: 8/minute
  - Itineraries: 6/minute
  - Router: 100/minute
- Rate limits use centralized `buildRateLimit(workflow, identifier)` factory function.
- Telemetry events per call: `workflow`, `tool`, `cacheHit`, `durationMs`.
- Error recovery: All streaming routes use `onError` handlers for user-friendly error messages.

## Validation & Local Testing

```bash
cd frontend
pnpm biome:check
pnpm type-check
pnpm test:run
```

## UI Rendering

The chat page detects assistant JSON with `schemaVersion` and renders cards:

- `flight.v1` → FlightOfferCard
- `stay.v1` → StayCard
- `budget.v1` → BudgetChart
- `dest.v1` → DestinationCard
- `itin.v1` → ItineraryTimeline

Quick actions exist in the Prompt action menu to kick off common searches (flights, stays, budget, destination research, itinerary planning).

## Observability

### Telemetry Queries

#### Success Rate

Query for success rate (2xx responses / total requests):

```javascript
// Example: Count 2xx vs total requests per workflow
// Filter logs by "agent.span" events and group by workflow
// Success: status < 400, Failure: status >= 400
```

#### Latency Metrics

Query for p50 and p95 latency:

```javascript
// Example: Extract durationMs from "agent.span" logs
// Calculate percentiles: p50 (median), p95
// Filter by workflow and identifier_type
```

#### Rate Limit Hit Rate

Query for rate limit events:

```javascript
// Example: Count "rate_limit_exceeded" errors per identifier
// Filter by error: "rate_limit_exceeded" in agent route logs
// Group by workflow and time window
```

### Log Patterns

- Route-level spans: `agent.span` with `name`, `durationMs`, `workflow`, `identifier_type`, `modelId`
- Tool-level events: `agent.tool` with `tool`, `workflow`, `cacheHit`, `durationMs`, `status`
- Errors: `agent.error` with `error`, `reason`, redacted `message` and `context`

## Runtime Environment

Agents run on **Node.js runtime** (not Edge). This enables:

- Full access to Node.js APIs (crypto, fs, etc.)
- Upstash Redis client compatibility
- Supabase SSR client support

### Edge Runtime Considerations

If migrating to Edge runtime in the future, consider:

- Tool dependencies: Some tools may require Node.js APIs (e.g., `node:crypto` for hashing)
- Redis client: Verify Upstash Redis REST client compatibility with Edge
- Supabase client: Confirm `@supabase/ssr` Edge runtime support
- Provider resolution: Ensure BYOK registry works in Edge context

## Rollback

Because this is a pre-deploy full cutover, rollback means redeploying the prior build artifacts (no flag flip). If you still run legacy backends in parallel, route traffic at the edge to legacy endpoints as needed.
