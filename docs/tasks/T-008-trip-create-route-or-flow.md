# T-008 — Implement “Plan New Trip” create flow (fix `/dashboard/trips/create` dead link)

## Meta

- ID: `T-008`
- Priority: `P1`
- Status: `UNCLAIMED`
- Owner: `@handle-or-session`
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

- [ ] An authenticated user can initiate “Plan New Trip” from the dashboard without hitting a 404.
- [ ] The dashboard “Plan New Trip” CTA navigates to a valid destination and results in a visible trip creation UI (page or modal).
- [ ] If the CTA uses query params (e.g., `suggestion=...`), the create UI consumes it and pre-fills relevant fields.

## Likely Files

- `src/components/features/dashboard/quick-actions.tsx`
- `src/components/features/dashboard/trip-suggestions.tsx`
- `src/components/features/dashboard/__tests__/quick-actions.test.tsx`
- New route file(s) expected (one of):
  - `src/app/dashboard/trips/create/page.tsx`
  - Or refactor CTA to use an existing route + modal/action within `src/app/dashboard/trips/page.tsx`
- Trip creation server action(s):
  - Likely under `src/app/dashboard/trips/*/actions.ts` or `src/lib/trips/actions.ts` (exact location depends on existing patterns)

## Verification (commands)

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`

## Playwright Verification Steps (next-devtools `browser_eval`)

Prereq: Use a seeded local Supabase project or a mocked auth/session approach for dev (documented by `T-005` / `T-004`).

1. Navigate to `http://localhost:3000/dashboard` while authenticated.
2. Snapshot; click “Plan New Trip”.
3. Assert the resulting URL is NOT a 404 and shows a visible create-trip heading/form.
4. Navigate back to dashboard; click a suggested trip link (if present) that targets `/dashboard/trips/create?suggestion=...`.
5. Assert the create UI reflects the selected suggestion (prefilled destination/dates or a visible “Using suggestion …” indicator).

## Notes / Links (full URLs only)

- Next.js routing and route structure: https://nextjs.org/docs/app/getting-started/layouts-and-pages
