# Supabase runbook (local dev + type generation)

## Prerequisites

- Docker (required for `supabase start`)
- `pnpm` per repo `package.json`

## Local stack

- Start Supabase (Postgres/Auth/Storage):
  - `pnpm supabase:start`
- Stop Supabase:
  - `pnpm supabase:stop`
- Reset database (re-applies `supabase/migrations/*` + `supabase/seed.sql`):
  - `pnpm supabase:db:reset`
- One-shot bootstrap (start + reset + print status):
  - `pnpm supabase:bootstrap`

## Environment variables (local)

After `pnpm supabase:start`, get local URLs/keys via:

- `pnpm supabase:status`

Populate `.env.local` with at least:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-only; never `NEXT_PUBLIC_*`)

## Local auth email confirmations (Inbucket)

Supabase local is configured with Inbucket (`supabase/config.toml` `[inbucket]`):

- Inbox UI: `http://localhost:54324`
- When signing up locally, open the Inbucket inbox and click the confirmation link.
- Avoid “manual DB confirmation” hacks; they are easy to forget and don’t reflect production behavior.

## Type generation

Generate and update the committed DB types:

- `pnpm supabase:typegen`

This writes `src/lib/supabase/database.types.ts` from the local database (schemas: `auth`, `public`, `memories`, `storage`).

## Common workflow

1) Add/modify SQL in `supabase/migrations/*`
2) `pnpm supabase:db:reset`
3) `pnpm supabase:typegen`
4) Commit both the migration(s) and updated `src/lib/supabase/database.types.ts`

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
