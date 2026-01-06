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

## Environment variables (local)

After `pnpm supabase:start`, get local URLs/keys via:

- `pnpm supabase:status`

Populate `.env.local` with at least:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-only; never `NEXT_PUBLIC_*`)

## Type generation

Generate and update the committed DB types:

- `pnpm supabase:typegen`

This writes `src/lib/supabase/database.types.ts` from the local database (schemas: `auth`, `public`, `memories`, `storage`).

## Common workflow

1) Add/modify SQL in `supabase/migrations/*`
2) `pnpm supabase:db:reset`
3) `pnpm supabase:typegen`
4) Commit both the migration(s) and updated `src/lib/supabase/database.types.ts`
