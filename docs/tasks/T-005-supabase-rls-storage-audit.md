# T-005 — Supabase RLS + Storage policy audit (least privilege)

## Meta

- ID: `T-005`
- Priority: `P1`
- Status: `UNCLAIMED`
- Owner: `-`
- Depends on: `-`

## Problem

We must confirm Supabase database + storage policies enforce least privilege and match product intent for v1.0.0:

- Table RLS enabled where needed
- Policies restrict user-scoped data to `auth.uid()`
- Attachments bucket policy enforces per-user access
- Webhook secrets/HMAC verification aligns with configured routes

## Acceptance Criteria (black-box)

- [ ] Written audit notes in `docs/release/05-security-and-privacy.md` covering:
  - which tables are user-scoped and how RLS enforces ownership
  - storage bucket visibility and access patterns
  - webhook signing/verification expectations
- [ ] Any discovered policy gaps have dedicated P0/P1 task files.

## Likely Files

- `supabase/migrations/*`
- `supabase/config.toml`
- `docs/operations/supabase-webhooks.md`
- `src/lib/supabase/server.ts` / related SSR helpers

## Verification (commands)

Prereqs: Supabase CLI installed ([Supabase CLI docs](https://supabase.com/docs/guides/cli)).

- `cd supabase && supabase start`
- `cd supabase && supabase db reset --debug`
- `pnpm test:api` (route-level coverage)

## Playwright Verification Steps

1. Start app against local Supabase project
2. Create two users
3. Verify user A cannot read/modify user B resources (trips, chat sessions, attachments)

## Notes / Links (full URLs only)

- [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase Storage policies](https://supabase.com/docs/guides/storage/security/access-control)
