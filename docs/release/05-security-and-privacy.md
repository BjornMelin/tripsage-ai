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
- Routes that require auth must return standardized 401/403 responses via `src/lib/api/route-helpers.ts`:
  - 401: `unauthorizedResponse()` → `{ "error": "unauthorized", "reason": "Authentication required" }`
  - 403: `forbiddenResponse("...")` → `{ "error": "forbidden", "reason": "..." }`
- Logout must revoke tokens/server sessions and be verified via browser automation (Playwright):
  - `e2e/dashboard-functionality.spec.ts` → `test("logout functionality works", ...)`

## Rate Limiting / Abuse Controls

- Ensure cost-sensitive routes fail closed when Redis is unavailable:
  - AI streaming, embeddings, chat tools, travel API calls.
- Confirm bot protection is enabled where intended (BotID) and does not bypass auth.

## Privacy / PII

- Telemetry identifiers should be hashed/redacted; never log raw tokens, emails, or API keys.
- File uploads must restrict size/type and enforce per-user access.

## Supabase RLS + Storage (audit notes)

**Source of truth:** `supabase/migrations/20260120000000_base_schema.sql` (squashed, pre-deployment).

### User-scoped tables (examples)

These tables are intended to be scoped to `auth.uid()` (either direct ownership or via trip collaboration helpers):

- `public.trips`, `public.trip_collaborators`, `public.itinerary_items`
- `public.chat_sessions`, `public.chat_messages`, `public.chat_tool_calls`
- `public.saved_places`
- `public.file_attachments`
- `public.rag_documents` (readable by authenticated; managed by `service_role`)
- `memories.sessions`, `memories.turns`, `memories.turn_embeddings`

### Storage policies (attachments)

- `supabase/config.toml` defines the `attachments` bucket as private.
- Access to `storage.objects` is gated by `public.file_attachments` rows (“metadata is the authorization boundary”):
  - Users can read attachments for trips they can access.
  - Mutations are owner-only; identity fields (`bucket_name`, `file_path`, `user_id`) are guarded by the DB trigger.

Operational validation:

- See `docs/operations/runbooks/storage-owner-audit.md` for drift checks between `storage.objects` and `public.file_attachments`.
- See `docs/runbooks/supabase.md` (“Attachments: file_attachments invariants”) for local SQL verification and rollback steps.

### Webhooks (DB → app)

- Webhook payloads are verified (HMAC/QStash signing) before processing.
- Stripe webhooks are hardened per ADR-0070: signature verification with raw-body preservation, idempotency handling, rate limiting, and payment-event sensitivity.
- Webhook handler expectations and payload shapes are documented in `docs/api/internal/webhooks.md` and the runbooks under `docs/operations/runbooks/`.

## Output

Concrete findings and tasks will be tracked in `docs/tasks/INDEX.md` with P0/P1 labels.

- P0 (release blocker): security issue with credible exploit path or cross-tenant/PII impact; must be fixed (or feature removed) before release.
- P1 (post-release): security hardening or low-confidence risk; should be fixed soon after release with an explicit owner and follow-up date.
- Workflow: discovery → task created → remediation PR → verification (tests and/or Playwright) → close with evidence links.
- Ownership: release owner triages and assigns; code owners implement and attach verification output.
