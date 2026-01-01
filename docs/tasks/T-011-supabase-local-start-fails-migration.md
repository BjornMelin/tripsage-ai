# T-011 — Supabase local `start` fails due to migration SQL syntax error

## Meta

- ID: `T-011`
- Priority: `P0`
- Status: `UNCLAIMED`
- Owner: `@handle-or-session`
- Depends on: `-`

## Problem

Local Supabase cannot start because a migration contains invalid SQL (nested dollar-quoting), causing `supabase start` to abort and tear down containers/volumes.

This blocks local auth flows (register/login) and prevents end-to-end verification of dashboard routes that require Supabase SSR auth.

## Evidence

Running `pnpm dlx supabase start --debug` fails with:

- `ERROR: syntax error at or near "DELETE" (SQLSTATE 42601)`
- The failure points into `supabase/migrations/20251122000000_base_schema.sql` inside a `DO $$ ... $$;` block that calls `cron.schedule(..., $$DELETE ... $$)`.

## Acceptance Criteria (black-box)

- [ ] `pnpm dlx supabase start --debug` completes successfully.
- [ ] `pnpm dlx supabase status` shows API/Auth/Studio/etc running (not just the DB).
- [ ] Next.js dashboard auth flows can be verified locally (`/register` → `/dashboard`).

## Likely Files

- `supabase/migrations/20251122000000_base_schema.sql` (fix nested quoting in the `cron.schedule` call)

## Verification (commands)

- `pnpm dlx supabase stop --no-backup`
- `pnpm dlx supabase start --debug`
- `pnpm dlx supabase status`

## Notes / Links (full URLs only)

- Supabase CLI local development: https://supabase.com/docs/guides/cli/local-development

