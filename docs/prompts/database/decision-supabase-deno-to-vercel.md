# Supabase Deno to Vercel Migration Decision

Here's the full review, decision, and implementation plan based on a deep
code read, Zen analyses, and primary-doc research.

## Executive Decision

- **Recommendation**: Consolidate all **Deno**-based **Supabase Edge Functions**
  into **Vercel** (**Next.js 16**) Route Handlers + Background Functions, fed by
  **Supabase Database Webhooks**. Keep **Postgres** migrations and **RLS** in
  **Supabase**. **Remove Deno functions**.
- **Decision Framework Weighted Score**: **9.2/10**
  - **Solution Leverage** (35%): 9.4 → 3.29
  - **Application Value** (30%): 9.1 → 2.73
  - **Maintenance Load** (25%): 9.1 → 2.28
  - **Adaptability** (10%): 9.0 → 0.90
  - **Total**: **9.20**
- **Why**: One runtime (**Node/Edge**) on **Vercel** improves ops, logging, and
  developer velocity; all current tasks are HTTP + **Supabase JS** compatible;
  DB webhooks (**pg_net**) bridge triggers to **Vercel** reliably; **no features
  strictly require Deno**.

---

## What We Found

- **Deno Edge Functions** present and deployed via **Supabase CLI**:
  - `supabase/functions/trip-notifications/index.ts:1`
  - `supabase/functions/file-processing/index.ts:1`
  - `supabase/functions/cache-invalidation/index.ts:1`
  - `supabase/functions/generate-embeddings/index.ts:1`
  - `supabase/edge-functions/ai-processing/index.ts:1`
  - Shared client and env usage: `supabase/functions/_shared/supabase.ts:1`
  - Trigger scaffolding (currently `pg_notify`, not HTTP):
    `supabase/functions/setup_edge_function_triggers.sql:1`
- **Next.js SSR** + cookie integration is **correct and modern**:
  - `frontend/src/lib/supabase/server.ts:1`
  - `frontend/src/lib/supabase/client.ts:1`
  - `frontend/middleware.ts:7`

### Why Deno is used today

- **Supabase Edge Functions** run on **Deno**; historically simplest to invoke
  from DB triggers and keep service-role operations within **Supabase** infra.
- Current functions are HTTP-and-**Supabase JS** only (no native/binary add-ons),
  so not runtime-bound to **Deno**.

### Is Deno required here?

- **No**. All implemented functions can run as:
  - **Next.js Route Handlers** (**Node** runtime) for synchronous webhooks
  - **Vercel Background Functions** for longer jobs
  - DB triggers can call external HTTP via
    `supabase_functions.http_request` (**pg_net**).
- Colocation/latency benefit is **marginal** for these tasks and can be offset by
  region pinning and idempotent background processing.

---

## Code Review (Security/Quality)

### Confirmed strengths

- **SSR setup**: correct `@supabase/ssr` cookie adapters and middleware handling.
  `server.ts` and `middleware.ts` are aligned with official patterns.
- **Edge function code**: good CORS, token checks, webhook-secret checks, and
  error handling.

### High-priority issues

- `setup_edge_function_triggers.sql`: privileges and **SECURITY DEFINER** posture
  1) **Overbroad read access**
     - **Problem**: `GRANT SELECT ON webhook_logs TO authenticated`; exposes
       payloads of sensitive rows to all authenticated users.
     - **Fix**: Revoke SELECT for authenticated; add a narrow policy for an
       admin/service role only.
  2) **SECURITY DEFINER exposure**
     - **Problem**: `send_edge_function_webhook` is **SECURITY DEFINER** and
       granted to authenticated; enables forging payloads.
     - **Fix**: Revoke EXECUTE from authenticated; expose only to trusted
       backend role; or remove public invoke path.
  3) **Stable search_path**
     - **Problem**: **SECURITY DEFINER** without a pinned `search_path` risks
       function hijacking.
     - **Fix**: `ALTER FUNCTION ... SET search_path = pg_catalog, public`; and
       prefer fully-qualified calls to builtins.

### Medium-priority

- `generate-embeddings/index.ts`: Cold-start heavy xenova pipeline; prefer
  provider embeddings via **Gateway**/**OpenAI** on **Vercel**.
- Triggers use `pg_notify` comments rather than actual HTTP calls; ensure you
  migrate to **pg_net**/`supabase_functions.http_request` for production DB
  **Webhooks**.

### Low-priority

- Browser client fallback returns `{}` as **SupabaseClient**
  (`frontend/src/lib/supabase/client.ts:29`). Prefer explicit "disabled in SSR"
  path with clear logs.

### Top 3 fixes to apply immediately

- **Lock down SQL privileges** for `webhook_logs` and the **SECURITY DEFINER**
  function.
- **Replace pg_notify placeholders** with real **Database Webhooks** (**pg_net**)
  to hitting **Vercel** endpoints with **HMAC**.
- **Move embeddings to provider API**; remove heavy model load in the hot path.

---

## Deep Reasoning Summary

- The four function families (**notifications**, **file-processing**,
  **cache-invalidation**, **embeddings**) are **stateless**, rely on **HTTP APIs**
  (**Supabase JS**, **Upstash**, **Resend**, **OpenAI**), and **don't use
  Deno-only capabilities**.
- **Vercel** provides **Background Functions** (longer max duration), **Cron**,
  region pinning, unified logs, and tight integration with **Next.js Route
  Handlers**.
- **Supabase Database Webhooks** (**pg_net** + `supabase_functions.http_request`)
  are the **standard way** to push DB changes to external HTTP endpoints (your
  **Vercel APIs**). Add **idempotency** and **retries**; keep processing **async**
  when possible.
- **Latency** can be kept within **acceptable ranges** by pinning **Vercel**
  region near **Supabase** and using background jobs for heavier processing.
  Notifications, cache invalidation, and storage updates are **not
  user-facing blocking paths**.

---

## Consensus (Zen)

- The consensus run **favors migration to Vercel** with a weighted total **above
  9.0**. The pro-migration model produced a **9.14** weighted total; after
  cross-checking with docs and code, our final matrix is **9.20** with
  mitigations (region pinning, **HMAC**, **idempotency**, **retries**).

---

## Phased Migration Plan (Detailed)

### **Phase 0**: Pre-migration hardening (security and DB)

- **SQL security**
  - Revoke broad read: `webhook_logs` table
  - Restrict EXECUTE on `send_edge_function_webhook` to service role only
  - Pin `search_path` for **SECURITY DEFINER** functions
- **Replace pg_notify scaffolding** with **Database Webhooks**
  - Enable **pg_net** and `supabase_functions.http_request`
  - Create HTTP triggers to **Vercel** endpoints with **HMAC** header
- **Region selection**
  - Pin **Vercel** function regions to match your **Supabase** project region

### **Phase 1**: Build Vercel endpoints (parity with Deno)

- **Trip Notifications** → **Next.js route**: `api/hooks/trips/route.ts:1`
  - Validate **HMAC** signature
  - Resolve user info via **Supabase** service user (or least-privilege DB user)
  - Send email via **Resend**; send optional webhooks
  - **Idempotency**: use a unique constraint or **Redis** key on event id/time
- **File Processing** → **Next.js route**: `api/hooks/files/route.ts:1`
  - **Node** runtime only (**Storage** download/upload)
  - Virus scan stub preserved; plan external scanner integration (provider)
  - Image pipeline stub; future: outsource to an image worker or a queue
  - **Idempotency** and "uploading" → "completed/failed" state transitions
- **Cache Invalidation** → **Next.js route**: `api/hooks/cache/route.ts:1`
  - **Upstash Redis**: clear patterns/keys
  - DB cache tables cleanup (`search_*` tables)
  - Optional webhook notifications
- **Embeddings** → **Next.js route**: `api/embeddings/route.ts:1`
  - Replace xenova with provider embeddings via **Vercel AI SDK v6**
  - Optional upsert back into table

### **Phase 2**: Wire Supabase Database Webhooks to Vercel

- Create DB triggers with `supabase_functions.http_request`
  - **Per-table triggers**: `trips`, `flights`, `accommodations`, `search_*`tables,
    `trip_collaborators`, `chat_*`
  - Headers include: `Content-Type`, `X-Signature-HMAC`, `X-Event-Type`,
    `X-Table`
  - JSON body includes necessary row snapshot and metadata
- **Retry strategy**
  - Use **pg_net**/**backoff** on DB side
  - **Vercel**: respond 2xx only after acceptance; background offload when needed
- **Observability**
  - Structured logs (**JSON**) in **Vercel** functions
  - Dashboards for error rate, **P95 latency**, retry counts

### **Phase 3**: Dual-run and cutover

- **Dual-run** for **~1–2 weeks**: keep **Supabase Edge functions** deployed but
  direct DB webhooks to **Vercel**; compare outcomes and logs
- **Feature flags** to stop calling **Deno** endpoints from any client code
- Once **parity confirmed**: **remove Deno functions**

### **Phase 4**: Decommission Deno

- **Remove** `supabase/functions/*`and `supabase/edge-functions/*`
- **Drop Makefile steps** for functions deploy/logs and **Deno** lockfile workaround
- **Update docs and runbooks**; strip secrets no longer needed in **Supabase**
  function environment

### **Phase 5**: Post-migration improvements

- Add **Vercel Cron** for log cleanup and search cache pruning
- Consider queueing (**Upstash/QStash**, **Vercel Queues**) if workloads spike
- Expand automated tests for webhook handlers (**unit + integration**; mock
  **Supabase**/**Upstash**/**Resend**)

---

## Task Breakdown (Actionable)

### **Security/DB (critical)**

- **Revoke and restrict privileges** in
  `supabase/functions/setup_edge_function_triggers.sql:1`
  - **Remove** `GRANT SELECT` on `webhook_logs` to `authenticated`
  - **Restrict EXECUTE** for `send_edge_function_webhook` to service/admin
  - `ALTER FUNCTION ... SET search_path = pg_catalog, public`
- **Enable and configure Database Webhooks**
  - `CREATE EXTENSION IF NOT EXISTS pg_net`
  - Use `supabase_functions.http_request` in triggers

### **Vercel endpoints (server-only, dynamic)**

- `api/hooks/trips/route.ts:1`
  - `export const runtime = 'nodejs'`
  - `export const dynamic = 'force-dynamic'`
  - **Validate HMAC**; call **Supabase JS** with limited-privilege key; **Resend**
- `api/hooks/files/route.ts:1`
  - **Node** runtime; **Supabase Storage** read/write
  - Background offload for heavy ops if needed
- `api/hooks/cache/route.ts:1`
  - **Upstash Redis** via REST; DB cache cleanup
- `api/embeddings/route.ts:1`
  - Use **AI SDK v6** (`stream`/`generateObject`) and provider embeddings
  - Write embedding back (if provided id)

### **Ops/Config**

- `vercel.json`
  - `regions: ["iad1"]` (example, align with **Supabase** region)
  - `functions.maximumDuration` for background handlers
- **Env**
  - **Vercel Project env group** for: `SUPABASE_URL`,
    `SUPABASE_SERVICE_ROLE_KEY` (or scoped key), `NEXT_PUBLIC_SUPABASE_URL`,
    `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `RESEND_API_KEY`, **UPSTASH** tokens,
    `HMAC_SECRET`

### **Testing**

- **Unit tests** for each route handler
  - Validate signature, malformed payload, **idempotency**
- **Integration tests** with mocked **Supabase**/**Upstash**/**Resend**
- **Load test** background handler concurrency (files, cache)

### **Decommission**

- **Delete** `supabase/functions/*`and `supabase/edge-functions/*`
- **Remove Makefile** function deploy/log targets and **Deno** lock renames
- **Update docs**/TECH_DEBT.md closure

### **Rollback**

- **Keep Supabase Edge Functions** code in a tag for **30 days**
- **Toggle DB webhooks** back to **Supabase** endpoints if needed

---

## Supporting Evidence (Primary Docs)

- **Supabase SSR** (`createServerClient`/`cookies`/`middleware`)
  - <https://github.com/supabase/ssr/blob/main/docs/design.md>
- **Supabase Database Webhooks** + **pg_net** / `supabase_functions.http_request`
  - Database Webhooks overview:
    <https://supabase.com/docs/guides/database/webhooks>
  - pg_net extension:
    <https://supabase.com/docs/guides/database/extensions/pg_net>
- **Supabase Edge Functions** (**Deno**) examples, auth/webhooks
  - Auth hooks **Deno** function with **Resend**:
    <https://supabase.com/docs/guides/auth/auth-hooks/send-email-hook>
- **Next.js 16 Route Handlers** (App Router)
  - <https://nextjs.org/docs/app/building-your-application/routing/route-handlers>
- **Vercel Functions** (duration, background, region, cron)
  - Overview: <https://vercel.com/docs/functions>
  - Duration: <https://vercel.com/docs/functions/configuring-functions/duration>
  - Regions: <https://vercel.com/docs/functions/configuring-functions/region>
  - Cron: <https://vercel.com/docs/cron-jobs>
- **AI SDK v6** (for embeddings/streaming server routes)
  - `streamText`/`toUIMessageStreamResponse`:
    <https://ai-sdk.dev/docs/reference/ai-sdk-core/stream-text>
  - **Next.js App Router**:
    <https://ai-sdk.dev/docs/getting-started/nextjs-app-router>

---

## Answer to the Core Question

- **Why are we using Deno?** Because **Supabase Edge Functions** run on **Deno**
  and were a straightforward way to run server-side code close to the DB/storage
  with triggers. This made early integration simple but introduced a **second
  runtime/toolchain**.
- **Can/should we switch to "direct Supabase" without Deno?** **Yes**. In practice
  this means:
  - Keep **Supabase** for DB/Auth/Storage and invoke **Vercel** webhooks from DB
    triggers (**pg_net**)
  - Use **Supabase JS** from **Vercel Route Handlers**/**Background Functions**
    for operations once invoked
  - This **removes the need for Deno Edge Functions**
- **Is Deno still needed?** **Not for current features**. It's **optional**;
  choose to **retire it**.

**Would you like me to:**

- **Draft the exact SQL** for database webhooks (**pg_net** `http_request`
  invocations) and **HMAC** header usage?
- **Scaffold Next.js handlers** under `frontend/src/app/api/hooks/*` with signature
  checks and typed payloads?
- **Apply the SQL hardening changes** in
  `supabase/functions/setup_edge_function_triggers.sql` and include a short
  migration note?
