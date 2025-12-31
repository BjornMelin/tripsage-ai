# T-003 — Make E2E runnable by default (browser installs/docs/config)

## Meta

- ID: `T-003`
- Priority: `P1`
- Status: `UNCLAIMED`
- Owner: `-`
- Depends on: `-`

## Problem

`pnpm test:e2e` runs Playwright projects for `chromium`, `firefox`, and `webkit`. In a fresh environment, Firefox/WebKit browser executables may not be installed, causing immediate failures (even if Chromium is available).

Additionally, passing `--project=chromium` through `pnpm test:e2e` is unreliable because the command becomes `playwright test -- --project=chromium` (options treated as file patterns).

## Acceptance Criteria (black-box)

- [ ] Docs clearly specify how to run Chromium-only E2E and how to install browsers.
- [ ] `pnpm exec playwright test --project=chromium` is the documented Chromium-only command.
- [ ] Either:
  - (A) `pnpm test:e2e` is documented as requiring `pnpm exec playwright install` first, or
  - (B) config is updated so local default runs Chromium-only unless explicitly opting into all browsers.

## Likely Files

- `playwright.config.ts`
- `docs/release/04-test-plan.md`
- `docs/agents/04-playwright-e2e.md`

## Verification (commands)

- `pnpm exec playwright install` (if choosing option A)
- `pnpm exec playwright test --project=chromium`

## Playwright Verification Steps

1. Install browsers if needed: `pnpm exec playwright install`
2. Run Chromium suite: `pnpm exec playwright test --project=chromium`
3. (Optional) Run full suite: `pnpm test:e2e`

## Notes / Links (full URLs only)

- Playwright browsers install: https://playwright.dev/docs/browsers

