# T-008 — Implement “Plan New Trip” create flow (fix `/dashboard/trips/create` dead link)

## Meta

- ID: `T-008`
- Priority: `P1`
- Status: `DONE`
- Owner: `codex-session-t008-gpt52`
- Depends on: `T-002` (dashboard stability work may overlap)

## Problem

Multiple dashboard components link to `/dashboard/trips/create`, but that route is not present in the App Router inventory.

Evidence:

- `docs/release/_logs/nextjs-routes.json` includes `/dashboard/trips` and `/dashboard/trips/[id]` but NOT `/dashboard/trips/create`.
- Hard-coded link usage:
  - `src/components/features/dashboard/quick-actions.tsx` (action “Plan New Trip”)
  - `src/components/features/dashboard/trip-suggestions.tsx` (links into `/dashboard/trips/create?suggestion=...`)
  - Tests assert the link target is `/dashboard/trips/create` (`src/components/features/dashboard/__tests__/quick-actions.test.tsx`)

Impact:

- If a user is authenticated and clicks “Plan New Trip”, navigation likely results in a 404 or an unintended redirect, blocking a core product journey (create a trip).

## Acceptance Criteria (black-box)

- [x] An authenticated user can initiate “Plan New Trip” from the dashboard without hitting a 404.
- [x] The dashboard “Plan New Trip” CTA navigates to a valid destination and results in a visible trip creation UI (page or modal).
- [x] If the CTA uses query params (e.g., `suggestion=...`), the create UI consumes it and pre-fills relevant fields.

## Likely Files

- `src/components/features/dashboard/quick-actions.tsx`
- `src/components/features/dashboard/trip-suggestions.tsx`
- `src/components/features/dashboard/__tests__/quick-actions.test.tsx`
- New route file(s) expected (one of):
  - `src/app/dashboard/trips/create/page.tsx`
  - Or refactor CTA to use an existing route + modal/action within `src/app/dashboard/trips/page.tsx`
- Trip creation server action(s):
  - `src/app/dashboard/trips/create/actions.ts`
- Optional UI helper (if needed):
  - `src/app/dashboard/trips/create/trip-create-form.tsx`
- Trip creation validation/schema (if needed):
  - `src/domain/schemas/trips.ts`
- Auth verification blocker follow-up:
  - `docs/tasks/T-011-supabase-local-start-fails-migration.md`

## Implementation (summary)

- Added `src/app/dashboard/trips/create/page.tsx` to ensure `/dashboard/trips/create` is a real route and renders a trip-creation UI.
- The UI consumes `?suggestion=...`:
  - Always shows a visible “Using suggestion” indicator and the raw suggestion id.
  - Attempts to load suggestion details from `/api/trips/suggestions` and pre-fills destination/title/dates when found.
- Trip creation uses existing authenticated API flow via `useCreateTrip()` (`POST /api/trips`), then navigates to `/dashboard/trips/:id`.

## Tool Availability Check (recorded)

- Next DevTools MCP:
  - `next-devtools.init` ✅
  - `next-devtools.nextjs_index` ✅ (found server on port `3000`)
  - `nextjs_call:get_routes` ✅
  - `nextjs_call:get_errors` ✅
  - `nextjs_call:get_logs` ✅ (log path: `.next/dev/logs/next-development.log`)
  - `browser_eval` ✅ (chrome, headless)
- shadcn:
  - `get_project_registries` ✅ (`@shadcn`)
  - Examples referenced:
    - `card-with-form`
    - `form-rhf-demo`
- Supabase docs:
  - `supabase.search_docs` ✅ (SSR client + advanced SSR guide)

## Runtime Evidence (Next DevTools)

- Before: `nextjs_call:get_routes` did **not** include `/dashboard/trips/create`.
- After: `nextjs_call:get_routes` includes `/dashboard/trips/create`.
- `nextjs_call:get_errors`: “No errors detected in 1 browser session(s).”

## Verification (commands)

- ✅ `pnpm biome:fix`
- ✅ `pnpm type-check`
- ✅ `pnpm test:affected` (no affected tests found; exit 0)

## Playwright Verification Steps (next-devtools `browser_eval`)

Prereq: Use a seeded local Supabase project or a mocked auth/session approach for dev (documented by `T-005` / `T-004`).

1. Navigate to `http://localhost:3000/dashboard` while authenticated.
2. Snapshot; click “Plan New Trip”.
3. Assert the resulting URL is NOT a 404 and shows a visible create-trip heading/form.
4. Navigate back to dashboard; click a suggested trip link (if present) that targets `/dashboard/trips/create?suggestion=...`.
5. Assert the create UI reflects the selected suggestion (prefilled destination/dates or a visible “Using suggestion …” indicator).

### Browser eval evidence

- Navigated to `http://localhost:3000/dashboard` → redirected to `http://localhost:3000/login?next=%2Fdashboard` (unauthenticated redirect works).
- Screenshot: `/tmp/playwright-mcp-output/1767257452461/page-2026-01-01T08-51-04-143Z.png`

### Auth verification status

- **BLOCKED** (local Supabase cannot start due to migration error). Follow-up: `T-011`.
- Unblock steps (high-level):
  1. Fix the nested dollar-quoting in `supabase/migrations/20251122000000_base_schema.sql` (see `T-011`).
  2. Run `pnpm dlx supabase start --debug` and confirm `pnpm dlx supabase status` shows API/Auth running.
  3. Update `.env.local` with the local Supabase URL + anon key from `supabase status`.
  4. Start `pnpm dev`, register at `http://localhost:3000/register`, then re-run the `browser_eval` steps above while authenticated.

## Notes / Links (full URLs only)

- Next.js routing and route structure: https://nextjs.org/docs/app/getting-started/layouts-and-pages
- Next.js `useSearchParams`: https://nextjs.org/docs/app/api-reference/functions/use-search-params
- Next.js `useRouter`: https://nextjs.org/docs/app/api-reference/functions/use-router
- Supabase SSR client: https://supabase.com/docs/guides/auth/server-side/creating-a-client
- Supabase SSR advanced guide: https://supabase.com/docs/guides/auth/server-side/advanced-guide
- shadcn/ui Card docs: https://ui.shadcn.com/docs/components/card
- shadcn/ui Form docs: https://ui.shadcn.com/docs/components/form
