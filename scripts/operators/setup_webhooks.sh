#!/usr/bin/env bash
set -euo pipefail

# Setup Supabase → Vercel webhooks by configuring Postgres GUCs and optional verification.
# Requirements: psql, DATABASE_URL (or PG* vars), WEBHOOK_TRIPS_URL, WEBHOOK_CACHE_URL, HMAC_SECRET

err() { echo "[setup_webhooks] $*" >&2; }
need() { if [ -z "${!1:-}" ]; then err "Missing required env: $1"; exit 1; fi; }

need WEBHOOK_TRIPS_URL
need WEBHOOK_CACHE_URL
need HMAC_SECRET

psql_run() {
  if [ -n "${DATABASE_URL:-}" ]; then
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 "$@"
  else
    psql -v ON_ERROR_STOP=1 "$@"
  fi
}

echo "[setup_webhooks] Configuring Postgres settings (GUCs) for webhooks..."
psql_run \
  --set=trips_url="${WEBHOOK_TRIPS_URL}" \
  --set=cache_url="${WEBHOOK_CACHE_URL}" \
  --set=hmac_secret="${HMAC_SECRET}" \
  -Atqc "DO $$ BEGIN \\
    EXECUTE format('ALTER DATABASE %I SET app.vercel_webhook_trips = %L', current_database(), :'trips_url'); \\
    EXECUTE format('ALTER DATABASE %I SET app.vercel_webhook_cache = %L', current_database(), :'cache_url'); \\
    EXECUTE format('ALTER DATABASE %I SET app.webhook_hmac_secret = %L', current_database(), :'hmac_secret'); \\nEND $$;"

echo "[setup_webhooks] Verifying settings..."
psql_run -Atqc "SELECT current_setting('app.vercel_webhook_trips', true)  AS trips_url,\n           current_setting('app.vercel_webhook_cache', true)  AS cache_url,\n           nullif(current_setting('app.webhook_hmac_secret', true), '') IS NOT NULL AS hmac_set;"

echo "[setup_webhooks] Run scripts/operators/verify_webhook_secret.sh for CI-friendly secret validation"

echo "[setup_webhooks] Done. Optionally test with curl as documented in docs/operators/supabase-webhooks.md"
