# T-009 — Fix `/reset-password` “Contact support” link (remove `/support` 404)

## Meta

- ID: `T-009`
- Priority: `P1`
- Status: `DONE`
- Owner: `release-orchestrator`
- Depends on: `-`

## Problem

`/reset-password` rendered “Contact support” links pointing to `/support`, but `/support` is not a valid route (404). This created a broken link in the unauthenticated recovery journey.

Evidence:

- Browser automation via Next DevTools `browser_eval` confirmed `http://localhost:3000/support` returned 404.
- Link sources:
  - `src/app/(auth)/reset-password/page.tsx`
  - `src/components/auth/reset-password-form.tsx` (computes `supportPath`)

## Acceptance Criteria (black-box)

- [x] `http://localhost:3000/reset-password` renders “Contact support” links that navigate to `http://localhost:3000/contact`.
- [x] No UI link points to `/support` in the password reset journey.

## Likely Files

- `src/app/(auth)/reset-password/page.tsx`
- `src/components/auth/reset-password-form.tsx`

## Verification (commands)

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`

## Playwright Verification Steps (next-devtools `browser_eval`)

1. Navigate to `http://localhost:3000/reset-password`.
2. Snapshot and locate the “Contact support” link(s).
3. Assert each resolves to `/contact`.
4. Navigate to `http://localhost:3000/support` and assert it is not linked from the reset-password page.

## Notes / Links (full URLs only)

- Next.js routing: https://nextjs.org/docs/app/getting-started/layouts-and-pages
