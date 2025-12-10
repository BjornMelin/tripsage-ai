# SPEC-0021: Supabase Database Webhooks to Vercel Route Handlers Consolidation

**Status**: Implemented
**Date**: 2025-12-10
**ADRs**: ADR-0040, ADR-0041, ADR-0048

## Summary

Migrate Deno-based Supabase Edge Functions to Vercel endpoints. Use Supabase Database Webhooks (pg_net + `supabase_functions.http_request`) to POST events to Vercel. Implement Node runtime Route Handlers and Background Functions for:

- Trip notifications (`/api/hooks/trips`)
- File processing (`/api/hooks/files`)
- Cache invalidation (`/api/hooks/cache`)
- Embeddings (`/api/embeddings`)

Decommission Supabase Edge Functions and related CLI deploy steps after dual-run validation.

## Goals

- Single runtime (Vercel) for application compute
- Maintain or improve reliability with idempotent handlers and retries
- Preserve security posture (HMAC signatures; least-privilege DB user)

## Non‑Goals

- Rewriting DB schema or RLS policies beyond minimal fixes for webhook logs and definers
- Introducing binary-heavy media processing pipelines (future work may add a queue/worker)

## Architecture

### Event Flow

1. Postgres trigger fires on target tables (INSERT/UPDATE/DELETE)
2. Trigger calls `supabase_functions.http_request` with:
   - URL: Vercel endpoint (regional)
   - Method: POST
   - Headers: `Content-Type: application/json`, `X-Event-Type`, `X-Table`, `X-Signature-HMAC`
   - Body: `json_build_object` of `type`, `table`, `schema`, `record`, `old_record`, `occurred_at`
   - Timeout: 5–10s (async, non-blocking)
3. Vercel endpoint validates signature, persists/updates as needed via Supabase JS with restricted key, and responds 2xx on acceptance; long work is offloaded to Background Functions.

### Regions and Runtime

- Pin Vercel functions to the Supabase region (e.g., `iad1`) via `vercel.json`
- Use `export const runtime = 'nodejs'` and `export const dynamic = 'force-dynamic'` on Route Handlers; Background Functions for tasks > request lifecycle

## Webhook Flow Mapping

| Table | Events | Target Handler | Cache Tags | QStash | Notes |
|-------|--------|----------------|------------|--------|-------|
| `trip_collaborators` | INSERT/UPDATE/DELETE | `/api/hooks/trips` | N/A | Yes (notify-collaborators) | Resend email, optional downstream webhook |
| `file_attachments` | INSERT/UPDATE | `/api/hooks/files` | N/A | No | Lightweight verification only |
| `trips` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | trip, user_trips, trip_search, search, search_cache | No | Version bump |
| `flights` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | flight, flight_search, search, search_cache | No | Version bump |
| `accommodations` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | accommodation, hotel_search, search, search_cache | No | Version bump |
| `search_destinations` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | search, search_cache | No | Version bump |
| `search_flights` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | search, search_cache | No | Version bump |
| `search_hotels` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | search, search_cache | No | Version bump |
| `search_activities` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | search, search_cache | No | Version bump |
| `chat_messages` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | memory, conversation, chat_memory | No | Version bump |
| `chat_sessions` | INSERT/UPDATE/DELETE | `/api/hooks/cache` | memory, conversation, chat_memory | No | Version bump |

## Security

- HMAC signature: `X-Signature-HMAC: hex(hmac_sha256(secret, raw_body))`
- Shared secret stored in Supabase config and Vercel env (`HMAC_SECRET`)
- Restricted DB key: create a Postgres service user limited to necessary tables/ops, used by Vercel
- SQL hardening:
  - Revoke `SELECT` on `webhook_logs` for `authenticated`
  - Restrict `EXECUTE` on SECURITY DEFINER functions to service/admin role only
  - Pin `search_path` for SECURITY DEFINER functions to `pg_catalog, public`

## Endpoints

### POST /api/hooks/trips

- Headers: `X-Event-Type`, `X-Table`, `X-Signature-HMAC`
- Body: `{ type, table, schema, record, old_record, occurred_at }`
- Behavior:
  - Validate signature and known table (e.g., `trip_collaborators`).
  - Compute a stable event key from table, type, occurred_at, and record hash.
  - Enforce idempotency via Upstash Redis (`SET NX` with TTL) using the event key.
  - For `trip_collaborators`, enqueue a job to the QStash-backed notification worker
    (see SPEC-0025). The worker rejects requests unless `QSTASH_CURRENT_SIGNING_KEY`
    is configured and the `Upstash-Signature` header verifies. The route only falls
    back to in-process work when QStash is intentionally disabled for development.

### POST /api/hooks/files

- Node runtime only (uses Supabase Storage)
- Behavior:
  - Validate signature
  - For INSERT on `file_attachments` with `uploading` status → background process
  - Processing includes Storage download, virus-scan stub, optional image transform, and metadata update
  - Idempotency on `file_id` + transition

### POST /api/hooks/cache

- Behavior:
  - Validate signature via the shared HMAC helper.
  - Determine cache tags for the table (e.g., `trip`, `search`) and bump their version
    counters in Upstash Redis via `bumpTags(tags)`; consumers compose cache keys as
    `tag:v{version}:{key}` using `src/lib/cache/tags.ts`.
  - Return the bumped versions for observability; no Redis key deletion or downstream
    webhook forwarding occurs in the final implementation.

### POST /api/embeddings

- Behavior:
  - Accept `{ text }` or `{ property }` payload
  - Use provider embeddings via AI SDK (OpenAI/Gateway)
  - Optionally upsert vector into target table

## Database (SQL)

Enable pg_net and setup webhooks:

```sql
-- Enable extension (if not enabled)
create extension if not exists pg_net;

-- Example trigger for trip_collaborators
create or replace function public.notify_trip_collaborators() returns trigger as $$
declare
  url text := current_setting('app.vercel_webhook_trips', true);
  secret text := current_setting('app.webhook_hmac_secret', true);
  payload jsonb;
begin
  payload := jsonb_build_object(
    'type', TG_OP,
    'table', TG_TABLE_NAME,
    'schema', TG_TABLE_SCHEMA,
    'record', case when TG_OP = 'DELETE' then to_jsonb(OLD) else to_jsonb(NEW) end,
    'old_record', case when TG_OP = 'UPDATE' then to_jsonb(OLD) else null end,
    'occurred_at', now()
  );

  perform supabase_functions.http_request(
    url,
    'POST',
    jsonb_build_object(
      'Content-Type', 'application/json',
      'X-Event-Type', TG_OP,
      'X-Table', TG_TABLE_NAME,
      -- HMAC computed in app layer if pgcrypto available; alternatively skip and rely on IP allowlist
      'X-Signature-HMAC', null
    ),
    payload,
    8000
  );

  return coalesce(NEW, OLD);
end; $$ language plpgsql security definer set search_path = pg_catalog, public;

drop trigger if exists trg_trip_collaborators_webhook on public.trip_collaborators;
create trigger trg_trip_collaborators_webhook
after insert or update or delete on public.trip_collaborators
for each row execute function public.notify_trip_collaborators();
```

Notes:

- If HMAC must be computed in SQL, add `pgcrypto` and compute `encode(hmac(payload::text, secret, 'sha256'), 'hex')` before calling `http_request`.
- Prefer storing `app.*` GUCs through `alter database ... set` or secrets table.

## Configuration

Vercel env:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY` (or restricted service key)
- `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`
- `RESEND_API_KEY`
- `HMAC_SECRET`

vercel.json (excerpt):

```json
{
  "functions": {
    "app/api/hooks/**": { "runtime": "nodejs", "maxDuration": 60, "regions": ["iad1"] },
    "app/api/embeddings/route.ts": { "runtime": "nodejs", "maxDuration": 60, "regions": ["iad1"] }
  }
}
```

## Failure Modes & Retries

- Supabase Database Webhooks are at-least-once: handlers must be idempotent
- Use exponential backoff on Vercel Background re-queues when needed
- Alert on non-2xx rates and latency spikes; log structured JSON

## Testing

- Unit: HMAC verification, payload validation, idempotency guards
- Integration: mock Supabase/Upstash/Resend; verify state transitions
- Load: burst events on file_attachments and trip_collaborators; measure P95 < 250ms acceptance

## Migration Plan

1. Implement Vercel endpoints and configure env/regions
2. Create SQL triggers for Database Webhooks (tables: trips, flights, accommodations, search_*, trip_collaborators, chat_*)
3. Dual-run: route DB events to Vercel while keeping Deno deployed; compare logs/results for 1–2 weeks
4. Remove Deno functions and Makefile targets; update docs/runbooks

## Rollback

- Re-enable Deno endpoints and point triggers back if parity issues arise
- Keep tagged snapshot of removed functions for 30 days

## Production Checklist

### Required Environment Variables (Vercel)

| Variable | Required | Description |
|----------|----------|-------------|
| `HMAC_SECRET` | Yes | Shared secret for Supabase→Vercel webhook signatures |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key for admin operations |
| `UPSTASH_REDIS_REST_URL` | Yes | Upstash Redis URL for idempotency/cache |
| `UPSTASH_REDIS_REST_TOKEN` | Yes | Upstash Redis token |
| `QSTASH_TOKEN` | Yes | QStash token for job publishing |
| `QSTASH_CURRENT_SIGNING_KEY` | Yes | QStash signature verification |
| `QSTASH_NEXT_SIGNING_KEY` | No | Key rotation support |
| `RESEND_API_KEY` | No | Email notifications |
| `COLLAB_WEBHOOK_URL` | No | Downstream webhook URL |

### Supabase Database Configuration

```sql
-- Set webhook URLs
ALTER DATABASE postgres SET app.vercel_webhook_trips = 'https://your-app.vercel.app/api/hooks/trips';
ALTER DATABASE postgres SET app.vercel_webhook_cache = 'https://your-app.vercel.app/api/hooks/cache';
ALTER DATABASE postgres SET app.webhook_hmac_secret = 'your-secret-here';
```

### Verification Steps

1. Deploy Vercel functions
2. Set environment variables in Vercel dashboard
3. Configure Supabase database settings via SQL
4. Test with a `trip_collaborators` INSERT
5. Verify idempotency with duplicate events
6. Check telemetry spans in observability dashboard

## Monitoring & Alerts

### Key Metrics

| Metric | Threshold | Alert |
|--------|-----------|-------|
| Webhook verification failures | >10/min | Critical |
| Duplicate event rate | >20% | Warning |
| QStash DLQ size | >0 | Warning |
| Webhook latency P95 | >500ms | Warning |

### Telemetry Spans

- `webhook.trips` - Trip collaborator webhook processing
- `webhook.files` - File attachment webhook processing
- `webhook.cache` - Cache invalidation webhook processing
- `jobs.notify-collaborators` - QStash notification worker
- `notifications.collaborators` - Email/webhook delivery
- `qstash.dlq.push` - Dead letter queue entry creation
- `qstash.dlq.list` - Dead letter queue listing
- `qstash.dlq.remove` - Dead letter queue entry removal

### Dead Letter Queue

Failed jobs after max retries are stored in Redis under `qstash-dlq:*` keys. Monitor:

- `qstash-dlq:notify-collaborators` - Failed notification jobs

DLQ configuration (see `src/lib/qstash/config.ts`):

- Max entries per job type: 1000
- TTL: 7 days
- Key prefix: `qstash-dlq`

### Runbook

1. **High verification failure rate**: Check HMAC_SECRET matches between Supabase and Vercel
2. **DLQ entries accumulating**: Check Resend/webhook health, review error logs
3. **High duplicate rate**: Check Redis connectivity, review idempotency TTL
4. **Worker failures**: Check QStash dashboard, verify signing keys configured
