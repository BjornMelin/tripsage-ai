# ADR-0024: BYOK Routes and Security (Next.js + Supabase Vault)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01
**Category**: security, frontend

## Context

We are migrating BYOK key CRUD/validation from FastAPI to Next.js route handlers. Secrets must never reach clients; storage uses Supabase Vault with SECURITY DEFINER RPCs protected by PostgREST JWT claim checks.

## Decision

- Implement Next.js routes:
  - `POST /api/keys` → upsert via `insert_user_api_key`
  - `DELETE /api/keys/[service]` → delete via `delete_user_api_key`
  - `POST /api/keys/validate` → provider metadata check (no persist)
- Add server-only Supabase admin client using `SUPABASE_SERVICE_ROLE_KEY`.
- Centralize Vault RPC helpers in `frontend/src/lib/supabase/rpc.ts`.
- Enforce PostgREST claims guard in SQL: `request.jwt.claims->>'role'='service_role'`.
- Rate limit with Upstash: `10/min` (POST/DELETE) and `20/min` (validate).
- Redact `api_key` in logs and never return secrets.

## Consequences

### Positive

- SSR-only secret handling; strict separation of concerns.
- Minimal client footprint; reuse Upstash rate limiter already in repo.

### Negative

- Provider validation performs a lightweight metadata call; network variability can cause transient failures (handled as invalid/NETWORK_ERROR).

## References

- PostgREST roles/claims: <https://docs.postgrest.org/en/v10/auth.html>
- Supabase Vault RPCs: `supabase/migrations/20251030000000_vault_api_keys.sql`
- Rate limiting ADR: `docs/adrs/adr-0020-rate-limiting-strategy.md`
