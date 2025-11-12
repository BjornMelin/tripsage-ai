# Frontend Agent Operations (Full Cutover)

This runbook covers operating the frontend-only Flight and Accommodation agents implemented with Vercel AI SDK v6. This deployment performs a full cutover (no feature flags/waves).

## Endpoints

- `POST /api/agents/flights` – Flight search (streaming)
- `POST /api/agents/accommodations` – Accommodation search (streaming)

Both stream UI-compatible responses via `toUIMessageStreamResponse()`.

## Required Environment

- Upstash Redis for caching and rate limiting:
  - `UPSTASH_REDIS_REST_URL`
  - `UPSTASH_REDIS_REST_TOKEN`
- Supabase SSR:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Model provider BYOK/Gateway: configured in `frontend/src/lib/providers/registry.ts`.
- Flights provider (Duffel): prefer `DUFFEL_ACCESS_TOKEN` (fallback `DUFFEL_API_KEY`).
- Optional per-workflow temperature (defaults to 0.3):
  - `AGENT_TEMP_FLIGHT`, `AGENT_TEMP_ACCOMMODATION`

## Guardrails (Always On)

- Per-tool Redis caching with TTLs and SHA-256 input hashing.
- Upstash sliding-window rate limits (per workflow/tool):
  - Flights: 8/minute
  - Accommodations: 10/minute
- Telemetry events per call: `workflow`, `tool`, `cacheHit`, `durationMs`.

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

Quick actions exist in the Prompt action menu to kick off common searches.

## Rollback

Because this is a pre-deploy full cutover, rollback means redeploying the prior build artifacts (no flag flip). If you still run legacy backends in parallel, route traffic at the edge to legacy endpoints as needed.
