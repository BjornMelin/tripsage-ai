# TripSage AI — Security & Privacy (v1.0.0)

## Threat Model (summary)

- Auth/session theft, CSRF, XSS, SSRF.
- Abuse of AI endpoints (cost + prompt injection).
- Data exposure via misconfigured Supabase RLS or storage buckets.
- Webhook forgery / replay (QStash / external providers).

## Non-Negotiables

- Secrets only via env; never exposed to client bundles.
- RLS must enforce tenant isolation and least privilege.
- All inputs validated at boundaries (route handlers + server actions).
- Rate limiting on externally exposed endpoints with abuse potential.

## Required Reviews (v1.0.0)

- Route inventory: ensure no unexpected unauthenticated access (see `docs/release/01-current-state-audit.md` route table).
- Supabase RLS: confirm every user-scoped table enforces `auth.uid()` ownership (see `supabase/migrations/`).
- Storage buckets: confirm private buckets + signed URLs for attachments (see `supabase/config.toml` bucket config).
- Webhooks: verify signed webhook validation (HMAC / QStash) on `/api/hooks/*`.
- Logs/telemetry: ensure no PII leakage (see `docs/development/backend/observability.md`).
- Env validation: production must fail fast on invalid/placeholder secrets; non-production may be lenient for optional integrations (see `docs/tasks/T-001-dev-server-env-validation.md`).

## Authentication & Session Security

- SSR auth should use Supabase SSR helpers (server-only).
- Routes that require auth must return standardized 401/403 responses.
- Logout must revoke tokens/server sessions (verify in browser automation).

## Rate Limiting / Abuse Controls

- Ensure cost-sensitive routes fail closed when Redis is unavailable:
  - AI streaming, embeddings, chat tools, travel API calls.
- Confirm bot protection is enabled where intended (BotID) and does not bypass auth.

## Privacy / PII

- Telemetry identifiers should be hashed/redacted; never log raw tokens, emails, or API keys.
- File uploads must restrict size/type and enforce per-user access.

## Output

Concrete findings and tasks will be tracked in `docs/tasks/INDEX.md` with P0/P1 labels.
