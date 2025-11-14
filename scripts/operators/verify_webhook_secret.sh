#!/usr/bin/env bash
set -euo pipefail

# Validates that Postgres GUC app.webhook_hmac_secret matches local/Vercel HMAC_SECRET
# Requirements: psql, DATABASE_URL (or PG* vars), HMAC_SECRET

err() { echo "[verify_webhook_secret] $*" >&2; }
need() { if [ -z "${!1:-}" ]; then err "Missing required env: $1"; exit 1; fi; }

need HMAC_SECRET

psql_run() {
  if [ -n "${DATABASE_URL:-}" ]; then
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 "$@"
  else
    psql -v ON_ERROR_STOP=1 "$@"
  fi
}

status=$(psql_run --set=hmac_secret="${HMAC_SECRET}" -Atqc "
SELECT CASE
  WHEN coalesce(current_setting('app.webhook_hmac_secret', true), '') = '' THEN 'MISSING'
  WHEN current_setting('app.webhook_hmac_secret', true) = :'hmac_secret' THEN 'MATCH'
  ELSE 'MISMATCH'
END;")

case "$status" in
  MATCH)
    echo "[verify_webhook_secret] OK: Database secret matches HMAC_SECRET"
    ;;
  MISSING)
    err "Database GUC app.webhook_hmac_secret is not set"
    exit 1
    ;;
  MISMATCH)
    err "Database GUC does not match HMAC_SECRET"
    exit 1
    ;;
  *)
    err "Unexpected verification result: $status"
    exit 1
    ;;
 esac
