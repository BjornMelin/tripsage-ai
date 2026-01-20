# T-011 — Supabase local `start` fails due to migration SQL syntax error

## Meta

- ID: `T-011`
- Priority: `P0`
- Status: `DONE`
- Owner: `codex-session-t008-gpt52`
- Depends on: `-`

## Problem

Local Supabase cannot start because a migration contains invalid SQL (nested dollar-quoting), causing `supabase start` to abort and tear down containers/volumes.

This blocks local auth flows (register/login) and prevents end-to-end verification of dashboard routes that require Supabase SSR auth.

## Evidence

Previously, running `pnpm supabase:bootstrap` failed with:

- `ERROR: syntax error at or near "DELETE" (SQLSTATE 42601)`
- The failure points into the consolidated migration `supabase/migrations/20260120000000_base_schema.sql` inside a `DO $$ ... $$;` block that calls `cron.schedule(..., $$DELETE ... $$)`.

## Acceptance Criteria (black-box)

- [ ] `pnpm supabase:bootstrap` completes successfully.
- [ ] `pnpm supabase:status` shows API/Auth/Studio/etc running (not just the DB).
- [ ] Next.js dashboard auth flows can be verified locally (`/register` → `/dashboard`).

## Likely Files

- `supabase/migrations/20260120000000_base_schema.sql` (fix nested quoting in the `cron.schedule` call)

## Verification (commands)

- `pnpm supabase:stop`
- `pnpm supabase:bootstrap`
- `pnpm supabase:status`

## Notes / Links (full URLs only)

- Supabase CLI local development: <https://supabase.com/docs/guides/cli/local-development>
