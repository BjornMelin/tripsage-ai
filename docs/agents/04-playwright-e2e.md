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

- Install browsers if needed: `pnpm exec playwright install`
- Chromium-only (recommended local default): `pnpm exec playwright test --project=chromium`
- Full suite: `pnpm test:e2e`
- For code changes also run:
  - `pnpm biome:fix`
  - `pnpm type-check`
  - `pnpm test:affected`

## Local Gotcha

- Do not run `pnpm dev` while `pnpm test:e2e` is running; Next.js will refuse to start a second dev server due to `.next/dev/lock`.

## References (full URLs)

- Playwright test runner: https://playwright.dev/docs/test-intro

## When stuck

- Use `gh_grep.searchGitHub` to find stable selector patterns and CI-hardening techniques; record full URLs in the task file.
