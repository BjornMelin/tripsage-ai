# SPEC-0011: BYOK Routes and Security (Next.js + Supabase Vault)

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-11-01

## Objective

Move BYOK key CRUD and validation to Next.js route handlers using Supabase Vault RPCs guarded by PostgREST claims. Ensure no secret leakage and add rate limits and tests.

## Routes

- POST `/api/keys`
  - Body: `{ service: 'openai'|'openrouter'|'anthropic'|'xai', api_key: string }`
  - Response: `204 No Content` on success; `400` invalid service/body; `401` unauthenticated; `500` on RPC failure
- DELETE `/api/keys/[service]`
  - Response: `204 No Content` on success; `400` invalid service; `401` unauthenticated; `500` on failure
- POST `/api/keys/validate`
  - Body: `{ service: string, api_key: string }`
  - Response: `{ is_valid: boolean, reason?: string }`

## Server Components

- `frontend/src/lib/supabase/admin.ts`: Admin client factory using `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
- `frontend/src/lib/supabase/rpc.ts`: Typed wrappers: `insertUserApiKey`, `deleteUserApiKey`, `getUserApiKey`, `touchUserApiKey`.

## Security

- SQL guard: `coalesce((current_setting('request.jwt.claims', true)::json->>'role'),'') = 'service_role'` in RPCs.
- Server-only env usage; no secrets serialized to client.
- Logs redact `api_key`.
- Each Next.js route imports `"server-only"` and exports `dynamic = "force-dynamic"` / `revalidate = 0` so responses are evaluated per request and never cached or served to clients.
- Handlers normalize service identifiers (trim/lowercase) once before calling Vault RPCs to prevent mismatched deletes.

## Rate Limiting

- Upstash Ratelimit enabled when `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are set.
- Limits: `10/min` for POST/DELETE; `20/min` for validate.

## Error Mapping

- JSON error shape: `{ error: string, code?: string }` with appropriate HTTP status.
- Validation returns `is_valid: false` and `reason` for unauthorized/network/HTTP status.
- Planned standard codes (target, per ADR-0024):
  - `VAULT_UNAVAILABLE` — vault extension/service not reachable.
  - `INVALID_KEY` — provider rejected key or validation failed.
  - `NETWORK_ERROR` — network/transport failure when calling provider.
- Current implementation (routes in `frontend/src/app/api/keys/**`):
  - `transport_error`, `http_<status>`, `unauthorized` from validation handler
  - `db_error` for Supabase failures
- **Follow-up (pre-GA):** Map current codes to planned standard set above (see mapping table below) so clients have a stable contract. This must be completed before BYOK is generally available; create a tracking issue with owner assignment and target release milestone.
  - Recommended mapping: `db_error` → `VAULT_UNAVAILABLE`; `transport_error`/`http_5xx` → `NETWORK_ERROR`; `http_4xx`/`unauthorized` → `INVALID_KEY`
  - Update all route handlers in `frontend/src/app/api/keys/**` and integration tests accordingly.

## Testing

- Vitest unit tests for RPC wrappers with `createAdminSupabase` mocked.
- Integration tests for route handlers with Supabase SSR and provider fetch mocked.
- Helper tests covering `getClientIpFromHeaders`/`buildRateLimitKey` ensure rate-limit identifiers always fall back to `"unknown"` when proxy headers are absent.

## Links

- ADR: [ADR-0024](../../architecture/decisions/adr-0024-byok-routes-and-security.md)
- PostgREST docs: <https://docs.postgrest.org/en/v10/auth.html>
