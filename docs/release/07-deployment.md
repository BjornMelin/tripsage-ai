# TripSage AI — Deployment (v1.0.0)

This runbook is the source of truth for deploying the Next.js 16 app to Vercel (primary) and for self-host smoke checks.

## 1) Deployment target + strategy decision

### Target

- **Primary platform:** Vercel (Next.js App Router, Node.js runtime)
- **Data/Auth/Storage:** Supabase
- **Rate limiting / idempotency / cache:** Upstash Redis (HTTP/REST) via `@upstash/redis`
- **Async jobs (optional):** Upstash QStash via `@upstash/qstash`

### Git deployments (decision for v1.0.0)

**Decision: enable Git deployments.**

Rationale:
- “Push to main → deploy” is the default Vercel workflow and makes the deploy path one-click obvious.
- Preview deployments remain available for PR validation; if cost control becomes a concern on free tiers, disable them via `git.deploymentEnabled` patterns (see Vercel docs).

Reference: https://vercel.com/docs/project-configuration/git-configuration

## 2) Vercel configuration decisions (what we rely on)

### `vercel.json`

- `git.deploymentEnabled`: enabled (Git deployments on) — see https://vercel.com/docs/project-configuration/git-configuration
- `functions.src/app/api/**/route.*.maxDuration = 60`: sets a uniform upper bound for Route Handlers. Some routes may also export a smaller `maxDuration` (e.g. demo streaming routes).

### Next.js build output (`output: "standalone"`)

This repo sets `output: "standalone"` in `next.config.ts` to produce a minimal `.next/standalone/server.js` bundle for self-hosting scenarios. On Vercel, use the Next.js framework preset (no custom outputDirectory needed).

Reference: https://nextjs.org/docs/app/api-reference/config/next-config-js/output

### Environment variables: build-time vs runtime (Next.js)

- Variables prefixed with `NEXT_PUBLIC_` are inlined into the client bundle at **build time** and will not change until you rebuild. Set these correctly for each Vercel environment before deploying.
- Non-`NEXT_PUBLIC_` variables are server-only.

Reference: https://nextjs.org/docs/app/guides/environment-variables

## 3) Environment variable matrix (production)

Source-of-truth reconciliation:
- Templates: `.env.example`, `.env.test.example`
- Validation: `src/domain/schemas/env.ts`, `src/lib/env/server.ts`, `src/lib/env/client.ts`
- Runtime injection differences: `playwright.config.ts` (E2E webServer injects placeholder Supabase env for local test boot)
- Repo-wide scan: `rg` on `process.env.*`, `getServerEnv*`, `getClientEnv*`, `NEXT_PUBLIC_*`, `SUPABASE`, `UPSTASH`, `QSTASH`, `AI_GATEWAY`, `STRIPE`, `RESEND`, `BOTID`

Table columns:
- **Required (prod)** means “needed for a functional production deploy” (not just “process boots”).

| ENV VAR | Required (prod) | Used by (feature/routes) | Where validated | Notes |
|---|---:|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Auth + DB access across app; required at server start | `src/domain/schemas/env.ts` (`envSchema`, `clientEnvSchema`) | Must be a valid URL. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Yes (preferred) | Supabase public key (client + SSR) | `src/lib/env/server.ts`, `src/lib/env/client.ts` | Preferred Supabase key name; mapped into `NEXT_PUBLIC_SUPABASE_ANON_KEY` internally. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes (legacy) | Supabase public key (client + SSR) | `src/domain/schemas/env.ts` (`envSchema`, `clientEnvSchema`) | If `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` is set, this can be unset. |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes (ops) | Admin-only Supabase client for server routes (webhooks, embedding persistence, admin RPCs) | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/supabase/admin.ts` | Keep server-side only. Required for webhook handlers that call admin client. |
| `SUPABASE_JWT_SECRET` | Yes | Required by production env validation; also used as fallback secret for MFA backup-code hashing if `MFA_BACKUP_CODE_PEPPER` is unset | `src/domain/schemas/env.ts` + `src/lib/security/mfa.ts` | Must be non-empty and ≥32 chars in production. |
| `MFA_BACKUP_CODE_PEPPER` | Recommended | MFA backup codes hashing | `src/domain/schemas/env.ts` + `src/lib/security/mfa.ts` | If unset, falls back to `SUPABASE_JWT_SECRET` (rotating JWT secret would invalidate backup codes). |
| `TELEMETRY_HASH_SECRET` | Yes | Production env validation; hashed identifiers in telemetry | `src/domain/schemas/env.ts` | Must be non-empty and ≥32 chars in production. |
| `NEXT_PUBLIC_SITE_URL` | Yes | Absolute URL building (server origin), QStash job enqueue URL construction | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/qstash/client.ts`, `src/lib/url/server-origin.ts` | Set to `https://<your-domain>` in production. |
| `APP_BASE_URL` | Recommended | Absolute URL building (server origin) | `src/domain/schemas/env.ts` (optional) | Alternative to `NEXT_PUBLIC_SITE_URL` for server-origin config. |
| `NEXT_PUBLIC_APP_URL` | Recommended | Auth redirect/origin helpers in several flows | Not in `envSchema`; used in `src/lib/activities/booking.ts`, `src/app/auth/password/reset-request/route.ts`, and UI | Keep aligned with the deployed site URL. |
| `UPSTASH_REDIS_REST_URL` | Yes | Rate limiting (most API routes), webhook idempotency, caching | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/redis.ts` | Without Redis, many routes configured as `fail_closed` will return `503`. |
| `UPSTASH_REDIS_REST_TOKEN` | Yes | Rate limiting (most API routes), webhook idempotency, caching | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/redis.ts` | Use Upstash REST token (keep server-side only). |
| `IDEMPOTENCY_FAIL_OPEN` | Recommended | Idempotency policy default for non-critical paths | `src/lib/env/server-flags.ts` | Default is `true` (fail-open). Webhook/job handlers still fail-closed explicitly. |
| `QSTASH_TOKEN` | Recommended | Durable async job enqueue (collaborator notifications, memory sync enqueue) | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/qstash/client.ts` | If unset, jobs fall back to in-process `after()` behavior where implemented. |
| `QSTASH_CURRENT_SIGNING_KEY` | Required if QStash enabled | Verify QStash job requests (`/api/jobs/*`) | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/qstash/receiver.ts` | Must be ≥32 chars. Required when accepting QStash deliveries. |
| `QSTASH_NEXT_SIGNING_KEY` | Recommended | Key rotation support for QStash | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/qstash/receiver.ts` | If unset, receiver falls back to current key and emits an alert. |
| `HMAC_SECRET` | Required if Supabase→Vercel webhooks enabled | Verifies `x-signature-hmac` for `/api/hooks/*` | `src/domain/schemas/env.ts` (optional) + runtime usage in `src/lib/webhooks/payload.ts` | Shared secret with Supabase DB triggers/webhooks. |
| `COLLAB_WEBHOOK_URL` | Optional | Optional downstream collaborator webhook forwarding | `src/domain/schemas/env.ts` | Must be a valid URL if set. |
| `RESEND_API_KEY` | Optional | Outbound email (collaborator notifications) | `src/domain/schemas/env.ts` | Must start with `re_` if set. |
| `RESEND_FROM_EMAIL` | Optional | Outbound email | `src/domain/schemas/env.ts` | Use a verified sender in Resend. |
| `RESEND_FROM_NAME` | Optional | Outbound email | `src/domain/schemas/env.ts` | Defaults to UI copy if unset. |
| `AI_GATEWAY_API_KEY` | Optional | Vercel AI Gateway fallback provider | `src/domain/schemas/env.ts` + Vercel docs | See https://vercel.com/docs/ai-gateway/authentication |
| `AI_GATEWAY_URL` | Optional | Override gateway base URL | `src/domain/schemas/env.ts` | Defaults to `https://ai-gateway.vercel.sh/v1` when needed. |
| `OPENAI_API_KEY` | Optional | Server-side OpenAI fallback provider | `src/domain/schemas/env.ts` | Must start with `sk-` if set. |
| `OPENROUTER_API_KEY` | Optional | Server-side OpenRouter fallback provider | `src/domain/schemas/env.ts` | Used when BYOK is missing and fallback is enabled. |
| `ANTHROPIC_API_KEY` | Optional | Server-side Anthropic fallback provider | `src/domain/schemas/env.ts` | Must start with `sk-ant-` if set. |
| `XAI_API_KEY` | Optional | Server-side xAI fallback provider | `src/domain/schemas/env.ts` | Optional fallback provider. |
| `EMBEDDINGS_API_KEY` | Optional (enables endpoint) | Enables `/api/embeddings` internal-key auth | `src/domain/schemas/env.ts` + runtime usage in `src/app/api/embeddings/route.ts` | If unset, `/api/embeddings` returns `503 embeddings_disabled`. |
| `FIRECRAWL_API_KEY` | Optional | Web crawl/search tools for agents | `src/domain/schemas/env.ts` | Required only if enabling web-crawl/search tools. |
| `FIRECRAWL_BASE_URL` | Optional | Web crawl/search tools | `src/domain/schemas/env.ts` | Defaults to `https://api.firecrawl.dev/v2` in templates. |
| `GOOGLE_MAPS_SERVER_API_KEY` | Optional (feature) | Places/Geocode/Routes/Time Zone server routes | `src/domain/schemas/env.ts` + `src/lib/env/server.ts` | Required for map-backed endpoints; restrict by IP + APIs. |
| `NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY` | Optional (feature) | Maps JS / Places in browser | `src/domain/schemas/env.ts` + `src/lib/env/client.ts` | Restrict by HTTP referrer. |
| `OPENWEATHERMAP_API_KEY` | Optional (feature) | Weather endpoints | `src/domain/schemas/env.ts` | Required only if weather features enabled. |
| `STRIPE_SECRET_KEY` | Optional (feature) | Payments | `src/domain/schemas/env.ts` | Must start with `sk_test_` or `sk_live_` if set. |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Optional (feature) | Payments (client) | `src/domain/schemas/env.ts` | Must start with `pk_test_` or `pk_live_` if set. |
| `AMADEUS_CLIENT_ID` | Optional (feature) | Flight search provider | `src/domain/schemas/env.ts` | Required only if Amadeus features enabled. |
| `AMADEUS_CLIENT_SECRET` | Optional (feature) | Flight search provider | `src/domain/schemas/env.ts` | Required only if Amadeus features enabled. |
| `AMADEUS_ENV` | Optional | Provider environment selection | `src/domain/schemas/env.ts` | `test` or `production`. |
| `DUFFEL_ACCESS_TOKEN` | Optional (feature) | Flight search provider | `src/domain/schemas/env.ts` | Optional alternative provider. |
| `DUFFEL_API_KEY` | Optional (feature) | Flight search provider | `src/domain/schemas/env.ts` | Optional alternative provider. |
| `ENABLE_AI_DEMO` | Optional | Enables `/ai-demo` + `/api/ai/stream` demo behavior | `src/domain/schemas/env.ts` + runtime usage in `src/app/api/ai/stream/route.ts` | Defaults to `false`. |
| `TELEMETRY_AI_DEMO_KEY` | Optional | Auth for `/api/telemetry/ai-demo` | `src/domain/schemas/env.ts` | If enabling AI demo telemetry routes, set ≥32 chars. |
| `BOTID_ENABLE` | Optional | Enables Vercel BotID protection for selected routes in `production,preview` by default | `src/lib/env/server-flags.ts`, `src/config/bot-protection.ts` | See https://vercel.com/docs/botid/get-started. To disable in prod, set `BOTID_ENABLE=development,test` (or any CSV excluding `production`). |
| `TRUST_PROXY` | Optional | Trusted proxy behavior for IP parsing (server) | `src/lib/env/server-flags.ts` | Set if running behind a proxy that sets standard IP headers. |
| `NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT` | Optional | Client OTLP export endpoint | `src/lib/env/client.ts` | Client-side only; must be a URL if set. |
| `NEXT_PUBLIC_API_URL` | Optional | Client API base URL | `src/domain/schemas/env.ts` | Defaults to same-origin behavior if unset (depending on feature). |
| `NEXT_PUBLIC_APP_NAME` | Optional | UI branding | `src/domain/schemas/env.ts` | Defaults to `TripSage`. |
| `NEXT_PUBLIC_BASE_PATH` | Optional | Hosting under a sub-path | `src/domain/schemas/env.ts` | If set, ensure Next config + routes align. |
| `NEXT_PUBLIC_BASE_URL` | Optional (legacy) | Fallback origin handling | Not in `envSchema`; used in `src/lib/url/*-origin.ts` | Prefer `NEXT_PUBLIC_SITE_URL` / `APP_BASE_URL`. |
| `NEXT_PUBLIC_FALLBACK_HOTEL_IMAGE` | Optional | UI fallback asset | `src/domain/schemas/env.ts` | Optional. |
| `NEXT_PUBLIC_TELEMETRY_SILENT` | Optional | Client-side telemetry silence | `src/lib/telemetry/constants.ts` | `1` disables console noise for perf tests. |
| `TELEMETRY_SILENT` | Optional | Server telemetry silence | `src/lib/env/server-flags.ts` | `1` disables some operational alert noise. |
| `ANALYZE` | Optional | Build analyzer flag | `src/domain/schemas/env.ts` | Boolean (`true`/`false`, `1`/`0`). |
| `DEBUG` | Optional | Debug behavior | `src/domain/schemas/env.ts` | Boolean (`true`/`false`, `1`/`0`). |
| `PORT` | Optional | Self-host port for standalone server | `src/domain/schemas/env.ts` + Next.js output docs | `PORT=3000` is default. |
| `HOSTNAME` | Optional | Self-host bind host for standalone server | `src/domain/schemas/env.ts` + Next.js output docs | Use `0.0.0.0` for container binding. |
| `PGVECTOR_HNSW_M` | Optional (DB) | pgvector index tuning | `supabase/migrations/20251122000000_base_schema.sql` (uses `current_setting`) | This is a Postgres setting (GUC), not a Vercel env var. Defaults exist. |
| `PGVECTOR_HNSW_EF_CONSTRUCTION` | Optional (DB) | pgvector index tuning | `supabase/migrations/20251122000000_base_schema.sql` | Postgres setting (GUC). |
| `PGVECTOR_HNSW_EF_SEARCH_DEFAULT` | Optional (DB) | pgvector search tuning | `supabase/migrations/20251122000000_base_schema.sql` | Postgres setting (GUC). |
| `MEMORIES_RETENTION_DAYS` | Optional (DB) | Memory retention (cron/cleanup) | `supabase/migrations/20251122000000_base_schema.sql` | Postgres setting (GUC). |

Notes on template-only / currently-unused entries:
- `.env.example` includes `GOOGLE_MAPS_API_KEY`, `BACKEND_API_URL`, and `EPS_*` variables; they are not referenced in `src/**` (as of v1.0.0). Keep them unset unless/until the codebase re-introduces those integrations.

## 4) Supabase setup (minimum viable)

### 4.1 Create project + keys

- Create a Supabase project and collect:
  - Project URL
  - Publishable key (`sb_publishable_...`) **preferred** (or legacy anon key)
  - Service role key (server-only)

References:
- SSR client setup (Next.js): https://supabase.com/docs/guides/auth/server-side/creating-a-client
- API keys overview: https://supabase.com/docs/guides/api/api-keys

### 4.2 Auth redirect URLs (Vercel)

Configure allowed redirect URLs in Supabase Auth (URL Configuration), including:
- Production site URL: `https://<your-domain>/**`
- Local dev: `http://localhost:3000/**`
- Vercel Preview wildcard (team slug placeholder): `https://*-<team-or-account-slug>.vercel.app/**`

Reference: https://supabase.com/docs/guides/auth/redirect-urls

### 4.3 Apply database migrations (required)

This repo’s DB schema and policies live in `supabase/migrations/` and must be applied before production traffic.

Recommended (repo-provided Make targets):

```bash
make supa.link PROJECT_REF=<your-project-ref>
make supa.db.push
```

Alternative (Supabase CLI):

```bash
supabase link --project-ref <your-project-ref>
supabase db push
```

### 4.4 Storage buckets + policies

`supabase/migrations/20251122000000_base_schema.sql` creates storage buckets and RLS policies (including `attachments`, `avatars`, `trip-images`).

Routes that depend on Storage:
- `POST /api/chat/attachments` uploads to bucket `attachments`
- `GET /api/attachments/files` lists + signs URLs from bucket `attachments`

Reference (Storage access control concepts): https://supabase.com/docs/guides/storage/security/access-control

### 4.5 Database → Vercel webhooks (as applicable)

This app includes webhook handlers:
- `POST /api/hooks/cache`
- `POST /api/hooks/files`
- `POST /api/hooks/trips`

They enforce:
- Rate limiting + idempotency via Upstash Redis
- HMAC verification via `HMAC_SECRET` using `x-signature-hmac`

Minimum setup:
1. Set `HMAC_SECRET` in Vercel (prod + preview if using webhooks in preview).
2. Configure Supabase to emit HTTP requests to the Vercel endpoints when relevant tables change.
   - The SQL trigger-based approach described in `docs/specs/active/0021-spec-supabase-webhooks-vercel-consolidation.md` matches the expected payload/headers.
   - If you use `pg_net`, Supabase provides a debugging guide: https://supabase.com/docs/guides/troubleshooting/webhook-debugging-guide

## 5) Upstash setup (minimum viable)

### 5.1 Redis (required for production)

TripSage uses Upstash Redis (REST) for:
- Rate limiting (many API routes default to fail-closed if Redis is unavailable)
- Webhook/job idempotency keys
- Small JSON caches

Set these in Vercel (prod + preview):
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

References:
- Upstash Redis client: https://upstash.com/docs/redis/howto/connectwithupstashredis
- Vercel env vars: https://vercel.com/docs/projects/environment-variables

### 5.2 QStash (optional but recommended)

If you want durable retries for background notifications/jobs, set:
- `QSTASH_TOKEN` (publish)
- `QSTASH_CURRENT_SIGNING_KEY`, `QSTASH_NEXT_SIGNING_KEY` (verify deliveries)

References:
- Signature verification: https://upstash.com/docs/qstash/howto/signature
- Signing key rotation: https://upstash.com/docs/qstash/howto/roll-signing-keys

## 6) Build + start verification (required evidence for releases)

### 6.1 Local build

```bash
pnpm build
```

### 6.2 Local start (standalone)

`pnpm start` runs `.next/standalone/server.js` and does **not** inherit `.env.local` automatically in all setups. Ensure required production env vars are present in the shell.

Minimum to boot for local `pnpm start` (examples only; do not use real secrets):

```bash
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co \
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_<...> \
SUPABASE_JWT_SECRET=<32+ chars> \
TELEMETRY_HASH_SECRET=<32+ chars> \
pnpm start
```

Reference: https://nextjs.org/docs/app/api-reference/config/next-config-js/output

## 7) Browser validation steps (deterministic)

After deploy (or local `pnpm dev`), verify:

1. `GET /` renders (no 500s)
2. `GET /login` renders
3. `GET /register` renders
4. Confirm API routes return expected auth errors (401/403) rather than 500/503 when unauthenticated

## References (full URLs)

- Next.js deploying: https://nextjs.org/docs/app/building-your-application/deploying
- Next.js env vars: https://nextjs.org/docs/app/guides/environment-variables
- Next.js output (standalone): https://nextjs.org/docs/app/api-reference/config/next-config-js/output
- Vercel env vars: https://vercel.com/docs/projects/environment-variables
- Vercel git config: https://vercel.com/docs/project-configuration/git-configuration
- Vercel Next.js: https://vercel.com/docs/frameworks/nextjs
- Vercel AI Gateway auth: https://vercel.com/docs/ai-gateway/authentication
- Vercel BotID: https://vercel.com/docs/botid/get-started
- Supabase SSR client: https://supabase.com/docs/guides/auth/server-side/creating-a-client
- Supabase auth redirect URLs: https://supabase.com/docs/guides/auth/redirect-urls
- Supabase API keys: https://supabase.com/docs/guides/api/api-keys
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Storage access control: https://supabase.com/docs/guides/storage/security/access-control
- Supabase pg_net webhook debugging: https://supabase.com/docs/guides/troubleshooting/webhook-debugging-guide
- Upstash Redis connect: https://upstash.com/docs/redis/howto/connectwithupstashredis
- Upstash QStash signature verification: https://upstash.com/docs/qstash/howto/signature
- Upstash QStash key rotation: https://upstash.com/docs/qstash/howto/roll-signing-keys
