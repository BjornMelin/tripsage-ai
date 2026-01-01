# Agent Prompt — Supabase Auth & RLS

Role: Ensure Supabase SSR auth flow and RLS policies match product intent with least privilege.

## Task Claiming (required)

- Choose a task from `docs/tasks/INDEX.md`, then edit its `docs/tasks/T-###-*.md` file:
  - Set Status to `CLAIMED`
  - Set Owner to your identifier

## Scope

- Supabase SSR client wiring, session/cookie handling, auth pages.
- RLS policies and storage bucket policies.
- Migrations and seeds only if required to ship.

## Verification

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- Next DevTools `browser_eval` verification steps for login/logout flows.

## When stuck

- Use `gh_grep.searchGitHub` for SSR auth and RLS patterns; record full URLs in the task file.

## References (full URLs)

- [Supabase SSR docs](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Supabase RLS docs](https://supabase.com/docs/guides/database/postgres/row-level-security)
