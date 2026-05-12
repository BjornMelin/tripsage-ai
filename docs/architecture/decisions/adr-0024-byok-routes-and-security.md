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
- Mark each route module with `import "server-only"`. With Cache Components enabled, Route Segment config options like `dynamic` and `revalidate` are disabled, so request-time behavior is enforced by auth-scoped Request APIs (`cookies()`, `headers()`) and by avoiding `use cache` on BYOK/user-scoped handlers.
  **Note:** Routes accessing `cookies()` or `headers()` (required for Supabase SSR auth) cannot use `"use cache"` directives per Next.js Cache Components restrictions; they are automatically dynamic.
  See [Spec: BYOK Routes and Security (Next.js + Supabase Vault)](../../specs/archive/0011-spec-byok-routes-and-security.md).
- Add server-only Supabase admin client using `SUPABASE_SERVICE_ROLE_KEY`.
- Centralize Vault RPC helpers in `src/lib/supabase/rpc.ts`.
- Enforce PostgREST claims guard in SQL: `request.jwt.claims->>'role'='service_role'`.
- Rate limit with Upstash: `10/min` (POST/DELETE) and `20/min` (validate).
- Redact `api_key` in logs and never return secrets.

### Failure modes & environment guardrails

- **Vault availability:** Production must have `vault`/`supabase_vault` installed; migrations fail fast if missing (see `supabase/migrations/20260120000000_base_schema.sql`). Local/CI may use the stubbed `vault.secrets` table but must never ship to prod.
- **Error surfaces:** Distinguish infrastructure errors (`VAULT_UNAVAILABLE`) from user errors (`INVALID_KEY`), transport errors (`NETWORK_ERROR`), and timeout errors (`REQUEST_TIMEOUT`). Codes are documented in [SPEC-0011](../../specs/archive/0011-spec-byok-routes-and-security.md) and returned by `/api/keys/*` handlers.
- **Rotation/readiness checks:** `/api/health/byok` is protected by the scoped `BYOK_HEALTHCHECK_KEY` operator token, calls the service-role-only `check_byok_vault_health()` RPC, creates/decrypts/deletes a non-user probe secret, and returns only status metadata. Operators wire HTTP 5xx and p95 latency >5s to Sentry/Datadog or the active OpenTelemetry backend. Tracking: [#632](https://github.com/BjornMelin/tripsage-ai/issues/632), [#633](https://github.com/BjornMelin/tripsage-ai/issues/633)
- **No-secret fallback:** Never persist BYOK secrets to regular tables or environment variables; stubs are for local/CI only. Deployment validation should fail if the stub schema exists in production (`app.environment=prod` guard in migration).

### Monitoring and operational follow-ups

The BYOK production readiness loop is implemented in application code. Operators must still create provider-specific monitors in the active observability backend:

- **Health endpoint delivery:** `/api/health/byok` performs a lightweight Vault/RPC readiness ping through `check_byok_vault_health()` and is exercised by `pnpm ops ai check byok-health` when `BYOK_HEALTHCHECK_KEY` is configured.
- **Alert wiring:** Add Datadog + Sentry alerts on `/api/health/byok` for HTTP 5xx and p95 latency > 5s (page on 3 consecutive failures, otherwise create ticket). Reuse the BYOK operator runbook for incident triage.

## Consequences

### Positive

- SSR-only secret handling; strict separation of concerns.
- Minimal client footprint; reuse Upstash rate limiter already in repo.

### Negative

- Provider validation performs a lightweight metadata call; network variability can cause transient failures (handled as invalid/NETWORK_ERROR) or timeouts (`REQUEST_TIMEOUT`).

## References

- PostgREST roles/claims: <https://docs.postgrest.org/en/v10/auth.html>
- Supabase Vault RPCs: `supabase/migrations/20260120000000_base_schema.sql` (historical split migrations are archived under `supabase/migrations/archive/`)
- BYOK health RPC: `supabase/migrations/20260511000000_byok_vault_health_check.sql`
- Rate-limiting ADR: [ADR-0032](adr-0032-centralized-rate-limiting.md)
