# T-006 — Fix navbar “Sign up” 404 link

## Meta

- ID: `T-006`
- Priority: `P0`
- Status: `DONE`
- Owner: `release-orchestrator`
- Depends on: `-`

## Problem

On the marketing landing page (`http://localhost:3000/`), the top navbar “Sign up” link routes to `/signup`, which is not a valid App Router route (404).

Evidence:

- Route inventory does not contain `/signup` (see `docs/release/_logs/nextjs-routes.json`).
- Browser automation via Next DevTools `browser_eval` confirmed `http://localhost:3000/signup` returns 404.

## Acceptance Criteria (black-box)

- [ ] Visiting `http://localhost:3000/` shows a navbar “Sign up” link that navigates to `http://localhost:3000/register` (NOT `/signup`).
- [ ] `http://localhost:3000/signup` no longer appears as a navigation target anywhere in the marketing navbar.

## Likely Files

- `src/components/layouts/navbar.tsx`
- `src/lib/routes.ts` (if routes are centralized and should be used instead of hard-coded paths)

## Verification (commands)

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`

## Playwright Verification Steps (next-devtools `browser_eval`)

1. Navigate to `http://localhost:3000/`.
2. Snapshot the page and locate the navbar link named “Sign up”.
3. Assert its URL is `/register`.
4. Navigate to `http://localhost:3000/signup`.
5. Assert the page does NOT render a Next.js 404 (either redirects to `/register` or the route is removed from all entrypoints).

## Notes / Links (full URLs only)

- Next.js App Router routing basics: https://nextjs.org/docs/app/getting-started/layouts-and-pages
