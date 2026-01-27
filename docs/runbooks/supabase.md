# Supabase runbook (local dev + type generation)

## Prerequisites

- Docker (required for `supabase start`)
- `pnpm` per repo `package.json`
- Supabase CLI: this repo runs a pinned CLI via `pnpm dlx supabase@2.72.8` in `package.json` scripts (no global install required). If you choose to install the CLI locally, Supabase’s docs note `pnpm add supabase --save-dev --allow-build=supabase` may be required on pnpm v10+.

## Local stack

- Start Supabase (Postgres/Auth/Storage):
  - `pnpm supabase:start`
- Stop Supabase:
  - `pnpm supabase:stop`
- Reset database (re-applies the squashed migration `supabase/migrations/20260120000000_base_schema.sql`; skips `supabase/seed.sql` — use `pnpm supabase:seed:*`):
  - `pnpm supabase:db:reset`
- One-shot bootstrap (start + reset + print status):
  - `pnpm supabase:bootstrap`
- Reset + seed (deterministic sample data):
  - `pnpm supabase:reset:dev` (UI development dataset)
  - `pnpm supabase:reset:e2e` (Playwright/E2E dataset, for when you want to run E2E against a real local DB)
  - `pnpm supabase:reset:payments` (payments/Stripe dataset)
  - `pnpm supabase:reset:calendar` (calendar/OAuth dataset)
  - `pnpm supabase:reset:edge-cases` (validation/error-path dataset)

## Environment variables (local)

After `pnpm supabase:start`, get local URLs/keys via:

- `pnpm supabase:status`

Populate `.env.local` with at least:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (preferred) or `NEXT_PUBLIC_SUPABASE_ANON_KEY` (legacy)
- `SUPABASE_SERVICE_ROLE_KEY` (server-only; use the `sb_secret_…` key printed by `pnpm supabase:status`; never `NEXT_PUBLIC_*`)
- (Recommended) `SUPABASE_JWT_SECRET` (use `JWT_SECRET` from `pnpm supabase:status` for local non-test flows like MFA)

### WSL storage proxy workaround

If `/storage/v1/*` returns `500` from `http://127.0.0.1:54321`, use the storage proxy:

- `SUPABASE_STORAGE_URL=http://127.0.0.1:54331`
- Keep `NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321` for REST/Auth.
- Re-run `pnpm supabase:bootstrap`

## Seed data (dev + e2e)

TripSage keeps a deterministic seed script for local development and E2E testing:

- `pnpm supabase:seed:dev` — creates/updates a small “realistic” dataset (trips, itinerary, saved places, chat) for UI dev
- `pnpm supabase:seed:e2e` — creates/updates a minimal dataset with stable users for Playwright flows
- `pnpm supabase:seed:payments` — creates/updates a payments-focused dataset (Stripe/webhook fixtures + representative rows)
- `pnpm supabase:seed:calendar` — creates/updates a calendar-focused dataset
- `pnpm supabase:seed:edge-cases` — creates/updates an edge-case dataset (constraints, missing fields, partial states)

Notes:

- Seeding requires `SUPABASE_SERVICE_ROLE_KEY` because it uses `supabase.auth.admin.*` to create confirmed users.
- Seed data is designed to be **idempotent**: rerunning should converge to the same dataset without needing a full reset.
- Seed fixtures live in `scripts/seed/fixtures/` and are uploaded into Supabase Storage buckets (`avatars`, `attachments`) as part of seeding.
- RAG/memory embedding generation uses AI SDK v6:
  - If `AI_GATEWAY_API_KEY` or `OPENAI_API_KEY` is configured, real embeddings are generated (`openai/text-embedding-3-small`, 1536 dims).
  - If no embedding provider is configured, seeding falls back to a deterministic local embedding model for offline/dev/test. This preserves end-to-end flows but does **not** provide real semantic relevance.
- RAG reranking uses Together.ai via AI SDK v6 `rerank()` when `TOGETHER_AI_API_KEY` is set; otherwise reranking degrades to a no-op reranker.

## Local auth email confirmations (Inbucket / Mailpit)

Supabase local is configured with Inbucket (`supabase/config.toml` `[inbucket]`).
In newer Supabase CLI versions, `pnpm supabase:status` may label this service as **Mailpit**.

- Inbox UI: `http://localhost:54324`
- When signing up locally, open the Inbucket inbox and click the confirmation link.
- Avoid “manual DB confirmation” hacks; they are easy to forget and don’t reflect production behavior.

## Type generation

Generate and update the committed DB types:

- `pnpm supabase:typegen`

This writes `src/lib/supabase/database.types.ts` from the local database (schemas: `auth`, `public`, `memories`, `storage`).

## Common workflow

1) Add/modify SQL in `supabase/migrations/20260120000000_base_schema.sql` (historical split migrations are archived under `supabase/migrations/archive/`)
2) `pnpm supabase:db:reset`
3) `pnpm supabase:typegen`
4) Commit both the migration(s) and updated `src/lib/supabase/database.types.ts`

## Supabase CLI upgrades (local)

Supabase recommends stopping local containers and deleting data volumes before upgrading the CLI to ensure managed services apply internal migrations on a clean state. For this repo, `pnpm supabase:bootstrap` starts from a clean slate by calling `supabase stop --no-backup` before bringing the stack up again.

## Playwright E2E note

The default Playwright setup (`pnpm test:e2e:*`) starts its dev server and uses a mock Supabase Auth HTTP server (`scripts/e2e-webserver.mjs`) on `http://127.0.0.1:54329`. It does **not** require local Supabase.

Use local Supabase when you specifically want to validate real DB/RLS behavior and the full ingestion + RAG pipelines end-to-end.

## RAG smoke test (manual, full local stack)

This is the quickest way to validate end-to-end RAG retrieval against the local database:

1) `pnpm supabase:reset:dev`
2) `pnpm dev`
3) Sign in with the seeded user:
   - `dev.owner@example.local` / `dev-password-change-me`
4) Go to `/chat` and ask:
   - “Search my `user_content` documents for `seeded` and summarize what you find.”

Expected: the assistant triggers a `ragSearch` tool call and returns snippets from seeded `user_content` fixtures.

Notes:

- This validates the whole stack: `rag_documents` rows exist, embeddings are generated, `hybrid_rag_search` RPC returns results, and the agent tool wiring works.
- Meaningful semantic relevance locally requires `AI_GATEWAY_API_KEY` or `OPENAI_API_KEY`; deterministic embeddings are for offline/dev/CI and are not semantically meaningful.

## RLS hardening checks (recommended before deploying migrations)

### Attachments: file_attachments invariants

Detect potentially dangerous metadata rows (paths that do not start with their owner id):

```sql
select
  id,
  user_id,
  file_path
from public.file_attachments
where
  split_part(file_path, '/', 1) <> user_id::text
  and not (
    split_part(file_path, '/', 1) = 'chat'
    and split_part(file_path, '/', 2) = user_id::text
  );
```

Sanity-check the oldest / most common prefixes in `file_path`:

```sql
select
  split_part(file_path, '/', 1) as prefix,
  count(*)::bigint as rows
from public.file_attachments
group by 1
order by rows desc
limit 20;
```

### RAG: rag_documents scoping

Find legacy user_content rows that are missing `user_id`:

```sql
select
  count(*)::bigint as rows
from public.rag_documents
where namespace = 'user_content' and user_id is null;
```

### RAG: validate trip/user invariant

This PR adds the constraint `rag_documents_trip_requires_user_check` as `NOT VALID` to avoid blocking deployments if legacy data violates it. You should backfill/clean legacy rows and then validate the constraint.

Find violating rows (trip-scoped docs with missing `user_id`):

```sql
select
  id,
  trip_id,
  chat_id,
  namespace
from public.rag_documents
where trip_id is not null and user_id is null
order by created_at desc
limit 50;
```

Batch backfill example (repeat until 0 rows remain). This uses `chat_id` ownership when present, otherwise falls back to the trip owner:

```sql
-- Safe to rerun until 0 rows are affected.
with batch as (
  select
    d.id,
    coalesce(cs.user_id, t.user_id) as new_user_id
  from public.rag_documents d
  left join public.chat_sessions cs on cs.id = d.chat_id
  left join public.trips t on t.id = d.trip_id
  where d.trip_id is not null and d.user_id is null
  limit 1000
)
update public.rag_documents d
set user_id = batch.new_user_id
from batch
where d.id = batch.id and batch.new_user_id is not null;
```

Validate the constraint (run off-peak; `VALIDATE CONSTRAINT` takes a `SHARE UPDATE EXCLUSIVE` lock that does not block `SELECT`/`INSERT`/`UPDATE`/`DELETE`, but does block other `ALTER TABLE` operations):

```sql
alter table public.rag_documents
validate constraint rag_documents_trip_requires_user_check;
```

### Rollback (DDL)

If you need to revert the DB-level invariants added in this PR:

```sql
drop trigger if exists file_attachments_prevent_identity_change on public.file_attachments;
drop function if exists public.prevent_file_attachments_identity_change();
```

## Deployment checklist (prod/staging)

Recommended rollout order for the RLS/trigger hardening migrations:

1) Deploy DB migrations (RLS policies + trigger) to staging.
   - Verify the SQL Editor session user in staging (used by the attachment trigger bypass):
     - `select session_user, current_user;`
2) Run the validation queries above; expect:
   - `file_attachments` prefix mismatch query returns 0 rows (or only known legacy rows you accept).
   - `rag_documents` user_content NULL user_id count is understood (ideally 0).
3) Exercise the affected API routes in staging:
   - `/api/chat/attachments` upload + list (`/api/attachments/files`)
   - `/api/rag/index` and `/api/rag/search`
4) Monitor for trigger rejections in application logs / PostgREST logs:
   - Errors containing `file_path cannot be modified`, `user_id cannot be modified`, `bucket_name cannot be modified`
5) Promote to production and repeat steps (2) and (4).

### Suggested alerting thresholds

- Staging: alert on any trigger rejection (should be 0).
- Production: alert if trigger rejections > 5/min for 5 minutes, or if attachment uploads start failing across multiple users.

### Local verification (psql)

If you want to prove the trigger blocks identity mutations under the `authenticated` role:

```sql
-- As a superuser (local dev), simulate a PostgREST request by setting JWT claims:
begin;
set local role authenticated;
select set_config('request.jwt.claim.role', 'authenticated', true);
select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000001', true);

-- Insert a test metadata row (adjust required columns if schema changes)
insert into public.file_attachments (id, user_id, bucket_name, file_path, file_size, filename, mime_type, original_filename, upload_status)
values (
  gen_random_uuid(),
  '00000000-0000-4000-8000-000000000001',
  'attachments',
  '00000000-0000-4000-8000-000000000001/test/path.txt',
  1,
  'test',
  'text/plain',
  'path.txt',
  'uploading'
)
returning id;

-- Attempt to mutate file_path (should error)
update public.file_attachments
set file_path = '00000000-0000-4000-8000-000000000001/evil.txt'
where user_id = '00000000-0000-4000-8000-000000000001';

rollback;
```

### Upload metadata authorization window

The attachments upload is authorized by the corresponding `public.file_attachments` row.
Only rows with `upload_status = 'uploading'` created within the last 15 minutes authorize an upload
(`created_at > now() - interval '15 minutes'`). Stale `uploading` rows older than 15 minutes may
still exist in the database (especially in local dev) but will no longer authorize uploads; cleanup
is handled out-of-band (this runbook does not require `pg_cron`).

### Service role key rotation

- Treat `SUPABASE_SERVICE_ROLE_KEY` as a production secret; keep it server-only.
- If compromise is suspected, rotate the key in Supabase and redeploy server environments immediately.
