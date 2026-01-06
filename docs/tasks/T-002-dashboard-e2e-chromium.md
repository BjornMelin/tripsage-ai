# T-002 — Fix Chromium E2E failures (dashboard load + theme toggle banner)

## Meta

- ID: `T-002`
- Priority: `P0`
- Status: `DONE`
- Owner: `codex-session-t002-a`
- Depends on: `T-001`

## Problem

Chromium E2E failures in `e2e/dashboard-functionality.spec.ts`:

1. `dashboard page renders correctly after authentication` times out on `page.goto("/dashboard")` waiting for `"load"` even though the dashboard content is visible in the snapshot.
2. `theme toggle works` times out locating the theme toggle within `getByRole("banner")`, implying the header is not exposing a `banner` landmark (semantic `<header>` or `role="banner"`).

## Acceptance Criteria (black-box)

- [x] `pnpm exec playwright test --project=chromium e2e/dashboard-functionality.spec.ts` passes.
- [x] Theme toggle is discoverable via accessibility semantics (banner landmark preferred) and the theme menu items are reachable.

## Likely Files

- `e2e/dashboard-functionality.spec.ts`
- Header/nav components under `src/components/layouts/**` (where the theme toggle + user menu render)

## Verification (commands)

- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- `pnpm exec playwright test --project=chromium e2e/dashboard-functionality.spec.ts`

## Playwright Verification Steps

1. Run: `pnpm exec playwright test --project=chromium e2e/dashboard-functionality.spec.ts`
2. Confirm:
   - login → dashboard navigation completes
   - theme toggle button is found and menu items `Light`, `Dark`, `System` appear
   - selecting `Dark` updates `html` class accordingly

## Notes / Links (full URLs only)

- [Playwright `page.goto` navigation timing](https://playwright.dev/docs/api/class-page#page-goto)
- [WAI-ARIA landmark roles (banner)](https://www.w3.org/WAI/ARIA/apg/practices/landmark-regions/)

## Resolution Summary

- Fixed missing/undiscoverable `banner` landmark by removing the global `<main>` wrapper in the root layout (nested `<main>` prevents descendant `<header>` from mapping to `role="banner"`).
- Stabilized Chromium navigation by using `page.goto(..., { waitUntil: "domcontentloaded" })` for `/dashboard` navigations in the spec (avoids flakes when `load` is delayed).
- Prevented dashboard profile navigation from redirecting to login in E2E by initializing the auth store from `/auth/me` on the profile page before enforcing client-side redirects.

## Files Changed

- `src/app/layout.tsx` — replaced global `<main>` wrapper with a `<div>` to avoid nested main landmarks and allow dashboard header to become the `banner`.
- `src/app/dashboard/profile/page.tsx` — initialize auth store via `/auth/me` (cookie-based SSR session) before redirecting unauth users.
- `e2e/dashboard-functionality.spec.ts` — use `waitUntil: "domcontentloaded"` for `/dashboard` navigations; added a hydration-ready wait in the user-nav test.
- `src/app/dashboard/profile/__tests__/profile-page.test.tsx` — updated auth store mock to include `initialize`.
- `src/features/profile/components/__tests__/profile-smoke.test.tsx` — updated auth store mock to include `initialize`.

## Browser Verification (Next DevTools MCP)

- Started dev server on `http://localhost:3000`.
- `browser_eval`:
  - Navigated to `http://localhost:3000/login` and verified a single `main` landmark and a `banner` landmark in the accessibility snapshot after the layout change.
  - Navigated to `http://localhost:3000/dashboard` and confirmed redirect to `http://localhost:3000/login?next=%2Fdashboard` when unauthenticated (expected).
  - `nextjs_call:get_errors` reported no runtime errors.
- Stopped the dev server before running Playwright E2E (avoids `.next/dev/lock` conflicts).

## Command Evidence

- `pnpm exec playwright test --project=chromium e2e/dashboard-functionality.spec.ts` → **PASS** (8 passed)
- `pnpm biome:fix` → **PASS**
- `pnpm type-check` → **PASS**
- `pnpm test:affected` → **PASS**

## Extra References (full URLs only)

- [Next.js project structure / layout conventions](https://nextjs.org/docs/app/getting-started/project-structure)
