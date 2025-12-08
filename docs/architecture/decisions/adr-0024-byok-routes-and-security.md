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

- **Vault availability:** Production must have `vault`/`supabase_vault` installed; migrations fail fast if missing (see `supabase/migrations/20251122000000_base_schema.sql`). Local/CI may use the stubbed `vault.secrets` table but must never ship to prod.
- **Error surfaces:** Distinguish infrastructure errors (`VAULT_UNAVAILABLE`) from user errors (`INVALID_KEY`) and transport errors (`NETWORK_ERROR`). Codes are documented in [SPEC-0011](../specs/archive/0011-spec-byok-routes-and-security.md) and returned by `/api/keys/*` handlers.
- **Rotation/readiness checks:** Health check endpoint (service-role) pings `vault.decrypted_secrets`; integrate alerts with existing Sentry + Datadog monitors (HTTP 5xx or latency >5s triggers pager). Configure monitor on `/api/health/byok` once deployed.
- **No-secret fallback:** Never persist BYOK secrets to regular tables or environment variables; stubs are for local/CI only. Deployment validation should fail if the stub schema exists in production (`app.environment=prod` guard in migration).

### Monitoring and operational follow-ups

- **Health endpoint delivery:** `/api/health/byok` (service-role) is required for readiness/rotation checks and is not yet implemented. Action: add a Next.js route that performs a lightweight `vault.decrypted_secrets` ping and returns 200/500; block production deploy of BYOK without it.
- **Alert wiring:** Add Datadog + Sentry alerts on `/api/health/byok` for HTTP 5xx and p95 latency > 5s (page on 3 consecutive failures, otherwise create ticket). Reuse existing incident runbook once monitors are live.

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
