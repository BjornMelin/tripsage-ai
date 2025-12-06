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
- Mark each route module with `import "server-only"` plus `export const dynamic = "force-dynamic"` / `revalidate = 0`
  so BYOK responses are never cached or executed on the client.
  **Note:** Routes accessing `cookies()` or `headers()` (required for Supabase SSR auth) cannot use `"use cache"` directives per Next.js Cache Components restrictions; they are automatically dynamic.
  See [Spec: BYOK Routes and Security (Next.js + Supabase Vault)](../specs/0011-spec-byok-routes-and-security.md).
- Add server-only Supabase admin client using `SUPABASE_SERVICE_ROLE_KEY`.
- Centralize Vault RPC helpers in `frontend/src/lib/supabase/rpc.ts`.
- Enforce PostgREST claims guard in SQL: `request.jwt.claims->>'role'='service_role'`.
- Rate limit with Upstash: `10/min` (POST/DELETE) and `20/min` (validate).
- Redact `api_key` in logs and never return secrets.

### Failure modes & environment guardrails

- **Vault availability:** Production must have `vault`/`supabase_vault` installed; migrations fail fast if missing. Local/CI may use the stubbed `vault.secrets` table but must never ship to prod.
- **Error surfaces:** Distinguish infrastructure errors (`VAULT_UNAVAILABLE`) from user errors (`INVALID_KEY`). Service role RPCs should return consistent error codes for frontend handling.
- **Rotation/readiness checks:** Add a lightweight health check (service role) that calls `vault.decrypted_secrets` and raises alerts if unavailable.
- **No-secret fallback:** Never persist BYOK secrets to regular tables or environment variables; stubs are for local/CI only.

## Consequences

### Positive

- SSR-only secret handling; strict separation of concerns.
- Minimal client footprint; reuse Upstash rate limiter already in repo.

### Negative

- Provider validation performs a lightweight metadata call; network variability can cause transient failures (handled as invalid/NETWORK_ERROR).

## References

- PostgREST roles/claims: <https://docs.postgrest.org/en/v10/auth.html>
- Supabase Vault RPCs: `supabase/migrations/20251030000000_vault_api_keys.sql`
- Rate-limiting ADR: `docs/architecture/decisions/adr-0020-rate-limiting-strategy.md`
