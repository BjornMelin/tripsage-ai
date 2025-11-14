# Supabase Webhooks (DB → Vercel) – Operator Guide

This guide shows how to configure Postgres settings (GUCs) for the consolidated webhook migration and how to verify end‑to‑end delivery with a signed HMAC request. It also explains how trip collaborator notifications are processed via Upstash QStash and Resend.

## Prerequisites

- Apply the consolidated migration: `20251113034500_webhooks_consolidated.sql`.
- Vercel project deployed with the webhook routes:
  - `/api/hooks/trips`
  - `/api/hooks/cache`
  - `/api/jobs/notify-collaborators` (QStash worker for trip notifications)
- Vercel env var `HMAC_SECRET` set to a strong secret.
- Vercel env vars for notifications:
  - `QSTASH_TOKEN`, `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY`
  - `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `RESEND_FROM_NAME`
  - Optional `COLLAB_WEBHOOK_URL`
- The QStash worker rejects requests when `QSTASH_CURRENT_SIGNING_KEY` is missing or
  signatures fail verification. Configure the keys before directing production traffic.

## 1) Configure Postgres settings (GUCs)

Run in psql or Supabase SQL editor (or execute `scripts/operators/setup_webhooks.sh`). Replace values to match your environment.

```sql
-- Set once on the database (preferred). Replace <db_name> and your domain.
ALTER DATABASE <db_name>
  SET app.vercel_webhook_trips = 'https://<your-vercel-domain>/api/hooks/trips';
ALTER DATABASE <db_name>
  SET app.vercel_webhook_cache = 'https://<your-vercel-domain>/api/hooks/cache';
ALTER DATABASE <db_name>
  SET app.webhook_hmac_secret   = '<same-secret-as-VERCEL-HMAC_SECRET>';

-- Verify
SELECT current_setting('app.vercel_webhook_trips', true)  AS trips_url,
       current_setting('app.vercel_webhook_cache', true)  AS cache_url,
       nullif(current_setting('app.webhook_hmac_secret', true), '') IS NOT NULL AS hmac_set;
```

Notes

- You can also set per-session using `SET` during testing. The migration functions use `current_setting(..., true)` which returns NULL when unset.
- Secrets rotate by updating the database setting and Vercel env atomically (briefly accept both on server during rotation if desired).
- Automate validation with `scripts/operators/verify_webhook_secret.sh`. The script exits non-zero if the database GUC diverges from `HMAC_SECRET`, making it safe to run in CI/CD checklists.
- `.github/workflows/deploy.yml` executes the verification script before creating a deployment. Configure the `PRIMARY_DATABASE_URL` secret (or fallback `DATABASE_URL`) with a writable primary Supabase connection string so drift stops the workflow instead of silently shipping.

## 2) Test signed webhook (manual)

Prepare a small JSON payload and compute `X-Signature-HMAC` in your shell using `openssl`.

```bash
# Example payload (trip_collaborators INSERT)
payload='{"type":"INSERT","table":"trip_collaborators","record":{"id":"test","trip_id":1},"occurred_at":"2025-11-13T03:00:00Z"}'

# Compute HMAC (hex) with same secret used in Vercel/Supabase
sig=$(printf "%s" "$payload" | openssl dgst -sha256 -hmac "$HMAC_SECRET" -hex | sed 's/^.* //')

# Send to TRIPS webhook
curl -i \
  -H 'Content-Type: application/json' \
  -H "X-Signature-HMAC: $sig" \
  -d "$payload" \
  https://<your-vercel-domain>/api/hooks/trips
```

Expected (hook only)

- `HTTP/1.1 200 OK` and JSON `{ ok: true, ... }` or `{ ok: true, skipped: true }` depending on payload/table.
- 401 for invalid/missing signature.

## 3) Test end‑to‑end from Postgres

Set the GUCs and execute a change to a subscribed table (e.g., `INSERT INTO trip_collaborators ...`). The trigger will POST to your Vercel route with a signed HMAC.

If QStash is configured, `/api/hooks/trips` enqueues a job to `/api/jobs/notify-collaborators`.
The worker validates the `Upstash-Signature` header with the configured signing keys and
returns HTTP 500 if the keys are missing. Only development environments without QStash
fall back to in-process notifications.

Cache invalidation events post to `/api/hooks/cache`, which bumps per-tag version
counters in Upstash Redis. Downstream consumers compose cache keys as
`tag:v{version}:{key}`; no Redis key purging or downstream webhooks occur.

Troubleshooting

- Use Vercel function logs; look for span names `webhook.trips` / `webhook.cache`.
- Verify `app.webhook_hmac_secret` matches `HMAC_SECRET` exactly (no quotes/whitespace).
- If you see 401s, re‑compute signature locally using the exact JSON the DB sends (`payload::text`).

## 4) Security notes

- HMAC header is omitted when no secret is configured; handlers reject missing/invalid signatures.
- Functions run with `SECURITY DEFINER` and `search_path = pg_catalog, public` to avoid hijacking.
- Keep secrets in DB settings; do not store them in tables.
- QStash uses `Upstash-Signature` for worker calls; worker routes verify signatures with the configured signing keys and fail closed when they are absent.

## 5) Observability

- Webhook handlers emit spans `webhook.trips`, `webhook.cache`, and `webhook.files`. Failures due to missing secrets add an event `webhook_verification_failed` on the active span (`reason = missing_secret_env | invalid_signature | invalid_json | invalid_payload_shape`).
- Both handlers also log structured `[operational-alert]` entries when verification fails. Alerts are JSON with `event` (`webhook.verification_failed`) and a reason attribute; wire log drains or SIEM queries to page on repeated failures.
- Redis-backed helpers emit `redis.unavailable` spans and matching `[operational-alert]` log entries when cache invalidation or idempotency would silently degrade due to missing Upstash credentials. Investigate environment configuration immediately when this event appears.
