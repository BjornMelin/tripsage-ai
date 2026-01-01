# T-003 — Make E2E runnable by default (browser installs/docs/config)

## Meta

- ID: `T-003`
- Priority: `P1`
- Status: `DONE`
- Owner: `codex-session-t003-a`
- Depends on: `-`

## Problem

`pnpm test:e2e` runs Playwright projects for `chromium`, `firefox`, and `webkit`. In a fresh environment, Firefox/WebKit browser executables may not be installed, causing immediate failures (even if Chromium is available).

Additionally, passing `--project=chromium` through `pnpm test:e2e` is unreliable because pnpm forwards args as `playwright test -- --project=chromium` (the extra `--` breaks Playwright option parsing; flags become file patterns).

## Chosen Option

- Option: **A (docs + script alias)**
- Rationale: Keep existing cross-browser coverage available (`pnpm test:e2e`), but make the default local path deterministic (Chromium-only) and avoid pnpm arg-forwarding surprises.

## Acceptance Criteria (black-box)

- [x] Docs clearly specify how to run Chromium-only E2E and how to install browsers.
- [x] `pnpm exec playwright test --project=chromium` is the documented Chromium-only command.
- [x] Either:
  - (A) `pnpm test:e2e` is documented as requiring `pnpm exec playwright install` first, or
  - (B) config is updated so local default runs Chromium-only unless explicitly opting into all browsers.

## Likely Files

- `playwright.config.ts`
- `docs/release/04-test-plan.md`
- `docs/agents/04-playwright-e2e.md`

## Changes Made

- Added `pnpm test:e2e:chromium` script to avoid pnpm arg-forwarding issues.
- Updated release + agent docs with:
  - Chromium-only default commands
  - browser install + Linux deps guidance
  - explicit warning about `pnpm test:e2e -- --project=chromium`

## Verification (commands)

- `pnpm exec playwright install chromium` (or `pnpm exec playwright install` for all browsers)
- `pnpm exec playwright test --project=chromium`
- `pnpm test:e2e:chromium`

## Playwright Verification Steps

1. Install browsers if needed: `pnpm exec playwright install chromium`
2. Run Chromium suite: `pnpm test:e2e:chromium` (or `pnpm exec playwright test --project=chromium`)
3. (Optional) Run full suite: `pnpm test:e2e`

## Evidence

### Phase A — Runtime MCP + browser baseline (2025-12-31)

- Dev server: `pnpm dev` (served on `http://localhost:3000`)
- Next DevTools MCP:
  - `next-devtools.init` (project root)
  - `nextjs_index` → discovered server on port `3000`
  - `nextjs_call:get_routes` → includes `/` and `/login`
  - `nextjs_call:get_logs` → `.next/dev/logs/next-development.log` (contained `✓ Ready in 833ms`)
  - `browser_eval` (chrome, headless):
    - `GET http://localhost:3000/` screenshot: `/tmp/playwright-mcp-output/1767221756890/page-2025-12-31T22-56-06-761Z.png`
    - `GET http://localhost:3000/login` screenshot: `/tmp/playwright-mcp-output/1767221756890/page-2025-12-31T22-56-18-249Z.png`
    - Console messages: HMR connected + React DevTools info; **no errors**
  - `nextjs_call:get_errors` → `No errors detected in 1 browser session(s).`

### Phase B — Playwright runs (dev server stopped)

- Repro of pnpm arg-forwarding trap:
  - Command: `pnpm test:e2e -- --project=chromium --help`
  - Observed: `playwright test -- --project=chromium --help` → `Error: No tests found.` (exit 1)
- Baseline run: `pnpm exec playwright test --project=chromium` → `16 passed, 1 skipped` (≈1.9m)
- Script alias run: `pnpm test:e2e:chromium` → `16 passed, 1 skipped` (≈1.8m)

## Notes / Links (full URLs only)

- [Playwright browsers install + deps](https://playwright.dev/docs/browsers)
- [Playwright CLI (`install`, `install-deps`, `--with-deps`)](https://playwright.dev/docs/test-cli)
- [Playwright install (pnpm)](https://playwright.dev/docs/intro)
- [Playwright test runner](https://playwright.dev/docs/test-intro)
- Real-world “Chromium-only by default” script patterns:
  - <https://github.com/tldraw/tldraw/blob/main/apps/dotcom/client/package.json>
  - <https://github.com/TanStack/router/blob/main/e2e/react-start/basic/package.json>
