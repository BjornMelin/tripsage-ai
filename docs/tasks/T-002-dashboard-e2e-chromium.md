# T-002 — Fix Chromium E2E failures (dashboard load + theme toggle banner)

## Meta

- ID: `T-002`
- Priority: `P0`
- Status: `UNCLAIMED`
- Owner: `-`
- Depends on: `T-001`

## Problem

Chromium E2E failures in `e2e/dashboard-functionality.spec.ts`:

1. `dashboard page renders correctly after authentication` times out on `page.goto("/dashboard")` waiting for `"load"` even though the dashboard content is visible in the snapshot.
2. `theme toggle works` times out locating the theme toggle within `getByRole("banner")`, implying the header is not exposing a `banner` landmark (semantic `<header>` or `role="banner"`).

## Acceptance Criteria (black-box)

- [ ] `pnpm exec playwright test --project=chromium e2e/dashboard-functionality.spec.ts` passes.
- [ ] Theme toggle is discoverable via accessibility semantics (banner landmark preferred) and the theme menu items are reachable.

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

- Playwright navigation timing: https://playwright.dev/docs/api/class-page#page-goto
- WAI-ARIA landmark roles (banner): https://www.w3.org/WAI/ARIA/apg/practices/landmark-regions/

