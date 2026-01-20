# T-005 — Supabase RLS + Storage policy audit (least privilege)

## Meta

- ID: `T-005`
- Priority: `P1`
- Status: `DONE`
- Owner: `codex-session-rag-finalization`
- Depends on: `-`

## Problem

We must confirm Supabase database + storage policies enforce least privilege and match product intent for v1.0.0:

- Table RLS enabled where needed
- Policies restrict user-scoped data to `auth.uid()`
- Attachments bucket policy enforces per-user access
- Webhook secrets/HMAC verification aligns with configured routes

## Acceptance Criteria (black-box)

- [x] Written audit notes in `docs/release/05-security-and-privacy.md` covering:
  - which tables are user-scoped and how RLS enforces ownership
  - storage bucket visibility and access patterns
  - webhook signing/verification expectations
- [x] Any discovered policy gaps have dedicated P0/P1 task files.
  - Result: no P0/P1 gaps discovered in this pass; see the audit notes and the Storage owner/audit runbook below.

## Likely Files

- `supabase/migrations/*`
- `supabase/config.toml`
- `docs/operations/supabase-webhooks.md`
- `src/lib/supabase/server.ts` / related SSR helpers

## Verification (commands)

Prereqs: Docker-compatible container runtime + Supabase CLI (see `docs/runbooks/supabase.md`).

- `pnpm supabase:bootstrap`
- `pnpm supabase:reset:dev`
- `pnpm test:api` (route-level coverage)

## Playwright Verification Steps

1. Start app against local Supabase project
2. Create two users
3. Verify user A cannot read/modify user B resources (trips, chat sessions, attachments)

## Notes / Links (full URLs only)

- [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Supabase Storage policies](https://supabase.com/docs/guides/storage/security/access-control)

## Evidence

- Audit notes: `docs/release/05-security-and-privacy.md`
- Canonical schema: `supabase/migrations/20260120000000_base_schema.sql`
- Storage drift checks: `docs/operations/runbooks/storage-owner-audit.md`
- Local verification + rollback snippets: `docs/runbooks/supabase.md`
