# Agent Prompt — Playwright E2E

Role: Implement deterministic Playwright flows for the v1.0.0 critical journey and keep them stable.

## Task Claiming (required)

- Choose a task from `docs/tasks/INDEX.md`, then edit its `docs/tasks/T-###-*.md` file:
  - Set Status to `CLAIMED`
  - Set Owner to your identifier

## Scope

- Add/repair Playwright tests under `e2e/` for:
  - landing → auth → primary workflow → settings → logout
- Prefer accessibility-driven selectors.
- Keep tests independent and fast.

## Verification

- Install browsers (fresh machine):
  - Chromium-only: `pnpm exec playwright install chromium`
  - All (chromium/firefox/webkit): `pnpm exec playwright install`
  - Linux deps (Ubuntu/WSL/CI): `pnpm exec playwright install-deps chromium` (or `pnpm exec playwright install --with-deps chromium`)
- Chromium-only (recommended local default): `pnpm test:e2e:chromium` (or `pnpm exec playwright test --project=chromium`)
- Full suite (all configured browsers): `pnpm test:e2e`
- For code changes also run:
  - `pnpm biome:fix`
  - `pnpm type-check`
  - `pnpm test:affected`

## Local Gotcha

- Do not run `pnpm dev` while `pnpm test:e2e` is running; Next.js will refuse to start a second dev server due to `.next/dev/lock`.

## pnpm Args Gotcha

- Avoid `pnpm test:e2e -- --project=chromium` — pnpm forwards args as `playwright test -- --project=chromium` (the extra `--` breaks Playwright option parsing). Use `pnpm test:e2e:chromium` or `pnpm exec playwright test --project=chromium` instead.

## References (full URLs)

- [Playwright test runner](https://playwright.dev/docs/test-intro)
- [Playwright browsers + deps install](https://playwright.dev/docs/browsers)
- [Playwright CLI](https://playwright.dev/docs/test-cli)
- [Playwright install (pnpm)](https://playwright.dev/docs/intro)

## When stuck

- Use `gh_grep.searchGitHub` to find stable selector patterns and CI-hardening techniques; record full URLs in the task file.
